"""
Tests for the ingestion parsers.
"""

import csv
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.ingestion.csv_parser import (
    AmexCsvParser,
    GenericCsvParser,
)
from app.ingestion.pdf_parser import RbcPdfParser
from app.ingestion.statement_router import StatementRouter


def _write_csv(path: str, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# AmexCsvParser
# ---------------------------------------------------------------------------


class TestAmexCsvParser:
    def test_can_handle_valid_amex_csv(self, tmp_path):
        p = tmp_path / "amex.csv"
        _write_csv(
            str(p),
            [
                {
                    "Date": "15 Jan 2024",
                    "Date Processed": "17 Jan 2024",
                    "Description": "STARBUCKS",
                    "Amount": "5.50",
                }
            ],
            ["Date", "Date Processed", "Description", "Amount"],
        )
        assert AmexCsvParser().can_handle(str(p))

    def test_cannot_handle_wrong_columns(self, tmp_path):
        p = tmp_path / "other.csv"
        _write_csv(
            str(p),
            [{"Date": "2024-01-15", "Memo": "test", "Value": "5"}],
            ["Date", "Memo", "Value"],
        )
        assert not AmexCsvParser().can_handle(str(p))

    def test_cannot_handle_pdf(self, tmp_path):
        p = tmp_path / "statement.pdf"
        p.write_bytes(b"")
        assert not AmexCsvParser().can_handle(str(p))

    def test_parse_normalises_dates_and_amount(self, tmp_path):
        p = tmp_path / "amex.csv"
        _write_csv(
            str(p),
            [
                {
                    "Date": "15 Jan 2024",
                    "Date Processed": "17 Jan 2024",
                    "Description": "TIM HORTONS",
                    "Amount": "5.50",
                },
                {
                    "Date": "20 Jan 2024",
                    "Date Processed": "22 Jan 2024",
                    "Description": "PAYMENT RECEIVED",
                    "Amount": "-200.00",
                },
            ],
            ["Date", "Date Processed", "Description", "Amount"],
        )
        rows = AmexCsvParser().parse(str(p))
        assert len(rows) == 2
        assert rows[0]["transaction_date"] == "2024-01-15"
        assert rows[0]["posting_date"] == "2024-01-17"
        assert rows[0]["description_raw"] == "TIM HORTONS"
        assert rows[0]["amount"] == 5.50
        assert rows[0]["institution"] == "Amex"
        assert rows[0]["currency"] == "CAD"
        # Payment is negative
        assert rows[1]["amount"] == -200.00

    def test_parse_institution_and_source_type(self, tmp_path):
        p = tmp_path / "amex_march.csv"
        _write_csv(
            str(p),
            [
                {
                    "Date": "01 Mar 2024",
                    "Date Processed": "03 Mar 2024",
                    "Description": "GROCERY",
                    "Amount": "42.00",
                }
            ],
            ["Date", "Date Processed", "Description", "Amount"],
        )
        rows = AmexCsvParser().parse(str(p))
        assert rows[0]["institution"] == "Amex"
        assert rows[0]["source_type"] == "credit_card"


# ---------------------------------------------------------------------------
# RbcPdfParser
# ---------------------------------------------------------------------------


def _make_rbc_line(text: str, x1: float = 300.0, bottom: float = 400.0) -> dict:
    return {"text": text, "x1": x1, "bottom": bottom}


def _mock_pdfplumber(lines: list[dict]):
    """Return a context-manager mock that yields a single PDF page with given lines."""
    mock_page = MagicMock()
    mock_page.extract_text_lines.return_value = lines
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_pdf)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


class TestRbcPdfParser:
    def test_can_handle_pdf(self, tmp_path):
        p = tmp_path / "statement.pdf"
        p.write_bytes(b"")
        assert RbcPdfParser().can_handle(str(p))

    def test_cannot_handle_csv(self, tmp_path):
        p = tmp_path / "data.csv"
        p.write_text("")
        assert not RbcPdfParser().can_handle(str(p))

    def test_parse_basic_transaction(self, tmp_path):
        # Filename: closing date 2023-03-17 → statement_year=2023, statement_month=3
        pdf_path = tmp_path / "Visa Statement-2423 2023-03-17.pdf"
        pdf_path.write_bytes(b"")

        lines = [_make_rbc_line("MAR 10 MAR 11 TIM HORTONS -$3.75")]

        with patch(
            "app.ingestion.pdf_parser.pdfplumber.open",
            return_value=_mock_pdfplumber(lines),
        ):
            rows = RbcPdfParser().parse(str(pdf_path))

        assert len(rows) == 1
        assert rows[0]["transaction_date"] == "2023-03-10"
        assert rows[0]["posting_date"] == "2023-03-11"
        assert rows[0]["description_raw"] == "TIM HORTONS"
        assert rows[0]["amount"] == -3.75
        assert rows[0]["institution"] == "RBC"
        assert rows[0]["currency"] == "CAD"
        assert rows[0]["source_type"] == "credit_card"

    def test_parse_cross_year_transaction(self, tmp_path):
        # Statement closes JAN 2023; a DEC transaction belongs to 2022
        pdf_path = tmp_path / "Visa Statement-2423 2023-01-17.pdf"
        pdf_path.write_bytes(b"")

        lines = [_make_rbc_line("DEC 15 DEC 16 COSTCO -$85.00")]

        with patch(
            "app.ingestion.pdf_parser.pdfplumber.open",
            return_value=_mock_pdfplumber(lines),
        ):
            rows = RbcPdfParser().parse(str(pdf_path))

        assert rows[0]["transaction_date"] == "2022-12-15"
        assert rows[0]["posting_date"] == "2022-12-16"

    def test_parse_skips_header_region_lines(self, tmp_path):
        # bottom <= 200 should be filtered out (header/footer region)
        pdf_path = tmp_path / "Visa Statement-2423 2023-03-17.pdf"
        pdf_path.write_bytes(b"")

        lines = [
            _make_rbc_line(
                "MAR 10 MAR 11 VALID TRANSACTION -$5.00", x1=300.0, bottom=400.0
            ),
            _make_rbc_line(
                "MAR 05 MAR 06 FOOTER NOISE -$1.00", x1=300.0, bottom=150.0
            ),  # filtered
        ]

        with patch(
            "app.ingestion.pdf_parser.pdfplumber.open",
            return_value=_mock_pdfplumber(lines),
        ):
            rows = RbcPdfParser().parse(str(pdf_path))

        assert len(rows) == 1
        assert rows[0]["description_raw"] == "VALID TRANSACTION"

    def test_parse_skips_right_column_lines(self, tmp_path):
        # x1 >= 350 should be filtered out (right summary column)
        pdf_path = tmp_path / "Visa Statement-2423 2023-03-17.pdf"
        pdf_path.write_bytes(b"")

        lines = [
            _make_rbc_line("MAR 10 MAR 11 REAL TXN -$5.00", x1=300.0, bottom=400.0),
            _make_rbc_line(
                "MAR 10 MAR 11 RIGHT COLUMN -$5.00", x1=360.0, bottom=400.0
            ),  # filtered
        ]

        with patch(
            "app.ingestion.pdf_parser.pdfplumber.open",
            return_value=_mock_pdfplumber(lines),
        ):
            rows = RbcPdfParser().parse(str(pdf_path))

        assert len(rows) == 1

    def test_parse_compact_month_day_format(self, tmp_path):
        # Handles 'FEB17' (no space between month and day)
        pdf_path = tmp_path / "Visa Statement-2423 2023-03-17.pdf"
        pdf_path.write_bytes(b"")

        lines = [_make_rbc_line("FEB17 FEB18 NETFLIX -$17.99")]

        with patch(
            "app.ingestion.pdf_parser.pdfplumber.open",
            return_value=_mock_pdfplumber(lines),
        ):
            rows = RbcPdfParser().parse(str(pdf_path))

        assert len(rows) == 1
        assert rows[0]["transaction_date"] == "2023-02-17"

    def test_parse_filename_fallback_on_bad_name(self, tmp_path):
        # Filename with no parseable date should not crash
        pdf_path = tmp_path / "statement.pdf"
        pdf_path.write_bytes(b"")

        lines = [_make_rbc_line("MAR 10 MAR 11 TEST -$1.00")]

        with patch(
            "app.ingestion.pdf_parser.pdfplumber.open",
            return_value=_mock_pdfplumber(lines),
        ):
            rows = RbcPdfParser().parse(str(pdf_path))
        # Just verify it doesn't raise and returns a row
        assert len(rows) == 1

    def test_parse_uses_source_name_for_statement_date(self, tmp_path):
        # Streamlit saves uploads to temporary names; parser should use original name.
        pdf_path = tmp_path / "tmp_upload.pdf"
        pdf_path.write_bytes(b"")

        lines = [_make_rbc_line("DEC 15 DEC 16 COSTCO -$85.00")]

        with patch(
            "app.ingestion.pdf_parser.pdfplumber.open",
            return_value=_mock_pdfplumber(lines),
        ):
            rows = RbcPdfParser().parse(
                str(pdf_path), source_name="Visa Statement-2423 2023-01-17.pdf"
            )

        assert rows[0]["transaction_date"] == "2022-12-15"
        assert rows[0]["posting_date"] == "2022-12-16"


# ---------------------------------------------------------------------------
# GenericCsvParser (retained from original suite)
# ---------------------------------------------------------------------------


class TestGenericCsvParser:
    def test_parse_minimal_csv(self, tmp_path):
        p = tmp_path / "generic.csv"
        _write_csv(
            str(p),
            [
                {
                    "date": "2024-03-01",
                    "description": "GROCERY STORE",
                    "amount": "-42.00",
                }
            ],
            ["date", "description", "amount"],
        )
        rows = GenericCsvParser().parse(str(p))
        assert len(rows) == 1
        assert rows[0]["description_raw"] == "GROCERY STORE"

    def test_raises_on_unrecognized_columns(self, tmp_path):
        p = tmp_path / "bad.csv"
        _write_csv(str(p), [{"foo": "bar"}], ["foo"])
        with pytest.raises(ValueError, match="could not identify"):
            GenericCsvParser().parse(str(p))


# ---------------------------------------------------------------------------
# StatementRouter
# ---------------------------------------------------------------------------


class TestStatementRouter:
    def test_routes_amex_csv(self, tmp_path):
        p = tmp_path / "amex.csv"
        _write_csv(
            str(p),
            [
                {
                    "Date": "15 Jan 2024",
                    "Date Processed": "17 Jan 2024",
                    "Description": "COSTCO",
                    "Amount": "55.00",
                }
            ],
            ["Date", "Date Processed", "Description", "Amount"],
        )
        rows = StatementRouter().parse(str(p))
        assert rows[0]["institution"] == "Amex"

    def test_routes_rbc_pdf(self, tmp_path):
        pdf_path = tmp_path / "Visa Statement-2423 2023-03-17.pdf"
        pdf_path.write_bytes(b"")

        lines = [_make_rbc_line("MAR 10 MAR 11 SHOPPERS -$12.00")]

        with patch(
            "app.ingestion.pdf_parser.pdfplumber.open",
            return_value=_mock_pdfplumber(lines),
        ):
            rows = StatementRouter().parse(str(pdf_path))

        assert rows[0]["institution"] == "RBC"

    def test_raises_for_unknown_type(self, tmp_path):
        p = tmp_path / "unknown.xlsx"
        p.write_text("dummy")
        with pytest.raises(ValueError, match="No parser found"):
            StatementRouter().parse(str(p))

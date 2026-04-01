"""
Tests for the ingestion parsers.
"""
import csv
import os
import tempfile
from pathlib import Path

import pytest

from app.ingestion.csv_parser import ChaseCsvParser, BoACsvParser, GenericCsvParser
from app.ingestion.statement_router import StatementRouter


def _write_csv(path: str, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class TestChaseCsvParser:
    def test_can_handle_valid_chase_csv(self, tmp_path):
        p = tmp_path / "chase.csv"
        _write_csv(
            str(p),
            [{"Transaction Date": "01/15/2024", "Post Date": "01/16/2024",
              "Description": "STARBUCKS", "Category": "Food", "Type": "Sale", "Amount": "-5.00"}],
            ["Transaction Date", "Post Date", "Description", "Category", "Type", "Amount"],
        )
        assert ChaseCsvParser().can_handle(str(p))

    def test_cannot_handle_wrong_columns(self, tmp_path):
        p = tmp_path / "other.csv"
        _write_csv(str(p), [{"Date": "2024-01-15", "Memo": "test", "Value": "5"}],
                   ["Date", "Memo", "Value"])
        assert not ChaseCsvParser().can_handle(str(p))

    def test_parse_returns_rows(self, tmp_path):
        p = tmp_path / "chase.csv"
        _write_csv(
            str(p),
            [
                {"Transaction Date": "01/15/2024", "Post Date": "01/16/2024",
                 "Description": "STARBUCKS #123", "Category": "Food", "Type": "Sale", "Amount": "-5.75"},
                {"Transaction Date": "01/20/2024", "Post Date": "01/21/2024",
                 "Description": "NETFLIX", "Category": "Entertainment", "Type": "Sale", "Amount": "-15.99"},
            ],
            ["Transaction Date", "Post Date", "Description", "Category", "Type", "Amount"],
        )
        rows = ChaseCsvParser().parse(str(p))
        assert len(rows) == 2
        assert rows[0]["institution"] == "Chase"
        assert rows[0]["description_raw"] == "STARBUCKS #123"
        assert float(rows[0]["amount"]) == -5.75


class TestGenericCsvParser:
    def test_parse_minimal_csv(self, tmp_path):
        p = tmp_path / "generic.csv"
        _write_csv(
            str(p),
            [{"date": "2024-03-01", "description": "GROCERY STORE", "amount": "-42.00"}],
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


class TestStatementRouter:
    def test_routes_chase_csv(self, tmp_path):
        p = tmp_path / "chase.csv"
        _write_csv(
            str(p),
            [{"Transaction Date": "01/15/2024", "Description": "TEST", "Amount": "-1.00"}],
            ["Transaction Date", "Description", "Amount"],
        )
        rows = StatementRouter().parse(str(p))
        assert rows[0]["institution"] == "Chase"

    def test_raises_for_unknown_type(self, tmp_path):
        p = tmp_path / "unknown.xlsx"
        p.write_text("dummy")
        with pytest.raises(ValueError, match="No parser found"):
            StatementRouter().parse(str(p))

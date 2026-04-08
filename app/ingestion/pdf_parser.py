import datetime
import logging
import re
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)

MONTHS = [
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
]

# Spatial thresholds for RBC statement body (excludes headers/footers/right column)
_PDF_X1_THRESHOLD = 350
_PDF_BOTTOM_THRESHOLD = 200

# RBC transaction lines: 'MON DD MON DD Description -$amount'
# Handles both 'FEB 17' (space-separated) and 'FEB17' (compact) month/day tokens.
_MONTH_ALT = "|".join(MONTHS)
_TXN_RE = re.compile(
    rf"^({_MONTH_ALT})\s*(\d{{1,2}})\s+({_MONTH_ALT})\s*(\d{{1,2}})\s+(.*?)\s+(-?\$[\d,]+\.\d{{2}})\s*$",
    re.IGNORECASE,
)


def _resolve_year(month_abbr: str, statement_year: int, statement_month: int) -> int:
    """
    If the transaction month is later than the statement closing month, the
    transaction belongs to the prior year (e.g. a DEC entry on a JAN statement).
    """
    txn_month = MONTHS.index(month_abbr.upper()) + 1
    return statement_year if txn_month <= statement_month else statement_year - 1


def _format_date(month_abbr: str, day: int, year: int) -> str:
    month = MONTHS.index(month_abbr.upper()) + 1
    return f"{year}-{month:02d}-{day:02d}"


class RbcPdfParser:
    """
    Parses RBC Visa PDF statements using pdfplumber.

    Transaction lines follow the format:
        MON DD  MON DD  Description  -$Amount
    where the first date is the transaction date and the second is the posting date.

    Year inference: extracted from the filename suffix, expected to be 'YYYY-MM-DD'
    (e.g. 'Visa Statement-2423 2022-01-17.pdf'). Transactions whose month falls
    after the statement closing month are assigned to the prior year, handling
    Dec-to-Jan rollovers correctly.

    Spatial filtering (x1 < 350, bottom > 200) restricts extraction to the
    transaction body, skipping page headers, footers, and the right-side summary
    column that pdfplumber would otherwise include.
    """

    def can_handle(self, file_path: str) -> bool:
        return file_path.lower().endswith(".pdf")

    def parse(self, file_path: str, source_name: str | None = None) -> list[dict]:
        pdf_path = Path(file_path)
        file_name = Path(source_name).stem if source_name else pdf_path.stem

        statement_year, statement_month = self._extract_statement_date(
            pdf_path, source_name
        )

        lines = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                lines.extend(page.extract_text_lines(y_tolerance=0))

        transaction_texts = [
            line["text"]
            for line in lines
            if (
                line.get("x1", float("inf")) < _PDF_X1_THRESHOLD
                and line.get("bottom", float("inf")) > _PDF_BOTTOM_THRESHOLD
                and "$" in line.get("text", "")
                and any(line.get("text", "").upper().startswith(m) for m in MONTHS)
            )
        ]

        rows = []
        for text in transaction_texts:
            match = _TXN_RE.match(text)
            if not match:
                continue
            date_mon, date_day, dp_mon, dp_day, description, amount_str = match.groups()
            date_year = _resolve_year(date_mon, statement_year, statement_month)
            dp_year = _resolve_year(dp_mon, statement_year, statement_month)
            # Convert '$12.34' / '-$12.34' to float
            amount = float(amount_str.replace("$", "").replace(",", ""))
            rows.append(
                {
                    "transaction_date": _format_date(
                        date_mon, int(date_day), date_year
                    ),
                    "posting_date": _format_date(dp_mon, int(dp_day), dp_year),
                    "description_raw": description.strip(),
                    "amount": amount,
                    "institution": "RBC",
                    "source_type": "credit_card",
                    "account_name": file_name,
                    "statement_id": file_name,
                    "currency": "CAD",
                }
            )

        logger.info("RbcPdfParser: parsed %d rows from %s", len(rows), file_path)
        return rows

    def _extract_statement_date(
        self, pdf_path: Path, source_name: str | None = None
    ) -> tuple[int, int]:
        """
        Pull closing year and month from the filename.
        Expects the last space-delimited token in the stem to be 'YYYY-MM-DD'.
        Falls back to today's year/month if parsing fails.
        """
        try:
            name_stem = Path(source_name).stem if source_name else pdf_path.stem
            date_part = name_stem.split(" ")[-1]  # e.g. '2022-01-17'
            parts = date_part.split("-")
            return int(parts[0]), int(parts[1])
        except (IndexError, ValueError):
            logger.warning(
                "RbcPdfParser: could not parse statement date from filename %r; "
                "defaulting to current year/month",
                source_name or pdf_path.name,
            )
            today = datetime.date.today()
            return today.year, today.month

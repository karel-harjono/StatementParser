import re
import logging
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)

# Matches lines like: 01/15/2024  STARBUCKS #12345  -5.75
_TX_LINE = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4})\s+(.+?)\s+([-]?\$?[\d,]+\.\d{2})\s*$"
)


class AmexPdfParser:
    """
    Parses American Express PDF statements using pdfplumber.
    Extracts lines that match a date + description + amount pattern.
    """

    def can_handle(self, file_path: str) -> bool:
        return file_path.lower().endswith(".pdf")

    def parse(self, file_path: str) -> list[dict]:
        rows = []
        file_name = Path(file_path).stem

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                for line in text.splitlines():
                    match = _TX_LINE.match(line.strip())
                    if match:
                        date_str, description, amount_str = match.groups()
                        amount_clean = amount_str.replace("$", "").replace(",", "")
                        rows.append({
                            "transaction_date": date_str,
                            "posting_date": None,
                            "description_raw": description.strip(),
                            "amount": float(amount_clean),
                            "institution": "Amex",
                            "source_type": "credit_card",
                            "account_name": file_name,
                            "statement_id": file_name,
                            "currency": "USD",
                        })

        logger.info("AmexPdfParser: parsed %d rows from %s", len(rows), file_path)
        return rows

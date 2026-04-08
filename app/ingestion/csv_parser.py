import logging
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class BaseStatementParser(ABC):
    @abstractmethod
    def can_handle(self, file_path: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse(self, file_path: str, source_name: str | None = None) -> list[dict]:
        raise NotImplementedError


class AmexCsvParser(BaseStatementParser):
    """
    Handles American Express CSV exports.

    Amex statements are downloaded as CSV (not PDF). The expected columns are:
        Date, Date Processed, Description, Amount
    Dates are in 'DD Mon YYYY' format (e.g. '15 Jan 2024').
    Amount is a signed float: positive = charge, negative = payment/credit.
    """

    REQUIRED_COLUMNS = {"Date", "Date Processed", "Description", "Amount"}

    def can_handle(self, file_path: str) -> bool:
        if not file_path.lower().endswith(".csv"):
            return False
        try:
            df = pd.read_csv(file_path, nrows=1)
            return self.REQUIRED_COLUMNS.issubset(set(df.columns))
        except Exception:
            return False

    def parse(self, file_path: str, source_name: str | None = None) -> list[dict]:
        df = pd.read_csv(file_path)
        file_name = Path(source_name).stem if source_name else Path(file_path).stem
        rows = []
        for _, row in df.iterrows():
            transaction_date = pd.to_datetime(
                row.get("Date", ""), format="%d %b %Y", errors="coerce"
            )
            posting_date = pd.to_datetime(
                row.get("Date Processed", ""), format="%d %b %Y", errors="coerce"
            )
            rows.append(
                {
                    "transaction_date": transaction_date.strftime("%Y-%m-%d")
                    if pd.notna(transaction_date)
                    else None,
                    "posting_date": posting_date.strftime("%Y-%m-%d")
                    if pd.notna(posting_date)
                    else None,
                    "description_raw": str(row.get("Description", "")),
                    "amount": float(row.get("Amount", 0)),
                    "institution": "Amex",
                    "source_type": "credit_card",
                    "account_name": file_name,
                    "statement_id": file_name,
                    "currency": "CAD",
                }
            )
        logger.info("AmexCsvParser: parsed %d rows from %s", len(rows), file_path)
        return rows


class GenericCsvParser(BaseStatementParser):
    """
    Fallback CSV parser.  Tries to auto-detect date, description, and amount
    columns by name (case-insensitive).
    """

    DATE_ALIASES = ["date", "transaction date", "trans date", "txn date"]
    DESC_ALIASES = ["description", "memo", "narrative", "details", "payee"]
    AMOUNT_ALIASES = ["amount", "debit", "credit", "transaction amount"]

    def can_handle(self, file_path: str) -> bool:
        return file_path.lower().endswith(".csv")

    def parse(self, file_path: str, source_name: str | None = None) -> list[dict]:
        df = pd.read_csv(file_path)
        lower_cols = {c.lower(): c for c in df.columns}

        date_col = self._find_col(lower_cols, self.DATE_ALIASES)
        desc_col = self._find_col(lower_cols, self.DESC_ALIASES)
        amount_col = self._find_col(lower_cols, self.AMOUNT_ALIASES)

        if not all([date_col, desc_col, amount_col]):
            raise ValueError(
                f"GenericCsvParser could not identify required columns in {file_path}. "
                f"Found: {list(df.columns)}"
            )

        file_name = Path(source_name).stem if source_name else Path(file_path).stem
        rows = []
        for _, row in df.iterrows():
            rows.append(
                {
                    "transaction_date": row[date_col],  # type: ignore
                    "posting_date": None,
                    "description_raw": str(row[desc_col]),  # type: ignore
                    "amount": row[amount_col],  # type: ignore
                    "institution": "Unknown",
                    "source_type": "bank",
                    "account_name": file_name,
                    "statement_id": file_name,
                    "currency": "USD",
                }
            )
        logger.info("GenericCsvParser: parsed %d rows from %s", len(rows), file_path)
        return rows

    def _find_col(self, lower_cols: dict[str, str], aliases: list[str]) -> str | None:
        for alias in aliases:
            if alias in lower_cols:
                return lower_cols[alias]
        return None

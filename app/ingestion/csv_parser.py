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
    def parse(self, file_path: str) -> list[dict]:
        raise NotImplementedError


class ChaseCsvParser(BaseStatementParser):
    """
    Handles Chase bank and credit card CSV exports.
    Expected columns: Transaction Date, Post Date, Description, Category, Type, Amount
    """

    REQUIRED_COLUMNS = {"Transaction Date", "Description", "Amount"}

    def can_handle(self, file_path: str) -> bool:
        if not file_path.lower().endswith(".csv"):
            return False
        try:
            df = pd.read_csv(file_path, nrows=1)
            return self.REQUIRED_COLUMNS.issubset(set(df.columns))
        except Exception:
            return False

    def parse(self, file_path: str) -> list[dict]:
        df = pd.read_csv(file_path)
        file_name = Path(file_path).stem
        rows = []
        for _, row in df.iterrows():
            rows.append({
                "transaction_date": row.get("Transaction Date", ""),
                "posting_date": row.get("Post Date"),
                "description_raw": str(row.get("Description", "")),
                "amount": row.get("Amount", 0),
                "institution": "Chase",
                "source_type": "credit_card",
                "account_name": file_name,
                "statement_id": file_name,
                "currency": "USD",
            })
        logger.info("ChaseCsvParser: parsed %d rows from %s", len(rows), file_path)
        return rows


class BoACsvParser(BaseStatementParser):
    """
    Handles Bank of America CSV exports.
    BoA prepends several header lines before the actual data; we skip 6 rows.
    Expected columns (after skip): Date, Description, Amount, Running Bal.
    """

    REQUIRED_COLUMNS = {"Date", "Description", "Amount"}

    def can_handle(self, file_path: str) -> bool:
        if not file_path.lower().endswith(".csv"):
            return False
        try:
            df = pd.read_csv(file_path, skiprows=6, nrows=1)
            return self.REQUIRED_COLUMNS.issubset(set(df.columns))
        except Exception:
            return False

    def parse(self, file_path: str) -> list[dict]:
        df = pd.read_csv(file_path, skiprows=6)
        file_name = Path(file_path).stem
        rows = []
        for _, row in df.iterrows():
            if pd.isna(row.get("Date")):
                continue
            rows.append({
                "transaction_date": row.get("Date", ""),
                "posting_date": None,
                "description_raw": str(row.get("Description", "")),
                "amount": row.get("Amount", 0),
                "institution": "Bank of America",
                "source_type": "bank",
                "account_name": file_name,
                "statement_id": file_name,
                "currency": "USD",
            })
        logger.info("BoACsvParser: parsed %d rows from %s", len(rows), file_path)
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

    def parse(self, file_path: str) -> list[dict]:
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

        file_name = Path(file_path).stem
        rows = []
        for _, row in df.iterrows():
            rows.append({
                "transaction_date": row[date_col],
                "posting_date": None,
                "description_raw": str(row[desc_col]),
                "amount": row[amount_col],
                "institution": "Unknown",
                "source_type": "bank",
                "account_name": file_name,
                "statement_id": file_name,
                "currency": "USD",
            })
        logger.info("GenericCsvParser: parsed %d rows from %s", len(rows), file_path)
        return rows

    def _find_col(self, lower_cols: dict[str, str], aliases: list[str]) -> str | None:
        for alias in aliases:
            if alias in lower_cols:
                return lower_cols[alias]
        return None

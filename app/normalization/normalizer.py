from decimal import Decimal, InvalidOperation
from datetime import date
from typing import Optional

from app.normalization.transaction_model import Transaction, make_hash_key
from app.normalization.cleaners import clean_description
from app.normalization.merchant_rules import extract_merchant
from app.utils.dates import safe_parse_date


class Normalizer:
    def normalize(self, raw: dict) -> Transaction:
        description_raw = str(raw.get("description_raw", raw.get("description", "")))
        description_clean = clean_description(description_raw)

        transaction_date = self._parse_date(
            raw.get("transaction_date", raw.get("date", ""))
        )
        posting_date = self._parse_date(raw.get("posting_date", raw.get("post_date")))
        amount = self._parse_amount(raw.get("amount", "0"))
        currency = str(raw.get("currency", "USD"))
        account_name = str(raw.get("account_name", ""))
        institution = str(raw.get("institution", ""))
        source_type = str(raw.get("source_type", "bank"))
        statement_id = str(raw.get("statement_id", ""))
        transaction_type = self._infer_transaction_type(
            amount, raw.get("transaction_type")
        )
        merchant = extract_merchant(description_clean)
        hash_key = make_hash_key(transaction_date, amount, description_clean, account_name)

        return Transaction(
            id=None,
            source_type=source_type,
            institution=institution,
            account_name=account_name,
            statement_id=statement_id,
            transaction_date=transaction_date,
            posting_date=posting_date,
            description_raw=description_raw,
            description_clean=description_clean,
            amount=amount,
            currency=currency,
            transaction_type=transaction_type,
            category=None,
            subcategory=None,
            confidence=None,
            categorization_method=None,
            review_status="pending",
            merchant=merchant,
            hash_key=hash_key,
        )

    def _parse_date(self, value) -> Optional[date]:
        if value is None:
            return None
        if isinstance(value, date):
            return value
        result = safe_parse_date(str(value))
        # Fall back to epoch rather than None so the dataclass always has a date
        if result is None:
            from datetime import date as _date
            return _date(1970, 1, 1)
        return result

    def _parse_amount(self, value) -> Decimal:
        if isinstance(value, Decimal):
            return value
        try:
            cleaned = str(value).replace(",", "").replace("$", "").strip()
            return Decimal(cleaned)
        except InvalidOperation:
            return Decimal("0")

    def _infer_transaction_type(self, amount: Decimal, explicit: Optional[str]) -> str:
        if explicit:
            return str(explicit).lower()
        if amount < 0:
            return "debit"
        if amount > 0:
            return "credit"
        return "unknown"

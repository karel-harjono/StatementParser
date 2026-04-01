import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class Transaction:
    id: Optional[int]
    source_type: str          # "bank" | "credit_card"
    institution: str          # "Chase", "Amex", etc.
    account_name: str
    statement_id: str
    transaction_date: date
    posting_date: Optional[date]
    description_raw: str
    description_clean: str
    amount: Decimal
    currency: str
    transaction_type: str     # "debit", "credit", "payment", "refund"
    category: Optional[str]
    subcategory: Optional[str]
    confidence: Optional[float]
    categorization_method: Optional[str]   # "rule", "model", "manual"
    review_status: str        # "pending", "reviewed", "approved"
    merchant: Optional[str]
    hash_key: str             # for deduping


def make_hash_key(
    transaction_date: date,
    amount: Decimal,
    description_clean: str,
    account_name: str,
) -> str:
    raw = f"{transaction_date}|{amount}|{description_clean}|{account_name}"
    return hashlib.sha256(raw.encode()).hexdigest()

"""
Tests for the normalization layer.
"""
from decimal import Decimal

import pytest

from app.normalization.normalizer import Normalizer
from app.normalization.transaction_model import make_hash_key
from app.normalization.cleaners import clean_description
from app.normalization.merchant_rules import extract_merchant


RAW_CHASE_ROW = {
    "transaction_date": "01/15/2024",
    "posting_date": "01/16/2024",
    "description_raw": "STARBUCKS #03456 CHICAGO IL",
    "amount": "-5.75",
    "institution": "Chase",
    "source_type": "credit_card",
    "account_name": "chase_jan_2024",
    "statement_id": "chase_jan_2024",
    "currency": "USD",
}


class TestNormalizer:
    def test_normalize_produces_transaction(self):
        tx = Normalizer().normalize(RAW_CHASE_ROW)
        assert tx.institution == "Chase"
        assert tx.amount == Decimal("-5.75")
        assert tx.transaction_type == "debit"
        assert tx.review_status == "pending"
        assert tx.currency == "USD"

    def test_hash_key_is_deterministic(self):
        tx1 = Normalizer().normalize(RAW_CHASE_ROW)
        tx2 = Normalizer().normalize(RAW_CHASE_ROW)
        assert tx1.hash_key == tx2.hash_key

    def test_hash_key_differs_for_different_amounts(self):
        row2 = {**RAW_CHASE_ROW, "amount": "-10.00"}
        tx1 = Normalizer().normalize(RAW_CHASE_ROW)
        tx2 = Normalizer().normalize(row2)
        assert tx1.hash_key != tx2.hash_key

    def test_positive_amount_is_credit(self):
        row = {**RAW_CHASE_ROW, "amount": "500.00", "description_raw": "PAYROLL"}
        tx = Normalizer().normalize(row)
        assert tx.transaction_type == "credit"


class TestCleaners:
    def test_uppercases_and_strips(self):
        assert clean_description("  starbucks  ") == "STARBUCKS"

    def test_removes_long_numbers(self):
        result = clean_description("STARBUCKS #123456789 CHICAGO")
        assert "123456789" not in result
        assert "STARBUCKS" in result


class TestMerchantRules:
    @pytest.mark.parametrize("desc,expected", [
        ("WHOLEFDS 1234 CHICAGO", "Whole Foods"),
        ("NETFLIX.COM MONTHLY", "Netflix"),
        ("UBER EATS ORDER", "Uber Eats"),
        ("STARBUCKS #03456", "Starbucks"),
        ("LYFT *RIDE SFO", "Lyft"),
    ])
    def test_known_merchants(self, desc, expected):
        assert extract_merchant(desc.upper()) == expected

    def test_unknown_returns_none(self):
        assert extract_merchant("RANDOM LOCAL SHOP 12345") is None

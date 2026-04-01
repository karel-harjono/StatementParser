"""
Tests for the full categorization pipeline.
"""
import pytest
from decimal import Decimal
from datetime import date

from app.categorization.categorizer import Categorizer
from app.categorization.rules_engine import RulesEngine, CategoryRule
from app.normalization.transaction_model import Transaction


def _make_tx(description: str, amount: float = -10.0) -> Transaction:
    return Transaction(
        id=None,
        source_type="credit_card",
        institution="Chase",
        account_name="test",
        statement_id="test",
        transaction_date=date(2024, 1, 15),
        posting_date=None,
        description_raw=description,
        description_clean=description.upper(),
        amount=Decimal(str(amount)),
        currency="USD",
        transaction_type="debit",
        category=None,
        subcategory=None,
        confidence=None,
        categorization_method=None,
        review_status="pending",
        merchant=None,
        hash_key="abc123",
    )


class TestCategorizer:
    def setup_method(self):
        self.categorizer = Categorizer()

    def test_rule_match_returns_high_confidence(self):
        tx = _make_tx("STARBUCKS #03456 CHICAGO")
        category, confidence, method = self.categorizer.categorize(tx)
        assert category == "Dining"
        assert confidence == 0.99
        assert method == "rule"

    def test_no_match_falls_to_other(self):
        tx = _make_tx("RANDOM UNKNOWN SHOP 999")
        category, confidence, method = self.categorizer.categorize(tx)
        assert category == "Other"
        assert confidence == 0.0
        assert method == "needs_review"

    def test_netflix_is_subscriptions(self):
        tx = _make_tx("NETFLIX.COM")
        category, _, _ = self.categorizer.categorize(tx)
        assert category == "Subscriptions"

    def test_payroll_is_income(self):
        tx = _make_tx("DIRECT DEPOSIT PAYROLL", amount=3000.0)
        category, _, method = self.categorizer.categorize(tx)
        assert category == "Income"
        assert method == "rule"

    def test_custom_rules_override_default(self):
        custom_rules = [
            CategoryRule(None, "CUSTOM_SHOP", "contains", "Shopping", "Custom", 99, True),
        ]
        categorizer = Categorizer(rules_engine=RulesEngine(custom_rules))
        tx = _make_tx("CUSTOM_SHOP ONLINE")
        category, _, _ = categorizer.categorize(tx)
        assert category == "Shopping"

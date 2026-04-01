"""
Tests for the rules engine.
"""
import pytest

from app.categorization.rules_engine import RulesEngine, CategoryRule, DEFAULT_RULES


class TestRulesEngine:
    def setup_method(self):
        self.engine = RulesEngine(DEFAULT_RULES)

    @pytest.mark.parametrize("desc,expected_cat", [
        ("WHOLEFDS 001 CHICAGO IL", "Groceries"),
        ("TRADER JOES 42", "Groceries"),
        ("STARBUCKS #03456", "Dining"),
        ("NETFLIX.COM", "Subscriptions"),
        ("UBER EATS ORDER", "Dining"),
        ("UBER *TRIP", "Transport"),
        ("LYFT *RIDE SFO", "Transport"),
        ("SPOTIFY MONTHLY", "Subscriptions"),
        ("WALGREENS #1234", "Healthcare"),
        ("DIRECT DEPOSIT PAYROLL", "Income"),
        ("ZELLE PAYMENT", "Transfers"),
        ("ANNUAL FEE CHARGED", "Fees"),
    ])
    def test_known_patterns(self, desc, expected_cat):
        rule = self.engine.match(desc.upper())
        assert rule is not None, f"No rule matched {desc!r}"
        assert rule.category == expected_cat, (
            f"Expected {expected_cat!r}, got {rule.category!r} for {desc!r}"
        )

    def test_no_match_returns_none(self):
        assert self.engine.match("RANDOM UNKNOWN MERCHANT XYZ") is None

    def test_higher_priority_wins(self):
        # "UBER EATS" should match Dining (priority 25) not Transport Uber (priority 15)
        rule = self.engine.match("UBER EATS ORDER 12345")
        assert rule.category == "Dining"

    def test_inactive_rule_skipped(self):
        rules = [
            CategoryRule(None, "TESTMERCH", "contains", "Shopping", None, 10, False),
        ]
        engine = RulesEngine(rules)
        assert engine.match("TESTMERCH ONLINE") is None

    def test_add_rule(self):
        self.engine.add_rule(
            CategoryRule(None, "NEWSHOP", "contains", "Shopping", None, 5, True)
        )
        rule = self.engine.match("NEWSHOP PURCHASE")
        assert rule is not None
        assert rule.category == "Shopping"

    def test_exact_match(self):
        engine = RulesEngine([
            CategoryRule(None, "RENT", "exact", "Rent", None, 10, True)
        ])
        assert engine.match("RENT") is not None
        assert engine.match("RENT PAYMENT") is None   # not exact

    def test_regex_match(self):
        engine = RulesEngine([
            CategoryRule(None, r"PG&E|COMCAST", "regex", "Utilities", None, 10, True)
        ])
        assert engine.match("PG&E BILL") is not None
        assert engine.match("COMCAST MONTHLY") is not None
        assert engine.match("CHASECARD") is None

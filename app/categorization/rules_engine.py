import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CategoryRule:
    id: int | None
    pattern: str
    match_type: str   # "exact" | "contains" | "regex"
    category: str
    subcategory: str | None
    priority: int
    active: bool


DEFAULT_RULES: list[CategoryRule] = [
    # Groceries
    CategoryRule(None, "WHOLEFDS", "contains", "Groceries", None, 10, True),
    CategoryRule(None, "WHOLE FOODS", "contains", "Groceries", None, 10, True),
    CategoryRule(None, "TRADER JOE", "contains", "Groceries", None, 10, True),
    CategoryRule(None, "SAFEWAY", "contains", "Groceries", None, 10, True),
    CategoryRule(None, "KROGER", "contains", "Groceries", None, 10, True),
    CategoryRule(None, "COSTCO", "contains", "Groceries", None, 10, True),
    CategoryRule(None, "ALDI", "contains", "Groceries", None, 10, True),
    CategoryRule(None, "SPROUTS", "contains", "Groceries", None, 10, True),
    # Dining – delivery (check before generic Uber)
    CategoryRule(None, "UBER EATS", "contains", "Dining", "Delivery", 25, True),
    CategoryRule(None, "UBEREATS", "contains", "Dining", "Delivery", 25, True),
    CategoryRule(None, "DOORDASH", "contains", "Dining", "Delivery", 20, True),
    CategoryRule(None, "GRUBHUB", "contains", "Dining", "Delivery", 20, True),
    CategoryRule(None, "POSTMATES", "contains", "Dining", "Delivery", 20, True),
    # Dining – coffee
    CategoryRule(None, "STARBUCKS", "contains", "Dining", "Coffee", 10, True),
    CategoryRule(None, "DUNKIN", "contains", "Dining", "Coffee", 10, True),
    # Transport
    CategoryRule(None, "UBER", "contains", "Transport", "Rideshare", 15, True),
    CategoryRule(None, "LYFT", "contains", "Transport", "Rideshare", 15, True),
    CategoryRule(None, r"PARKING|PARKWHIZ|SPOTHERO", "regex", "Transport", "Parking", 15, True),
    CategoryRule(None, r"GAS|SHELL|CHEVRON|EXXON|BP |SUNOCO|CITGO", "regex", "Transport", "Gas", 15, True),
    CategoryRule(None, r"METRO|SUBWAY|TRANSIT|MUNI|CALTRAIN|BART|MTA", "regex", "Transport", "Transit", 15, True),
    # Subscriptions
    CategoryRule(None, "NETFLIX", "contains", "Subscriptions", "Streaming", 10, True),
    CategoryRule(None, "SPOTIFY", "contains", "Subscriptions", "Streaming", 10, True),
    CategoryRule(None, "HULU", "contains", "Subscriptions", "Streaming", 10, True),
    CategoryRule(None, "DISNEY", "contains", "Subscriptions", "Streaming", 10, True),
    CategoryRule(None, "APPLE", "contains", "Subscriptions", "Software", 5, True),
    CategoryRule(None, "AMAZON PRIME", "contains", "Subscriptions", None, 15, True),
    CategoryRule(None, r"GITHUB|DROPBOX|GOOGLE ONE|ICLOUD|SLACK|NOTION|ADOBE", "regex", "Subscriptions", "Software", 10, True),
    # Shopping
    CategoryRule(None, "AMAZON", "contains", "Shopping", None, 5, True),
    CategoryRule(None, "AMZN", "contains", "Shopping", None, 5, True),
    CategoryRule(None, "TARGET", "contains", "Shopping", None, 5, True),
    CategoryRule(None, "WALMART", "contains", "Shopping", None, 5, True),
    CategoryRule(None, "EBAY", "contains", "Shopping", None, 5, True),
    CategoryRule(None, "ETSY", "contains", "Shopping", None, 5, True),
    # Healthcare
    CategoryRule(None, "WALGREENS", "contains", "Healthcare", "Pharmacy", 10, True),
    CategoryRule(None, "CVS", "contains", "Healthcare", "Pharmacy", 10, True),
    CategoryRule(None, r"PHARMACY|RITE AID|DUANE READE", "regex", "Healthcare", "Pharmacy", 10, True),
    # Utilities
    CategoryRule(None, r"PG&E|CONEDISON|CON ED|NATIONAL GRID|AT&T|VERIZON|COMCAST|XFINITY|T-MOBILE|TMOBILE", "regex", "Utilities", None, 20, True),
    # Insurance
    CategoryRule(None, r"INSURANCE|GEICO|STATE FARM|ALLSTATE|PROGRESSIVE", "regex", "Insurance", None, 20, True),
    # Income
    CategoryRule(None, r"PAYROLL|DIRECT DEP|DIRECT DEPOSIT|SALARY|ACH DEPOSIT", "regex", "Income", "Payroll", 50, True),
    # Transfers
    CategoryRule(None, r"TRANSFER|ZELLE|VENMO|PAYPAL|CASH APP|CASHAPP", "regex", "Transfers", None, 30, True),
    # Fees & charges
    CategoryRule(None, r"ATM|CASH WITHDRAWAL|WITHDRAW", "regex", "Fees", "Cash", 20, True),
    CategoryRule(None, r"INTEREST CHARGE|ANNUAL FEE|LATE FEE|FOREIGN TRANSACTION|OVERDRAFT", "regex", "Fees", None, 25, True),
]


class RulesEngine:
    def __init__(self, rules: list[CategoryRule] | None = None):
        self.rules = sorted(rules or DEFAULT_RULES, key=lambda r: -r.priority)

    def match(self, description_clean: str) -> CategoryRule | None:
        text = description_clean.upper()
        for rule in self.rules:
            if not rule.active:
                continue
            try:
                if self._matches(rule, text):
                    return rule
            except re.error as exc:
                logger.warning("Invalid regex in rule %r: %s", rule.pattern, exc)
        return None

    def _matches(self, rule: CategoryRule, text: str) -> bool:
        if rule.match_type == "exact":
            return text == rule.pattern.upper()
        if rule.match_type == "contains":
            return rule.pattern.upper() in text
        if rule.match_type == "regex":
            return bool(re.search(rule.pattern, text))
        return False

    def add_rule(self, rule: CategoryRule) -> None:
        self.rules.append(rule)
        self.rules.sort(key=lambda r: -r.priority)

    def reload(self, rules: list[CategoryRule]) -> None:
        self.rules = sorted(rules, key=lambda r: -r.priority)

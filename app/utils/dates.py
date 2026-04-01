from datetime import date
from dateutil.parser import parse as dateutil_parse


def parse_date(value: str) -> date:
    return dateutil_parse(value).date()


def safe_parse_date(value: str) -> date | None:
    try:
        return parse_date(value)
    except (ValueError, TypeError, OverflowError):
        return None

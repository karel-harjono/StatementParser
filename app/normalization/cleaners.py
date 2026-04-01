import re

from app.utils.text import clean_text


def clean_description(raw: str) -> str:
    cleaned = clean_text(raw)
    # Remove long numeric sequences (card numbers, reference numbers)
    cleaned = re.sub(r"\b\d{5,}\b", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

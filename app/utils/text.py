import re


def clean_text(text: str) -> str:
    text = text.upper().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s#&/\-]", "", text)
    return text


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())

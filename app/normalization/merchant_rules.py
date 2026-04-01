from rapidfuzz import process, fuzz

MERCHANT_ALIASES: dict[str, str] = {
    "WHOLEFDS": "Whole Foods",
    "WHOLE FOODS": "Whole Foods",
    "TRADER JOE": "Trader Joe's",
    "SAFEWAY": "Safeway",
    "KROGER": "Kroger",
    "COSTCO": "Costco",
    "WALMART": "Walmart",
    "TARGET": "Target",
    "WALGREENS": "Walgreens",
    "CVS": "CVS Pharmacy",
    "UBEREATS": "Uber Eats",
    "UBER EATS": "Uber Eats",
    "DOORDASH": "DoorDash",
    "GRUBHUB": "GrubHub",
    "UBER": "Uber",
    "LYFT": "Lyft",
    "NETFLIX": "Netflix",
    "SPOTIFY": "Spotify",
    "HULU": "Hulu",
    "DISNEY PLUS": "Disney+",
    "AMAZON PRIME": "Amazon Prime",
    "AMAZON": "Amazon",
    "AMZN": "Amazon",
    "STARBUCKS": "Starbucks",
    "APPLE": "Apple",
}


def extract_merchant(description_clean: str) -> str | None:
    # Exact substring match first (fast path)
    for keyword, merchant in MERCHANT_ALIASES.items():
        if keyword in description_clean:
            return merchant

    # Fuzzy fallback for typos / slight variations
    result = process.extractOne(
        description_clean,
        MERCHANT_ALIASES.keys(),
        scorer=fuzz.partial_ratio,
        score_cutoff=88,
    )
    if result:
        return MERCHANT_ALIASES[result[0]]

    return None

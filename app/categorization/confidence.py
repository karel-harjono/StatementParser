from app.config import CONFIDENCE_AUTO_ACCEPT, CONFIDENCE_REVIEW_THRESHOLD


def determine_review_status(category: str, confidence: float) -> str:
    if confidence >= CONFIDENCE_AUTO_ACCEPT:
        return "approved"
    return "pending"

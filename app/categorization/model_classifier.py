from dataclasses import dataclass


@dataclass
class Prediction:
    category: str
    confidence: float


class ModelClassifier:
    """
    MVP stub. Returns low confidence to push unmatched transactions to the
    review queue.  Replace with TF-IDF + LogisticRegression once enough
    labeled data has been collected via manual review.
    """

    def predict(self, description_clean: str, amount: float = 0.0) -> Prediction:
        return Prediction(category="Other", confidence=0.0)

    def is_trained(self) -> bool:
        return False

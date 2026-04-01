from app.categorization.rules_engine import RulesEngine
from app.categorization.model_classifier import ModelClassifier
from app.normalization.transaction_model import Transaction


class Categorizer:
    def __init__(
        self,
        rules_engine: RulesEngine | None = None,
        model: ModelClassifier | None = None,
    ):
        self.rules_engine = rules_engine or RulesEngine()
        self.model = model or ModelClassifier()

    def categorize(self, tx: Transaction) -> tuple[str, float, str]:
        """
        Returns (category, confidence, method).
        method: "rule" | "model" | "needs_review"
        """
        rule = self.rules_engine.match(tx.description_clean)
        if rule:
            return rule.category, 0.99, "rule"

        if self.model.is_trained():
            pred = self.model.predict(tx.description_clean, float(tx.amount))
            if pred.confidence >= 0.80:
                return pred.category, pred.confidence, "model"

        return "Other", 0.0, "needs_review"

import logging

from app.storage.repositories import TransactionRepository
from app.categorization.categorizer import Categorizer
from app.config import CONFIDENCE_AUTO_ACCEPT

logger = logging.getLogger(__name__)


class RecategorizationService:
    """
    Re-runs the categorization pipeline over all non-manual transactions.
    Useful after adding new rules or retraining the model.
    """

    def __init__(
        self,
        repo: TransactionRepository | None = None,
        categorizer: Categorizer | None = None,
    ):
        self.repo = repo or TransactionRepository()
        self.categorizer = categorizer or Categorizer()

    def recategorize_all(self) -> int:
        transactions = self.repo.get_all()
        updated = 0
        for tx in transactions:
            if tx.categorization_method == "manual":
                continue
            category, confidence, method = self.categorizer.categorize(tx)
            review_status = "approved" if confidence >= CONFIDENCE_AUTO_ACCEPT else "pending"
            self.repo.update_category(tx.id, category, tx.subcategory, method, review_status)
            updated += 1

        logger.info("RecategorizationService: updated %d transactions", updated)
        return updated

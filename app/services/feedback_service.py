import logging

from app.storage.repositories import TransactionRepository, FeedbackRepository

logger = logging.getLogger(__name__)


class FeedbackService:
    def __init__(
        self,
        tx_repo: TransactionRepository | None = None,
        feedback_repo: FeedbackRepository | None = None,
    ):
        self.tx_repo = tx_repo or TransactionRepository()
        self.feedback_repo = feedback_repo or FeedbackRepository()

    def approve(self, tx_id: int, current_category: str | None) -> None:
        """Mark the current category as accepted by the user."""
        self.tx_repo.update_category(
            tx_id, current_category or "Other", None, "manual", "reviewed"
        )
        self.feedback_repo.save(tx_id, current_category, current_category or "Other", "user")
        logger.info("Transaction %d approved with category %s", tx_id, current_category)

    def recategorize(
        self,
        tx_id: int,
        old_category: str | None,
        new_category: str,
        subcategory: str | None = None,
    ) -> None:
        """Change a transaction's category and record feedback."""
        self.tx_repo.update_category(tx_id, new_category, subcategory, "manual", "reviewed")
        self.feedback_repo.save(tx_id, old_category, new_category, "user")
        logger.info(
            "Transaction %d recategorized: %s -> %s", tx_id, old_category, new_category
        )

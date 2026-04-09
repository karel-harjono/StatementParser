import logging

from app.storage.repositories import TransactionRepository, RulesRepository
from app.categorization.categorizer import Categorizer
from app.categorization.rules_engine import RulesEngine, DEFAULT_RULES
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
        rules_repo: RulesRepository | None = None,
    ):
        self.repo = repo or TransactionRepository()
        if categorizer is not None:
            self.categorizer = categorizer
        else:
            if rules_repo is not None:
                db_rules = rules_repo.get_all_active()
                merged = sorted(db_rules + DEFAULT_RULES, key=lambda r: -r.priority)
                self.categorizer = Categorizer(rules_engine=RulesEngine(merged))
            else:
                self.categorizer = Categorizer()

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

    def recategorize_pending(self) -> int:
        """
        Re-run rules against only pending/uncategorized transactions.
        Called after saving a new rule so the queue updates immediately.
        """
        transactions = self.repo.get_pending_review()
        updated = 0
        for tx in transactions:
            if tx.categorization_method == "manual":
                continue
            category, confidence, method = self.categorizer.categorize(tx)
            if category == tx.category:
                continue
            review_status = "approved" if confidence >= CONFIDENCE_AUTO_ACCEPT else "pending"
            self.repo.update_category(tx.id, category, tx.subcategory, method, review_status)
            updated += 1

        logger.info("RecategorizationService.recategorize_pending: updated %d transactions", updated)
        return updated

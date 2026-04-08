import logging
from pathlib import Path

from app.categorization.categorizer import Categorizer
from app.config import CONFIDENCE_AUTO_ACCEPT
from app.ingestion.statement_router import StatementRouter
from app.normalization.normalizer import Normalizer
from app.normalization.transaction_model import Transaction
from app.storage.db import init_db
from app.storage.repositories import StatementRepository, TransactionRepository

logger = logging.getLogger(__name__)


class ImportService:
    def __init__(
        self,
        parser_router: StatementRouter | None = None,
        normalizer: Normalizer | None = None,
        categorizer: Categorizer | None = None,
        repo: TransactionRepository | None = None,
        statement_repo: StatementRepository | None = None,
    ):
        self.parser_router = parser_router or StatementRouter()
        self.normalizer = normalizer or Normalizer()
        self.categorizer = categorizer or Categorizer()
        self.repo = repo or TransactionRepository()
        self.statement_repo = statement_repo or StatementRepository()

    def import_file(
        self, file_path: str, source_name: str | None = None
    ) -> list[Transaction]:
        init_db()

        file_name = source_name or Path(file_path).name
        logger.info("ImportService: starting import of %s", file_name)

        raw_rows = self.parser_router.parse(file_path, source_name=file_name)
        if not raw_rows:
            logger.warning("ImportService: no rows parsed from %s", file_name)
            return []

        institution = raw_rows[0].get("institution", "Unknown")
        source_type = raw_rows[0].get("source_type", "bank")
        self.statement_repo.save(file_name, institution, source_type)

        transactions = [self.normalizer.normalize(r) for r in raw_rows]

        saved: list[Transaction] = []
        skipped = 0
        for tx in transactions:
            if self.repo.exists_by_hash(tx.hash_key):
                skipped += 1
                continue

            category, confidence, method = self.categorizer.categorize(tx)
            tx.category = category
            tx.confidence = confidence
            tx.categorization_method = method
            tx.review_status = (
                "approved" if confidence >= CONFIDENCE_AUTO_ACCEPT else "pending"
            )

            saved.append(self.repo.save_transaction(tx))

        logger.info(
            "ImportService: saved %d transactions, skipped %d duplicates from %s",
            len(saved),
            skipped,
            file_name,
        )
        return saved

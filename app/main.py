"""
Application entry point.
Used for CLI testing and to confirm the pipeline is wired correctly.
"""
import logging

from app.utils.logging import setup_logging
from app.storage.db import init_db

setup_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("StatementParser starting up")
    init_db()
    logger.info("Database ready")


if __name__ == "__main__":
    main()

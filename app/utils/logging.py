import logging
from logging.handlers import RotatingFileHandler

from app.config import LOGS_DIR

_LOG_FILE = LOGS_DIR / "statementparser.log"
_FMT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB per file
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(_FMT))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(_FMT))

    logging.basicConfig(level=level, handlers=[file_handler, console_handler])

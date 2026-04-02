from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EXPORTS_DIR = DATA_DIR / "exports"
DB_PATH = DATA_DIR / "transactions.db"
LOGS_DIR = BASE_DIR / "logs"

# Confidence thresholds
CONFIDENCE_AUTO_ACCEPT: float = 0.85
CONFIDENCE_REVIEW_THRESHOLD: float = 0.50

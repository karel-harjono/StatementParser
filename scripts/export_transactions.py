#!/usr/bin/env python3
"""
CLI script: export transactions to a CSV file.

Usage:
    poetry run python scripts/export_transactions.py
    poetry run python scripts/export_transactions.py --output data/exports/my_export.csv
    poetry run python scripts/export_transactions.py --category Groceries
"""
import sys
import argparse
import csv
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.logging import setup_logging
from app.storage.db import init_db
from app.storage.repositories import TransactionRepository
from app.config import EXPORTS_DIR

setup_logging()
logger = logging.getLogger(__name__)

FIELDNAMES = [
    "id", "transaction_date", "institution", "account_name",
    "description_raw", "description_clean", "merchant", "amount",
    "currency", "transaction_type", "category", "subcategory",
    "confidence", "categorization_method", "review_status",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Export transactions to CSV.")
    parser.add_argument("--output", help="Output file path", default=None)
    parser.add_argument("--category", help="Filter by category", default=None)
    parser.add_argument("--status", help="Filter by review_status", default=None)
    args = parser.parse_args()

    init_db()
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    filters: dict = {}
    if args.category:
        filters["category"] = args.category
    if args.status:
        filters["review_status"] = args.status

    repo = TransactionRepository()
    transactions = repo.get_all(filters or None)

    if not transactions:
        print("No transactions found.", file=sys.stderr)
        sys.exit(0)

    output_path = args.output or str(
        EXPORTS_DIR / f"export_{datetime.now():%Y%m%d_%H%M%S}.csv"
    )
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for tx in transactions:
            writer.writerow({
                "id": tx.id,
                "transaction_date": tx.transaction_date,
                "institution": tx.institution,
                "account_name": tx.account_name,
                "description_raw": tx.description_raw,
                "description_clean": tx.description_clean,
                "merchant": tx.merchant or "",
                "amount": str(tx.amount),
                "currency": tx.currency,
                "transaction_type": tx.transaction_type,
                "category": tx.category or "",
                "subcategory": tx.subcategory or "",
                "confidence": tx.confidence or "",
                "categorization_method": tx.categorization_method or "",
                "review_status": tx.review_status,
            })

    print(f"Exported {len(transactions)} transactions to {output_path}.")


if __name__ == "__main__":
    main()

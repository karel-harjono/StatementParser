#!/usr/bin/env python3
"""
CLI script: import a statement file into the database.

Usage:
    poetry run python scripts/import_statement.py path/to/statement.csv
    poetry run python scripts/import_statement.py path/to/amex.pdf
"""
import sys
import argparse
import logging
from pathlib import Path

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.logging import setup_logging
from app.services.import_service import ImportService

setup_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a bank/card statement.")
    parser.add_argument("file", help="Path to the statement file (CSV or PDF)")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: file not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    svc = ImportService()
    saved = svc.import_file(str(file_path))
    print(f"Imported {len(saved)} new transactions from {file_path.name}.")


if __name__ == "__main__":
    main()

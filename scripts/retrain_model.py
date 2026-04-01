#!/usr/bin/env python3
"""
CLI script: retrain the ML classifier using manually reviewed transactions.

This is a placeholder for after enough labeled data has been collected via
the review queue.  Implement with TF-IDF + LogisticRegression from scikit-learn.

Usage:
    poetry run python scripts/retrain_model.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.logging import setup_logging
from app.storage.db import init_db
from app.storage.repositories import TransactionRepository

setup_logging()


def main() -> None:
    init_db()
    repo = TransactionRepository()
    reviewed = repo.get_all({"review_status": "reviewed"})

    print(f"Found {len(reviewed)} manually reviewed transactions.")

    if len(reviewed) < 50:
        print(
            "Not enough labeled data to train a reliable model. "
            "Continue reviewing transactions in the UI and run this script again later."
        )
        sys.exit(0)

    # TODO: implement TF-IDF + LogisticRegression training
    # from sklearn.feature_extraction.text import TfidfVectorizer
    # from sklearn.linear_model import LogisticRegression
    # from sklearn.pipeline import Pipeline
    # import joblib
    #
    # X = [tx.description_clean for tx in reviewed]
    # y = [tx.category for tx in reviewed]
    # pipeline = Pipeline([("tfidf", TfidfVectorizer()), ("clf", LogisticRegression())])
    # pipeline.fit(X, y)
    # joblib.dump(pipeline, "models/trained/classifier.joblib")
    # print("Model saved to models/trained/classifier.joblib")

    print("Retraining not yet implemented. See TODO in this script.")


if __name__ == "__main__":
    main()

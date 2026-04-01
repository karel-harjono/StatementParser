# StatementParser


bank_categorizer/
├─ app/
│  ├─ __init__.py
│  ├─ config.py
│  ├─ main.py
│  │
│  ├─ ingestion/
│  │  ├─ __init__.py
│  │  ├─ pdf_parser.py
│  │  ├─ csv_parser.py
│  │  ├─ ocr_fallback.py
│  │  └─ statement_router.py
│  │
│  ├─ normalization/
│  │  ├─ __init__.py
│  │  ├─ cleaners.py
│  │  ├─ merchant_rules.py
│  │  ├─ transaction_model.py
│  │  └─ normalizer.py
│  │
│  ├─ categorization/
│  │  ├─ __init__.py
│  │  ├─ categories.py
│  │  ├─ rules_engine.py
│  │  ├─ model_classifier.py
│  │  ├─ confidence.py
│  │  └─ categorizer.py
│  │
│  ├─ storage/
│  │  ├─ __init__.py
│  │  ├─ db.py
│  │  ├─ repositories.py
│  │  └─ schema.sql
│  │
│  ├─ services/
│  │  ├─ __init__.py
│  │  ├─ import_service.py
│  │  ├─ recategorization_service.py
│  │  └─ feedback_service.py
│  │
│  ├─ ui/
│  │  ├─ streamlit_app.py
│  │  ├─ pages/
│  │  │  ├─ 1_review_queue.py
│  │  │  ├─ 2_transactions.py
│  │  │  ├─ 3_rules_manager.py
│  │  │  └─ 4_reports.py
│  │  └─ components/
│  │     ├─ transaction_table.py
│  │     └─ category_editor.py
│  │
│  └─ utils/
│     ├─ logging.py
│     ├─ dates.py
│     └─ text.py
│
├─ data/
│  ├─ raw/
│  ├─ processed/
│  └─ exports/
│
├─ models/
│  ├─ trained/
│  └─ artifacts/
│
├─ tests/
│  ├─ test_parsers.py
│  ├─ test_normalizer.py
│  ├─ test_rules_engine.py
│  └─ test_categorizer.py
│
├─ scripts/
│  ├─ import_statement.py
│  ├─ retrain_model.py
│  └─ export_transactions.py
│
├─ pyproject.toml
├─ README.md
└─ .env


## Core idea

Do not tie parsing, categorization, and UI together too early.

Keep them separate:

ingestion/ extracts transactions from raw files
normalization/ makes all banks/cards look the same
categorization/ decides category and confidence
storage/ saves everything
ui/ only reads and updates records

That separation makes the system much easier to debug.

## Canonical transaction schema

Everything should become one transaction model, regardless of source.

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

@dataclass
class Transaction:
    id: Optional[int]
    source_type: str          # "bank" | "credit_card"
    institution: str          # "Chase", "Amex", etc.
    account_name: str
    statement_id: str
    transaction_date: date
    posting_date: Optional[date]
    description_raw: str
    description_clean: str
    amount: Decimal
    currency: str
    transaction_type: str     # "debit", "credit", "payment", "refund"
    category: Optional[str]
    subcategory: Optional[str]
    confidence: Optional[float]
    categorization_method: Optional[str]   # "rule", "model", "manual"
    review_status: str        # "pending", "reviewed", "approved"
    merchant: Optional[str]
    hash_key: str             # for deduping

This is the most important design decision.

Parsing strategy

Bank statements and credit card statements are messy, so use adapters.

Example:
class BaseStatementParser:
    def can_handle(self, file_path: str) -> bool:
        raise NotImplementedError

    def parse(self, file_path: str) -> list[dict]:
        raise NotImplementedError
class ChaseCsvParser(BaseStatementParser):
    ...

class AmexPdfParser(BaseStatementParser):
    ...

class BoACsvParser(BaseStatementParser):
    ...

class StatementRouter:
    def __init__(self, parsers):
        self.parsers = parsers

    def parse(self, file_path: str):
        for parser in self.parsers:
            if parser.can_handle(file_path):
                return parser.parse(file_path)
        raise ValueError(f"No parser found for {file_path}")


## Categorization strategy

Use a 3-layer approach.

1. deterministic rules first

These are fast, transparent, and easy to fix.

Examples:

UBER → Transport
NETFLIX → Entertainment
WHOLEFDS, TRADER JOE, SAFEWAY → Groceries
2. ML/LLM classifier second

For transactions not matched by rules.

Input:

cleaned description
amount
institution
maybe historical merchant-category pairs

Output:

predicted category
confidence
3. fallback to review queue

If confidence is low, send to Streamlit.

Pseudo-flow:
def categorize(tx):
    rule_match = rules_engine.match(tx.description_clean)
    if rule_match:
        return rule_match.category, 0.99, "rule"

    pred = model.predict(tx)
    if pred.confidence >= 0.80:
        return pred.category, pred.confidence, "model"

    return "Other", pred.confidence, "needs_review"

## Categories design

Keep categories stable and small at first.

Example top-level categories:
CATEGORIES = [
    "Groceries",
    "Dining",
    "Transport",
    "Shopping",
    "Utilities",
    "Rent",
    "Mortgage",
    "Insurance",
    "Healthcare",
    "Travel",
    "Entertainment",
    "Subscriptions",
    "Income",
    "Transfers",
    "Fees",
    "Taxes",
    "Other",
]

## Storage

SQLite is a good first choice. It works well with Streamlit and local development.

Useful tables:

transactions
id
statement_id
institution
account_name
transaction_date
description_raw
description_clean
merchant
amount
category
subcategory
confidence
categorization_method
review_status
hash_key
category_rules
id
pattern
match_type
category
subcategory
priority
active
review_feedback
id
transaction_id
old_category
new_category
reviewed_by
reviewed_at
statements
id
file_name
institution
imported_at
source_type

This lets manual corrections become training data.

## Streamlit UI

The UI should focus on exception handling, not everything at once.

Good pages:

Review Queue

Show:

transactions with low confidence
transactions categorized as Other
uncategorized transactions

Actions:

approve suggested category
change category
create rule from selection
mark merchant alias
Transactions Explorer

Filter by:

date range
amount
category
institution
merchant
review status
Rules Manager

Let user:

add/edit/delete rules
test rules against sample descriptions
change rule priority
Reports

Basic summaries:

spend by month
spend by category
uncategorized count
top merchants

## Recommended app flow

Upload statement
  -> Detect parser
  -> Extract rows
  -> Normalize
  -> Deduplicate
  -> Apply rules
  -> Apply model
  -> Save results
  -> Show review queue in Streamlit
  -> User corrects category
  -> Save feedback
  -> Optionally create new rule / retrain model

Important product decisions
1. rules should override model

If a user explicitly maps a merchant, trust that over model output.

2. manual corrections are gold

Every manual correction should be stored for:

future rules
retraining
merchant alias mapping
3. confidence threshold should be tunable

Example:

>= 0.85: auto-accept
0.50–0.84: send to review
< 0.50: mark as Other
4. deduping matters

Statements often overlap or get re-imported.

Create a hash_key from:

date
amount
normalized description
account
Suggested technologies
parsing: pandas, pdfplumber, camelot or tabula-py for tables
validation/models: pydantic or dataclasses
DB: sqlite3 or SQLAlchemy
ML baseline: scikit-learn
UI: streamlit

For version 1, I would avoid overengineering with microservices, queues, or cloud deployment.

Practical module responsibilities
ingestion/

Only extract raw rows from files.

normalization/

Convert raw rows into your canonical transaction object.

categorization/rules_engine.py

Exact match, contains, regex, merchant aliases, priority ordering.

categorization/model_classifier.py

Can start with a simple TF-IDF + logistic regression model on cleaned descriptions.

services/import_service.py

Orchestrates the whole import pipeline.

services/feedback_service.py

Takes manual review decisions and updates records/rules/training data.

## Minimal MVP

Build this first:

CSV and one PDF parser
transaction normalization
rules-based categorization
fallback category = Other
Streamlit review queue
save manual corrections in SQLite

Then add:

confidence scoring
ML classifier
rule generation from manual corrections
retraining script
Example import service shape

class ImportService:
    def __init__(self, parser_router, normalizer, categorizer, repo):
        self.parser_router = parser_router
        self.normalizer = normalizer
        self.categorizer = categorizer
        self.repo = repo

    def import_file(self, file_path: str):
        raw_rows = self.parser_router.parse(file_path)
        transactions = [self.normalizer.normalize(r) for r in raw_rows]

        saved = []
        for tx in transactions:
            if self.repo.exists_by_hash(tx.hash_key):
                continue

            category, confidence, method = self.categorizer.categorize(tx)
            tx.category = category
            tx.confidence = confidence
            tx.categorization_method = method
            tx.review_status = "pending" if category == "Other" or confidence < 0.80 else "approved"

            saved.append(self.repo.save_transaction(tx))

        return saved
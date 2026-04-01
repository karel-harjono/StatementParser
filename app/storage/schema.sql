CREATE TABLE IF NOT EXISTS statements (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name   TEXT    NOT NULL,
    institution TEXT    NOT NULL,
    source_type TEXT    NOT NULL,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    statement_id          TEXT    NOT NULL,
    source_type           TEXT    NOT NULL,
    institution           TEXT    NOT NULL,
    account_name          TEXT    NOT NULL,
    transaction_date      DATE    NOT NULL,
    posting_date          DATE,
    description_raw       TEXT    NOT NULL,
    description_clean     TEXT    NOT NULL,
    merchant              TEXT,
    amount                TEXT    NOT NULL,
    currency              TEXT    NOT NULL DEFAULT 'USD',
    transaction_type      TEXT    NOT NULL,
    category              TEXT,
    subcategory           TEXT,
    confidence            REAL,
    categorization_method TEXT,
    review_status         TEXT    NOT NULL DEFAULT 'pending',
    hash_key              TEXT    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS category_rules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern     TEXT    NOT NULL,
    match_type  TEXT    NOT NULL,
    category    TEXT    NOT NULL,
    subcategory TEXT,
    priority    INTEGER NOT NULL DEFAULT 10,
    active      INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS review_feedback (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id),
    old_category   TEXT,
    new_category   TEXT    NOT NULL,
    reviewed_by    TEXT,
    reviewed_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

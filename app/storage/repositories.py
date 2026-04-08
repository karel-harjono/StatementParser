import sqlite3
import logging
from decimal import Decimal

from app.storage.db import get_connection
from app.normalization.transaction_model import Transaction
from app.categorization.rules_engine import CategoryRule
from dateutil.parser import parse as dateutil_parse

logger = logging.getLogger(__name__)


class TransactionRepository:
    def exists_by_hash(self, hash_key: str) -> bool:
        conn = get_connection()
        row = conn.execute(
            "SELECT 1 FROM transactions WHERE hash_key = ?", (hash_key,)
        ).fetchone()
        return row is not None

    def save_transaction(self, tx: Transaction) -> Transaction:
        conn = get_connection()
        with conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO transactions (
                    statement_id, source_type, institution, account_name,
                    transaction_date, posting_date, description_raw, description_clean,
                    merchant, amount, currency, transaction_type,
                    category, subcategory, confidence, categorization_method,
                    review_status, hash_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tx.statement_id,
                    tx.source_type,
                    tx.institution,
                    tx.account_name,
                    str(tx.transaction_date),
                    str(tx.posting_date) if tx.posting_date else None,
                    tx.description_raw,
                    tx.description_clean,
                    tx.merchant,
                    str(tx.amount),
                    tx.currency,
                    tx.transaction_type,
                    tx.category,
                    tx.subcategory,
                    tx.confidence,
                    tx.categorization_method,
                    tx.review_status,
                    tx.hash_key,
                ),
            )
            tx.id = cursor.lastrowid
        return tx

    def get_pending_review(self) -> list[Transaction]:
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT * FROM transactions
            WHERE review_status = 'pending'
               OR category = 'Other'
               OR category IS NULL
            ORDER BY transaction_date DESC
            """
        ).fetchall()
        return [self._row_to_tx(r) for r in rows]

    def get_all(self, filters: dict | None = None) -> list[Transaction]:
        conn = get_connection()
        sql = "SELECT * FROM transactions WHERE 1=1"
        params: list = []
        if filters:
            if filters.get("category"):
                sql += " AND category = ?"
                params.append(filters["category"])
            if filters.get("institution"):
                sql += " AND institution = ?"
                params.append(filters["institution"])
            if filters.get("review_status"):
                sql += " AND review_status = ?"
                params.append(filters["review_status"])
            if filters.get("date_from"):
                sql += " AND transaction_date >= ?"
                params.append(str(filters["date_from"]))
            if filters.get("date_to"):
                sql += " AND transaction_date <= ?"
                params.append(str(filters["date_to"]))
            if filters.get("merchant"):
                sql += " AND merchant LIKE ?"
                params.append(f"%{filters['merchant']}%")
        sql += " ORDER BY transaction_date DESC"
        rows = conn.execute(sql, params).fetchall()
        return [self._row_to_tx(r) for r in rows]

    def get_by_id(self, tx_id: int) -> Transaction | None:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM transactions WHERE id = ?", (tx_id,)
        ).fetchone()
        return self._row_to_tx(row) if row else None

    def update_category(
        self,
        tx_id: int,
        category: str,
        subcategory: str | None,
        method: str,
        review_status: str,
    ) -> None:
        conn = get_connection()
        with conn:
            conn.execute(
                """
                UPDATE transactions
                SET category = ?, subcategory = ?,
                    categorization_method = ?, review_status = ?
                WHERE id = ?
                """,
                (category, subcategory, method, review_status, tx_id),
            )

    def _row_to_tx(self, row: sqlite3.Row) -> Transaction:
        return Transaction(
            id=row["id"],
            source_type=row["source_type"],
            institution=row["institution"],
            account_name=row["account_name"],
            statement_id=row["statement_id"],
            transaction_date=dateutil_parse(str(row["transaction_date"])),
            posting_date=dateutil_parse(str(row["posting_date"])) if row["posting_date"] else None,
            description_raw=row["description_raw"],
            description_clean=row["description_clean"],
            amount=Decimal(row["amount"]),
            currency=row["currency"],
            transaction_type=row["transaction_type"],
            category=row["category"],
            subcategory=row["subcategory"],
            confidence=row["confidence"],
            categorization_method=row["categorization_method"],
            review_status=row["review_status"],
            merchant=row["merchant"],
            hash_key=row["hash_key"],
        )


class StatementRepository:
    def save(self, file_name: str, institution: str, source_type: str) -> int | None:
        conn = get_connection()
        with conn:
            cursor = conn.execute(
                "INSERT INTO statements (file_name, institution, source_type) VALUES (?, ?, ?)",
                (file_name, institution, source_type),
            )
            return cursor.lastrowid

    def get_all(self) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM statements ORDER BY imported_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


class RulesRepository:
    def get_all(self) -> list[CategoryRule]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM category_rules ORDER BY priority DESC"
        ).fetchall()
        return [self._row_to_rule(r) for r in rows]

    def get_all_active(self) -> list[CategoryRule]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM category_rules WHERE active = 1 ORDER BY priority DESC"
        ).fetchall()
        return [self._row_to_rule(r) for r in rows]

    def save(self, rule: CategoryRule) -> CategoryRule:
        conn = get_connection()
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO category_rules
                    (pattern, match_type, category, subcategory, priority, active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    rule.pattern,
                    rule.match_type,
                    rule.category,
                    rule.subcategory,
                    rule.priority,
                    int(rule.active),
                ),
            )
            rule.id = cursor.lastrowid
        return rule

    def delete(self, rule_id: int) -> None:
        conn = get_connection()
        with conn:
            conn.execute("DELETE FROM category_rules WHERE id = ?", (rule_id,))

    def toggle_active(self, rule_id: int, active: bool) -> None:
        conn = get_connection()
        with conn:
            conn.execute(
                "UPDATE category_rules SET active = ? WHERE id = ?",
                (int(active), rule_id),
            )

    def _row_to_rule(self, row: sqlite3.Row) -> CategoryRule:
        return CategoryRule(
            id=row["id"],
            pattern=row["pattern"],
            match_type=row["match_type"],
            category=row["category"],
            subcategory=row["subcategory"],
            priority=row["priority"],
            active=bool(row["active"]),
        )


class FeedbackRepository:
    def save(
        self,
        transaction_id: int,
        old_category: str | None,
        new_category: str,
        reviewed_by: str | None = None,
    ) -> None:
        conn = get_connection()
        with conn:
            conn.execute(
                """
                INSERT INTO review_feedback
                    (transaction_id, old_category, new_category, reviewed_by)
                VALUES (?, ?, ?, ?)
                """,
                (transaction_id, old_category, new_category, reviewed_by),
            )

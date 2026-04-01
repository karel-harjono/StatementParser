"""
Transactions Explorer – filter and browse all transactions.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st
from app.storage.db import init_db
from app.storage.repositories import TransactionRepository
from app.services.feedback_service import FeedbackService
from app.categorization.categories import CATEGORIES
from app.ui.components.transaction_table import render_transaction_table
from app.ui.components.category_editor import render_category_editor

init_db()

st.set_page_config(page_title="Transactions", layout="wide")
st.title("Transactions")

repo = TransactionRepository()
feedback_svc = FeedbackService()

# ── Sidebar filters ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")
    cat_filter = st.selectbox("Category", ["All"] + CATEGORIES)
    status_filter = st.selectbox(
        "Review Status", ["All", "pending", "reviewed", "approved"]
    )
    date_from = st.date_input("From date", value=None)
    date_to = st.date_input("To date", value=None)

filters: dict = {}
if cat_filter != "All":
    filters["category"] = cat_filter
if status_filter != "All":
    filters["review_status"] = status_filter
if date_from:
    filters["date_from"] = date_from
if date_to:
    filters["date_to"] = date_to

transactions = repo.get_all(filters or None)

st.write(f"**{len(transactions)}** transactions")

# ── Table view ───────────────────────────────────────────────────────────────
render_transaction_table(transactions)

# ── Inline edit ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("Edit a transaction")
if transactions:
    tx_ids = {f"{tx.transaction_date} | {tx.description_clean} | ${float(tx.amount):.2f}": tx for tx in transactions}
    selected_label = st.selectbox("Select transaction", list(tx_ids.keys()))
    selected_tx = tx_ids[selected_label]

    result = render_category_editor(
        selected_tx.id,
        selected_tx.category,
        selected_tx.subcategory,
        key_prefix="txexp",
    )
    if result:
        new_cat, new_sub = result
        feedback_svc.recategorize(selected_tx.id, selected_tx.category, new_cat, new_sub)
        st.success(f"Updated to {new_cat}")
        st.rerun()

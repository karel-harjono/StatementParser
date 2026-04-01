"""
Review Queue – transactions that need human attention.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st
from app.storage.db import init_db
from app.storage.repositories import TransactionRepository
from app.services.feedback_service import FeedbackService
from app.ui.components.category_editor import render_category_editor

init_db()

st.set_page_config(page_title="Review Queue", layout="wide")
st.title("Review Queue")
st.write("Transactions with low confidence or categorized as *Other*.")

repo = TransactionRepository()
feedback_svc = FeedbackService()

pending = repo.get_pending_review()

if not pending:
    st.success("No transactions need review.")
    st.stop()

st.write(f"**{len(pending)}** transactions awaiting review.")

for tx in pending:
    with st.expander(
        f"{tx.transaction_date}  |  {tx.description_clean}  |  ${float(tx.amount):.2f}  |  {tx.category or 'Uncategorized'}",
        expanded=False,
    ):
        col_info, col_edit = st.columns([3, 2])
        with col_info:
            st.write(f"**Institution:** {tx.institution}")
            st.write(f"**Merchant:** {tx.merchant or '—'}")
            st.write(f"**Raw description:** {tx.description_raw}")
            st.write(f"**Confidence:** {tx.confidence or 0:.0%}")
            st.write(f"**Method:** {tx.categorization_method or '—'}")

        with col_edit:
            result = render_category_editor(
                tx.id,
                tx.category,
                tx.subcategory,
                key_prefix="rq",
            )
            if result:
                new_cat, new_sub = result
                feedback_svc.recategorize(tx.id, tx.category, new_cat, new_sub)
                st.success(f"Saved: {new_cat}")
                st.rerun()

            if st.button("Approve as-is", key=f"rq_approve_{tx.id}"):
                feedback_svc.approve(tx.id, tx.category)
                st.success("Approved.")
                st.rerun()

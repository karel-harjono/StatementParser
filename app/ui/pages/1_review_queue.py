"""
Review Queue – transactions that need human attention.

Features:
  - SQL-level pagination (LIMIT / OFFSET) — never loads the full list
  - Sidebar: compact rules table + quick Add Rule form
  - Per-transaction inline rule creator with "Check Impact" preview
  - Sort controls, progress bar, colour-coded confidence, Refresh button
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st

from app.categorization.categories import CATEGORIES
from app.categorization.rules_engine import CategoryRule
from app.services.feedback_service import FeedbackService
from app.storage.db import init_db
from app.storage.repositories import RulesRepository, TransactionRepository
from app.ui.components.category_editor import render_category_editor

# ── Initialise ────────────────────────────────────────────────────────────────
init_db()
st.set_page_config(page_title="Review Queue", layout="wide")

repo = TransactionRepository()
rules_repo = RulesRepository()
feedback_svc = FeedbackService()

# ── Session-state defaults ────────────────────────────────────────────────────
if "rq_page" not in st.session_state:
    st.session_state.rq_page = 0
if "rq_page_size" not in st.session_state:
    st.session_state.rq_page_size = 25
if "rq_sort" not in st.session_state:
    st.session_state.rq_sort = "date_desc"

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR – Rules panel
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Categorization Rules")

    sidebar_rules = rules_repo.get_all()
    active_count = sum(1 for r in sidebar_rules if r.active)
    st.caption(f"{active_count} active · {len(sidebar_rules)} total")

    if sidebar_rules:
        import pandas as pd

        rules_df = pd.DataFrame(
            [
                {
                    "ID": r.id,
                    "Pattern": r.pattern,
                    "Type": r.match_type,
                    "Category": r.category,
                    "Sub": r.subcategory or "",
                    "Pri": r.priority,
                    "On": "✅" if r.active else "❌",
                }
                for r in sidebar_rules
            ]
        )
        st.dataframe(rules_df, use_container_width=True, hide_index=True, height=280)
    else:
        st.info("No custom rules saved yet.")

    if st.button("🔄 Refresh Rules", use_container_width=True):
        st.rerun()

    st.divider()
    st.subheader("Quick Add Rule")

    with st.form("sidebar_add_rule"):
        sb_pattern = st.text_input("Pattern *", placeholder="STARBUCKS")
        sb_match = st.selectbox("Match type", ["contains", "exact", "regex"])
        sb_cat = st.selectbox("Category *", CATEGORIES)
        sb_sub = st.text_input("Subcategory", placeholder="optional")
        sb_pri = st.slider("Priority", 1, 100, 10)
        sb_submitted = st.form_submit_button("Add Rule", use_container_width=True)

    if sb_submitted:
        if not sb_pattern.strip():
            st.error("Pattern is required.")
        else:
            rules_repo.save(
                CategoryRule(
                    id=None,
                    pattern=sb_pattern.strip(),
                    match_type=sb_match,
                    category=sb_cat,
                    subcategory=sb_sub.strip() or None,
                    priority=sb_pri,
                    active=True,
                )
            )
            st.success(f"Rule added: {sb_pattern!r} → {sb_cat}")
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN AREA – Header & controls
# ─────────────────────────────────────────────────────────────────────────────
st.title("Review Queue")
st.caption("Transactions with low confidence or categorized as *Other*.")

total = repo.count_pending_review()

if total == 0:
    st.success("✅ No transactions need review — queue is clear!")
    st.stop()

# Progress / summary row
hdr_left, hdr_mid, hdr_right = st.columns([3, 2, 2])
with hdr_left:
    st.metric("Awaiting Review", total)
with hdr_mid:
    sort_options = {
        "Date (newest first)": "date_desc",
        "Date (oldest first)": "date_asc",
        "Amount (largest first)": "amount_desc",
        "Amount (smallest first)": "amount_asc",
        "Confidence (lowest first)": "confidence_asc",
    }
    sort_label = st.selectbox(
        "Sort by",
        list(sort_options.keys()),
        index=list(sort_options.values()).index(st.session_state.rq_sort),
    )
    new_sort = sort_options[sort_label]
    if new_sort != st.session_state.rq_sort:
        st.session_state.rq_sort = new_sort
        st.session_state.rq_page = 0
        st.rerun()
with hdr_right:
    if st.button("🔄 Refresh View", use_container_width=True):
        st.rerun()


# ── Pagination controls (top) ─────────────────────────────────────────────────
def _page_size_changed():
    st.session_state.rq_page = 0


pc_left, pc_mid, pc_right = st.columns([2, 3, 2])
with pc_left:
    page_size = st.selectbox(
        "Transactions per page",
        [10, 25, 50],
        index=[10, 25, 50].index(st.session_state.rq_page_size),
        on_change=_page_size_changed,
        key="rq_page_size",
    )

page = st.session_state.rq_page
total_pages = max(1, -(-total // page_size))  # ceiling division
page = min(page, total_pages - 1)

offset = page * page_size
start_item = offset + 1
end_item = min(offset + page_size, total)

with pc_mid:
    st.write(
        f"**Page {page + 1} of {total_pages}** &nbsp;·&nbsp; Showing {start_item}–{end_item} of {total}"
    )

with pc_right:
    nav_l, nav_r = st.columns(2)
    if nav_l.button("◀ Prev", disabled=(page == 0), use_container_width=True):
        st.session_state.rq_page = page - 1
        st.rerun()
    if nav_r.button(
        "Next ▶", disabled=(page >= total_pages - 1), use_container_width=True
    ):
        st.session_state.rq_page = page + 1
        st.rerun()

st.divider()

# ── Load current page ─────────────────────────────────────────────────────────
page_txs = repo.get_pending_review_paginated(
    offset=offset,
    limit=page_size,
    sort=st.session_state.rq_sort,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper – pattern matcher (mirrors RulesEngine._matches)
# ─────────────────────────────────────────────────────────────────────────────
def _matches_pattern(pattern: str, match_type: str, text_upper: str) -> bool:
    try:
        if match_type == "exact":
            return text_upper == pattern.upper()
        if match_type == "contains":
            return pattern.upper() in text_upper
        if match_type == "regex":
            return bool(re.search(pattern, text_upper))
    except re.error:
        pass
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Transaction list
# ─────────────────────────────────────────────────────────────────────────────
for tx in page_txs:
    expander_label = (
        f"{str(tx.transaction_date)[:10]}  |  "
        f"{tx.description_clean}  |  "
        f"${float(tx.amount):.2f}  |  "
        f"{tx.category or 'Uncategorized'}"
    )

    if tx.id is None:
        continue  # should never happen for DB-fetched rows

    with st.expander(expander_label, expanded=False):
        # ── Category editor & approve ─────────────────────────────────────────
        # col_edit, col_approve = st.columns([4, 1])

        # with col_edit:
        #     result = render_category_editor(
        #         tx.id,
        #         tx.category,
        #         tx.subcategory,
        #         key_prefix="rq",
        #     )
        #     if result:
        #         new_cat, new_sub = result
        #         feedback_svc.recategorize(tx.id, tx.category, new_cat, new_sub)
        #         st.success(f"Saved: {new_cat}")
        #         st.rerun()

        # with col_approve:
        #     st.write("")  # vertical alignment spacer
        #     if st.button(
        #         "Approve as-is", key=f"rq_approve_{tx.id}", use_container_width=True
        #     ):
        #         feedback_svc.approve(tx.id, tx.category)
        #         st.success("Approved.")
        #         st.rerun()

        # ── Inline rule creator ───────────────────────────────────────────────
        # st.divider()
        st.caption("➕ Create Rule from this Transaction")

        default_pattern = tx.merchant or tx.description_clean or ""

        rl_col1, rl_col2 = st.columns(2)
        with rl_col1:
            rl_pattern = st.text_input(
                "Pattern *",
                value=default_pattern,
                key=f"rl_pat_{tx.id}",
            )
            rl_match = st.selectbox(
                "Match type",
                ["contains", "exact", "regex"],
                key=f"rl_match_{tx.id}",
            )
        with rl_col2:
            rl_cat_idx = (
                CATEGORIES.index(tx.category) if tx.category in CATEGORIES else 0
            )
            rl_cat = st.selectbox(
                "Category",
                CATEGORIES,
                index=rl_cat_idx,
                key=f"rl_cat_{tx.id}",
            )
            rl_sub = st.text_input(
                "Subcategory",
                value=tx.subcategory or "",
                placeholder="optional",
                key=f"rl_sub_{tx.id}",
            )

        rl_pri = st.slider("Priority", 1, 100, 10, key=f"rl_pri_{tx.id}")

        btn_check, btn_add = st.columns(2)

        with btn_check:
            if st.button(
                "🔍 Check Impact",
                key=f"rl_impact_{tx.id}",
                use_container_width=True,
            ):
                if rl_pattern.strip():
                    all_descs = repo.get_pending_descriptions()
                    count = sum(
                        1
                        for d in all_descs
                        if _matches_pattern(rl_pattern.strip(), rl_match, d.upper())
                    )
                    st.info(
                        f"This rule would match **{count}** of {len(all_descs)} pending transactions."
                    )
                else:
                    st.warning("Enter a pattern first.")

        with btn_add:
            if st.button(
                "💾 Add Rule", key=f"rl_save_{tx.id}", use_container_width=True
            ):
                if not rl_pattern.strip():
                    st.error("Pattern is required.")
                else:
                    rules_repo.save(
                        CategoryRule(
                            id=None,
                            pattern=rl_pattern.strip(),
                            match_type=rl_match,
                            category=rl_cat,
                            subcategory=rl_sub.strip() or None,
                            priority=rl_pri,
                            active=True,
                        )
                    )
                    st.success(
                        f"Rule added: {rl_pattern!r} → {rl_cat}. "
                        "Click **🔄 Refresh View** above to re-evaluate the queue."
                    )

# ── Pagination controls (bottom, mirrors top) ─────────────────────────────────
st.divider()
bot_l, bot_m, bot_r = st.columns([2, 3, 2])
with bot_l:
    st.write(
        f"**Page {page + 1} of {total_pages}** &nbsp;·&nbsp; Showing {start_item}–{end_item} of {total}"
    )
with bot_m:
    pass
with bot_r:
    bn_l, bn_r = st.columns(2)
    if bn_l.button(
        "◀ Prev ", disabled=(page == 0), use_container_width=True, key="bot_prev"
    ):
        st.session_state.rq_page = page - 1
        st.rerun()
    if bn_r.button(
        "Next ▶ ",
        disabled=(page >= total_pages - 1),
        use_container_width=True,
        key="bot_next",
    ):
        st.session_state.rq_page = page + 1
        st.rerun()

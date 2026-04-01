"""
Rules Manager – add, edit, and delete categorization rules.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st
from app.storage.db import init_db
from app.storage.repositories import RulesRepository
from app.categorization.rules_engine import CategoryRule, RulesEngine
from app.categorization.categories import CATEGORIES

init_db()

st.set_page_config(page_title="Rules Manager", layout="wide")
st.title("Rules Manager")

rules_repo = RulesRepository()

# ── Existing rules ────────────────────────────────────────────────────────────
st.subheader("Existing rules")
rules = rules_repo.get_all()

if not rules:
    st.info("No custom rules saved yet. Add one below.")
else:
    for rule in rules:
        with st.expander(
            f"[#{rule.id}] {rule.match_type.upper()}: {rule.pattern!r} → {rule.category}",
            expanded=False,
        ):
            col1, col2, col3 = st.columns([1, 1, 1])
            col1.write(f"**Category:** {rule.category}")
            col1.write(f"**Subcategory:** {rule.subcategory or '—'}")
            col2.write(f"**Match type:** {rule.match_type}")
            col2.write(f"**Priority:** {rule.priority}")
            col3.write(f"**Active:** {'✅' if rule.active else '❌'}")

            btn_col1, btn_col2 = st.columns(2)
            if btn_col1.button(
                "Disable" if rule.active else "Enable", key=f"toggle_{rule.id}"
            ):
                rules_repo.toggle_active(rule.id, not rule.active)
                st.rerun()
            if btn_col2.button("Delete", key=f"delete_{rule.id}"):
                rules_repo.delete(rule.id)
                st.rerun()

# ── Test a description ────────────────────────────────────────────────────────
st.divider()
st.subheader("Test a description")
test_desc = st.text_input("Description to test", placeholder="e.g. STARBUCKS #1234 CHICAGO IL")
if test_desc:
    engine = RulesEngine(rules_repo.get_all_active())
    hit = engine.match(test_desc)
    if hit:
        st.success(f"Matched rule #{hit.id}: **{hit.category}** / {hit.subcategory or '—'}")
    else:
        st.warning("No rule matched — would fall through to model / Other.")

# ── Add new rule ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("Add new rule")

with st.form("new_rule_form"):
    pattern = st.text_input("Pattern *", placeholder="STARBUCKS")
    match_type = st.selectbox("Match type", ["contains", "exact", "regex"])
    category = st.selectbox("Category *", CATEGORIES)
    subcategory = st.text_input("Subcategory", placeholder="optional")
    priority = st.slider("Priority", 1, 100, 10)
    submitted = st.form_submit_button("Add Rule")

if submitted:
    if not pattern:
        st.error("Pattern is required.")
    else:
        new_rule = CategoryRule(
            id=None,
            pattern=pattern,
            match_type=match_type,
            category=category,
            subcategory=subcategory or None,
            priority=priority,
            active=True,
        )
        rules_repo.save(new_rule)
        st.success(f"Rule added: {pattern!r} → {category}")
        st.rerun()

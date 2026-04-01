"""
Reusable component: inline category editor for a single transaction.
Returns (new_category, new_subcategory) or None if no change.
"""
import streamlit as st
from app.categorization.categories import CATEGORIES


def render_category_editor(
    tx_id: int,
    current_category: str | None,
    current_subcategory: str | None = None,
    key_prefix: str = "",
) -> tuple[str, str | None] | None:
    """
    Renders a selectbox + optional subcategory text input.
    Returns (category, subcategory) when the user clicks Save, else None.
    """
    col1, col2, col3 = st.columns([2, 2, 1])

    default_idx = CATEGORIES.index(current_category) if current_category in CATEGORIES else 0
    new_cat = col1.selectbox(
        "Category",
        CATEGORIES,
        index=default_idx,
        key=f"{key_prefix}_cat_{tx_id}",
        label_visibility="collapsed",
    )
    new_sub = col2.text_input(
        "Subcategory",
        value=current_subcategory or "",
        key=f"{key_prefix}_sub_{tx_id}",
        placeholder="Subcategory (optional)",
        label_visibility="collapsed",
    )
    save = col3.button("Save", key=f"{key_prefix}_save_{tx_id}")

    if save:
        return new_cat, new_sub or None
    return None

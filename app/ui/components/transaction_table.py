"""
Reusable component: render a DataFrame of transactions.
"""
import pandas as pd
import streamlit as st

from app.normalization.transaction_model import Transaction


def transactions_to_df(transactions: list[Transaction]) -> pd.DataFrame:
    records = []
    for tx in transactions:
        records.append(
            {
                "id": tx.id,
                "Date": str(tx.transaction_date),
                "Institution": tx.institution,
                "Description": tx.description_clean,
                "Merchant": tx.merchant or "",
                "Amount": float(tx.amount),
                "Type": tx.transaction_type,
                "Category": tx.category or "",
                "Subcategory": tx.subcategory or "",
                "Confidence": round(tx.confidence or 0.0, 2),
                "Method": tx.categorization_method or "",
                "Status": tx.review_status,
            }
        )
    return pd.DataFrame(records)


def render_transaction_table(transactions: list[Transaction]) -> None:
    if not transactions:
        st.info("No transactions to show.")
        return
    df = transactions_to_df(transactions)
    st.dataframe(df, use_container_width=True, hide_index=True)

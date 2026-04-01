"""
Reports – spending summaries.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st
import pandas as pd
from app.storage.db import init_db
from app.storage.repositories import TransactionRepository
from app.ui.components.transaction_table import transactions_to_df

init_db()

st.set_page_config(page_title="Reports", layout="wide")
st.title("Reports")

repo = TransactionRepository()
transactions = repo.get_all()

if not transactions:
    st.info("No transactions yet. Import a statement first.")
    st.stop()

df = transactions_to_df(transactions)
df["Date"] = pd.to_datetime(df["Date"])
df["Month"] = df["Date"].dt.to_period("M").astype(str)

# ── KPIs ──────────────────────────────────────────────────────────────────────
total_spend = df[df["Amount"] < 0]["Amount"].sum()
total_income = df[df["Amount"] > 0]["Amount"].sum()
uncategorized = (df["Category"] == "Other").sum()

k1, k2, k3 = st.columns(3)
k1.metric("Total Spend", f"${abs(total_spend):,.2f}")
k2.metric("Total Income", f"${total_income:,.2f}")
k3.metric("Uncategorized", int(uncategorized))

st.divider()

# ── Spend by category ─────────────────────────────────────────────────────────
st.subheader("Spend by Category")
spend = (
    df[df["Amount"] < 0]
    .groupby("Category")["Amount"]
    .sum()
    .abs()
    .sort_values(ascending=False)
    .reset_index()
    .rename(columns={"Amount": "Total Spend"})
)
st.bar_chart(spend.set_index("Category")["Total Spend"])
st.dataframe(spend, use_container_width=True, hide_index=True)

st.divider()

# ── Spend by month ────────────────────────────────────────────────────────────
st.subheader("Spend by Month")
monthly = (
    df[df["Amount"] < 0]
    .groupby("Month")["Amount"]
    .sum()
    .abs()
    .sort_index()
    .reset_index()
    .rename(columns={"Amount": "Total Spend"})
)
st.bar_chart(monthly.set_index("Month")["Total Spend"])

st.divider()

# ── Top merchants ─────────────────────────────────────────────────────────────
st.subheader("Top Merchants")
top_merchants = (
    df[df["Merchant"] != ""]
    .groupby("Merchant")["Amount"]
    .sum()
    .abs()
    .sort_values(ascending=False)
    .head(15)
    .reset_index()
    .rename(columns={"Amount": "Total"})
)
st.dataframe(top_merchants, use_container_width=True, hide_index=True)

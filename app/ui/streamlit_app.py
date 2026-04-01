"""
Main Streamlit entry point.
Run with: streamlit run app/ui/streamlit_app.py
"""
import sys
from pathlib import Path

# Ensure the project root is on sys.path when running via `streamlit run`
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from app.storage.db import init_db

init_db()

st.set_page_config(
    page_title="StatementParser",
    page_icon="🏦",
    layout="wide",
)

st.title("StatementParser")
st.write("Use the sidebar to navigate between pages.")

st.markdown(
    """
    ### Quick start
    1. **Upload a statement** using the importer below
    2. Visit **Review Queue** to categorize flagged transactions
    3. Explore all transactions in **Transactions**
    4. Manage keyword rules in **Rules Manager**
    5. View spending summaries in **Reports**
    """
)

st.divider()
st.header("Import a Statement")

uploaded = st.file_uploader(
    "Upload a CSV or PDF bank / credit card statement",
    type=["csv", "pdf"],
    help="Supported: Chase CSV, Bank of America CSV, Amex PDF, generic CSV",
)

if uploaded:
    import tempfile, os
    from app.services.import_service import ImportService

    with tempfile.NamedTemporaryFile(
        delete=False, suffix=Path(uploaded.name).suffix
    ) as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name

    try:
        with st.spinner(f"Importing {uploaded.name}…"):
            svc = ImportService()
            saved = svc.import_file(tmp_path)

        st.success(f"Imported **{len(saved)}** new transactions from `{uploaded.name}`.")
        if saved:
            st.info("Head to **Review Queue** to categorize pending transactions.")
    except Exception as exc:
        st.error(f"Import failed: {exc}")
    finally:
        os.unlink(tmp_path)

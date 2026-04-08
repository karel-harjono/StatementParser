"""
Main Streamlit entry point.
Run with: streamlit run app/ui/streamlit_app.py
"""

import os
import sys
import tempfile
from pathlib import Path

# Ensure the project root is on sys.path when running via `streamlit run`
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from app.services.import_service import ImportService
from app.storage.db import init_db
from app.utils.logging import setup_logging

setup_logging()

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


if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "is_imported" not in st.session_state:
    st.session_state.is_imported = False


if st.button(
    "Reset Uploader, More to upload?", disabled=not st.session_state.is_imported
):
    ## reset state
    st.session_state.is_imported = False
    st.session_state.uploader_key += 1
    st.rerun()

uploaded_list = st.file_uploader(
    "Upload a CSV or PDF bank / credit card statement",
    type=["csv", "pdf"],
    help="Supported: Amex CSV, RBC PDF, generic CSV",
    accept_multiple_files=True,
    key=f"file_uploader_{st.session_state.uploader_key}",
    disabled=st.session_state.is_imported,
)


def mark_imported():
    st.session_state.is_imported = True


saved = []
if st.button(
    "Import Statement",
    disabled=(not uploaded_list or st.session_state.is_imported),
    on_click=mark_imported,
):
    for file in uploaded_list:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(file.name).suffix
        ) as tmp:
            tmp.write(file.read())
            tmp_path = tmp.name

        try:
            with st.spinner(f"Importing {file.name}…"):
                svc = ImportService()
                saved = svc.import_file(tmp_path, source_name=file.name)
            if saved:
                st.success(
                    f"Imported **{len(saved)}** new transactions from `{file.name}`."
                )
            else:
                st.warning(f"Import file {file} seems to be empty or null.")
        except Exception as exc:
            st.error(f"Import failed: {exc}")
        finally:
            os.unlink(tmp_path)

if saved:
    st.info("Head to **Review Queue** to categorize pending transactions.")

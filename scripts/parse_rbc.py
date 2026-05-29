"""
Simple parser for RBC Visa statement PDFs in a folder, single PDF, or .zip file.

Output columns:
Date (MM-DD-YYYY), Store / Vendor, $ Amount, Expense Category

Install dependency:
    pip install pdfplumber

Run:
    python parse_documents_to_csv.py documents.zip transactions.csv
    python parse_documents_to_csv.py statement.pdf transactions.csv
    python parse_documents_to_csv.py ./pdf_folder transactions.csv
"""

import csv
import re
import sys
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime

import pdfplumber


COLUMNS = ["Date (MM-DD-YYYY)", "Store / Vendor", "$ Amount", "Expense Category"]

MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}

# Matches lines like:
# JUN 28 JUN 30 ROCCO'S NO FRILLS #364 TORONTO ON $42.15
TX_LINE = re.compile(
    r"^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(\d{1,2})\s+"
    r"(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(\d{1,2})\s+(.+)$"
)

AMOUNT = re.compile(r"-?\$[\d,]+\.\d{2}")

PERIOD = re.compile(
    r"STATEMENT FROM\s+([A-Z]{3})\s+\d{1,2}\s+TO\s+([A-Z]{3})\s+\d{1,2},\s+(\d{4})"
)


def categorize(vendor: str, amount: float) -> str:
    """
    Very simple keyword-based expense categorization.
    Edit this function to add your own categories.
    """
    v = vendor.upper()

    if amount < 0 or "PAYMENT" in v or "REBATE" in v:
        return "Payment / Credit"

    if "CASH ADVANCE" in v or "INTEREST" in v or "ANNUAL FEE" in v or v == "FEE":
        return "Fees / Interest"

    if any(x in v for x in ["NO FRILLS", "SUPERMARKET", "GROCERY", "T&T"]):
        return "Groceries"

    if any(
        x in v
        for x in [
            "PITA",
            "YUPDDUK",
            "RESTAURANT",
            "CAFE",
            "COFFEE",
            "MCDONALD",
            "TIM HORTONS",
        ]
    ):
        return "Dining"

    if any(x in v for x in ["STEAM", "NETFLIX", "SPOTIFY", "DISNEY", "APPLE.COM/BILL"]):
        return "Entertainment"

    if any(x in v for x in ["BASECAMP", "CLIMBING", "GYM", "FITNESS"]):
        return "Fitness"

    if any(x in v for x in ["DUUO", "COOPERATORS", "INSURANCE"]):
        return "Insurance"

    if any(x in v for x in ["UBER", "LYFT", "PRESTO", "TTC", "TRANSIT", "AIR", "HOTEL"]):
        return "Travel / Transportation"

    if any(x in v for x in ["WISE", "PAYPAL", "E-TRANSFER"]):
        return "Transfers"

    return "Other"


def statement_end_month_year(text: str, pdf_path: Path) -> tuple[int, int]:
    """
    Use the statement period when present.
    Fall back to a year found in the filename.
    """
    match = PERIOD.search(text)

    if match:
        end_month = MONTHS[match.group(2)]
        end_year = int(match.group(3))
        return end_month, end_year

    year_match = re.search(r"(20\d{2})", pdf_path.name)
    year = int(year_match.group(1)) if year_match else datetime.today().year

    return 12, year


def full_transaction_date(tx_month: str, tx_day: str, end_month: int, end_year: int) -> str:
    """
    RBC rows usually show transaction date as MON DD only.
    This infers the year from the statement end date.
    """
    month = MONTHS[tx_month]

    if month > end_month:
        year = end_year - 1
    else:
        year = end_year

    return f"{month:02d}-{int(tx_day):02d}-{year}"


def clean_vendor(vendor: str) -> str:
    """Clean spacing and remove accidental trailing long numbers."""
    vendor = re.sub(r"\s+", " ", vendor).strip()
    vendor = re.sub(r"\s+\d{16,}$", "", vendor).strip()
    return vendor


def parse_pdf(pdf_path: Path) -> list[dict]:
    """Parse one PDF and return rows for the CSV."""
    rows = []

    with pdfplumber.open(pdf_path) as pdf:
        all_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        end_month, end_year = statement_end_month_year(all_text, pdf_path)

        for page in pdf.pages:
            text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""

            for line in text.splitlines():
                line = re.sub(r"\s+", " ", line).strip()
                match = TX_LINE.match(line)

                if not match:
                    continue

                tx_month, tx_day, _post_month, _post_day, rest = match.groups()

                amount_match = AMOUNT.search(rest)

                if not amount_match:
                    continue

                vendor = clean_vendor(rest[: amount_match.start()])

                amount_text = amount_match.group(0)
                amount_text = amount_text.replace("$", "").replace(",", "")
                amount = float(amount_text)

                # Skip summary/balance lines if they are picked up by accident.
                if vendor.upper().startswith(
                    (
                        "TOTAL ACCOUNT BALANCE",
                        "NEW BALANCE",
                        "PREVIOUS ACCOUNT BALANCE",
                    )
                ):
                    continue

                rows.append(
                    {
                        "Date (MM-DD-YYYY)": full_transaction_date(
                            tx_month, tx_day, end_month, end_year
                        ),
                        "Description": vendor,
                        "Amount": f"{amount:.2f}",
                        "Expense Category": categorize(vendor, amount),
                    }
                )

    return rows


def pdf_files_from_input(input_path: Path):
    """
    Accept a folder containing PDFs and/or ZIP files, one PDF, or one ZIP file.

    Returns:
        list of PDF paths, temp directory object or None

    Important:
        The returned temp_dir must stay alive until you are done parsing the PDFs,
        because extracted ZIP contents live inside it.
    """
    temp_dir = tempfile.TemporaryDirectory()
    extracted_root = Path(temp_dir.name)

    pdfs = []

    def extract_zip(zip_path: Path):
        target_dir = extracted_root / zip_path.stem
        target_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(target_dir)

        return sorted(target_dir.rglob("*.pdf"))

    if input_path.is_dir():
        # PDFs directly inside the folder
        pdfs.extend(sorted(input_path.glob("*.pdf")))

        # ZIPs directly inside the folder
        for zip_path in sorted(input_path.glob("*.zip")):
            pdfs.extend(extract_zip(zip_path))

        if not pdfs:
            temp_dir.cleanup()
            return [], None

        return pdfs, temp_dir

    if input_path.suffix.lower() == ".pdf":
        temp_dir.cleanup()
        return [input_path], None

    if input_path.suffix.lower() == ".zip":
        pdfs.extend(extract_zip(input_path))

        if not pdfs:
            temp_dir.cleanup()
            return [], None

        return pdfs, temp_dir

    temp_dir.cleanup()
    raise ValueError(
        "Input must be a .zip file, a .pdf file, or a folder containing PDFs and/or ZIPs."
    )


def main():
    if len(sys.argv) != 3:
        print("Usage: python parse_documents_to_csv.py INPUT.zip_or_pdf_folder OUTPUT.csv")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_csv = Path(sys.argv[2])

    pdfs, temp_dir = pdf_files_from_input(input_path)

    if not pdfs:
        print("No PDF files found.")
        sys.exit(1)

    all_rows = []

    for pdf in pdfs:
        print(f"Parsing {pdf.name}...")
        all_rows.extend(parse_pdf(pdf))

    all_rows.sort(
        key=lambda row: datetime.strptime(row["Date (MM-DD-YYYY)"], "%m-%d-%Y")
    )

    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(all_rows)

    if temp_dir:
        temp_dir.cleanup()

    print(f"Wrote {len(all_rows)} rows to {output_csv}")


if __name__ == "__main__":
    main()
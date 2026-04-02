"""
Statement parser for AMEX and RBC credit card statements.
Combines CSV files and extracts transactions from PDF statements.
"""

import json
import re
from pathlib import Path

import pandas as pd
import pdfplumber

# Constants
AMEX_INPUT_DIR = "./statements/amex"
RBC_INPUT_DIR = "./statements/rbc"
OUTPUT_DIR = "./output/csv"
COMBINED_OUTPUT_DIR = "./output/combined"
MANIFEST_FILE = "./output/processed_files.json"

MONTHS = [
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
]

# PDF extraction parameters
PDF_X1_THRESHOLD = 350
PDF_BOTTOM_THRESHOLD = 200

# Regex to parse RBC transaction lines: 'MON DD MON DD description $amount'
# Handles both 'FEB 17' (space-separated) and 'FEB17' (compact) month/day tokens.
_MONTH_ALT = "|".join(MONTHS)
_TXN_RE = re.compile(
    rf"^({_MONTH_ALT})\s*(\d{{1,2}})\s+({_MONTH_ALT})\s*(\d{{1,2}})\s+(.*?)\s+(-?\$[\d,]+\.\d{{2}})\s*$",
    re.IGNORECASE,
)


def load_manifest() -> list[dict]:
    """Load the processed-files manifest from disk, returning an empty list if absent."""
    path = Path(MANIFEST_FILE)
    if path.exists():
        with path.open() as f:
            return json.load(f)
    return []


def save_manifest(entries: list[dict]) -> None:
    """Persist the processed-files manifest to disk."""
    path = Path(MANIFEST_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(entries, f, indent=2)


def compile_csv(input_dir, output_dir=OUTPUT_DIR, output_file_name="combined.csv"):
    """
    Combine all CSV files from a directory into a single CSV file.

    Args:
        input_dir: Directory containing CSV files to combine
        output_dir: Directory to save the combined CSV file
        output_file_name: Name of the output file

    Returns:
        Combined DataFrame or None if no CSV files found
    """
    input_path = Path(input_dir)
    csv_files = list(input_path.glob("*.csv"))

    if not csv_files:
        print(f"No CSV files found in {input_dir}/")
        return None

    # Read and concatenate all CSV files
    dataframes = [pd.read_csv(csv_file) for csv_file in csv_files]
    combined_df = pd.concat(dataframes, ignore_index=True)

    # Save combined file
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(output_path / output_file_name, index=False)
    print("Writing to " + output_dir + "/" + output_file_name)

    return combined_df


def _format_date(month_abbr: str, day: int, year: int) -> str:
    """
    Convert a month abbreviation, integer day, and resolved year into an ISO 8601
    date string 'YYYY-MM-DD', compatible with pandas and standard tooling.
    """
    month = MONTHS.index(month_abbr.upper()) + 1
    return f"{year}-{month:02d}-{day:02d}"


def _resolve_year(date_str: str, statement_year: int, statement_month: int) -> int:
    """
    Determine the correct year for a transaction date like 'NOV15'.
    If the transaction month is later than the statement closing month,
    the transaction belongs to the prior year (e.g. DEC on a JAN statement).
    """
    month_abbr = date_str[:3].upper()
    if month_abbr not in MONTHS:
        return statement_year
    txn_month = MONTHS.index(month_abbr) + 1  # 1-based
    return statement_year if txn_month <= statement_month else statement_year - 1


def extract_amex_transactions(
    csv_dir, manifest: list[dict] | None = None
) -> pd.DataFrame | None:
    """
    Extract transactions from all AMEX CSV statements in a directory.
    Normalises dates from 'DD Mon YYYY' to ISO 8601 'YYYY-MM-DD' and
    formats amounts as '$12.34' strings to match the RBC output schema.

    Args:
        csv_dir: Directory containing AMEX CSV statement files

    Returns:
        Combined DataFrame with columns: Date, Date Processed, Description, Amount
        or None if no CSV files are found.
    """
    csv_files = sorted(Path(csv_dir).glob("*.csv"))

    if not csv_files:
        print(f"No CSV files found in {csv_dir}/")
        return None

    frames = []
    for csv_path in csv_files:
        print(f"  Reading {csv_path.name}...")
        df = pd.read_csv(csv_path)

        # Normalise dates: 'DD Mon YYYY' → 'YYYY-MM-DD'
        df["Date"] = pd.to_datetime(
            df["Date"], format="%d %b %Y", errors="coerce"
        ).dt.strftime("%Y-%m-%d")
        df["Date Processed"] = pd.to_datetime(
            df["Date Processed"], format="%d %b %Y", errors="coerce"
        ).dt.strftime("%Y-%m-%d")

        # Normalise amount: float → '$12.34' string (matches RBC schema)
        df["Amount"] = df["Amount"].apply(
            lambda v: f"-${abs(v):.2f}" if float(v) < 0 else f"${float(v):.2f}"
        )

        frames.append(df[["Date", "Date Processed", "Description", "Amount"]])

        if manifest is not None:
            manifest.append(
                {
                    "file": csv_path.name,
                    "type": "amex",
                    "processed_at": pd.Timestamp.now().isoformat(),
                    "rows": len(df),
                }
            )

    return pd.concat(frames, ignore_index=True)


def extract_rbc_transactions(pdf_path) -> pd.DataFrame:
    """
    Extract transactions from a single RBC Visa PDF statement.
    The year is inferred from the filename (e.g. 'Visa Statement-2423 2022-01-17.pdf').
    Dates like 'DEC15' on a January statement are resolved to the prior year.

    Args:
        pdf_path: Path to the RBC PDF statement

    Returns:
        DataFrame with columns: Date, Date Processed, Description, Amount
    """
    pdf_path = Path(pdf_path)

    # Extract statement closing year/month from filename
    date_part = pdf_path.stem.split(" ")[-1]  # e.g. '2022-01-17'
    statement_year = int(date_part.split("-")[0])
    statement_month = int(date_part.split("-")[1])

    words = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words.extend(page.extract_text_lines(y_tolerance=0))

    # Filter to transaction lines
    transaction_texts = [
        w["text"]
        for w in words
        if (
            w.get("x1", float("inf")) < PDF_X1_THRESHOLD
            and w.get("bottom", float("inf")) > PDF_BOTTOM_THRESHOLD
            and "$" in w.get("text", "").upper()
            and any(w.get("text", "").upper().startswith(month) for month in MONTHS)
        )
    ]

    # Parse each transaction line with the compiled regex
    rows = []
    for text in transaction_texts:
        m = _TXN_RE.match(text)
        if not m:
            continue
        date_mon, date_day, dp_mon, dp_day, description, amount = m.groups()
        date_year = _resolve_year(date_mon, statement_year, statement_month)
        dp_year = _resolve_year(dp_mon, statement_year, statement_month)
        rows.append(
            {
                "Date": _format_date(date_mon, int(date_day), date_year),
                "Date Processed": _format_date(dp_mon, int(dp_day), dp_year),
                "Description": description,
                "Amount": amount,
            }
        )

    return pd.DataFrame(
        rows, columns=["Date", "Date Processed", "Description", "Amount"]
    )


def extract_all_rbc_transactions(
    rbc_dir, manifest: list[dict] | None = None
) -> pd.DataFrame | None:
    """
    Extract and combine transactions from all RBC Visa PDF statements in a directory.

    Args:
        rbc_dir: Directory containing RBC PDF statements

    Returns:
        Combined DataFrame or None if no PDFs found
    """
    pdf_files = sorted(Path(rbc_dir).glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {rbc_dir}/")
        return None

    all_dfs = []
    for pdf_path in pdf_files:
        print(f"  Parsing {pdf_path.name}...")
        df = extract_rbc_transactions(pdf_path)
        all_dfs.append(df)

        if manifest is not None:
            manifest.append(
                {
                    "file": pdf_path.name,
                    "type": "rbc",
                    "processed_at": pd.Timestamp.now().isoformat(),
                    "rows": len(df),
                }
            )

    return pd.concat(all_dfs, ignore_index=True)


def main():
    """Main execution function."""
    manifest = load_manifest()

    # Process AMEX statements
    print("Processing AMEX statements...")
    amex_df = extract_amex_transactions(AMEX_INPUT_DIR, manifest=manifest)
    timestamp = pd.Timestamp.now().strftime("%Y_%m")
    if amex_df is not None:
        amex_output_file = f"amex_compiled_{timestamp}.csv"
        amex_df.to_csv(Path(OUTPUT_DIR) / amex_output_file, index=False)
        print(f"Extracted {len(amex_df)} AMEX transactions from {AMEX_INPUT_DIR}")

    # Process all RBC PDF statements
    print("\nProcessing RBC PDF statements...")
    rbc_df = extract_all_rbc_transactions(RBC_INPUT_DIR, manifest=manifest)

    timestamp = pd.Timestamp.now().strftime("%Y_%m")
    if rbc_df is not None:
        rbc_output_file = f"rbc_visa_compiled_{timestamp}.csv"
        rbc_df.to_csv(Path(OUTPUT_DIR) / rbc_output_file, index=False)
        print(f"Extracted {len(rbc_df)} RBC transactions from {RBC_INPUT_DIR}")

    # Combine all CSV files into final output
    print("\nCombining all statements...")
    combined_output_file = f"combined_{timestamp}.csv"
    final_result = compile_csv(
        OUTPUT_DIR,
        output_dir=COMBINED_OUTPUT_DIR,
        output_file_name=combined_output_file,
    )

    if final_result is not None:
        print("\nFinal combined statistics:")
        print(final_result.describe())

    save_manifest(manifest)
    print(f"\nManifest updated: {MANIFEST_FILE} ({len(manifest)} files recorded)")


if __name__ == "__main__":
    main()

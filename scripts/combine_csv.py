import csv
import sys
from pathlib import Path
from datetime import datetime


def convert_date(value: str) -> str:
    """
    Convert date from yyyy-mm-dd to mm-dd-yyyy.
    Leaves the value unchanged if it cannot be parsed.
    """
    try:
        return datetime.strptime(value.strip(), "%d %b %Y").strftime("%m-%d-%Y")
    except ValueError:
        return value


def combine_csv_files(input_dir: Path, output_file: Path):
    csv_files = sorted(input_dir.glob("*.csv"))

    if not csv_files:
        print("No CSV files found.")
        return

    header_written = False
    total_rows = 0

    with output_file.open("w", newline="", encoding="utf-8") as out_f:
        writer = None
        date_index = None

        for csv_file in csv_files:
            print(f"Reading {csv_file.name}...")

            with csv_file.open("r", newline="", encoding="utf-8") as in_f:
                reader = csv.reader(in_f)

                try:
                    header = next(reader)
                except StopIteration:
                    continue

                if not header_written:
                    if "Date" in header:
                        date_index: int = header.index("Date")
                        date_processed_index = header.index("Date Processed")
                        del header[date_processed_index]
                    else:
                        print('Warning: No "Date" column found.')
                        date_index = None
                    
                    writer = csv.writer(out_f)
                    writer.writerow(header)
                    header_written = True

                for row in reader:
                    if date_index is not None and date_index < len(row):
                        row[date_index] = convert_date(row[date_index])
                    del row[date_processed_index]

                    writer.writerow(row)
                    total_rows += 1

    print(f"Combined {len(csv_files)} CSV files into {output_file}")
    print(f"Wrote {total_rows} data rows.")


def main():
    if len(sys.argv) != 3:
        print("Usage: python combine_csvs.py INPUT_DIRECTORY output.csv")
        sys.exit(1)

    input_dir = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    if not input_dir.is_dir():
        print("Input path must be a directory.")
        sys.exit(1)

    combine_csv_files(input_dir, output_file)


if __name__ == "__main__":
    main()
from pathlib import Path
import pandas as pd
import sys

if len(sys.argv) < 2:
    print("Usage: python remove_payments.py input_file")
    sys.exit(1)

input_file = Path(sys.argv[1])
output_file = input_file.stem + '-no-payments.csv'

df = pd.read_csv(input_file)

df = df[df['Store / Vendor'] != 'PAYMENT - THANK YOU / PAIEMENT - MERCI']
print(df.head())

df.to_csv(output_file)
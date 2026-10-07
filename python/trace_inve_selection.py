import pandas as pd
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "python"))

import extract_financials

PRODUCTION_FILE = BASE_DIR / "data" / "financials_raw.csv"

df = pd.read_csv(PRODUCTION_FILE)

inve = df[
    (df["ticker"] == "INVE") &
    (df["fiscal_year"].isin([2021, 2022]))
].copy()

print("PRODUCTION ROWS")
print("=" * 60)
print(
    inve[
        [
            "ticker",
            "company",
            "period_end",
            "fiscal_year",
            "net_income",
            "net_income_concept",
            "source_filed",
        ]
    ].to_string(index=False)
)

print()
print("NET INCOME CONCEPTS")
print("-" * 60)

for _, row in inve.iterrows():
    print(f"\nFiscal year: {row['fiscal_year']}")
    print(f"Period end: {row['period_end']}")
    print(f"Selected value: {row['net_income']}")
    print(f"Selected concept: {row['net_income_concept']}")
    print(f"Filed: {row['source_filed']}")

print()
print("AVAILABLE ANNUAL NET INCOME RECORDS")
print("-" * 60)

zip_path = BASE_DIR / "data" / "companyfacts.zip"

with extract_financials.zipfile.ZipFile(zip_path) as zf:
    zip_index = extract_financials.build_zip_index(zf)

    cik = str(int(inve.iloc[0]["cik"])).zfill(10)

    company_json = extract_financials.load_company_json(
        zf,
        zip_index,
        cik
    )

facts = extract_financials.get_us_gaap_facts(company_json)

if "NetIncomeLoss" not in facts:
    print("NetIncomeLoss not found.")
    sys.exit()

records = facts["NetIncomeLoss"].get("units", {}).get("USD", [])

annual = []

for record in records:
    if record.get("form") not in {"10-K", "10-K/A"}:
        continue

    if record.get("fp") != "FY":
        continue

    annual.append(record)

if not annual:
    print("No annual NetIncomeLoss records found.")
else:
    annual_df = pd.DataFrame(annual)

    columns = [
        "start",
        "end",
        "filed",
        "form",
        "fy",
        "fp",
        "val",
        "accn",
    ]

    columns = [column for column in columns if column in annual_df.columns]

    print(
        annual_df[columns]
        .sort_values(["end", "filed"])
        .to_string(index=False)
    )
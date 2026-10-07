import pandas as pd
from pathlib import Path
import sys
import zipfile

BASE_DIR = Path(__file__).resolve().parent.parent
UNIVERSE_FILE = BASE_DIR / "data" / "classified_investment_universe.csv"
ZIP_FILE = BASE_DIR / "data" / "companyfacts.zip"

sys.path.append(str(BASE_DIR / "python"))
import extract_financials


def find_anomalies(records):
    annual = []

    for record in records:
        if record.get("form") not in {"10-K", "10-K/A"}:
            continue

        if record.get("fp") != "FY":
            continue

        if not record.get("start") or not record.get("end"):
            continue

        annual.append(record)

    anomalies = []

    for record in annual:
        if record.get("form") != "10-K/A":
            continue

        period_end = record["end"]
        amended_value = record.get("val")

        if amended_value is None or amended_value == 0:
            continue

        previous = [
            r for r in annual
            if r.get("end") == period_end
            and r.get("form") == "10-K"
            and r.get("val") not in (None, 0)
            and r.get("filed", "") < record.get("filed", "")
        ]

        if not previous:
            continue

        previous_record = max(previous, key=lambda r: r.get("filed", ""))

        previous_value = previous_record["val"]

        ratio = abs(amended_value / previous_value)

        if 900000 <= ratio <= 1100000:
            anomalies.append({
                "period_end": period_end,
                "previous_value": previous_value,
                "amended_value": amended_value,
                "ratio": ratio,
                "previous_filed": previous_record.get("filed"),
                "amended_filed": record.get("filed"),
                "previous_accn": previous_record.get("accn"),
                "amended_accn": record.get("accn"),
            })

    return anomalies


df = pd.read_csv(UNIVERSE_FILE)
df = df[df["investment_eligible"] == True].copy()

print(f"Companies to scan: {len(df):,}")
print("Scanning Company Facts...")
print()

results = []

with zipfile.ZipFile(ZIP_FILE) as zf:
    zip_index = extract_financials.build_zip_index(zf)

    for i, row in enumerate(df.itertuples(index=False), start=1):
        cik = str(int(row.cik)).zfill(10)

        try:
            company_json = extract_financials.load_company_json(
                zf,
                zip_index,
                cik
            )

            facts = extract_financials.get_us_gaap_facts(company_json)

            net_income = facts.get("NetIncomeLoss")

            if not net_income:
                continue

            units = net_income.get("units", {})

            for unit, records in units.items():
                anomalies = find_anomalies(records)

                for anomaly in anomalies:
                    results.append({
                        "ticker": row.ticker,
                        "company": row.company,
                        "cik": cik,
                        "concept": "NetIncomeLoss",
                        "unit": unit,
                        **anomaly
                    })

        except Exception:
            continue

        if i % 500 == 0:
            print(f"Processed {i:,}/{len(df):,}")

print()
print("=" * 70)
print("SCALING ANOMALIES FOUND")
print("=" * 70)

if results:
    result_df = pd.DataFrame(results)

    print(f"Anomalies: {len(result_df):,}")
    print(f"Companies affected: {result_df['ticker'].nunique():,}")
    print()

    print(
        result_df[
            [
                "ticker",
                "company",
                "period_end",
                "previous_value",
                "amended_value",
                "ratio",
                "previous_filed",
                "amended_filed"
            ]
        ].to_string(index=False)
    )

    output_file = BASE_DIR / "data" / "scaling_anomalies.csv"
    result_df.to_csv(output_file, index=False)

    print()
    print(f"Saved to: {output_file}")

else:
    print("No 1,000,000x scaling anomalies found.")
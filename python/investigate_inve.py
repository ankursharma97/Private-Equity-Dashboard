# Only investigating financial record of INVE technology

import zipfile
from pathlib import Path

import pandas as pd

import extract_financials

BASE_DIR = Path(__file__).resolve().parent.parent
ZIP_FILE = BASE_DIR / "data" / "companyfacts.zip"
FINANCIALS_FILE = BASE_DIR / "data" / "financials_raw.csv"


def main():
    # Load the production row for INVE
    df = pd.read_csv(FINANCIALS_FILE)

    inve = df[df["ticker"] == "INVE"].copy()

    print("INVE PRODUCTION ROWS")
    print("=" * 60)

    if inve.empty:
        print("INVE was not found in financials_raw.csv")
        return

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

    # Find INVE's SEC Company Facts file
    cik = str(inve.iloc[0]["cik"]).split(".")[0].zfill(10)

    print("SEC COMPANY FACTS")
    print("-" * 60)
    print(f"CIK: {cik}")

    with zipfile.ZipFile(ZIP_FILE, "r") as zf:
        zip_index = extract_financials.build_zip_index(zf)

        if cik not in zip_index:
            print("INVE Company Facts file was not found.")
            return

        facts = extract_financials.load_company_json(
    zf,
    zip_index,
    cik
)
    us_gaap = facts.get("facts", {}).get("us-gaap", {})

    concept_name = inve.iloc[0]["net_income_concept"]

    print(f"Concept: {concept_name}")
    print()

    concept = us_gaap.get(concept_name)

    if not concept:
        print("Selected concept was not found in Company Facts.")
        return

    units = concept.get("units", {})

    print("AVAILABLE UNITS")
    print("-" * 60)
    print(list(units.keys()))

    for unit, records in units.items():
        records_df = pd.DataFrame(records)

        if records_df.empty:
            continue

        print()
        print(f"UNIT: {unit}")
        print("-" * 60)

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

        available_columns = [
            column for column in columns
            if column in records_df.columns
        ]

        print(
            records_df[
                available_columns
            ].sort_values("filed").tail(30).to_string(index=False)
        )

    print()
    print("=" * 60)
    print("INVE INVESTIGATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
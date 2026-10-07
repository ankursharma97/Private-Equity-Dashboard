import zipfile
from pathlib import Path

import pandas as pd

import extract_financials


BASE_DIR = Path(__file__).resolve().parent.parent

ZIP_FILE = BASE_DIR / "data" / "companyfacts.zip"
UNIVERSE_FILE = BASE_DIR / "data" / "classified_investment_universe.csv"
OUTPUT_FILE = BASE_DIR / "data" / "extraction_failure_diagnostic.csv"


def main():
    print("EXTRACTION FAILURE DIAGNOSTIC")
    print("=" * 50)

    universe = pd.read_csv(UNIVERSE_FILE)

    if "investment_eligible" not in universe.columns:
        raise ValueError(
            "classified_investment_universe.csv is missing "
            "'investment_eligible'."
        )

    universe["ticker"] = (
        universe["ticker"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    universe = universe[
        universe["investment_eligible"] == True
    ].copy()

    print(f"Eligible companies in universe: {len(universe):,}")
    print()

    print(f"Opening Company Facts:\n{ZIP_FILE}")
    print("Building ZIP index...")

    errors = []
    successful = 0
    failed = 0

    with zipfile.ZipFile(ZIP_FILE, "r") as zf:
        zip_index = extract_financials.build_zip_index(zf)

        print(f"Indexed files: {len(zip_index):,}")
        print()

        for position, (_, company_row) in enumerate(
            universe.iterrows(),
            start=1
        ):
            ticker = str(company_row["ticker"]).upper()
            company = company_row["company"]
            cik = company_row["cik"]

            try:
                rows = extract_financials.extract_company(
                    company_row,
                    zf,
                    zip_index
                )

                if rows:
                    successful += 1
                else:
                    failed += 1

                    errors.append({
                        "position": position,
                        "ticker": ticker,
                        "company": company,
                        "cik": cik,
                        "error_type": "NO_ANNUAL_PERIODS",
                        "error_message": (
                            "No annual financial periods found."
                        ),
                    })

                    print(
                        f"FAILED [{position}/{len(universe)}] "
                        f"{ticker} | {company}"
                    )
                    print("  Type: NO_ANNUAL_PERIODS")

            except Exception as exc:
                failed += 1

                errors.append({
                    "position": position,
                    "ticker": ticker,
                    "company": company,
                    "cik": cik,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                })

                print(
                    f"FAILED [{position}/{len(universe)}] "
                    f"{ticker} | {company}"
                )
                print(f"  Type: {type(exc).__name__}")
                print(f"  Error: {exc}")

            if position % 100 == 0 or position == len(universe):
                success_rate = successful / position * 100
                failure_rate = failed / position * 100

                print(
                    f"[{position:,}/{len(universe):,}] "
                    f"Successful: {successful:,} | "
                    f"Failed: {failed:,} | "
                    f"Success rate: {success_rate:.2f}%"
                )

    error_df = pd.DataFrame(errors)

    if not error_df.empty:
        error_df.to_csv(OUTPUT_FILE, index=False)

    print()
    print("=" * 50)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 50)

    print(f"Companies tested: {len(universe):,}")
    print(f"Successful: {successful:,}")
    print(f"Failed: {failed:,}")

    if len(universe) > 0:
        success_rate = successful / len(universe) * 100
        failure_rate = failed / len(universe) * 100

        print(f"Success rate: {success_rate:.2f}%")
        print(f"Failure rate: {failure_rate:.2f}%")

    if not error_df.empty:
        print()
        print(f"Diagnostic file saved to:")
        print(OUTPUT_FILE)

        print()
        print("FAILURE TYPES")
        print("-" * 50)
        print(
            error_df["error_type"]
            .value_counts()
            .to_string()
        )

        print()
        print("FAILED COMPANIES")
        print("-" * 50)

        print(
            error_df[
                [
                    "position",
                    "ticker",
                    "company",
                    "error_type",
                    "error_message",
                ]
            ].to_string(index=False)
        )
    else:
        print()
        print("No failures detected.")


if __name__ == "__main__":
    main()
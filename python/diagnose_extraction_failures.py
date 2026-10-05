import zipfile
from pathlib import Path

import pandas as pd

import extract_financials


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ZIP_FILE = BASE_DIR / "data" / "companyfacts.zip"
UNIVERSE_FILE = BASE_DIR / "data" / "investment_universe.csv"

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "extraction_failure_diagnostic.csv"
)


# ============================================================
# CONFIGURATION
# ============================================================

# We only diagnose the first 600 companies because that is
# where we already observed the high failure rate.
TEST_COMPANIES = 600


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("EXTRACTION FAILURE DIAGNOSTIC")
    print("=" * 80)

    print()

    # --------------------------------------------------------
    # LOAD UNIVERSE
    # --------------------------------------------------------

    universe = pd.read_csv(
        UNIVERSE_FILE
    )

    universe["ticker"] = (
        universe["ticker"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    universe = universe.head(
        TEST_COMPANIES
    ).copy()

    print(
        f"Companies being diagnosed: "
        f"{len(universe):,}"
    )

    print()

    # --------------------------------------------------------
    # OPEN ZIP
    # --------------------------------------------------------

    print(
        f"Opening Company Facts:\n{ZIP_FILE}"
    )

    errors = []

    successful = 0
    failed = 0

    with zipfile.ZipFile(
        ZIP_FILE,
        "r"
    ) as zf:

        print(
            "Building ZIP index..."
        )

        zip_index = (
            extract_financials.build_zip_index(
                zf
            )
        )

        print(
            f"Indexed files: "
            f"{len(zip_index):,}"
        )

        print()

        # ----------------------------------------------------
        # PROCESS COMPANIES
        # ----------------------------------------------------

        for position, (_, company_row) in enumerate(
            universe.iterrows(),
            start=1
        ):

            ticker = str(
                company_row["ticker"]
            ).upper()

            company = company_row[
                "company"
            ]

            cik = company_row[
                "cik"
            ]

            try:

                rows = (
                    extract_financials.extract_company(
                        company_row,
                        zf,
                        zip_index
                    )
                )

                if rows:

                    successful += 1

                else:

                    failed += 1

                    error_record = {
                        "position": position,
                        "ticker": ticker,
                        "company": company,
                        "cik": cik,
                        "error_type": (
                            "NO_ANNUAL_PERIODS"
                        ),
                        "error_message": (
                            "No annual financial "
                            "periods found."
                        ),
                    }

                    errors.append(
                        error_record
                    )

                    print()
                    print(
                        f"FAILED [{position}/"
                        f"{len(universe)}] "
                        f"{ticker} | "
                        f"{company}"
                    )

                    print(
                        "  Type: "
                        "NO_ANNUAL_PERIODS"
                    )

            except Exception as exc:

                failed += 1

                error_record = {
                    "position": position,
                    "ticker": ticker,
                    "company": company,
                    "cik": cik,
                    "error_type": type(
                        exc
                    ).__name__,
                    "error_message": str(
                        exc
                    ),
                }

                errors.append(
                    error_record
                )

                print()
                print(
                    f"FAILED [{position}/"
                    f"{len(universe)}] "
                    f"{ticker} | "
                    f"{company}"
                )

                print(
                    f"  Type: "
                    f"{type(exc).__name__}"
                )

                print(
                    f"  Error: "
                    f"{exc}"
                )

            # ------------------------------------------------
            # PROGRESS
            # ------------------------------------------------

            if (
                position % 50 == 0
                or position == len(universe)
            ):

                print()

                print(
                    f"Progress: "
                    f"{position:,}/"
                    f"{len(universe):,} | "
                    f"Successful: "
                    f"{successful:,} | "
                    f"Failed: "
                    f"{failed:,}"
                )

                print()

    # ========================================================
    # SAVE DIAGNOSTIC RESULTS
    # ========================================================

    error_df = pd.DataFrame(
        errors
    )

    if not error_df.empty:

        error_df.to_csv(
            OUTPUT_FILE,
            index=False
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)

    print()

    print(
        f"Companies tested: "
        f"{len(universe):,}"
    )

    print(
        f"Successful: "
        f"{successful:,}"
    )

    print(
        f"Failed: "
        f"{failed:,}"
    )

    if len(universe) > 0:

        success_rate = (
            successful
            / len(universe)
            * 100
        )

        failure_rate = (
            failed
            / len(universe)
            * 100
        )

        print(
            f"Success rate: "
            f"{success_rate:.2f}%"
        )

        print(
            f"Failure rate: "
            f"{failure_rate:.2f}%"
        )

    print()

    if not error_df.empty:

        print(
            f"Diagnostic file saved to:"
        )

        print(
            OUTPUT_FILE
        )

        print()

        print(
            "=" * 80
        )

        print(
            "FAILURE TYPES"
        )

        print(
            "=" * 80
        )

        print(
            error_df[
                "error_type"
            ].value_counts().to_string()
        )

        print()

        print(
            "=" * 80
        )

        print(
            "FAILED COMPANIES"
        )

        print(
            "=" * 80
        )

        print(
            error_df[
                [
                    "position",
                    "ticker",
                    "company",
                    "error_type",
                    "error_message",
                ]
            ].to_string(
                index=False
            )
        )

    else:

        print(
            "No failures detected."
        )


if __name__ == "__main__":
    main()
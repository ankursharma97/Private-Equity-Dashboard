import time
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


# ============================================================
# BENCHMARK COMPANY
# ============================================================

TEST_TICKER = "AAPL"


# ============================================================
# TIMER HELPER
# ============================================================

def elapsed(start):
    return time.perf_counter() - start


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("FINANCIAL EXTRACTION PERFORMANCE BENCHMARK")
    print("=" * 80)

    print()

    # --------------------------------------------------------
    # LOAD UNIVERSE
    # --------------------------------------------------------

    start = time.perf_counter()

    universe = pd.read_csv(
        UNIVERSE_FILE
    )

    universe["ticker"] = (
        universe["ticker"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    company_row = universe[
        universe["ticker"] == TEST_TICKER
    ].iloc[0]

    print(
        f"Company: {TEST_TICKER}"
    )

    print(
        f"CIK: {company_row['cik']}"
    )

    print(
        f"Universe loading: "
        f"{elapsed(start):.3f} seconds"
    )

    print()

    # --------------------------------------------------------
    # OPEN ZIP
    # --------------------------------------------------------

    start = time.perf_counter()

    zf = zipfile.ZipFile(
        ZIP_FILE,
        "r"
    )

    print(
        f"ZIP opening: "
        f"{elapsed(start):.3f} seconds"
    )

    # --------------------------------------------------------
    # BUILD ZIP INDEX
    # --------------------------------------------------------

    start = time.perf_counter()

    zip_index = (
        extract_financials.build_zip_index(
            zf
        )
    )

    print(
        f"ZIP index building: "
        f"{elapsed(start):.3f} seconds"
    )

    print(
        f"Indexed files: "
        f"{len(zip_index):,}"
    )

    print()

    # --------------------------------------------------------
    # LOAD COMPANY JSON
    # --------------------------------------------------------

    start = time.perf_counter()

    company_json = (
        extract_financials.load_company_json(
            zf,
            zip_index,
            company_row["cik"]
        )
    )

    print(
        f"Company JSON loading: "
        f"{elapsed(start):.3f} seconds"
    )

    # --------------------------------------------------------
    # GET US-GAAP FACTS
    # --------------------------------------------------------

    start = time.perf_counter()

    us_gaap = (
        extract_financials.get_us_gaap_facts(
            company_json
        )
    )

    print(
        f"US-GAAP extraction: "
        f"{elapsed(start):.3f} seconds"
    )

    print(
        f"US-GAAP concepts: "
        f"{len(us_gaap):,}"
    )

    print()

    # --------------------------------------------------------
    # PERIOD BACKBONE
    # --------------------------------------------------------

    start = time.perf_counter()

    period_ends = (
        extract_financials.get_period_backbone(
            us_gaap
        )
    )

    print(
        f"Period backbone: "
        f"{elapsed(start):.3f} seconds"
    )

    print(
        f"Periods: "
        f"{period_ends}"
    )

    print()

    # --------------------------------------------------------
    # FULL COMPANY EXTRACTION
    # --------------------------------------------------------

    start = time.perf_counter()

    rows = (
        extract_financials.extract_company(
            company_row,
            zf,
            zip_index
        )
    )

    extraction_time = elapsed(start)

    print()

    print(
        f"Full company extraction: "
        f"{extraction_time:.3f} seconds"
    )

    print(
        f"Rows extracted: "
        f"{len(rows):,}"
    )

    print()

    # --------------------------------------------------------
    # TOTAL
    # --------------------------------------------------------

    zf.close()

    print("=" * 80)
    print("BENCHMARK COMPLETE")
    print("=" * 80)

    print()

    print(
        f"Full extraction time: "
        f"{extraction_time:.3f} seconds"
    )

    print()

    if extraction_time > 60:

        print(
            "WARNING: Extraction is extremely slow."
        )

    elif extraction_time > 10:

        print(
            "WARNING: Extraction is slower than desired."
        )

    elif extraction_time > 3:

        print(
            "Extraction is moderate."
        )

    else:

        print(
            "Extraction speed looks reasonable."
        )


if __name__ == "__main__":
    main()
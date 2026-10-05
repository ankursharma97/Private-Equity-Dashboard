import json
import zipfile
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

COMPANYFACTS_ZIP = BASE_DIR / "data" / "companyfacts.zip"


TESTS = [
    {
        "ticker": "CAT",
        "cik": 18230,
        "concept": "SalesRevenueNet",
    },
    {
        "ticker": "NVDA",
        "cik": 1045810,
        "concept": "RevenueFromContractWithCustomerExcludingAssessedTax",
    },
    {
        "ticker": "JNJ",
        "cik": 200406,
        "concept": "OperatingIncomeLoss",
    },
]


def normalize_cik(cik):
    return str(int(cik)).zfill(10)


def load_companyfacts(zf, cik):

    target = f"CIK{normalize_cik(cik)}.json"

    matches = [
        name
        for name in zf.namelist()
        if name.endswith(target)
    ]

    if not matches:
        raise FileNotFoundError(target)

    with zf.open(matches[0]) as f:
        return json.load(f)


def inspect_metric(companyfacts, concept):

    facts = companyfacts.get("facts", {})
    us_gaap = facts.get("us-gaap", {})

    if concept not in us_gaap:

        print(f"CONCEPT NOT FOUND: {concept}")
        return

    units = us_gaap[concept].get("units", {})

    print()
    print(f"CONCEPT: {concept}")
    print(f"Units available: {list(units.keys())}")

    for unit_name, entries in units.items():

        print()
        print(f"UNIT: {unit_name}")
        print("-" * 100)

        rows = []

        for entry in entries:

            form = entry.get("form")
            fp = entry.get("fp")
            fy = entry.get("fy")
            start = entry.get("start")
            end = entry.get("end")
            filed = entry.get("filed")
            val = entry.get("val")
            frame = entry.get("frame")

            duration = None

            if start and end:

                start_date = pd.to_datetime(start)
                end_date = pd.to_datetime(end)

                duration = (
                    end_date - start_date
                ).days

            rows.append({
                "fy": fy,
                "form": form,
                "fp": fp,
                "start": start,
                "end": end,
                "duration_days": duration,
                "filed": filed,
                "frame": frame,
                "value": val,
            })

        df = pd.DataFrame(rows)

        if not df.empty:

            df = df.sort_values(
                ["end", "filed"],
                na_position="last"
            )

            print(
                df.to_string(index=False)
            )


def main():

    with zipfile.ZipFile(
        COMPANYFACTS_ZIP,
        "r"
    ) as zf:

        for test in TESTS:

            print()
            print("=" * 100)
            print(
                f"{test['ticker']} - "
                f"{test['concept']}"
            )
            print("=" * 100)

            companyfacts = load_companyfacts(
                zf,
                test["cik"]
            )

            inspect_metric(
                companyfacts,
                test["concept"]
            )


if __name__ == "__main__":
    main()
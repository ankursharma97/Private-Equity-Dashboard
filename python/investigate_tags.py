import zipfile
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ZIP_PATH = PROJECT_ROOT / "data" / "companyfacts.zip"

FILENAME = "CIK0000001750.json"

SEARCH_TERMS = [
    "OperatingIncome",
    "OperatingProfit",
    "IncomeLossFromContinuingOperations",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxes",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    "Revenue",
    "Debt",
]

with zipfile.ZipFile(ZIP_PATH, "r") as z:

    with z.open(FILENAME) as f:
        company = json.load(f)

    us_gaap = company["facts"]["us-gaap"]

    print("=" * 80)
    print(f"COMPANY: {company['entityName']}")
    print("=" * 80)

    for term in SEARCH_TERMS:

        print(f"\n{'=' * 80}")
        print(f"SEARCH: {term}")
        print("=" * 80)

        matches = [
            concept
            for concept in us_gaap
            if term.lower() in concept.lower()
        ]

        if not matches:
            print("No matches")
            continue

        for concept_name in matches:

            print(f"\n--- {concept_name} ---")

            concept = us_gaap[concept_name]

            print("Label:", concept.get("label"))

            units = concept.get("units", {})

            for unit, records in units.items():

                print(f"Unit: {unit}")

                # Show up to 5 recent records of any form
                records_sorted = sorted(
                    records,
                    key=lambda x: x.get("filed", ""),
                    reverse=True
                )

                for r in records_sorted[:5]:

                    print(
                        f"  value={r.get('val')} "
                        f"| form={r.get('form')} "
                        f"| fp={r.get('fp')} "
                        f"| fy={r.get('fy')} "
                        f"| start={r.get('start')} "
                        f"| end={r.get('end')} "
                        f"| filed={r.get('filed')}"
                    )
                    
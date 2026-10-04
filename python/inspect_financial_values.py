import zipfile
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ZIP_PATH = PROJECT_ROOT / "data" / "companyfacts.zip"

FILENAME = "CIK0000001750.json"

CONCEPTS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "OperatingIncomeLoss",
    "DepreciationDepletionAndAmortization",
    "NetIncomeLoss",
    "NetCashProvidedByUsedInOperatingActivities",
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "LongTermDebt",
    "LongTermDebtCurrent",
    "LongTermDebtNoncurrent",
    "CashAndCashEquivalentsAtCarryingValue",
]

with zipfile.ZipFile(ZIP_PATH, "r") as z:

    with z.open(FILENAME) as f:
        company = json.load(f)

    us_gaap = company["facts"]["us-gaap"]

    print("=" * 80)
    print(f"COMPANY: {company['entityName']}")
    print(f"CIK: {company['cik']}")
    print("=" * 80)

    for concept_name in CONCEPTS:

        print(f"\n{'=' * 80}")
        print(f"CONCEPT: {concept_name}")
        print("=" * 80)

        if concept_name not in us_gaap:
            print("NOT AVAILABLE")
            continue

        concept = us_gaap[concept_name]

        print(f"Label: {concept.get('label')}")
        print(f"Description: {concept.get('description')}")

        units = concept.get("units", {})

        for unit, records in units.items():

            print(f"\nUNIT: {unit}")

            # Show recent annual records
            annual_records = [
                r for r in records
                if r.get("form") == "10-K"
                and r.get("fp") == "FY"
            ]

            # Sort newest first
            annual_records = sorted(
                annual_records,
                key=lambda x: x.get("filed", ""),
                reverse=True
            )

            for record in annual_records[:8]:

                print(
                    f"  FY={record.get('fy')} "
                    f"| FY Period={record.get('fp')} "
                    f"| Start={record.get('start')} "
                    f"| End={record.get('end')} "
                    f"| Filed={record.get('filed')} "
                    f"| Value={record.get('val')}"
                )
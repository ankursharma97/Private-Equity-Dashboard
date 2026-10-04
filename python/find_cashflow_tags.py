import zipfile
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ZIP_PATH = PROJECT_ROOT / "data" / "companyfacts.zip"

filename = "CIK0000001750.json"

keywords = [
    "NetCashProvidedByUsedInOperatingActivities",
    "CashProvidedByUsedInOperatingActivities",
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsToAcquireProductiveAssets",
    "PropertyPlantAndEquipment",
    "CapitalExpenditures",
    "OperatingActivities",
]

with zipfile.ZipFile(ZIP_PATH, "r") as z:

    with z.open(filename) as f:
        company = json.load(f)

    us_gaap = company["facts"]["us-gaap"]

    print("=" * 70)
    print(f"COMPANY: {company['entityName']}")
    print("=" * 70)

    for keyword in keywords:

        matches = [
            concept
            for concept in us_gaap
            if keyword.lower() in concept.lower()
        ]

        print(f"\n[{keyword}]")

        if matches:
            for concept in matches:
                print("  -", concept)
        else:
            print("  No matches found")
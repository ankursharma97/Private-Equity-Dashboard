import zipfile
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ZIP_PATH = PROJECT_ROOT / "data" / "companyfacts.zip"

# Keywords for the financial concepts we care about
keywords = [
    "Revenue",
    "Sales",
    "OperatingIncome",
    "NetIncome",
    "Depreciation",
    "Amortization",
    "InterestExpense",
    "OperatingCashFlow",
    "CashAndCashEquivalents",
    "CapitalExpenditure",
    "Debt",
    "LongTermDebt",
    "StockholdersEquity",
]

with zipfile.ZipFile(ZIP_PATH, "r") as z:

    files = [
        f for f in z.namelist()
        if f.lower().endswith(".json")
    ]

    # Use AAR CORP. as our test company for now
    filename = "CIK0000001750.json"

    with z.open(filename) as f:
        company = json.load(f)

    us_gaap = company["facts"]["us-gaap"]

    print("=" * 70)
    print(f"COMPANY: {company['entityName']}")
    print(f"CIK: {company['cik']}")
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
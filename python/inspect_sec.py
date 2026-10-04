import zipfile
import json
from pathlib import Path

# Find the project folder automatically
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ZIP_PATH = PROJECT_ROOT / "data" / "companyfacts.zip"

print("Looking for:")
print(ZIP_PATH)

if not ZIP_PATH.exists():
    print("\nERROR: companyfacts.zip was not found.")
    exit()

with zipfile.ZipFile(ZIP_PATH, "r") as z:

    # Find JSON files inside the ZIP
    files = [
        f for f in z.namelist()
        if f.lower().endswith(".json")
    ]

    print(f"\nTotal JSON files: {len(files):,}")

    # Inspect one company
    first_file = files[0]

    print(f"\nInspecting: {first_file}")

    with z.open(first_file) as f:
        company = json.load(f)

    print("\nCompany name:")
    print(company.get("entityName"))

    print("\nCIK:")
    print(company.get("cik"))

    print("\nTop-level keys:")
    print(list(company.keys()))

    print("\nNamespaces:")
    print(list(company.get("facts", {}).keys()))

    # Count US-GAAP concepts
    us_gaap = company.get("facts", {}).get("us-gaap", {})

    print(f"\nUS-GAAP concepts available: {len(us_gaap):,}")

    print("\nFirst 30 US-GAAP concepts:")

    for concept in list(us_gaap.keys())[:30]:
        print(" -", concept)
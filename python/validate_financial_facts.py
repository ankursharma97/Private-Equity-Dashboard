import json
import zipfile
from pathlib import Path

import pandas as pd


# =============================================================================
# CONFIG
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
ZIP_FILE = BASE_DIR / "data" / "companyfacts.zip"

COMPANIES = {
    "JNJ": "0000200406",
    "AAPL": "0000320193",
    "CAT": "0000018230",
    "MSFT": "0000789019",
    "NVDA": "0001045810",
}

TARGET_CONCEPTS = {
    "operating_income": [
        "OperatingIncomeLoss",
    ],

    "interest": [
        "InterestExpenseNonOperating",
        "InterestExpenseNonoperating",
        "InterestExpense",
        "InterestPaidNet",
    ],

    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
        "PaymentsToAcquireBusinessesNetOfCashAcquired",
    ],
}


# =============================================================================
# HELPERS
# =============================================================================

def find_company_file(z, cik):
    """
    Find the actual Company Facts filename inside the ZIP.

    We do not assume a particular directory structure.
    """

    cik_padded = str(cik).zfill(10)

    candidates = [
        name
        for name in z.namelist()
        if name.lower().endswith(f"cik{cik_padded}.json".lower())
    ]

    if not candidates:
        # Fallback: look for the CIK anywhere in the filename.
        candidates = [
            name
            for name in z.namelist()
            if cik_padded in Path(name).name
            and name.lower().endswith(".json")
        ]

    if not candidates:
        raise KeyError(
            f"Could not find Company Facts JSON for CIK {cik_padded}"
        )

    if len(candidates) > 1:
        print()
        print(f"Multiple files found for CIK {cik_padded}:")
        for candidate in candidates:
            print(f"  {candidate}")
        print(f"Using: {candidates[0]}")

    return candidates[0]


def load_company_facts(cik):
    """
    Load one company's Company Facts JSON from companyfacts.zip.
    """

    with zipfile.ZipFile(ZIP_FILE, "r") as z:

        filename = find_company_file(z, cik)

        print(f"Loading {filename}")

        with z.open(filename) as f:
            return json.load(f)


def get_us_gaap_facts(company_facts):
    return company_facts.get("facts", {}).get("us-gaap", {})


def get_annual_records(concept_data):
    """
    Extract annual 10-K / 10-KA records.

    We use actual start/end dates rather than SEC 'fy'
    as the primary period identifier.
    """

    units = concept_data.get("units", {})

    records = []

    for unit, facts in units.items():

        for fact in facts:

            form = fact.get("form")

            if form not in {"10-K", "10-K/A"}:
                continue

            start = fact.get("start")
            end = fact.get("end")

            if not start or not end:
                continue

            start_date = pd.to_datetime(start)
            end_date = pd.to_datetime(end)

            duration_days = (end_date - start_date).days

            if not (300 <= duration_days <= 400):
                continue

            records.append({
                "unit": unit,
                "start": start,
                "end": end,
                "duration_days": duration_days,
                "filed": fact.get("filed"),
                "form": form,
                "fy": fact.get("fy"),
                "fp": fact.get("fp"),
                "frame": fact.get("frame"),
                "val": fact.get("val"),
                "accn": fact.get("accn"),
            })

    return records


def print_concept_records(ticker, facts, concept_name):

    print()
    print("-" * 100)
    print(f"{ticker} | {concept_name}")
    print("-" * 100)

    if concept_name not in facts:
        print("CONCEPT NOT FOUND")
        return

    concept_data = facts[concept_name]

    print(f"Label: {concept_data.get('label')}")
    print(f"Description: {concept_data.get('description')}")

    records = get_annual_records(concept_data)

    if not records:
        print("No annual 10-K / 10-KA records found.")
        return

    df = pd.DataFrame(records)

    df["end"] = pd.to_datetime(df["end"])
    df["filed"] = pd.to_datetime(df["filed"])

    df = df.sort_values(["end", "filed"])

    print()

    print(
        df[
            [
                "unit",
                "start",
                "end",
                "duration_days",
                "filed",
                "form",
                "fy",
                "fp",
                "frame",
                "val",
                "accn",
            ]
        ].to_string(index=False)
    )


def search_related_concepts(ticker, facts, keywords):

    print()
    print("=" * 100)
    print(f"{ticker} | RELATED CONCEPT SEARCH")
    print("=" * 100)

    matches = []

    for concept_name, concept_data in facts.items():

        text = " ".join([
            concept_name or "",
            concept_data.get("label", "") or "",
            concept_data.get("description", "") or "",
        ]).lower()

        if any(keyword.lower() in text for keyword in keywords):

            records = get_annual_records(concept_data)

            if records:

                latest_end = max(
                    pd.to_datetime(r["end"])
                    for r in records
                )

                matches.append({
                    "concept": concept_name,
                    "label": concept_data.get("label"),
                    "annual_records": len(records),
                    "latest_end": latest_end.date(),
                })

    if not matches:
        print("No related annual concepts found.")
        return

    result = pd.DataFrame(matches)

    result = result.sort_values(
        ["latest_end", "annual_records"],
        ascending=[False, False]
    )

    print(
        result.to_string(index=False)
    )


# =============================================================================
# MAIN
# =============================================================================

print("=" * 100)
print("SEC FINANCIAL FACT VALIDATION")
print("=" * 100)

print()
print(f"Company Facts ZIP:")
print(ZIP_FILE)

if not ZIP_FILE.exists():
    raise FileNotFoundError(
        f"Could not find Company Facts ZIP: {ZIP_FILE}"
    )


# =============================================================================
# 1. JNJ OPERATING INCOME
# =============================================================================

print()
print("=" * 100)
print("1. JNJ OPERATING INCOME VALIDATION")
print("=" * 100)

jnj_facts = get_us_gaap_facts(
    load_company_facts(COMPANIES["JNJ"])
)

print_concept_records(
    "JNJ",
    jnj_facts,
    "OperatingIncomeLoss"
)

search_related_concepts(
    "JNJ",
    jnj_facts,
    [
        "operating income",
        "income from operations",
        "operating profit",
    ]
)


# =============================================================================
# 2. INTEREST EXPENSE
# =============================================================================

print()
print("=" * 100)
print("2. INTEREST EXPENSE VALIDATION")
print("=" * 100)

for ticker in ["AAPL", "CAT", "JNJ", "MSFT", "NVDA"]:

    facts = get_us_gaap_facts(
        load_company_facts(COMPANIES[ticker])
    )

    print()
    print("#" * 100)
    print(f"{ticker}")
    print("#" * 100)

    for concept_name in TARGET_CONCEPTS["interest"]:

        if concept_name in facts:

            print_concept_records(
                ticker,
                facts,
                concept_name
            )


# =============================================================================
# 3. MSFT CAPEX
# =============================================================================

print()
print("=" * 100)
print("3. MSFT CAPEX VALIDATION")
print("=" * 100)

msft_facts = get_us_gaap_facts(
    load_company_facts(COMPANIES["MSFT"])
)

for concept_name in TARGET_CONCEPTS["capex"]:

    if concept_name in msft_facts:

        print_concept_records(
            "MSFT",
            msft_facts,
            concept_name
        )


search_related_concepts(
    "MSFT",
    msft_facts,
    [
        "property plant equipment",
        "property, plant and equipment",
        "capital expenditure",
        "capital expenditures",
        "productive assets",
        "purchase of property",
        "acquisition of property",
    ]
)


# =============================================================================
# COMPLETE
# =============================================================================

print()
print("=" * 100)
print("VALIDATION COMPLETE")
print("=" * 100)
import pandas as pd
from pathlib import Path


# CONFIGURATION

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "investment_universe.csv"
OUTPUT_FILE = BASE_DIR / "data" / "classified_investment_universe.csv"


# SIC CLASSIFICATION

# SEC SIC 6770 = Blank Checks
SPAC_SIC_CODES = {6770}

# NAME-BASED INDICATORS

# These are used only as secondary signals.
# SIC 6770 remains the strongest SPAC signal.

SPAC_NAME_PATTERNS = [
    "blank check",
    "blank-check",
    "special purpose acquisition",
    "special purpose acquisition company",
    "spac partners",
]


STRUCTURED_PRODUCT_PATTERNS = [
    "structured products",
    "structured product",
    "asset backed",
    "asset-backed",
    "securitization",
    "securitisation",
    "depositor trust",
    "asset backed trust",
    "asset-backed trust",
    "collateralized trust",
    "collateralised trust",
]


# HELPERS

def normalize_text(value):
    """Convert a value to lowercase text safely."""

    if pd.isna(value):
        return ""

    return str(value).strip().lower()


def get_sic_code(value):
    """
    Convert SIC to an integer where possible.

    SEC data may store SIC as values such as:
    6770.0
    """

    if pd.isna(value):
        return None

    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def contains_phrase(text, phrase):
    """Check whether a complete phrase appears in text."""

    return phrase.lower() in text


# CLASSIFICATION

def classify_entity(row):

    company = normalize_text(row.get("company"))
    entity_name = normalize_text(row.get("entity_name"))
    sic_description = normalize_text(row.get("sic_description"))

    sic_code = get_sic_code(row.get("sic"))

    combined_name = f"{company} {entity_name}"

    # 1. SEC SIC 6770 — Blank Checks

    if sic_code in SPAC_SIC_CODES:

        return pd.Series(
            [
                "SPAC / Acquisition Vehicle",
                False,
                "SEC SIC 6770: Blank Checks",
            ]
        )

    # 2. Explicit SEC SIC description

    if "blank checks" in sic_description:

        return pd.Series(
            [
                "SPAC / Acquisition Vehicle",
                False,
                "SEC SIC description identifies Blank Checks",
            ]
        )

    # 3. Explicit SPAC terminology
    #
    # IMPORTANT:
    # Do NOT search for "spac" as a simple substring.
    # That incorrectly matched names such as SpaceMobile.

    for pattern in SPAC_NAME_PATTERNS:

        if contains_phrase(combined_name, pattern):

            return pd.Series(
                [
                    "SPAC / Acquisition Vehicle",
                    False,
                    f"Explicit SPAC indicator: {pattern}",
                ]
            )

    # 4. Structured products
    #
    # Do NOT classify every company containing "trust"
    # as a structured product.
    #
    # REITs and royalty trusts can be legitimate investment
    # entities and should remain in the universe.

    for pattern in STRUCTURED_PRODUCT_PATTERNS:

        if contains_phrase(combined_name, pattern):

            return pd.Series(
                [
                    "Structured Product / Trust",
                    False,
                    f"Explicit structured-product indicator: {pattern}",
                ]
            )

    # 5. Default

    return pd.Series(
        [
            "Operating / Other Company",
            True,
            "No first-pass exclusion indicator detected",
        ]
    )

# MAIN

print("Loading investment universe...")

df = pd.read_csv(INPUT_FILE)

print(f"Total companies: {len(df):,}")


# VALIDATION

required_columns = [
    "company",
    "cik",
    "ticker",
    "sic",
    "sic_description",
    "entity_name",
]

missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing_columns:

    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )


# CLASSIFY

print()
print("Classifying entities...")

df[
    [
        "entity_type",
        "investment_eligible",
        "classification_reason",
    ]
] = df.apply(
    classify_entity,
    axis=1
)

# SAVE

df.to_csv(
    OUTPUT_FILE,
    index=False
)

# SUMMARY

print()
print("=" * 70)
print("CLASSIFICATION SUMMARY")
print("=" * 70)

summary = (
    df["entity_type"]
    .value_counts(dropna=False)
)

print()
print(summary.to_string())


print()
print("=" * 70)
print("INVESTMENT ELIGIBILITY")
print("=" * 70)

eligible_count = int(
    df["investment_eligible"].sum()
)

excluded_count = (
    len(df) - eligible_count
)

print()
print(f"Total 10-K filers:       {len(df):,}")
print(f"Investment eligible:     {eligible_count:,}")
print(f"Excluded:                {excluded_count:,}")

# SIC 6770 CHECK
print()
print("=" * 70)
print("SIC 6770 CHECK")
print("=" * 70)

sic_6770 = df[
    df["sic"].apply(get_sic_code) == 6770
]

print()
print(f"SIC 6770 companies:      {len(sic_6770):,}")
print(
    "Classified as SPAC:      "
    f"{(sic_6770['entity_type'] == 'SPAC / Acquisition Vehicle').sum():,}"
)

print()
print("=" * 70)
print("CLASSIFICATION COMPLETE")
print("=" * 70)

print()
print(f"Saved to:")
print(OUTPUT_FILE)
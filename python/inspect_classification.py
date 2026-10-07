import pandas as pd
from pathlib import Path


# CONFIGURATION
BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "classified_investment_universe.csv"

# Number of examples to display from each category
SAMPLE_SIZE = 30

# LOAD DATA
print("Loading classified investment universe...")

df = pd.read_csv(INPUT_FILE)

print(f"Total companies: {len(df):,}")

# BASIC VALIDATION
required_columns = [
    "company",
    "cik",
    "ticker",
    "sic",
    "sic_description",
    "entity_type",
    "investment_eligible",
    "classification_reason",
]

missing_columns = [
    column for column in required_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing expected columns: {missing_columns}"
    )


# CATEGORY SUMMARY
print()
print("=" * 75)
print("CATEGORY SUMMARY")
print("=" * 75)

summary = (
    df.groupby("entity_type")
    .agg(
        companies=("company", "count"),
        eligible=("investment_eligible", "sum"),
    )
    .sort_values("companies", ascending=False)
)

print(summary.to_string())


# DISPLAY FUNCTION
def show_examples(category, sample_size=SAMPLE_SIZE):
    subset = df[df["entity_type"] == category].copy()

    print()
    print("=" * 75)
    print(f"{category.upper()} — SAMPLE")
    print("=" * 75)

    print(f"Total in category: {len(subset):,}")
    print(f"Showing up to {sample_size} examples.")
    print()

    columns = [
        "company",
        "ticker",
        "sic",
        "sic_description",
        "classification_reason",
    ]

    sample = (
        subset[columns]
        .sort_values("company")
        .head(sample_size)
    )

    print(sample.to_string(index=False))


# INSPECT EACH CATEGORY
show_examples("SPAC / Acquisition Vehicle")

show_examples("Structured Product / Trust")

show_examples("Operating / Other Company")

# POTENTIAL REVIEW FLAGS
print()
print("=" * 75)
print("REVIEW FLAGS")
print("=" * 75)

# Companies classified as excluded
excluded = df[df["investment_eligible"] == False].copy()

print()
print(f"Excluded entities: {len(excluded):,}")

# Show companies with "Acquisition" in their name that were
# classified as eligible. This helps us check whether the
# name-based rules are behaving sensibly.
acquisition_eligible = df[
    (df["investment_eligible"] == True)
    &
    (
        df["company"]
        .astype(str)
        .str.contains("acquisition", case=False, na=False)
    )
].copy()

print()
print(
    "Eligible companies containing 'Acquisition' in the name:"
    f" {len(acquisition_eligible):,}"
)

if len(acquisition_eligible) > 0:
    print()

    print(
        acquisition_eligible[
            [
                "company",
                "ticker",
                "sic",
                "sic_description",
                "entity_type",
            ]
        ]
        .sort_values("company")
        .head(30)
        .to_string(index=False)
    )

print()
print("=" * 75)
print("INSPECTION COMPLETE")
print("=" * 75)

print()
print("No files were modified.")
print("Review the samples above before running production extraction.")
import pandas as pd
from pathlib import Path

# CONFIGURATION

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "classified_investment_universe.csv"

# LOAD DATA

print("Loading classified investment universe...")

df = pd.read_csv(INPUT_FILE)

print(f"Total companies: {len(df):,}")


# FIND ACQUISITION-NAMED COMPANIES

acquisition_entities = df[
    df["company"]
    .astype(str)
    .str.contains(
        "acquisition",
        case=False,
        na=False
    )
].copy()


# DISPLAY REVIEW TABLE

print()
print("=" * 110)
print("ACQUISITION-NAMED ENTITIES")
print("=" * 110)

print()
print(f"Total companies containing 'Acquisition': "
      f"{len(acquisition_entities):,}")

print()

columns = [
    "company",
    "ticker",
    "cik",
    "sic",
    "sic_description",
    "exchange",
    "has_10k",
    "form_10k_count",
    "entity_type",
    "investment_eligible",
]

# Only display columns that actually exist.
available_columns = [
    column for column in columns
    if column in acquisition_entities.columns
]

review_table = (
    acquisition_entities[available_columns]
    .sort_values(
        by=["investment_eligible", "company"],
        ascending=[True, True]
    )
)

print(
    review_table.to_string(index=False)
)

# SUMMARY BY SIC

print()
print("=" * 110)
print("SIC SUMMARY")
print("=" * 110)

sic_summary = (
    acquisition_entities
    .groupby(
        ["sic", "sic_description"],
        dropna=False
    )
    .size()
    .reset_index(name="companies")
    .sort_values(
        "companies",
        ascending=False
    )
)

print()
print(
    sic_summary.to_string(index=False)
)



# CURRENT CLASSIFICATION SUMMARY

print()
print("=" * 110)
print("CURRENT CLASSIFICATION")
print("=" * 110)

classification_summary = (
    acquisition_entities["entity_type"]
    .value_counts(dropna=False)
)

print()
print(
    classification_summary.to_string()
)

# POTENTIAL REVIEW FLAGS


print()
print("=" * 110)
print("POTENTIAL REVIEW FLAGS")
print("=" * 110)

# Acquisition entities that are currently classified as eligible.
eligible_acquisition = acquisition_entities[
    acquisition_entities["investment_eligible"] == True
].copy()

print()
print(
    "Currently eligible acquisition-named entities: "
    f"{len(eligible_acquisition):,}"
)

print()

if len(eligible_acquisition) > 0:

    print(
        eligible_acquisition[
            available_columns
        ].to_string(index=False)
    )

# SAVE REVIEW COPY

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "acquisition_entities_review.csv"
)

acquisition_entities.to_csv(
    OUTPUT_FILE,
    index=False
)

print()
print("=" * 110)
print("REVIEW COMPLETE")
print("=" * 110)

print()
print(f"Review file saved to:")
print(OUTPUT_FILE)

print()
print(
    "No classification decisions were changed."
)
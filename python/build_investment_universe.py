import pandas as pd
from pathlib import Path

# PATHS
BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "sec_submission_metadata.csv"
OUTPUT_FILE = BASE_DIR / "data" / "investment_universe.csv"

# LOAD DATA
print("Loading SEC submission metadata...")

df = pd.read_csv(INPUT_FILE)

print(f"Total SEC entities: {len(df):,}")

# BROAD INVESTMENT UNIVERSE (using companies with a 10-K filing history)
universe = df[df["has_10k"] == True].copy()

# BASIC CLASSIFICATION
universe["universe_status"] = "10-K Filer"

universe["sic_available"] = universe["sic"].notna()

universe["exchange_available"] = universe["exchange"].notna()

# SORT
universe = universe.sort_values(
    by=["sic_description", "company"],
    na_position="last"
)

# SAVE
universe.to_csv(
    OUTPUT_FILE,
    index=False
)

# SUMMARY
print()
print("Investment universe created.")
print(f"10-K companies: {len(universe):,}")
print(f"SIC available: {universe['sic_available'].sum():,}")
print(f"SIC missing: {(~universe['sic_available']).sum():,}")
print(f"Exchange available: {universe['exchange_available'].sum():,}")
print(f"Exchange missing: {(~universe['exchange_available']).sum():,}")
print()
print(f"Saved to: {OUTPUT_FILE}")
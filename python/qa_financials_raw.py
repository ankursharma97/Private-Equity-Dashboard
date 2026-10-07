import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "financials_raw.csv"

def main():
    print("FINANCIAL DATASET QA")
    print("=" * 60)

    df = pd.read_csv(INPUT_FILE)

    print(f"Rows: {len(df):,}")
    print(f"Companies: {df['ticker'].nunique():,}")
    print()

    print("COLUMNS")
    print("-" * 60)
    print(", ".join(df.columns))
    print()

    print("ROWS PER COMPANY")
    print("-" * 60)

    rows_per_company = df.groupby("ticker").size()

    print(f"Minimum rows: {rows_per_company.min()}")
    print(f"Maximum rows: {rows_per_company.max()}")
    print(f"Average rows: {rows_per_company.mean():.2f}")
    print()

    print("Companies with fewer than 5 rows:")
    fewer_than_5 = rows_per_company[rows_per_company < 5]

    if fewer_than_5.empty:
        print("None")
    else:
        print(f"Count: {len(fewer_than_5):,}")
        print(fewer_than_5.head(20).to_string())

    print()

    print("Companies with more than 5 rows:")
    more_than_5 = rows_per_company[rows_per_company > 5]

    if more_than_5.empty:
        print("None")
    else:
        print(f"Count: {len(more_than_5):,}")
        print(more_than_5.head(20).to_string())

    print()

    print("DUPLICATE COMPANY / PERIOD")
    print("-" * 60)

    duplicate_keys = df[
        df.duplicated(
            subset=["ticker", "period_end"],
            keep=False
        )
    ].sort_values(["ticker", "period_end"])

    print(f"Duplicate rows: {len(duplicate_keys):,}")

    if not duplicate_keys.empty:
        print()
        print(
            duplicate_keys[
                ["ticker", "company", "period_end"]
            ].head(30).to_string(index=False)
        )

    print()

    print("DUPLICATE COMPANY / FISCAL YEAR")
    print("-" * 60)

    duplicate_years = df[
        df.duplicated(
            subset=["ticker", "fiscal_year"],
            keep=False
        )
    ].sort_values(["ticker", "fiscal_year"])

    print(f"Duplicate rows: {len(duplicate_years):,}")

    if not duplicate_years.empty:
        print()
        print(
            duplicate_years[
                ["ticker", "company", "fiscal_year", "period_end"]
            ].head(30).to_string(index=False)
        )

    print()

    print("FIVE-YEAR COVERAGE")
    print("-" * 60)

    coverage = (
        df.groupby("ticker")
        .agg(
            company=("company", "first"),
            periods=("period_end", "nunique"),
            earliest_period=("period_end", "min"),
            latest_period=("period_end", "max")
        )
        .reset_index()
    )

    print(
        coverage["periods"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()

    print("MISSING DATA")
    print("-" * 60)

    financial_columns = [
        "revenue",
        "operating_income",
        "net_income",
        "da",
        "operating_cash_flow",
        "capex",
        "interest_expense",
        "cash",
        "debt",
        "equity"
    ]

    for column in financial_columns:
        if column not in df.columns:
            print(f"{column}: COLUMN NOT FOUND")
            continue

        missing = df[column].isna().sum()
        percentage = missing / len(df) * 100

        print(
            f"{column:<22} "
            f"{missing:>7,}/{len(df):,} "
            f"({percentage:>5.1f}%)"
        )

    print()

    print("NUMERIC SANITY CHECKS")
    print("-" * 60)

    numeric_columns = [
        "revenue",
        "operating_income",
        "net_income",
        "da",
        "operating_cash_flow",
        "capex",
        "interest_expense",
        "cash",
        "debt",
        "equity"
    ]

    for column in numeric_columns:
        if column not in df.columns:
            continue

        values = pd.to_numeric(df[column], errors="coerce")

        negative = (values < 0).sum()
        zero = (values == 0).sum()

        print(
            f"{column:<22} "
            f"negative: {negative:>7,} | "
            f"zero: {zero:>7,}"
        )

    print()

    print("CAPEX SIGN CHECK")
    print("-" * 60)

    if "capex" in df.columns:
        capex = pd.to_numeric(df["capex"], errors="coerce")

        print(f"Negative CapEx: {(capex < 0).sum():,}")
        print(f"Positive CapEx: {(capex > 0).sum():,}")
        print(f"Zero CapEx: {(capex == 0).sum():,}")
        print()

        print(
            "Largest CapEx values:"
        )
        print(
            capex.nlargest(10).to_string()
        )

    print()

    print("EXTREME VALUES")
    print("-" * 60)

    for column in [
        "revenue",
        "operating_income",
        "net_income",
        "operating_cash_flow",
        "capex"
    ]:
        if column not in df.columns:
            continue

        values = pd.to_numeric(df[column], errors="coerce")

        print()
        print(column)
        print(
            values.nlargest(5).to_string()
        )

    print()

    print("=" * 60)
    print("QA COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
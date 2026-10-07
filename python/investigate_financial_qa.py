import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "financials_raw.csv"


def main():
    # Load the production financial dataset
    df = pd.read_csv(INPUT_FILE)

    print("FINANCIAL QA INVESTIGATION")
    print("=" * 60)
    print(f"Rows: {len(df):,}")
    print(f"Companies: {df['ticker'].nunique():,}")
    print()

    # Find companies where fiscal_year appears more than once
    duplicate_years = (
        df[df.duplicated(["ticker", "fiscal_year"], keep=False)]
        .sort_values(["ticker", "fiscal_year", "period_end"])
    )

    print("DUPLICATE FISCAL YEAR CASES")
    print("-" * 60)
    print(f"Rows involved: {len(duplicate_years):,}")
    print(f"Companies involved: {duplicate_years['ticker'].nunique():,}")
    print()

    if not duplicate_years.empty:
        print(
            duplicate_years[
                [
                    "ticker",
                    "company",
                    "period_end",
                    "fiscal_year",
                    "sec_fy",
                    "sec_fp",
                    "source_filed",
                    "revenue",
                    "revenue_concept",
                ]
            ].head(50).to_string(index=False)
        )

    print()

    # Find companies with only one or two extracted periods
    period_counts = df.groupby("ticker").size()

    short_history = period_counts[period_counts <= 2]

    print("COMPANIES WITH 1–2 PERIODS")
    print("-" * 60)
    print(f"Companies: {len(short_history):,}")
    print()

    if not short_history.empty:
        short_tickers = short_history.index

        short_df = (
            df[df["ticker"].isin(short_tickers)]
            .sort_values(["ticker", "period_end"])
        )

        print(
            short_df[
                [
                    "ticker",
                    "company",
                    "period_end",
                    "fiscal_year",
                    "sec_fy",
                    "sec_fp",
                    "revenue",
                    "net_income",
                    "operating_cash_flow",
                ]
            ].to_string(index=False)
        )

    print()

    # Find the largest net income values
    print("LARGEST NET INCOME VALUES")
    print("-" * 60)

    net_income = pd.to_numeric(
        df["net_income"],
        errors="coerce"
    )

    largest_net_income = (
        df.loc[net_income.nlargest(10).index]
        [
            [
                "ticker",
                "company",
                "period_end",
                "fiscal_year",
                "net_income",
                "net_income_concept",
                "source_filed",
            ]
        ]
        .sort_values("net_income", ascending=False)
    )

    print(largest_net_income.to_string(index=False))
    print()

    # Find every negative CapEx value
    print("NEGATIVE CAPEX")
    print("-" * 60)

    capex = pd.to_numeric(
        df["capex"],
        errors="coerce"
    )

    negative_capex = (
        df.loc[capex < 0]
        [
            [
                "ticker",
                "company",
                "period_end",
                "fiscal_year",
                "capex",
                "capex_concept",
                "operating_cash_flow",
                "source_filed",
            ]
        ]
        .sort_values("capex")
    )

    print(f"Rows: {len(negative_capex):,}")

    if negative_capex.empty:
        print("None")
    else:
        print(negative_capex.to_string(index=False))

    print()

    # Show the largest revenue and CapEx values together
    print("LARGEST REVENUE / CAPEX CASES")
    print("-" * 60)

    largest_revenue = pd.to_numeric(
        df["revenue"],
        errors="coerce"
    )

    largest_capex = pd.to_numeric(
        df["capex"],
        errors="coerce"
    )

    suspicious = (
        df.loc[
            largest_revenue.nlargest(10).index.union(
                largest_capex.nlargest(10).index
            )
        ]
        [
            [
                "ticker",
                "company",
                "period_end",
                "fiscal_year",
                "revenue",
                "revenue_concept",
                "capex",
                "capex_concept",
            ]
        ]
        .sort_values("revenue", ascending=False)
    )

    print(suspicious.to_string(index=False))

    print()
    print("=" * 60)
    print("INVESTIGATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
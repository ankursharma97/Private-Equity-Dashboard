import json
import zipfile
from pathlib import Path

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ZIP_FILE = BASE_DIR / "data" / "companyfacts.zip"

TEST_COMPANIES = [
    "AAPL",
    "NVDA",
    "MSFT",
    "JNJ",
    "CAT",
]


# ============================================================
# DIAGNOSTIC SEARCH TERMS
# ============================================================

SEARCH_TERMS = {

    "revenue": [
        "revenue",
        "sales revenue",
        "sales",
    ],

    "operating_income": [
        "operating income",
        "income from operations",
        "operating profit",
    ],

    "da": [
        "depreciation",
        "amortization",
    ],

    "capex": [
        "payments to acquire property plant",
        "payments to acquire productive assets",
        "capital expenditures",
        "property plant and equipment",
    ],

    "interest_expense": [
        "interest expense",
        "interest costs",
        "interest and debt expense",
    ],
}


# Number of concepts to display for each metric/company.
TOP_N = 15


# ============================================================
# BASIC HELPERS
# ============================================================

def load_company_json(zf, cik):

    cik_padded = str(cik).zfill(10)

    matching_files = [
        name
        for name in zf.namelist()
        if name.endswith(
            f"CIK{cik_padded}.json"
        )
    ]

    if not matching_files:
        raise FileNotFoundError(
            f"Company Facts JSON not found for CIK {cik_padded}"
        )

    with zf.open(matching_files[0]) as f:
        return json.load(f)


def get_us_gaap_facts(company_json):

    return (
        company_json
        .get("facts", {})
        .get("us-gaap", {})
    )


def parse_date(value):

    if not value:
        return None

    try:
        return pd.to_datetime(value)

    except Exception:
        return None


def get_duration_days(start, end):

    start_date = parse_date(start)
    end_date = parse_date(end)

    if start_date is None or end_date is None:
        return None

    return (
        end_date - start_date
    ).days + 1


# ============================================================
# ANNUAL RECORD EXTRACTION
# ============================================================

def get_usd_records(concept_data):

    units = concept_data.get(
        "units",
        {}
    )

    if "USD" in units:
        return units["USD"]

    for _, records in units.items():
        return records

    return []


def get_valid_annual_records(concept_data):

    records = get_usd_records(
        concept_data
    )

    valid = []

    for record in records:

        start = record.get("start")
        end = record.get("end")

        if not start or not end:
            continue

        duration = get_duration_days(
            start,
            end
        )

        if duration is None:
            continue

        # Annual period.
        if not 300 <= duration <= 400:
            continue

        if record.get("form") not in [
            "10-K",
            "10-K/A",
        ]:
            continue

        value = record.get("val")

        if value is None:
            continue

        valid.append({
            "start": start,
            "end": end,
            "filed": record.get("filed"),
            "form": record.get("form"),
            "value": value,
        })

    return valid


def deduplicate_records(records):

    if not records:
        return []

    df = pd.DataFrame(records)

    df["end_date"] = pd.to_datetime(
        df["end"]
    )

    df["filed_date"] = pd.to_datetime(
        df["filed"],
        errors="coerce"
    )

    df = df.sort_values(
        [
            "end_date",
            "filed_date",
        ]
    )

    df = df.drop_duplicates(
        subset=["end_date"],
        keep="last"
    )

    return df.to_dict(
        "records"
    )


# ============================================================
# CONCEPT SEARCH
# ============================================================

def concept_matches_metric(
    concept_name,
    concept_data,
    search_terms
):

    label = concept_data.get(
        "label",
        ""
    )

    description = concept_data.get(
        "description",
        ""
    )

    searchable_text = (
        f"{concept_name} "
        f"{label} "
        f"{description}"
    ).lower()

    matched_terms = []

    for term in search_terms:

        if term.lower() in searchable_text:

            matched_terms.append(
                term
            )

    return matched_terms


def discover_metric_concepts(
    us_gaap,
    metric,
    search_terms
):

    candidates = []

    for concept_name, concept_data in us_gaap.items():

        matched_terms = concept_matches_metric(
            concept_name,
            concept_data,
            search_terms
        )

        if not matched_terms:
            continue

        records = get_valid_annual_records(
            concept_data
        )

        records = deduplicate_records(
            records
        )

        if not records:
            continue

        df = pd.DataFrame(records)

        df["end_date"] = pd.to_datetime(
            df["end"]
        )

        latest_end = df[
            "end_date"
        ].max()

        # Recent five-year-ish coverage.
        window_start = (
            latest_end
            - pd.DateOffset(years=5)
        )

        recent = df[
            df["end_date"] >= window_start
        ]

        recent_coverage = (
            recent["end_date"]
            .nunique()
        )

        candidates.append({

            "concept": concept_name,

            "label": concept_data.get(
                "label",
                ""
            ),

            "description": concept_data.get(
                "description",
                ""
            ),

            "latest_end": latest_end,

            "period_count": len(records),

            "recent_coverage": (
                recent_coverage
            ),

            "matched_terms": (
                ", ".join(
                    matched_terms
                )
            ),

            "records": records,
        })

    # --------------------------------------------------------
    # Rank primarily by recent coverage and current period.
    #
    # This is diagnostic only.
    # We are NOT using this as the final production
    # concept-selection rule.
    # --------------------------------------------------------

    candidates = sorted(
        candidates,
        key=lambda x: (
            x["recent_coverage"],
            x["latest_end"],
            x["period_count"],
        ),
        reverse=True
    )

    return candidates


# ============================================================
# DISPLAY
# ============================================================

def print_candidates(
    company_name,
    ticker,
    metric,
    candidates
):

    print()
    print("-" * 90)

    print(
        f"{company_name} ({ticker})"
    )

    print(
        f"METRIC: {metric.upper()}"
    )

    print("-" * 90)

    if not candidates:

        print(
            "No candidate concepts found."
        )

        return

    for index, candidate in enumerate(
        candidates[:TOP_N],
        start=1
    ):

        records = candidate[
            "records"
        ]

        latest_records = sorted(
            records,
            key=lambda x: x["end"],
            reverse=True
        )[:3]

        latest_periods = [
            record["end"]
            for record in latest_records
        ]

        print()
        print(
            f"{index}. "
            f"{candidate['concept']}"
        )

        print(
            f"   Label: "
            f"{candidate['label']}"
        )

        print(
            f"   Latest period: "
            f"{candidate['latest_end'].strftime('%Y-%m-%d')}"
        )

        print(
            f"   Recent coverage: "
            f"{candidate['recent_coverage']}"
        )

        print(
            f"   Total annual periods: "
            f"{candidate['period_count']}"
        )

        print(
            f"   Matched terms: "
            f"{candidate['matched_terms']}"
        )

        print(
            f"   Recent periods: "
            f"{', '.join(latest_periods)}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 90)

    print(
        "SEC CURRENT XBRL CONCEPT DISCOVERY"
    )

    print("=" * 90)

    universe_file = (
        BASE_DIR
        / "data"
        / "sec_submission_metadata.csv"
    )

    universe = pd.read_csv(
        universe_file
    )

    test_df = universe[
        universe["ticker"].isin(
            TEST_COMPANIES
        )
    ].copy()

    if test_df.empty:

        raise ValueError(
            "No test companies found."
        )

    with zipfile.ZipFile(
        ZIP_FILE,
        "r"
    ) as zf:

        for _, company_row in (
            test_df.iterrows()
        ):

            ticker = company_row[
                "ticker"
            ]

            company_name = company_row[
                "company"
            ]

            cik = int(
                company_row["cik"]
            )

            print()
            print()
            print("=" * 90)

            print(
                f"{company_name} ({ticker})"
            )

            print("=" * 90)

            try:

                company_json = (
                    load_company_json(
                        zf,
                        cik
                    )
                )

                us_gaap = (
                    get_us_gaap_facts(
                        company_json
                    )
                )

                for metric, terms in (
                    SEARCH_TERMS.items()
                ):

                    candidates = (
                        discover_metric_concepts(
                            us_gaap,
                            metric,
                            terms
                        )
                    )

                    print_candidates(
                        company_name,
                        ticker,
                        metric,
                        candidates
                    )

            except Exception as e:

                print(
                    f"ERROR: {e}"
                )


if __name__ == "__main__":
    main()
    
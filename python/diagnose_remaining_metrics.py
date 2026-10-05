import json
import zipfile
from pathlib import Path

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ZIP_FILE = BASE_DIR / "data" / "companyfacts.zip"
UNIVERSE_FILE = BASE_DIR / "data" / "investment_universe.csv"

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "remaining_metrics_diagnostic.txt"
)

TEST_COMPANIES = [
    "AAPL",
    "NVDA",
    "MSFT",
    "CAT",
    "JNJ",
]

ANNUAL_FORMS = {"10-K", "10-K/A"}

YEARS_TO_INSPECT = 6


# ============================================================
# BASIC HELPERS
# ============================================================

def parse_date(value):
    if not value:
        return None

    try:
        return pd.to_datetime(value)
    except Exception:
        return None


def get_duration_days(start, end):
    if not start or not end:
        return None

    start_date = parse_date(start)
    end_date = parse_date(end)

    if start_date is None or end_date is None:
        return None

    return (end_date - start_date).days + 1


def is_annual_period(record):
    """
    Annual income-statement / cash-flow period.

    We intentionally use start/end dates rather than SEC fy.
    """

    start = record.get("start")
    end = record.get("end")

    if not start or not end:
        return False

    duration = get_duration_days(start, end)

    if duration is None:
        return False

    return 300 <= duration <= 400


def is_instant_period(record):
    """
    Balance-sheet / point-in-time observation.
    """

    return (
        bool(record.get("end"))
        and not record.get("start")
    )


def normalize_value(record):
    if "val" in record:
        return record["val"]

    if "value" in record:
        return record["value"]

    return None


# ============================================================
# COMPANY FACTS
# ============================================================

def load_company_json(zf, cik):
    cik_padded = (
        str(cik)
        .split(".")[0]
        .zfill(10)
    )

    target = f"CIK{cik_padded}.json"

    matching_files = [
        name
        for name in zf.namelist()
        if name.endswith(target)
    ]

    if not matching_files:
        raise FileNotFoundError(
            f"Could not find Company Facts JSON "
            f"for CIK {cik_padded}"
        )

    with zf.open(matching_files[0]) as f:
        return json.load(f)


def get_us_gaap_facts(company_json):
    return (
        company_json
        .get("facts", {})
        .get("us-gaap", {})
    )


# ============================================================
# CONCEPT INSPECTION
# ============================================================

def get_concept_records(us_gaap, concept_name):
    concept = us_gaap.get(concept_name)

    if not concept:
        return []

    units = concept.get("units", {})

    if not units:
        return []

    # Prefer USD.
    if "USD" in units:
        return units["USD"]

    # Otherwise use first available unit.
    for _, records in units.items():
        return records

    return []


def inspect_concept(
    us_gaap,
    concept_name,
    annual_only=True
):
    """
    Extract useful metadata for one concept.
    """

    concept = us_gaap.get(concept_name)

    if not concept:
        return None

    label = concept.get(
        "label",
        ""
    )

    description = concept.get(
        "description",
        ""
    )

    records = get_concept_records(
        us_gaap,
        concept_name
    )

    usable = []

    for record in records:

        if annual_only:

            if not is_annual_period(record):
                continue

            if record.get("form") not in ANNUAL_FORMS:
                continue

        else:

            if not is_instant_period(record):
                continue

            if record.get("form") not in ANNUAL_FORMS:
                continue

        value = normalize_value(record)

        if value is None:
            continue

        usable.append(record)

    if not usable:
        return None

    periods = []

    for record in usable:

        end = record.get("end")

        if end:
            periods.append(end)

    periods = sorted(
        set(periods),
        reverse=True
    )

    latest_period = (
        periods[0]
        if periods
        else None
    )

    recent_periods = periods[
        :YEARS_TO_INSPECT
    ]

    return {
        "concept": concept_name,
        "label": label,
        "description": description,
        "latest_period": latest_period,
        "recent_coverage": len(
            recent_periods
        ),
        "total_periods": len(periods),
        "recent_periods": recent_periods,
        "records": usable,
    }


# ============================================================
# TARGETED SEARCH
# ============================================================

def concept_matches(
    concept_name,
    label,
    include_terms,
    exclude_terms=None
):
    """
    Diagnostic-only concept search.

    This is NOT used to automatically populate V5.
    """

    exclude_terms = (
        exclude_terms or []
    )

    text = (
        f"{concept_name} "
        f"{label}"
    ).lower()

    include_match = any(
        term.lower() in text
        for term in include_terms
    )

    if not include_match:
        return False

    exclude_match = any(
        term.lower() in text
        for term in exclude_terms
    )

    if exclude_match:
        return False

    return True


def find_matching_concepts(
    us_gaap,
    include_terms,
    exclude_terms=None,
    annual_only=True
):
    """
    Find candidate concepts for diagnostic inspection.
    """

    results = []

    for concept_name, concept in us_gaap.items():

        label = concept.get(
            "label",
            ""
        )

        if not concept_matches(
            concept_name,
            label,
            include_terms,
            exclude_terms
        ):
            continue

        inspected = inspect_concept(
            us_gaap,
            concept_name,
            annual_only=annual_only
        )

        if inspected is None:
            continue

        results.append(
            inspected
        )

    # Most recent first, then coverage.
    results.sort(
        key=lambda x: (
            pd.Timestamp(
                x["latest_period"]
            )
            if x["latest_period"]
            else pd.Timestamp.min,
            x["recent_coverage"],
            x["total_periods"],
        ),
        reverse=True,
    )

    return results


# ============================================================
# FORMATTING
# ============================================================

def format_candidate(
    rank,
    candidate
):
    lines = []

    lines.append(
        f"{rank}. {candidate['concept']}"
    )

    lines.append(
        f"   Label: {candidate['label']}"
    )

    if candidate["description"]:
        description = (
            candidate["description"]
            .replace("\n", " ")
            .strip()
        )

        # Keep diagnostic output readable.
        if len(description) > 300:
            description = (
                description[:300]
                + "..."
            )

        lines.append(
            f"   Definition: {description}"
        )

    lines.append(
        f"   Latest period: "
        f"{candidate['latest_period']}"
    )

    lines.append(
        f"   Recent coverage: "
        f"{candidate['recent_coverage']}"
    )

    lines.append(
        f"   Total annual periods: "
        f"{candidate['total_periods']}"
    )

    lines.append(
        "   Recent periods: "
        + ", ".join(
            candidate["recent_periods"]
        )
    )

    lines.append("")

    return lines


# ============================================================
# JNJ PERIOD DIAGNOSTIC
# ============================================================

def inspect_jnj_periods(
    us_gaap,
    concept_name
):
    """
    Print all annual records for a selected JNJ concept.

    This helps us understand the apparently duplicated
    2023 period-end dates.
    """

    records = get_concept_records(
        us_gaap,
        concept_name
    )

    usable = []

    for record in records:

        if not is_annual_period(record):
            continue

        if record.get("form") not in ANNUAL_FORMS:
            continue

        value = normalize_value(record)

        if value is None:
            continue

        usable.append(
            {
                "start": record.get("start"),
                "end": record.get("end"),
                "filed": record.get("filed"),
                "form": record.get("form"),
                "fy": record.get("fy"),
                "fp": record.get("fp"),
                "value": value,
                "accn": record.get("accn"),
            }
        )

    usable.sort(
        key=lambda x: (
            x["end"] or "",
            x["filed"] or "",
        ),
        reverse=True
    )

    return usable


# ============================================================
# MAIN DIAGNOSTIC
# ============================================================

def main():

    print("=" * 80)
    print("TARGETED SEC XBRL DIAGNOSTIC")
    print("=" * 80)

    universe = pd.read_csv(
        UNIVERSE_FILE
    )

    universe["ticker"] = (
        universe["ticker"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    test_df = universe[
        universe["ticker"].isin(
            TEST_COMPANIES
        )
    ].copy()

    output_lines = []

    def emit(text=""):
        print(text)
        output_lines.append(text)

    emit()
    emit(
        "This is a diagnostic only."
    )
    emit(
        "No production dataset is modified."
    )
    emit()

    with zipfile.ZipFile(
        ZIP_FILE,
        "r"
    ) as zf:

        # ====================================================
        # COMPANY LOOP
        # ====================================================

        for _, company_row in test_df.iterrows():

            ticker = str(
                company_row["ticker"]
            ).upper()

            cik = company_row["cik"]

            company_json = load_company_json(
                zf,
                cik
            )

            us_gaap = get_us_gaap_facts(
                company_json
            )

            emit()
            emit("=" * 80)
            emit(f"{ticker}")
            emit("=" * 80)

            # =================================================
            # 1. DEBT
            # =================================================

            emit()
            emit(
                "SECTION 1: DEBT CANDIDATES"
            )
            emit(
                "-" * 80
            )

            debt_candidates = (
                find_matching_concepts(
                    us_gaap,
                    include_terms=[
                        "debt",
                        "borrow",
                        "borrowing",
                        "notes payable",
                        "long term debt",
                        "longterm debt",
                    ],
                    exclude_terms=[
                        "debt securities",
                        "available for sale",
                        "debt instrument",
                        "debt obligation",
                        "debt maturity",
                        "debt securities held",
                    ],
                    annual_only=False,
                )
            )

            if not debt_candidates:

                emit(
                    "NO CURRENT DEBT CANDIDATES FOUND."
                )

            else:

                for rank, candidate in enumerate(
                    debt_candidates[:20],
                    start=1
                ):
                    for line in format_candidate(
                        rank,
                        candidate
                    ):
                        emit(line)

            # =================================================
            # 2. INTEREST EXPENSE
            # =================================================

            emit()
            emit(
                "SECTION 2: INTEREST EXPENSE CANDIDATES"
            )
            emit(
                "-" * 80
            )

            interest_candidates = (
                find_matching_concepts(
                    us_gaap,
                    include_terms=[
                        "interest expense",
                        "interest costs",
                        "interest paid",
                        "interest incurred",
                    ],
                    exclude_terms=[
                        "interest income",
                        "investment income",
                        "interest receivable",
                        "interest revenue",
                        "interest rate",
                        "interest income expense",
                    ],
                    annual_only=True,
                )
            )

            if not interest_candidates:

                emit(
                    "NO CURRENT INTEREST-EXPENSE "
                    "CANDIDATES FOUND."
                )

            else:

                for rank, candidate in enumerate(
                    interest_candidates[:20],
                    start=1
                ):
                    for line in format_candidate(
                        rank,
                        candidate
                    ):
                        emit(line)

            # =================================================
            # 3. OPERATING INCOME
            # =================================================

            emit()
            emit(
                "SECTION 3: OPERATING INCOME CANDIDATES"
            )
            emit(
                "-" * 80
            )

            operating_income_candidates = (
                find_matching_concepts(
                    us_gaap,
                    include_terms=[
                        "operating income",
                        "operating profit",
                        "income from operations",
                        "profit from operations",
                    ],
                    exclude_terms=[
                        "nonoperating",
                        "non-operating",
                        "segment reporting information",
                        "discontinued operation",
                    ],
                    annual_only=True,
                )
            )

            if not operating_income_candidates:

                emit(
                    "NO CURRENT OPERATING-INCOME "
                    "CANDIDATES FOUND."
                )

            else:

                for rank, candidate in enumerate(
                    operating_income_candidates[:20],
                    start=1
                ):
                    for line in format_candidate(
                        rank,
                        candidate
                    ):
                        emit(line)

            # =================================================
            # 4. JNJ PERIOD INVESTIGATION
            # =================================================

            if ticker == "JNJ":

                emit()
                emit(
                    "SECTION 4: JNJ PERIOD INVESTIGATION"
                )
                emit(
                    "-" * 80
                )

                # Revenue is used because it is a current
                # backbone concept in V5.
                emit(
                    "RevenueFromContractWithCustomer"
                    "ExcludingAssessedTax:"
                )

                revenue_records = (
                    inspect_jnj_periods(
                        us_gaap,
                        "RevenueFromContractWithCustomer"
                        "ExcludingAssessedTax"
                    )
                )

                for record in revenue_records[:10]:

                    emit(
                        f"  start={record['start']} | "
                        f"end={record['end']} | "
                        f"filed={record['filed']} | "
                        f"form={record['form']} | "
                        f"fy={record['fy']} | "
                        f"fp={record['fp']} | "
                        f"value={record['value']} | "
                        f"accn={record['accn']}"
                    )

                emit()
                emit(
                    "OperatingIncomeLoss:"
                )

                operating_records = (
                    inspect_jnj_periods(
                        us_gaap,
                        "OperatingIncomeLoss"
                    )
                )

                if not operating_records:

                    emit(
                        "  NO CURRENT ANNUAL "
                        "RECORDS."
                    )

                else:

                    for record in operating_records[:15]:

                        emit(
                            f"  start={record['start']} | "
                            f"end={record['end']} | "
                            f"filed={record['filed']} | "
                            f"form={record['form']} | "
                            f"fy={record['fy']} | "
                            f"fp={record['fp']} | "
                            f"value={record['value']} | "
                            f"accn={record['accn']}"
                        )

    # ========================================================
    # SAVE
    # ========================================================

    OUTPUT_FILE.write_text(
        "\n".join(output_lines),
        encoding="utf-8"
    )

    print()
    print("=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)
    print()
    print(
        f"Saved to:\n{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
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
    / "test_financial_extraction_v6.csv"
)

TEST_COMPANIES = [
    "AAPL",
    "MSFT",
    "NVDA",
    "CAT",
    "JNJ",
]

ANNUAL_FORMS = {
    "10-K",
    "10-K/A",
}


# ============================================================
# CONTROLLED XBRL CONCEPTS
# ============================================================

CONCEPTS = {

    # --------------------------------------------------------
    # Revenue
    # --------------------------------------------------------

    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
        "SalesRevenueServicesNet",
    ],

    # --------------------------------------------------------
    # Operating income
    # --------------------------------------------------------

    "operating_income": [
        "OperatingIncomeLoss",
    ],

    # --------------------------------------------------------
    # Net income
    # --------------------------------------------------------

    "net_income": [
        "NetIncomeLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
        "NetIncomeLossAttributableToNoncontrollingInterest",
    ],

    # --------------------------------------------------------
    # Depreciation & amortization
    # --------------------------------------------------------

    "da": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "DepreciationDepletionAndAmortizationPropertyPlantAndEquipment",
    ],

    # Composite fallback for companies such as MSFT.
    "depreciation": [
        "Depreciation",
    ],

    "amortization": [
        "AmortizationOfIntangibleAssets",
    ],

    # --------------------------------------------------------
    # Operating cash flow
    # --------------------------------------------------------

    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ],

    # --------------------------------------------------------
    # Capital expenditure
    # --------------------------------------------------------

    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ],

    # --------------------------------------------------------
    # Balance sheet
    # --------------------------------------------------------

    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
    ],

    "equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],

    # --------------------------------------------------------
    # Interest expense
    #
    # IMPORTANT:
    # InterestPaidNet is deliberately NOT included here.
    # Cash interest paid is not the same metric as interest
    # expense.
    # --------------------------------------------------------

    "interest_expense": [
        "InterestExpenseNonOperating",
        "InterestExpenseNonoperating",
        "InterestExpense",
    ],
}


# ============================================================
# DEBT CONCEPTS
# ============================================================

DEBT_COMBINED_CONCEPTS = [
    "DebtLongtermAndShorttermCombinedAmount",
    "LongTermDebtAndCapitalLeaseObligations",
]

DEBT_CURRENT_CONCEPTS = [
    "DebtCurrent",
    "LongTermDebtCurrent",
    "ShortTermBorrowings",
]

DEBT_NONCURRENT_CONCEPTS = [
    "LongTermDebtNoncurrent",
    "LongTermDebt",
]


# ============================================================
# HELPERS
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
    Identify full-year income statement / cash-flow periods.

    We intentionally use the actual start/end dates rather than
    SEC's fy field.
    """

    start = record.get("start")
    end = record.get("end")

    if not start or not end:
        return False

    duration = get_duration_days(
        start,
        end
    )

    if duration is None:
        return False

    return 300 <= duration <= 400


def is_instant_period(record):
    """
    Balance-sheet facts are point-in-time observations.
    """

    return (
        bool(record.get("end"))
        and not record.get("start")
    )


def get_record_value(record):
    if "val" in record:
        return record["val"]

    if "value" in record:
        return record["value"]

    return None


def get_units(concept):
    return concept.get(
        "units",
        {}
    )


def get_preferred_records(concept):
    """
    Prefer USD records.

    If USD does not exist, use the first available unit.
    """

    units = get_units(concept)

    if not units:
        return []

    if "USD" in units:
        return units["USD"]

    for _, records in units.items():
        return records

    return []


# ============================================================
# LOAD COMPANY FACTS
# ============================================================

def load_company_json(zf, cik):

    cik_string = (
        str(cik)
        .split(".")[0]
        .zfill(10)
    )

    target = (
        f"CIK{cik_string}.json"
    )

    matching_files = [
        name
        for name in zf.namelist()
        if name.endswith(target)
    ]

    if not matching_files:
        raise FileNotFoundError(
            f"Could not find Company Facts "
            f"JSON for CIK {cik_string}"
        )

    with zf.open(
        matching_files[0]
    ) as f:

        return json.load(f)


def get_us_gaap_facts(company_json):

    return (
        company_json
        .get("facts", {})
        .get("us-gaap", {})
    )


# ============================================================
# FACT EXTRACTION
# ============================================================

def get_annual_records(
    us_gaap,
    concept_name
):

    concept = us_gaap.get(
        concept_name
    )

    if not concept:
        return []

    records = (
        get_preferred_records(
            concept
        )
    )

    usable = []

    for record in records:

        if not is_annual_period(
            record
        ):
            continue

        if record.get("form") not in ANNUAL_FORMS:
            continue

        value = get_record_value(
            record
        )

        if value is None:
            continue

        end = record.get(
            "end"
        )

        if not end:
            continue

        usable.append(
            {
                "start": record.get(
                    "start"
                ),
                "end": end,
                "filed": record.get(
                    "filed"
                ),
                "form": record.get(
                    "form"
                ),
                "fy": record.get(
                    "fy"
                ),
                "fp": record.get(
                    "fp"
                ),
                "value": value,
                "accn": record.get(
                    "accn"
                ),
            }
        )

    return usable


def get_instant_records(
    us_gaap,
    concept_name
):

    concept = us_gaap.get(
        concept_name
    )

    if not concept:
        return []

    records = (
        get_preferred_records(
            concept
        )
    )

    usable = []

    for record in records:

        if not is_instant_period(
            record
        ):
            continue

        if record.get("form") not in ANNUAL_FORMS:
            continue

        value = get_record_value(
            record
        )

        if value is None:
            continue

        end = record.get(
            "end"
        )

        if not end:
            continue

        usable.append(
            {
                "end": end,
                "filed": record.get(
                    "filed"
                ),
                "form": record.get(
                    "form"
                ),
                "fy": record.get(
                    "fy"
                ),
                "fp": record.get(
                    "fp"
                ),
                "value": value,
                "accn": record.get(
                    "accn"
                ),
            }
        )

    return usable


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_by_end(
    records
):
    """
    Keep the latest filed record for each period end.

    This handles situations where the same fiscal period
    appears in multiple 10-K filings.
    """

    if not records:
        return []

    df = pd.DataFrame(
        records
    )

    df["filed_date"] = pd.to_datetime(
        df["filed"],
        errors="coerce"
    )

    df = df.sort_values(
        by=[
            "end",
            "filed_date",
        ],
        ascending=[
            True,
            True,
        ]
    )

    df = (
        df.drop_duplicates(
            subset=["end"],
            keep="last"
        )
    )

    return df.to_dict(
        orient="records"
    )


# ============================================================
# CONCEPT SELECTION
# ============================================================

def select_best_annual_concept(
    us_gaap,
    candidates,
    max_periods=5
):

    evaluated = []

    for priority, concept_name in enumerate(
        candidates
    ):

        records = get_annual_records(
            us_gaap,
            concept_name
        )

        records = deduplicate_by_end(
            records
        )

        if not records:
            continue

        periods = sorted(
            {
                r["end"]
                for r in records
            },
            reverse=True
        )

        recent_periods = periods[
            :max_periods
        ]

        latest_period = (
            recent_periods[0]
            if recent_periods
            else None
        )

        evaluated.append(
            {
                "concept": concept_name,
                "records": records,
                "periods": periods,
                "recent_coverage": len(
                    recent_periods
                ),
                "latest_period": latest_period,
                "priority": priority,
            }
        )

    if not evaluated:
        return None

    # Current coverage is more important than
    # historical volume.
    #
    # Latest period breaks ties.
    #
    # Candidate order is the final semantic tie-breaker.
    evaluated.sort(
        key=lambda x: (
            x["recent_coverage"],
            pd.Timestamp(
                x["latest_period"]
            )
            if x["latest_period"]
            else pd.Timestamp.min,
            -x["priority"],
        ),
        reverse=True
    )

    return evaluated[0]


def select_best_instant_concept(
    us_gaap,
    candidates,
    max_periods=5
):

    evaluated = []

    for priority, concept_name in enumerate(
        candidates
    ):

        records = get_instant_records(
            us_gaap,
            concept_name
        )

        records = deduplicate_by_end(
            records
        )

        if not records:
            continue

        periods = sorted(
            {
                r["end"]
                for r in records
            },
            reverse=True
        )

        recent_periods = periods[
            :max_periods
        ]

        latest_period = (
            recent_periods[0]
            if recent_periods
            else None
        )

        evaluated.append(
            {
                "concept": concept_name,
                "records": records,
                "periods": periods,
                "recent_coverage": len(
                    recent_periods
                ),
                "latest_period": latest_period,
                "priority": priority,
            }
        )

    if not evaluated:
        return None

    evaluated.sort(
        key=lambda x: (
            x["recent_coverage"],
            pd.Timestamp(
                x["latest_period"]
            )
            if x["latest_period"]
            else pd.Timestamp.min,
            -x["priority"],
        ),
        reverse=True
    )

    return evaluated[0]


# ============================================================
# VALUE LOOKUPS
# ============================================================

def records_to_value_map(
    records
):

    return {
        record["end"]: record["value"]
        for record in records
    }


def extract_annual_metric(
    us_gaap,
    candidates,
    period_ends
):

    selected = select_best_annual_concept(
        us_gaap,
        candidates
    )

    if selected is None:
        return {}, None

    value_map = records_to_value_map(
        selected["records"]
    )

    result = {
        period: value_map.get(
            period
        )
        for period in period_ends
    }

    return (
        result,
        selected["concept"]
    )


def extract_instant_metric(
    us_gaap,
    candidates,
    period_ends
):

    selected = select_best_instant_concept(
        us_gaap,
        candidates
    )

    if selected is None:
        return {}, None

    value_map = records_to_value_map(
        selected["records"]
    )

    result = {
        period: value_map.get(
            period
        )
        for period in period_ends
    }

    return (
        result,
        selected["concept"]
    )


# ============================================================
# COMPOSITE D&A
# ============================================================

def extract_da(
    us_gaap,
    period_ends
):

    # --------------------------------------------------------
    # First preference:
    # direct combined D&A concept.
    # --------------------------------------------------------

    direct_values, direct_concept = (
        extract_annual_metric(
            us_gaap,
            CONCEPTS["da"],
            period_ends
        )
    )

    if direct_concept is not None:

        return (
            direct_values,
            direct_concept
        )

    # --------------------------------------------------------
    # Fallback:
    #
    # D&A = Depreciation + Amortization
    #
    # This is used for companies such as Microsoft where
    # SEC Company Facts does not expose a current combined
    # D&A concept.
    # --------------------------------------------------------

    depreciation_values, depreciation_concept = (
        extract_annual_metric(
            us_gaap,
            CONCEPTS["depreciation"],
            period_ends
        )
    )

    amortization_values, amortization_concept = (
        extract_annual_metric(
            us_gaap,
            CONCEPTS["amortization"],
            period_ends
        )
    )

    if (
        depreciation_concept is None
        and amortization_concept is None
    ):
        return {}, None

    result = {}

    for period in period_ends:

        depreciation = (
            depreciation_values.get(
                period
            )
        )

        amortization = (
            amortization_values.get(
                period
            )
        )

        if (
            depreciation is None
            and amortization is None
        ):
            result[period] = None

        else:

            depreciation = (
                0
                if depreciation is None
                else depreciation
            )

            amortization = (
                0
                if amortization is None
                else amortization
            )

            result[period] = (
                depreciation
                + amortization
            )

    concept_description = (
        "Composite: "
        f"{depreciation_concept or 'NULL'}"
        " + "
        f"{amortization_concept or 'NULL'}"
    )

    return (
        result,
        concept_description
    )


# ============================================================
# DEBT EXTRACTION
# ============================================================

def extract_debt(
    us_gaap,
    period_ends
):

    # --------------------------------------------------------
    # 1. Try a combined debt concept first.
    # --------------------------------------------------------

    combined_values, combined_concept = (
        extract_instant_metric(
            us_gaap,
            DEBT_COMBINED_CONCEPTS,
            period_ends
        )
    )

    if combined_concept is not None:

        return (
            combined_values,
            combined_concept
        )

    # --------------------------------------------------------
    # 2. Otherwise construct:
    #
    # Total Debt =
    # Current Debt + Noncurrent Debt
    #
    # For CAT this specifically allows:
    #
    # LongTermDebtNoncurrent
    # +
    # ShortTermBorrowings
    # --------------------------------------------------------

    current_values, current_concept = (
        extract_instant_metric(
            us_gaap,
            DEBT_CURRENT_CONCEPTS,
            period_ends
        )
    )

    noncurrent_values, noncurrent_concept = (
        extract_instant_metric(
            us_gaap,
            DEBT_NONCURRENT_CONCEPTS,
            period_ends
        )
    )

    if (
        current_concept is None
        and noncurrent_concept is None
    ):
        return {}, None

    result = {}

    for period in period_ends:

        current = current_values.get(
            period
        )

        noncurrent = noncurrent_values.get(
            period
        )

        if (
            current is None
            and noncurrent is None
        ):
            result[period] = None
            continue

        current = (
            0
            if current is None
            else current
        )

        noncurrent = (
            0
            if noncurrent is None
            else noncurrent
        )

        result[period] = (
            current
            + noncurrent
        )

    concept_description = (
        "Composite: "
        f"{current_concept or 'NULL'}"
        " + "
        f"{noncurrent_concept or 'NULL'}"
    )

    return (
        result,
        concept_description
    )


# ============================================================
# PERIOD BACKBONE
# ============================================================

def get_period_backbone(
    us_gaap
):

    backbone_candidates = [
        "revenue",
        "net_income",
        "operating_income",
        "operating_cash_flow",
    ]

    for metric in backbone_candidates:

        selected = select_best_annual_concept(
            us_gaap,
            CONCEPTS[metric],
            max_periods=5
        )

        if selected is not None:

            periods = sorted(
                selected["periods"],
                reverse=True
            )

            return periods[:5]

    return []


# ============================================================
# FISCAL YEAR
# ============================================================

def derive_fiscal_year(
    period_end,
    source_fy=None
):
    """
    Primary reporting key = actual fiscal period-end year.

    SEC's fy is retained separately as source metadata.

    We do NOT overwrite the period using SEC fy.
    """

    if not period_end:
        return None

    date = parse_date(
        period_end
    )

    if date is None:
        return None

    return int(
        date.year
    )


# ============================================================
# COMPANY EXTRACTION
# ============================================================

def extract_company(
    company_row,
    zf
):

    ticker = str(
        company_row["ticker"]
    ).upper()

    company = company_row[
        "company"
    ]

    cik = company_row[
        "cik"
    ]

    print()
    print("=" * 80)
    print(
        f"{ticker} | {company}"
    )
    print("=" * 80)

    company_json = load_company_json(
        zf,
        cik
    )

    us_gaap = get_us_gaap_facts(
        company_json
    )

    # --------------------------------------------------------
    # Period backbone
    # --------------------------------------------------------

    period_ends = get_period_backbone(
        us_gaap
    )

    if not period_ends:

        print(
            "WARNING: No annual periods found."
        )

        return []

    print(
        "Periods:",
        ", ".join(period_ends)
    )

    # --------------------------------------------------------
    # Revenue
    # --------------------------------------------------------

    revenue_values, revenue_concept = (
        extract_annual_metric(
            us_gaap,
            CONCEPTS["revenue"],
            period_ends
        )
    )

    # --------------------------------------------------------
    # Operating income
    #
    # JNJ currently has no legitimate current
    # OperatingIncomeLoss concept in Company Facts.
    #
    # We intentionally DO NOT substitute another metric.
    # --------------------------------------------------------

    operating_income_values, operating_income_concept = (
        extract_annual_metric(
            us_gaap,
            CONCEPTS["operating_income"],
            period_ends
        )
    )

    # --------------------------------------------------------
    # Net income
    # --------------------------------------------------------

    net_income_values, net_income_concept = (
        extract_annual_metric(
            us_gaap,
            CONCEPTS["net_income"],
            period_ends
        )
    )

    # --------------------------------------------------------
    # D&A
    # --------------------------------------------------------

    da_values, da_concept = extract_da(
        us_gaap,
        period_ends
    )

    # --------------------------------------------------------
    # Operating cash flow
    # --------------------------------------------------------

    operating_cash_flow_values, operating_cash_flow_concept = (
        extract_annual_metric(
            us_gaap,
            CONCEPTS["operating_cash_flow"],
            period_ends
        )
    )

    # --------------------------------------------------------
    # CapEx
    # --------------------------------------------------------

    capex_values, capex_concept = (
        extract_annual_metric(
            us_gaap,
            CONCEPTS["capex"],
            period_ends
        )
    )

    # --------------------------------------------------------
    # Interest expense
    #
    # Strictly actual expense.
    #
    # InterestPaidNet is NOT used as a substitute.
    # --------------------------------------------------------

    interest_values, interest_concept = (
        extract_annual_metric(
            us_gaap,
            CONCEPTS["interest_expense"],
            period_ends
        )
    )

    # --------------------------------------------------------
    # Cash
    # --------------------------------------------------------

    cash_values, cash_concept = (
        extract_instant_metric(
            us_gaap,
            CONCEPTS["cash"],
            period_ends
        )
    )

    # --------------------------------------------------------
    # Equity
    # --------------------------------------------------------

    equity_values, equity_concept = (
        extract_instant_metric(
            us_gaap,
            CONCEPTS["equity"],
            period_ends
        )
    )

    # --------------------------------------------------------
    # Debt
    # --------------------------------------------------------

    debt_values, debt_concept = (
        extract_debt(
            us_gaap,
            period_ends
        )
    )

    # --------------------------------------------------------
    # Find source fiscal-year metadata.
    #
    # We use the selected revenue concept where possible.
    # The actual period end remains the primary period key.
    # --------------------------------------------------------

    fiscal_metadata = {}

    if revenue_concept is not None:

        revenue_selected = (
            select_best_annual_concept(
                us_gaap,
                [revenue_concept]
            )
        )

        if revenue_selected is not None:

            for record in revenue_selected[
                "records"
            ]:

                fiscal_metadata[
                    record["end"]
                ] = {
                    "source_fy": record.get(
                        "fy"
                    ),
                    "source_fp": record.get(
                        "fp"
                    ),
                    "source_filed": record.get(
                        "filed"
                    ),
                }

    # --------------------------------------------------------
    # Build rows
    # --------------------------------------------------------

    rows = []

    for period_end in period_ends:

        metadata = fiscal_metadata.get(
            period_end,
            {}
        )

        source_fy = metadata.get(
            "source_fy"
        )

        fiscal_year = derive_fiscal_year(
            period_end,
            source_fy
        )

        row = {

            "ticker": ticker,

            "company": company,

            "cik": cik,

            # Actual reporting period.
            "period_end": period_end,

            # Calendar year of actual period end.
            "fiscal_year": fiscal_year,

            # SEC source metadata retained
            # for audit/debugging.
            "sec_fy": source_fy,

            "sec_fp": metadata.get(
                "source_fp"
            ),

            "source_filed": metadata.get(
                "source_filed"
            ),

            # ------------------------------------------------
            # Raw financial values
            # ------------------------------------------------

            "revenue": revenue_values.get(
                period_end
            ),

            "operating_income": operating_income_values.get(
                period_end
            ),

            "net_income": net_income_values.get(
                period_end
            ),

            "da": da_values.get(
                period_end
            ),

            "operating_cash_flow": operating_cash_flow_values.get(
                period_end
            ),

            "capex": capex_values.get(
                period_end
            ),

            "interest_expense": interest_values.get(
                period_end
            ),

            "cash": cash_values.get(
                period_end
            ),

            "debt": debt_values.get(
                period_end
            ),

            "equity": equity_values.get(
                period_end
            ),

            # ------------------------------------------------
            # Selected concepts
            # ------------------------------------------------

            "revenue_concept": revenue_concept,

            "operating_income_concept": operating_income_concept,

            "net_income_concept": net_income_concept,

            "da_concept": da_concept,

            "operating_cash_flow_concept": (
                operating_cash_flow_concept
            ),

            "capex_concept": capex_concept,

            "interest_expense_concept": (
                interest_concept
            ),

            "cash_concept": cash_concept,

            "debt_concept": debt_concept,

            "equity_concept": equity_concept,
        }

        rows.append(
            row
        )

    # --------------------------------------------------------
    # Console summary
    # --------------------------------------------------------

    print()
    print(
        "Selected concepts:"
    )

    print(
        "  Revenue:",
        revenue_concept
    )

    print(
        "  Operating income:",
        operating_income_concept
    )

    print(
        "  Net income:",
        net_income_concept
    )

    print(
        "  D&A:",
        da_concept
    )

    print(
        "  Operating cash flow:",
        operating_cash_flow_concept
    )

    print(
        "  CapEx:",
        capex_concept
    )

    print(
        "  Interest expense:",
        interest_concept
    )

    print(
        "  Cash:",
        cash_concept
    )

    print(
        "  Debt:",
        debt_concept
    )

    print(
        "  Equity:",
        equity_concept
    )

    return rows


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print(
        "V6 FINANCIAL EXTRACTION TEST"
    )
    print("=" * 80)

    print()
    print(
        f"Loading universe: {UNIVERSE_FILE}"
    )

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

    print(
        f"Companies selected: "
        f"{len(test_df)}"
    )

    all_rows = []

    print()
    print(
        f"Opening SEC Company Facts: "
        f"{ZIP_FILE}"
    )

    with zipfile.ZipFile(
        ZIP_FILE,
        "r"
    ) as zf:

        for _, company_row in test_df.iterrows():

            try:

                rows = extract_company(
                    company_row,
                    zf
                )

                all_rows.extend(
                    rows
                )

            except Exception as exc:

                ticker = company_row[
                    "ticker"
                ]

                print()
                print(
                    f"ERROR extracting "
                    f"{ticker}: {exc}"
                )

    # ========================================================
    # CREATE DATAFRAME
    # ========================================================

    result = pd.DataFrame(
        all_rows
    )

    if result.empty:

        print()
        print(
            "ERROR: No rows extracted."
        )

        return

    # Sort chronologically within company.
    result = result.sort_values(
        by=[
            "ticker",
            "period_end",
        ],
        ascending=[
            True,
            False,
        ]
    )

    # ========================================================
    # MISSING DATA SUMMARY
    # ========================================================

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
        "equity",
    ]

    print()
    print("=" * 80)
    print(
        "MISSING DATA SUMMARY"
    )
    print("=" * 80)

    for column in financial_columns:

        missing = int(
            result[column].isna().sum()
        )

        total = len(result)

        print(
            f"{column:25s}: "
            f"{missing:2d}/{total}"
        )

    # ========================================================
    # SAVE
    # ========================================================

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print("=" * 80)
    print(
        "V6 EXTRACTION COMPLETE"
    )
    print("=" * 80)

    print()
    print(
        f"Rows extracted: "
        f"{len(result):,}"
    )

    print(
        f"Saved to:\n{OUTPUT_FILE}"
    )

    print()
    print(
        "Preview:"
    )

    print(
        result[
            [
                "ticker",
                "period_end",
                "fiscal_year",
                "revenue",
                "operating_income",
                "da",
                "capex",
                "interest_expense",
                "cash",
                "debt",
            ]
        ].to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()
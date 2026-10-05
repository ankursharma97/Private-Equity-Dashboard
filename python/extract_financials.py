import json
import zipfile
from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ZIP_FILE = BASE_DIR / "data" / "companyfacts.zip"
UNIVERSE_FILE = BASE_DIR / "data" / "investment_universe.csv"

OUTPUT_FILE = BASE_DIR / "data" / "financials_raw.csv"
ERROR_FILE = BASE_DIR / "data" / "financial_extraction_errors.csv"


# ============================================================
# CONFIGURATION
# ============================================================

ANNUAL_FORMS = {"10-K", "10-K/A"}

MAX_PERIODS = 5


# ============================================================
# SEC XBRL CONCEPTS
# ============================================================

CONCEPTS = {

    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
        "SalesRevenueServicesNet",
    ],

    "operating_income": [
        "OperatingIncomeLoss",
    ],

    "net_income": [
        "NetIncomeLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
        "NetIncomeLossAttributableToNoncontrollingInterest",
    ],

    "da": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "DepreciationDepletionAndAmortizationPropertyPlantAndEquipment",
    ],

    "depreciation": [
        "Depreciation",
    ],

    "amortization": [
        "AmortizationOfIntangibleAssets",
    ],

    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ],

    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ],

    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
    ],

    "equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],

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
# DATE / PERIOD HELPERS
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
    Identify full-year income-statement / cash-flow periods.

    We use the actual start/end dates rather than SEC's fy field.
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


# ============================================================
# RECORD HELPERS
# ============================================================

def get_record_value(record):

    if "val" in record:
        return record["val"]

    if "value" in record:
        return record["value"]

    return None


def get_preferred_records(concept):
    """
    Prefer USD records.

    If USD does not exist, use the first available unit.
    """

    units = concept.get(
        "units",
        {}
    )

    if not units:
        return []

    if "USD" in units:
        return units["USD"]

    for _, records in units.items():
        return records

    return []


# ============================================================
# COMPANY FACTS LOADING
# ============================================================

def build_zip_index(zf):
    """
    Build a CIK -> ZIP member lookup once.

    This avoids scanning the ZIP file's complete filename list
    for every company.
    """

    index = {}

    for name in zf.namelist():

        if not name.endswith(".json"):
            continue

        filename = Path(name).name

        if not filename.startswith("CIK"):
            continue

        cik_part = filename[3:-5]

        if cik_part.isdigit():
            index[cik_part.zfill(10)] = name

    return index


def load_company_json(
    zf,
    zip_index,
    cik
):

    cik_string = (
        str(cik)
        .split(".")[0]
        .zfill(10)
    )

    member = zip_index.get(
        cik_string
    )

    if member is None:
        raise FileNotFoundError(
            f"Company Facts JSON not found for CIK {cik_string}"
        )

    with zf.open(member) as f:
        return json.load(f)


def get_us_gaap_facts(company_json):

    return (
        company_json
        .get("facts", {})
        .get("us-gaap", {})
    )


# ============================================================
# ANNUAL RECORD EXTRACTION
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

    records = get_preferred_records(
        concept
    )

    usable = []

    for record in records:

        if not is_annual_period(record):
            continue

        if record.get("form") not in ANNUAL_FORMS:
            continue

        value = get_record_value(
            record
        )

        if value is None:
            continue

        end = record.get("end")

        if not end:
            continue

        usable.append(
            {
                "start": record.get("start"),
                "end": end,
                "filed": record.get("filed"),
                "form": record.get("form"),
                "fy": record.get("fy"),
                "fp": record.get("fp"),
                "value": value,
                "accn": record.get("accn"),
            }
        )

    return usable


# ============================================================
# INSTANT RECORD EXTRACTION
# ============================================================

def get_instant_records(
    us_gaap,
    concept_name
):

    concept = us_gaap.get(
        concept_name
    )

    if not concept:
        return []

    records = get_preferred_records(
        concept
    )

    usable = []

    for record in records:

        if not is_instant_period(record):
            continue

        if record.get("form") not in ANNUAL_FORMS:
            continue

        value = get_record_value(
            record
        )

        if value is None:
            continue

        end = record.get("end")

        if not end:
            continue

        usable.append(
            {
                "end": end,
                "filed": record.get("filed"),
                "form": record.get("form"),
                "fy": record.get("fy"),
                "fp": record.get("fp"),
                "value": value,
                "accn": record.get("accn"),
            }
        )

    return usable


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_by_end(records):
    """
    Keep the latest filed record for each period end.
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
            "filed_date"
        ],
        ascending=[
            True,
            True
        ]
    )

    df = df.drop_duplicates(
        subset=["end"],
        keep="last"
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

    evaluated.sort(
        key=lambda x: (
            x["recent_coverage"],
            (
                pd.Timestamp(
                    x["latest_period"]
                )
                if x["latest_period"]
                else pd.Timestamp.min
            ),
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
            (
                pd.Timestamp(
                    x["latest_period"]
                )
                if x["latest_period"]
                else pd.Timestamp.min
            ),
            -x["priority"],
        ),
        reverse=True
    )

    return evaluated[0]


# ============================================================
# VALUE MAPPING
# ============================================================

def records_to_value_map(records):

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
        candidates,
        max_periods=MAX_PERIODS
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
        candidates,
        max_periods=MAX_PERIODS
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
# D&A
# ============================================================

def extract_da(
    us_gaap,
    period_ends
):

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
        f"Composite: "
        f"{depreciation_concept or 'NULL'} + "
        f"{amortization_concept or 'NULL'}"
    )

    return (
        result,
        concept_description
    )


# ============================================================
# DEBT
# ============================================================

def extract_debt(
    us_gaap,
    period_ends
):

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
            current + noncurrent
        )

    concept_description = (
        f"Composite: "
        f"{current_concept or 'NULL'} + "
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
            max_periods=MAX_PERIODS
        )

        if selected is not None:

            periods = sorted(
                selected["periods"],
                reverse=True
            )

            return periods[:MAX_PERIODS]

    return []


# ============================================================
# FISCAL YEAR
# ============================================================

def derive_fiscal_year(
    period_end,
    source_fy=None
):

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
    zf,
    zip_index
):

    ticker = str(
        company_row["ticker"]
    ).upper()

    company = company_row["company"]
    cik = company_row["cik"]

    company_json = load_company_json(
        zf,
        zip_index,
        cik
    )

    us_gaap = get_us_gaap_facts(
        company_json
    )

    period_ends = get_period_backbone(
        us_gaap
    )

    if not period_ends:
        return []

    # --------------------------------------------------------
    # ANNUAL METRICS
    # --------------------------------------------------------

    revenue_values, revenue_concept = (
        extract_annual_metric(
            us_gaap,
            CONCEPTS["revenue"],
            period_ends
        )
    )

    operating_income_values, operating_income_concept = (
        extract_annual_metric(
            us_gaap,
            CONCEPTS["operating_income"],
            period_ends
        )
    )

    net_income_values, net_income_concept = (
        extract_annual_metric(
            us_gaap,
            CONCEPTS["net_income"],
            period_ends
        )
    )

    da_values, da_concept = extract_da(
        us_gaap,
        period_ends
    )

    operating_cash_flow_values, operating_cash_flow_concept = (
        extract_annual_metric(
            us_gaap,
            CONCEPTS["operating_cash_flow"],
            period_ends
        )
    )

    capex_values, capex_concept = (
        extract_annual_metric(
            us_gaap,
            CONCEPTS["capex"],
            period_ends
        )
    )

    interest_values, interest_concept = (
        extract_annual_metric(
            us_gaap,
            CONCEPTS["interest_expense"],
            period_ends
        )
    )

    # --------------------------------------------------------
    # INSTANT METRICS
    # --------------------------------------------------------

    cash_values, cash_concept = (
        extract_instant_metric(
            us_gaap,
            CONCEPTS["cash"],
            period_ends
        )
    )

    equity_values, equity_concept = (
        extract_instant_metric(
            us_gaap,
            CONCEPTS["equity"],
            period_ends
        )
    )

    debt_values, debt_concept = (
        extract_debt(
            us_gaap,
            period_ends
        )
    )

    # --------------------------------------------------------
    # SOURCE METADATA
    # --------------------------------------------------------

    fiscal_metadata = {}

    if revenue_concept is not None:

        revenue_selected = (
            select_best_annual_concept(
                us_gaap,
                [revenue_concept],
                max_periods=MAX_PERIODS
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
    # BUILD ROWS
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

            "period_end": period_end,

            "fiscal_year": fiscal_year,

            "sec_fy": source_fy,

            "sec_fp": metadata.get(
                "source_fp"
            ),

            "source_filed": metadata.get(
                "source_filed"
            ),

            # Financial values

            "revenue": revenue_values.get(
                period_end
            ),

            "operating_income": (
                operating_income_values.get(
                    period_end
                )
            ),

            "net_income": net_income_values.get(
                period_end
            ),

            "da": da_values.get(
                period_end
            ),

            "operating_cash_flow": (
                operating_cash_flow_values.get(
                    period_end
                )
            ),

            "capex": capex_values.get(
                period_end
            ),

            "interest_expense": (
                interest_values.get(
                    period_end
                )
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

            # Selected concepts

            "revenue_concept": revenue_concept,

            "operating_income_concept": (
                operating_income_concept
            ),

            "net_income_concept": (
                net_income_concept
            ),

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

        rows.append(row)

    return rows


# ============================================================
# MAIN PRODUCTION PIPELINE
# ============================================================

def main():

    print("=" * 80)
    print("PRODUCTION FINANCIAL EXTRACTION")
    print("=" * 80)

    print()

    # --------------------------------------------------------
    # LOAD INVESTMENT UNIVERSE
    # --------------------------------------------------------

    print(
        f"Loading universe:\n{UNIVERSE_FILE}"
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

    print(
        f"Companies to process: "
        f"{len(universe):,}"
    )

    print()

    # --------------------------------------------------------
    # OPEN COMPANY FACTS ZIP
    # --------------------------------------------------------

    print(
        f"Opening Company Facts:\n{ZIP_FILE}"
    )

    all_rows = []
    errors = []

    processed = 0
    successful = 0
    failed = 0

    with zipfile.ZipFile(
        ZIP_FILE,
        "r"
    ) as zf:

        print(
            "Building ZIP file index..."
        )

        zip_index = build_zip_index(
            zf
        )

        print(
            f"Company Facts files indexed: "
            f"{len(zip_index):,}"
        )

        print()

        # ----------------------------------------------------
        # PROCESS COMPANIES
        # ----------------------------------------------------

        for _, company_row in universe.iterrows():

            ticker = str(
                company_row["ticker"]
            ).upper()

            company = company_row[
                "company"
            ]

            processed += 1

            try:

                rows = extract_company(
                    company_row,
                    zf,
                    zip_index
                )

                if rows:

                    all_rows.extend(
                        rows
                    )

                    successful += 1

                else:

                    failed += 1

                    errors.append(
                        {
                            "ticker": ticker,
                            "company": company,
                            "cik": company_row[
                                "cik"
                            ],
                            "error": (
                                "No annual "
                                "financial periods found"
                            ),
                        }
                    )

            except Exception as exc:

                failed += 1

                errors.append(
                    {
                        "ticker": ticker,
                        "company": company,
                        "cik": company_row[
                            "cik"
                        ],
                        "error": str(exc),
                    }
                )

            # ------------------------------------------------
            # PROGRESS
            # ------------------------------------------------

            if (
                processed == 1
                or processed % 100 == 0
                or processed == len(universe)
            ):

                print(
                    f"[{processed:,}/"
                    f"{len(universe):,}] "
                    f"Processed | "
                    f"Successful: {successful:,} | "
                    f"Failed: {failed:,}"
                )

    # ========================================================
    # BUILD OUTPUT DATAFRAME
    # ========================================================

    print()

    print("=" * 80)
    print("BUILDING OUTPUT")
    print("=" * 80)

    if not all_rows:

        print(
            "ERROR: No financial rows were extracted."
        )

        return

    result = pd.DataFrame(
        all_rows
    )

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

    # --------------------------------------------------------
    # SAVE RAW FINANCIAL DATA
    # --------------------------------------------------------

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # SAVE ERRORS
    # --------------------------------------------------------

    if errors:

        error_df = pd.DataFrame(
            errors
        )

        error_df.to_csv(
            ERROR_FILE,
            index=False
        )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()

    print("=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)

    print()

    print(
        f"Universe companies: "
        f"{len(universe):,}"
    )

    print(
        f"Successfully processed: "
        f"{successful:,}"
    )

    print(
        f"Failed / no usable data: "
        f"{failed:,}"
    )

    print(
        f"Output rows: "
        f"{len(result):,}"
    )

    print()

    print(
        f"Financial dataset:\n"
        f"{OUTPUT_FILE}"
    )

    if errors:

        print()

        print(
            f"Error log:\n"
            f"{ERROR_FILE}"
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
    print("MISSING DATA SUMMARY")
    print("=" * 80)

    for column in financial_columns:

        missing = int(
            result[column].isna().sum()
        )

        total = len(result)

        percentage = (
            missing / total * 100
            if total
            else 0
        )

        print(
            f"{column:25s}: "
            f"{missing:8,}/{total:,} "
            f"({percentage:5.1f}%)"
        )

    print()

    print("=" * 80)
    print("PRODUCTION RUN FINISHED")
    print("=" * 80)


if __name__ == "__main__":
    main()
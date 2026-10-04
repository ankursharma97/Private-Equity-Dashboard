import json
import csv
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

OUTPUT_FILE = DATA_DIR / "sec_company_universe.csv" 

SEC_URL = "https://www.sec.gov/files/company_tickers.json"

# SEC USER AGENT
USER_AGENT = "PrivateEquityAnalyticsProject ankursharma9779@gmail.com"

#DOWNLOADING SEC COMPANY UNIVERSE DATA
def download_sec_company_data():

    request = urllib.request.Request(
        SEC_URL,
        headers={
            "User-Agent": USER_AGENT
        }
    )

    print("Downloading SEC company/ticker data...")

    with urllib.request.urlopen(request) as response:
        data = response.read()

        # SEC may return gzip-compressed content
        # Decompress it when necessary
        if response.headers.get("Content-Encoding") == "gzip":
            import gzip
            data = gzip.decompress(data)

    return json.loads(data.decode("utf-8"))

#BUILDING INITIAL COMPANY UNIVERSE
def build_universe(data):

    companies = []

    for item in data.values():

        cik = item.get("cik_str")
        ticker = item.get("ticker")
        company_name = item.get("title")

        if not cik or not company_name:
            continue

        companies.append({
            "company": company_name.strip(),
            "cik": str(cik).zfill(10),
            "ticker": ticker.strip() if ticker else ""
        })

    return companies

# REMOVE DUPLICATE CIKs
def remove_duplicates(companies):

    unique_companies = {}
    
    for company in companies:

        cik = company["cik"]

        if cik not in unique_companies:
            unique_companies[cik] = company

    return list(unique_companies.values())

#SAVE CSV
def save_csv(companies):

    DATA_DIR.mkdir(exist_ok=True)

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "company",
                "cik",
                "ticker"
            ]
        )

        writer.writeheader()
        writer.writerows(companies)

#MAIN
def main():

    print("=" * 60)
    print("PRIVATE EQUITY DEAL INTELLIGENCE PLATFORM")
    print("SEC COMPANY UNIVERSE BUILDER")
    print("=" * 60)

    # Download SEC mapping
    data = download_sec_company_data()

    print(f"SEC records received: {len(data):,}")

    # Build universe
    companies = build_universe(data)

    print(f"Companies before deduplication: {len(companies):,}")

    # Remove duplicate CIKs
    companies = remove_duplicates(companies)

    print(f"Unique companies: {len(companies):,}")

    # Save
    save_csv(companies)

    print()
    print("Universe construction complete.")
    print(f"Output: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
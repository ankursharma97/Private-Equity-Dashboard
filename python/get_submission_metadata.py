import csv
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# --------------------------------------------------
# CONFIG
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "sec_company_universe.csv"
OUTPUT_FILE = BASE_DIR / "data" / "sec_submission_metadata.csv"

USER_AGENT = "ankursharma9779@gmail.com"

REQUEST_DELAY = 0.15
MAX_RETRIES = 5


# SEC REQUEST
def fetch_submission(cik):
    url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"

    for attempt in range(MAX_RETRIES):
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                },
            )

            with urlopen(request, timeout=30) as response:
                raw_data = response.read()

                # SEC may return gzip-compressed content.
                if response.headers.get("Content-Encoding", "").lower() == "gzip":
                    import gzip
                    raw_data = gzip.decompress(raw_data)

                return json.loads(raw_data.decode("utf-8"))

        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            print(f"  Request failed ({attempt + 1}/{MAX_RETRIES}): {e}")

            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)

    return None

# MAIN
def main():

    print("Reading company universe...")

    with open(INPUT_FILE, "r", encoding="utf-8-sig", newline="") as f:
        companies = list(csv.DictReader(f))

    print(f"Companies to process: {len(companies)}")

    results = []

    for i, company in enumerate(companies, start=1):

        cik = int(company["cik"])
        name = company["company"]
        ticker = company.get("ticker", "")

        print(f"[{i}/{len(companies)}] {name} ({ticker})")

        data = fetch_submission(cik)

        if data is None:
            print("  FAILED")
            continue

        filings = data.get("filings", {})
        recent = filings.get("recent", {})

        forms = recent.get("form", [])

        form_counts = {}

        for form in forms:
            form_counts[form] = form_counts.get(form, 0) + 1

        has_10k = "10-K" in form_counts
        has_20f = "20-F" in form_counts
        has_40f = "40-F" in form_counts

        results.append({
            "company": name,
            "cik": cik,
            "ticker": ticker,
            "entity_name": data.get("name", ""),
            "sic": data.get("sic", ""),
            "sic_description": data.get("sicDescription", ""),
            "exchange": ", ".join(
    str(x) for x in data.get("exchanges", []) if x
),
            "has_10k": has_10k,
            "has_20f": has_20f,
            "has_40f": has_40f,
            "form_10k_count": form_counts.get("10-K", 0),
            "form_20f_count": form_counts.get("20-F", 0),
            "form_40f_count": form_counts.get("40-F", 0),
        })

        time.sleep(REQUEST_DELAY)

    print()
    print("Saving metadata...")

    fieldnames = [
        "company",
        "cik",
        "ticker",
        "entity_name",
        "sic",
        "sic_description",
        "exchange",
        "has_10k",
        "has_20f",
        "has_40f",
        "form_10k_count",
        "form_20f_count",
        "form_40f_count",
    ]

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Saved: {OUTPUT_FILE}")
    print(f"Successful records: {len(results)}")


if __name__ == "__main__":
    main()
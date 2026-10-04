import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

OUTPUT_FILE = DATA_DIR / "submission.zip"

SEC_URL = (
    "https://www.sec.gov/Archives/edgar/daily-index/"
    "bulkdata/submissions.zip"
)

# SEC USER AGENT
USER_AGENT = "PrivateEquityAnalyticsProject ankursharma9779@gmail.com"

#DOWNLOADING
def download_file():

    DATA_DIR.mkdir(exist_ok=True)

    request = urllib.request.Request(
        SEC_URL,
        headers={
            "User-Agent": USER_AGENT
        }
    )

    print("=" * 60)
    print("SEC SUBMISSIONS BULK DATA DOWNLOADER")
    print("=" * 60)
    print("Downloading submission.zip...")
    print("This may take some time.")

    with urllib.request.urlopen(request) as response:

        total_size = response.headers.get("Content-Length")

        if total_size:
            total_size = int(total_size)
            print(f"Download size: {total_size / (1024 ** 2):.1f} MB")

        downloaded = 0

        with open(OUTPUT_FILE, "wb") as file:

            while True:

                chunk = response.read(1024 * 1024)

                if not chunk:
                    break

                file.write(chunk)
                downloaded += len(chunk)

                if total_size:
                    percent = downloaded / total_size * 100
                    print(
                        f"\rProgress: {percent:6.2f}%",
                        end=""
                    )

    print()
    print()
    print("Download complete.")
    print(f"Saved to: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    download_file()
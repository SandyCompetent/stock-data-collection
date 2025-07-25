import os
import requests
import time
import random
import json
import csv
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- Configuration ---
# The stock/crypto/forex ticker you are interested in.
# Example: 'NVDA' or 'CRYPTO:BTC'
TICKER = 'NVDA'
# Optional: Specify topics to filter by. Leave empty to get all topics.
# Full list of topics can be found in the Alpha Vantage documentation.
# Example: ['technology', 'earnings']
TOPICS = []
# Folder to store the downloaded news data
DATA_FOLDER = 'NVDA_news_data'
# State file to keep track of download progress
STATE_FILE = 'news_state.json'

# Set your desired overall date range for the news articles
START_DATE = date(2009, 1, 1)
END_DATE = date.today()

# --- Advanced Configuration ---
# Number of months to fetch in a single API call.
# The API can be sensitive to large date ranges, so 3-6 months is a good starting point.
TIME_CHUNK_MONTHS = 6
# The API returns a maximum of 1000 results per call.
API_LIMIT = 1000
# Base URL for the Alpha Vantage API
API_BASE_URL = "https://www.alphavantage.co/query"


# --- Helper Functions ---

def get_api_keys():
    """Loads API keys from environment variables (e.g., API_KEY_1, API_KEY_2)."""
    keys = []
    i = 1
    while True:
        key = os.getenv(f'API_KEY_{i}')
        if key:
            keys.append(key)
            i += 1
        else:
            break
    if not keys:
        raise ValueError("No API keys found in environment variables. Please set API_KEY_1, API_KEY_2, etc.")
    return keys


def load_state():
    """Loads the last successfully fetched end date from the state file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state_data = json.load(f)
                # Return the date from which the next fetch should start
                return date.fromisoformat(state_data['next_start_date'])
        except (json.JSONDecodeError, KeyError):
            print("State file is corrupted or invalid. Starting from the beginning.")
            return START_DATE
    # If no state file, start from the configured START_DATE
    return START_DATE


def save_state(next_start_date):
    """Saves the next start date to the state file."""
    with open(STATE_FILE, 'w') as f:
        json.dump({'next_start_date': next_start_date.isoformat()}, f, indent=4)
    print(f"State saved. Next run will start from {next_start_date.strftime('%Y-%m-%d')}.")


# --- Main Logic ---

def fetch_news_for_period(api_key, time_from, time_to):
    """
    Fetches news and sentiment data for a specific time period and saves it as a CSV.
    Returns True on success, False on failure.
    """
    # Format dates to YYYYMMDDTHHMM format required by the API
    time_from_str = time_from.strftime('%Y%m%dT%H%M')
    time_to_str = time_to.strftime('%Y%m%dT%H%M')

    print(f"\nAttempting to fetch news from {time_from.strftime('%Y-%m-%d')} to {time_to.strftime('%Y-%m-%d')}")

    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": TICKER,
        "time_from": time_from_str,
        "time_to": time_to_str,
        "sort": "EARLIEST",  # Fetch oldest first to process chronologically
        "limit": API_LIMIT,
        "apikey": api_key,
    }
    if TOPICS:
        params["topics"] = ",".join(TOPICS)

    try:
        response = requests.get(API_BASE_URL, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        data = response.json()

        # Case 1: API explicitly says no articles were found. Treat as a success and move on.
        if "Information" in data and "No articles found" in data.get("Information", ""):
            print("No articles found for this period. Moving to the next time chunk.")
            return True

        # Case 2: API returns a genuine error message. This is a failure.
        if "Error Message" in data:
            print(f"API returned an error: {data}")
            return False

        feed = data.get("feed", [])
        if not feed:
            # Case 3: The 'feed' is empty or missing, but there was no error/info message.
            # This also means no articles were found.
            print("No articles found for this period (empty feed). Moving on.")
            return True

        # Create a unique filename for this data chunk
        ticker_str = TICKER.replace(':', '')  # Sanitize for filename
        filename = f"{ticker_str}_{time_from_str[:8]}_{time_to_str[:8]}.csv"
        os.makedirs(DATA_FOLDER, exist_ok=True)
        filepath = os.path.join(DATA_FOLDER, filename)

        # Flatten and write the data to a CSV file
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            # The headers will be the keys from the first article object
            fieldnames = feed[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for article in feed:
                # Create a copy to avoid modifying the original list
                row = article.copy()
                # Convert lists of objects/strings to a more CSV-friendly format
                row['authors'] = ', '.join(row.get('authors', []))
                row['topics'] = json.dumps(row.get('topics', []))
                row['ticker_sentiment'] = json.dumps(row.get('ticker_sentiment', []))
                writer.writerow(row)

        print(f"Successfully saved {len(feed)} articles to {filepath}")

        # If we hit the limit, it's likely there's more data in this period.
        if len(feed) == API_LIMIT:
            print(
                f"Warning: Reached the API limit of {API_LIMIT} articles. Some news within this period may have been missed.")

        return True

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False
    except json.JSONDecodeError:
        print(f"Failed to decode JSON from response. Response text: {response.text}")
        return False


def run_downloader():
    """
    Main function to loop through date ranges and download news data.
    """
    api_keys = get_api_keys()
    key_cycle = 0

    current_start_date = load_state()
    print(
        f"Starting downloader. Ticker: {TICKER}, Date Range: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")

    while current_start_date < END_DATE:
        # Determine the end of the current chunk
        period_end_date = current_start_date + relativedelta(months=TIME_CHUNK_MONTHS)
        # Ensure we don't go past the overall END_DATE
        period_end_date = min(period_end_date, END_DATE)

        # Convert date objects to datetime objects for the API call
        time_from = datetime.combine(current_start_date, datetime.min.time())
        time_to = datetime.combine(period_end_date, datetime.max.time())

        # Rotate through the available API keys
        api_key = api_keys[key_cycle % len(api_keys)]
        print(f"--- Using API Key #{(key_cycle % len(api_keys)) + 1} ---")
        key_cycle += 1

        success = fetch_news_for_period(api_key, time_from, time_to)

        if success:
            # If successful, update state to start from the end of the period we just fetched
            save_state(period_end_date)
            current_start_date = period_end_date

            # Wait before the next call to be respectful of the API rate limits
            wait_time = random.uniform(15, 25)  # A shorter delay as free tier is 25 requests/day
            print(f"Waiting for {wait_time:.0f} seconds...")
            time.sleep(wait_time)
        else:
            print("Failed to fetch data for the period. Stopping for this run.")
            print("This could be due to API rate limits. Try running the script again later.")
            break

    print("\nDownload process finished or reached the end date. ✅")


if __name__ == "__main__":
    run_downloader()

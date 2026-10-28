"""
NOTICE: This project was created for learning and demonstration purposes and is no longer maintained.
It has been merged into: https://github.com/SandyCompetent/stock-market-analysis
"""

import os
import requests
import time
import random
import json
import csv
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- Configuration ---
TICKER = 'NVDA'
DATA_FOLDER = 'NVDA_news_data'
STATE_FILE = 'news_state.json'
START_DATE = date(2022, 1, 1)
END_DATE = date.today()

# --- Advanced Configuration ---
TIME_CHUNK_MONTHS = 6
API_LIMIT = 1000
API_BASE_URL = "https://www.alphavantage.co/query"


# --- Helper Functions ---

def get_api_keys():
    """Loads API keys from environment variables."""
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
        raise ValueError("No API keys found. Please set API_KEY_1, API_KEY_2, etc.")
    print(f"[DEBUG] Found {len(keys)} API key(s).")
    return keys


def load_state():
    """Loads the last successfully fetched end date."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state_data = json.load(f)
                return date.fromisoformat(state_data['next_start_date'])
        except (json.JSONDecodeError, KeyError):
            print("State file is corrupted. Starting from the beginning.")
            return START_DATE
    return START_DATE


def save_state(next_start_date):
    """Saves the next start date to the state file."""
    with open(STATE_FILE, 'w') as f:
        json.dump({'next_start_date': next_start_date.isoformat()}, f, indent=4)
    print(f"State saved. Next run will start from {next_start_date.strftime('%Y-%m-%d')}.")


# --- Main Logic ---

def fetch_news_for_period(api_key, time_from, time_to):
    """
    Fetches news for a specific time period.
    Returns a status: 'SUCCESS', 'RATE_LIMIT', or 'FAILURE'.
    """
    time_from_str = time_from.strftime('%Y%m%dT%H%M')
    time_to_str = time_to.strftime('%Y%m%dT%H%M')

    params = {
        "function": "NEWS_SENTIMENT", "tickers": TICKER, "time_from": time_from_str,
        "time_to": time_to_str, "sort": "EARLIEST", "limit": API_LIMIT, "apikey": api_key,
    }

    try:
        response = requests.get(API_BASE_URL, params=params)
        print(f"[DEBUG] Status Code: {response.status_code}")
        response.raise_for_status()
        data = response.json()

        # ** NEW: Check for rate limit message **
        if "Information" in data and "rate limit" in data.get("Information", ""):
            print(f"❗️ API rate limit reached for this key. Response: {data['Information']}")
            return 'RATE_LIMIT'

        if "Error Message" in data:
            print(f"❌ API returned an error: {data}")
            return 'FAILURE'

        if "Information" in data and "No articles found" in data.get("Information", ""):
            print("No articles found for this period. Moving on.")
            return 'SUCCESS'  # This is a successful outcome

        feed = data.get("feed", [])
        if not feed:
            print("No articles found (empty feed). Moving on.")
            return 'SUCCESS'  # Also a successful outcome

        # --- Save data if found ---
        ticker_str = TICKER.replace(':', '')
        filename = f"{ticker_str}_{time_from_str[:8]}_{time_to_str[:8]}.csv"
        os.makedirs(DATA_FOLDER, exist_ok=True)
        filepath = os.path.join(DATA_FOLDER, filename)

        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = feed[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for article in feed:
                row = article.copy()
                row['authors'] = ', '.join(row.get('authors', []))
                row['topics'] = json.dumps(row.get('topics', []))
                row['ticker_sentiment'] = json.dumps(row.get('ticker_sentiment', []))
                writer.writerow(row)

        print(f"✅ Successfully saved {len(feed)} articles to {filepath}")
        if len(feed) == API_LIMIT:
            print(f"⚠️ Warning: Reached the API limit of {API_LIMIT} articles.")

        return 'SUCCESS'

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return 'FAILURE'
    except json.JSONDecodeError:
        print(f"❌ Failed to decode JSON. Raw Response: {response.text[:500]}")
        return 'FAILURE'


def run_downloader():
    """
    Main function to loop through dates and download news, with retries for rate limits.
    """
    api_keys = get_api_keys()
    key_cycle_index = 0

    current_start_date = load_state()
    print(f"Starting downloader for Ticker: {TICKER}")
    print(f"Resuming from saved state: {current_start_date.strftime('%Y-%m-%d')}")

    # --- REFACTORED LOGIC ---
    # Outer loop iterates through each date period
    while current_start_date < END_DATE:
        period_end_date = min(current_start_date + relativedelta(months=TIME_CHUNK_MONTHS), END_DATE)
        time_from = datetime.combine(current_start_date, datetime.min.time())
        time_to = datetime.combine(period_end_date, datetime.max.time())

        print(
            f"\n--- Processing period: {current_start_date.strftime('%Y-%m-%d')} to {period_end_date.strftime('%Y-%m-%d')} ---")

        period_succeeded = False
        # Inner loop retries with available API keys for the *same* period
        for i in range(len(api_keys)):
            current_key_index = key_cycle_index % len(api_keys)
            api_key = api_keys[current_key_index]
            print(f"Attempting with API Key #{current_key_index + 1}...")

            status = fetch_news_for_period(api_key, time_from, time_to)

            if status == 'SUCCESS':
                save_state(period_end_date)
                current_start_date = period_end_date
                period_succeeded = True
                key_cycle_index += 1  # Move to next key for the next period
                break  # Exit inner loop and move to the next date period

            elif status == 'RATE_LIMIT':
                key_cycle_index += 1  # Move to the next key to retry
                if i == len(api_keys) - 1:
                    print("🛑 All API keys have been exhausted for this period. Stopping.")
                    break
                else:
                    print("Switching to the next API key...")
                    time.sleep(2)  # Brief pause before retrying with a new key

            else:  # status == 'FAILURE'
                print("🛑 A hard failure occurred. Stopping the downloader.")
                # We break the inner loop, and since period_succeeded is False, the outer loop will also stop.
                break

        if not period_succeeded:
            print("Could not complete the period with any API key. Exiting.")
            break

        # Wait before starting the next period
        wait_time = random.uniform(15, 25)
        print(f"Period complete. Waiting for {wait_time:.0f} seconds...")
        time.sleep(wait_time)

    print("\nDownload process finished or stopped. ✅")


if __name__ == "__main__":
    run_downloader()

import os
import requests
import time
import random
import json
from datetime import date
from dateutil.relativedelta import relativedelta

# --- Configuration ---
SYMBOL = 'MRK'
INTERVAL = '1min'
DATA_FOLDER = 'MRK_stock_data'
STATE_FILE = 'state.json'

# Set your desired date range
START_DATE = date(2009, 1, 1)
END_DATE = date(2020, 12, 1)


# --- Helper Functions ---
def load_state():
    """Loads the last downloaded month from the state file."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state_data = json.load(f)
            return date.fromisoformat(state_data['last_month_downloaded'])
    # If no state file, start one month before the desired start date
    return START_DATE - relativedelta(months=1)


def save_state(last_month):
    """Saves the last downloaded month to the state file."""
    with open(STATE_FILE, 'w') as f:
        json.dump({'last_month_downloaded': last_month.isoformat()}, f, indent=4)


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
        raise ValueError("No API keys found in environment variables (e.g., API_KEY_1).")
    return keys


# --- Main Logic ---
# --- Main Logic ---
def fetch_month_data(api_key, month_to_fetch):
    """
    Fetches one month of data using a specific API key.
    Returns True on success, False on failure.
    """
    month_str = month_to_fetch.strftime('%Y-%m')
    print(f"\nAttempting to fetch data for month: {month_str}")

    params = {
        "function": "TIME_SERIES_INTRADAY",
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "month": month_str,
        "outputsize": "full",
        "apikey": api_key,
        "datatype": "csv"
    }
    try:
        response = requests.get("https://www.alphavantage.co/query", params=params)
        response.raise_for_status()

        # Check for API error messages in the response text
        if "Error Message" in response.text or "Information" in response.text:
            print(f"API returned an error/info message: {response.text}")
            return False

        # Save the data if the request was successful
        os.makedirs(DATA_FOLDER, exist_ok=True)
        filepath = os.path.join(DATA_FOLDER, f"{month_str}.csv")
        with open(filepath, 'w') as f:
            f.write(response.text)
        print(f"Successfully saved data for {month_str} to {filepath}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False


def run_downloader():
    """
    Main function to loop through API keys and download data for consecutive months.
    """
    api_keys = get_api_keys()
    num_keys = len(api_keys)
    print(f"Found {num_keys} API keys. Will attempt to download {num_keys} months of data.")

    last_downloaded_month = load_state()

    for i, key in enumerate(api_keys):
        month_to_fetch = last_downloaded_month + relativedelta(months=1)

        if month_to_fetch > END_DATE:
            print("All data for the specified range has been downloaded. Nothing to do. ✅")
            break

        print(f"--- Cycle {i + 1} of {num_keys} ---")
        print(f"Using API Key #{i + 1}")

        success = fetch_month_data(key, month_to_fetch)

        if success:
            # If successful, update the state for the next run
            last_downloaded_month = month_to_fetch
            save_state(last_downloaded_month)
            print(
                f"State updated. Next month to fetch is {(last_downloaded_month + relativedelta(months=1)).strftime('%Y-%m')}.")

            # If it's not the last key, wait before the next call
            if i < num_keys - 1:
                wait_time = random.uniform(65, 125)  # Random delay between 65-125 seconds
                print(f"Waiting for {wait_time:.0f} seconds to avoid rate limiting...")
                time.sleep(wait_time)
        else:
            print(f"Failed to fetch data with Key #{i + 1}. Stopping for this run.")
            # Stop if one key fails, as others might also be on cooldown
            break

    print("\nDownload process finished.")


if __name__ == "__main__":
    run_downloader()

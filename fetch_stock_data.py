import os
import requests
import pandas as pd
import json
from datetime import date
from dateutil.relativedelta import relativedelta

# --- Configuration ---
SYMBOL = 'MSK'
INTERVAL = '1min'
DATA_FOLDER = 'MSK_stock_data'
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
def fetch_historical_month():
    """Fetches the next month of historical data and saves it."""
    last_month = load_state()
    next_month = last_month + relativedelta(months=1)

    if next_month > END_DATE:
        print("All data for the specified range has been downloaded. Nothing to do. ✅")
        return

    month_str = next_month.strftime('%Y-%m')
    print(f"Attempting to fetch data for month: {month_str}")

    api_keys = get_api_keys()
    data_content = None

    for i, key in enumerate(api_keys):
        print(f"Trying with API Key #{i + 1}...")
        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": SYMBOL,
            "interval": INTERVAL,
            "month": month_str,
            "outputsize": "full",
            "apikey": key,
            "datatype": "csv"
        }
        try:
            response = requests.get("https://www.alphavantage.co/query", params=params)
            response.raise_for_status()

            if "Error Message" in response.text or "Information" in response.text:
                print(f"API returned an error/info message with Key #{i + 1}.")
                continue

            data_content = response.text
            print(f"Successfully fetched data with Key #{i + 1}.")
            break
        except requests.exceptions.RequestException as e:
            print(f"Request failed for Key #{i + 1}: {e}")
            continue

    if not data_content:
        print("All API keys failed. Aborting for this run.")
        return

    os.makedirs(DATA_FOLDER, exist_ok=True)
    filepath = os.path.join(DATA_FOLDER, f"{month_str}.csv")

    with open(filepath, 'w') as f:
        f.write(data_content)

    print(f"Data for {month_str} saved to {filepath}")

    save_state(next_month)
    print(f"State updated. Next run will fetch data for {(next_month + relativedelta(months=1)).strftime('%Y-%m')}.")


if __name__ == "__main__":
    fetch_historical_month()
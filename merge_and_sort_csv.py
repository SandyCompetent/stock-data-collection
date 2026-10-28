"""
NOTICE: This project was created for learning and demonstration purposes and is no longer maintained.
It has been merged into: https://github.com/SandyCompetent/stock-market-analysis
"""

import os
import pandas as pd
import glob

# --- Configuration ---
# The folder where your monthly CSV files are stored.
DATA_FOLDER = 'MRK_stock_data'
# The name of the final, merged output file.
OUTPUT_FILE = 'MRK_full_sorted_data.csv'
# The column to sort by. Alpha Vantage uses 'timestamp' for this API.
SORT_COLUMN = 'Date'


def merge_and_sort_csvs():
    """
    Finds all CSV files in a directory, merges them, sorts by timestamp,
    and saves the result to a new file.
    """
    # Check if the data folder exists
    if not os.path.isdir(DATA_FOLDER):
        print(f"Error: Data folder '{DATA_FOLDER}' not found.")
        print("Please make sure you have run the download script first.")
        return

    # Create a pattern to find all CSV files in the directory
    csv_pattern = os.path.join(DATA_FOLDER, '*.csv')
    csv_files = glob.glob(csv_pattern)

    if not csv_files:
        print(f"No CSV files found in '{DATA_FOLDER}'. Nothing to merge.")
        return

    print(f"Found {len(csv_files)} CSV files to merge.")

    # List to hold each DataFrame
    df_list = []
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            df_list.append(df)
        except Exception as e:
            print(f"Could not read or process {file}. Error: {e}")

    if not df_list:
        print("Could not read any dataframes. Aborting.")
        return

    # Concatenate all DataFrames into one
    print("Merging files...")
    merged_df = pd.concat(df_list, ignore_index=True)

    # --- Remove the 'open' column ---
    if 'open' in merged_df.columns:
        merged_df.drop(columns=['open'], inplace=True)
        print("Removed 'open' column.")

    # --- Rename the columns ---
    rename_map = {
        'timestamp': 'Date',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume'
    }

    merged_df.rename(columns=rename_map, inplace=True)
    print(f"Renamed columns: {rename_map.keys()}")

    # --- Sort the data ---
    print(f"Sorting data by '{SORT_COLUMN}'...")
    # 1. Convert the 'Date' column to datetime objects for accurate sorting
    merged_df[SORT_COLUMN] = pd.to_datetime(merged_df[SORT_COLUMN])

    # 2. Sort the DataFrame from earliest to latest
    merged_df.sort_values(by=SORT_COLUMN, ascending=True, inplace=True)

    # --- Save the final file ---
    try:
        merged_df.to_csv(OUTPUT_FILE, index=False)
        print("-" * 30)
        print(f"Success! Merged data saved to '{OUTPUT_FILE}'")
        print(f"Total rows: {len(merged_df)}")
        print("-" * 30)
    except Exception as e:
        print(f"Could not save the final file. Error: {e}")


if __name__ == "__main__":
    merge_and_sort_csvs()

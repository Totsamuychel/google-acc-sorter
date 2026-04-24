# -*- coding: utf-8 -*-
"""
Main entry point for Google Accounts Sorter.
Reads text files, parses accounts, uploads them to Google Sheets,
and moves the processed files to an archive directory.
"""

import os
import logging
import pandas as pd

from sorter.config import CREDENTIALS_FILE, HEADERS, SHEET_NAME, SOURCE_DIR, WORKSHEET_NAME
from sorter.gsheets import authenticate_gspread, ensure_headers, get_or_create_worksheet, append_data_to_sheet
from sorter.file_reader import ensure_directories_exist, get_source_files, archive_file
from sorter.parser import parse_data_line

# --- LOGGING CONFIGURATION ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main execution function."""
    logger.info("Starting Google Accounts Sorter...")
    
    # 1. Ensure required directories exist
    ensure_directories_exist()
    
    if not os.path.exists(CREDENTIALS_FILE):
        logger.error(f"Credentials file '{CREDENTIALS_FILE}' not found. Please follow the setup instructions.")
        return

    # 2. Authenticate and prepare Google Sheets
    client = authenticate_gspread()
    if not client:
        return
        
    worksheet = get_or_create_worksheet(client, SHEET_NAME, WORKSHEET_NAME)
    ensure_headers(worksheet, HEADERS)

    # 3. Read and parse data from files
    all_accounts_data = []
    source_files = get_source_files()

    if not source_files:
        logger.warning(f"No .txt files found in directory '{SOURCE_DIR}'.")
        return

    logger.info(f"Found {len(source_files)} text files to process.")

    processed_files = []

    for filename in source_files:
        filepath = os.path.join(SOURCE_DIR, filename)
        logger.info(f"Processing file: {filename}")
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parsed_data = parse_data_line(line)
                if parsed_data:
                    all_accounts_data.append(parsed_data)
                elif line.strip(): # Log warning only for non-empty lines
                    logger.warning(f"Could not parse line: '{line.strip()}' in file {filename}")
        
        # Mark file as successfully processed
        processed_files.append(filename)

    # 4. Format and write data to the spreadsheet
    if not all_accounts_data:
        logger.info("No new data to add to the spreadsheet.")
        
        # Even if there's no valid data, we might want to archive files so we don't process them again.
        for filename in processed_files:
            archive_file(filename)
        return

    logger.info(f"Prepared {len(all_accounts_data)} records for upload to Google Sheets.")
    
    # Use pandas for convenient row formatting
    df = pd.DataFrame(all_accounts_data, columns=['Логин', 'Пароль', 'Резервная почта'])
    df['Статус'] = 'Добавлено' # Add a status column for each new row
    
    # Convert DataFrame to a list of lists for gspread
    rows_to_append = df.values.tolist()
    
    # Append all rows in a single batch request for efficiency
    append_data_to_sheet(worksheet, rows_to_append)
    
    # 5. Archive processed files
    logger.info("Archiving processed files...")
    for filename in processed_files:
        archive_file(filename)
        
    logger.info("Finished processing successfully.")

if __name__ == '__main__':
    main()

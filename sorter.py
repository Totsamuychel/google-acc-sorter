# -*- coding: utf-8 -*-
import os
import gspread
import pandas as pd
import ollama
import logging
from google.oauth2.service_account import Credentials

# --- Settings ---
# Path to folder with source files
SOURCE_DIR = 'source_files'
# Name of the file with access keys Google API
CREDENTIALS_FILE = 'credentials.json'
# The name of the Google Sheet where the data will be saved.
SHEET_NAME = 'Учётные записи Google'
# Sheet name in the table
WORKSHEET_NAME = 'Аккаунты'
# Table headings
HEADERS = ['Логин', 'Пароль', 'Резервная почта', '  ']
# Ollama model for parsing complex strings
OLLAMA_MODEL = 'gpt-oss:20b'

# --- LOGGING CONFIGURATION ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def authenticate_gspread():
    """
    Authenticate in Google Sheets using a service account.
     Returns an authorized gspread client.
    """
    logging.info("Attempting to authenticate in Google API...")
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
        client = gspread.authorize(creds)
        logging.info("Authentication was successful.")
        return client
    except FileNotFoundError:
        logging.error(f"Файл '{CREDENTIALS_FILE}' not found. Please follow the instructions at the beginning of the script.")
        return None
    except Exception as e:
        logging.error(f"An error occurred during authentication.: {e}")
        return None

def get_or_create_worksheet(client, sheet_name, worksheet_name):
    """
    Gets or creates a Google Sheet and a sheet within it.
    """
    try:
        logging.info(f"Opening a table '{sheet_name}'...")
        spreadsheet = client.open(sheet_name)
    except gspread.exceptions.SpreadsheetNotFound:
        logging.warning(f"Table '{sheet_name}' not found. Create new...")
        spreadsheet = client.create(sheet_name)
        # Important: Share editing rights with yourself (service account)
        spreadsheet.share(client.auth.service_account_email, perm_type='user', role='writer')
        logging.info(f"Table '{sheet_name}' created and access granted.")

    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
        logging.info(f"Sheet '{worksheet_name}' found.")
    except gspread.exceptions.WorksheetNotFound:
        logging.warning(f"Sheet '{worksheet_name}' not found. Create new...")
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows="1000", cols="20")
        logging.info(f"Sheet '{worksheet_name}' created.")

    return worksheet

def ensure_headers(worksheet, headers):
    """
    Checks for headers on the sheet and adds them if they are missing.
    """
    try:
        first_row = worksheet.row_values(1)
        if first_row != headers:
            logging.info("Headings are missing or incorrect. I'm adding standard headings.")
            worksheet.update('A1', [headers])
    except gspread.exceptions.APIError as e:
        # If the sheet is empty, the API may return an error. In this case, simply add the headers.
        if 'exceeds grid limits' in str(e):
            logging.info("The sheet is empty. I'm adding headings.")
            worksheet.update('A1', [headers])
        else:
            raise e


def parse_with_ollama(line_content):
    """
    Uses the Ollama model to extract data from a complex format string.
    """
    system_prompt = (
        "You are a data extraction expert. Your task is to extract the login, password, and "
        "backup email from the provided line. The data must match the format "
        "login:password:backup_mail. If there are multiple entries in the line, extract only "
        "the first valid one. The response must contain ONLY a string in the format 'login:password:backup_email'. "
        "If you can't extract the data, please answer in one word: 'ERROR'."
    )
    
    try:
        logging.info(f"The string is too complex, I'm trying to recognize it using Ollama.: '{line_content[:50]}...'")
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': line_content},
            ],
        )
        result = response['message']['content'].strip()
        
        if result != 'ERROR' and len(result.split(':')) == 3:
            logging.info(f"Ollama successfully recognized the data: {result}")
            return result.split(':')
        else:
            logging.warning("Ollama could not recognize the data in the string.")
            return None
    except Exception as e:
        logging.error(f"There was an error accessing Ollama. Make sure the server is running. Error: {e}")
        return None


def parse_data_line(line):
    """
    Parses a single row of data. First, it tries simple splitting, then, if that fails, it resorts to Ollama.
    """
    line = line.strip()
    if not line:
        return None

    parts = line.split(':')
    # Simple check for standard format login:password:email
    if len(parts) == 3 and '@' in parts[0] and '@' in parts[2]:
        return parts

    # If simple parsing fails, we use the "heavy artillery"
    return parse_with_ollama(line)


def main():
    """
    The main function of the script.
    """
    # 1. Checking the presence of necessary files and folders
    if not os.path.exists(SOURCE_DIR):
        logging.error(f"Folder '{SOURCE_DIR}' not found. Please create it and place the .txt files in it.")
        return
        
    if not os.path.exists(CREDENTIALS_FILE):
        logging.error(f"File '{CREDENTIALS_FILE}' Not found. Follow the setup instructions.")
        return

    # 2. Authenticate and prepare Google Sheets
    client = authenticate_gspread()
    if not client:
        return
        
    worksheet = get_or_create_worksheet(client, SHEET_NAME, WORKSHEET_NAME)
    ensure_headers(worksheet, HEADERS)

    # 3. Reading and parsing data from files
    all_accounts_data = []
    source_files = [f for f in os.listdir(SOURCE_DIR) if f.endswith('.txt')]

    if not source_files:
        logging.warning(f"In folder '{SOURCE_DIR}' not found files with extension .txt.")
        return

    logging.info(f"Found {len(source_files)} text files for processing.")

    for filename in source_files:
        filepath = os.path.join(SOURCE_DIR, filename)
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parsed_data = parse_data_line(line)
                if parsed_data:
                    all_accounts_data.append(parsed_data)
                elif line.strip(): # We display a warning only for non-empty lines.
                    logging.warning(f"Unable to parse string: '{line.strip()}' in file {filename}")

    # 4. Forming and writing data to a table
    if not all_accounts_data:
        logging.info("No new data was found to add to the table..")
        return

    logging.info(f"Prepared {len(all_accounts_data)} entries to add to Google Таблицу.")
    
    # Using pandas for easy string formation
    df = pd.DataFrame(all_accounts_data, columns=['Login', 'Password', 'Backup mail'])
    df['Статус'] = 'Added' # Add a status for each new line
    
    # Converting a DataFrame to a List of Lists for gspread
    rows_to_append = df.values.tolist()
    
    # Add all rows in one query for efficiency
    worksheet.append_rows(rows_to_append, value_input_option='USER_ENTERED')
    
    logging.info(f"Successfully added {len(rows_to_append)} new entries in the table '{SHEET_NAME}'.")


if __name__ == '__main__':
    main()

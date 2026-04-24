# -*- coding: utf-8 -*-
"""Module for handling Google Sheets API authentication and operations."""

import logging
import gspread
from google.oauth2.service_account import Credentials

from sorter.config import CREDENTIALS_FILE, HEADERS, SHEET_NAME, WORKSHEET_NAME

logger = logging.getLogger(__name__)

def authenticate_gspread() -> gspread.client.Client:
    """
    Authenticate to Google Sheets using a service account.
    Returns the authorized gspread client.
    """
    logger.info("Attempting to authenticate with Google API...")
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
        client = gspread.authorize(creds)
        logger.info("Authentication successful.")
        return client
    except FileNotFoundError:
        logger.error(f"File '{CREDENTIALS_FILE}' not found. Please follow the setup instructions.")
        return None
    except Exception as e:
        logger.error(f"Error during authentication: {e}")
        return None

def get_or_create_worksheet(client: gspread.client.Client, sheet_name: str, worksheet_name: str) -> gspread.worksheet.Worksheet:
    """
    Retrieves or creates a Google Spreadsheet and the specified worksheet.
    """
    try:
        logger.info(f"Opening spreadsheet '{sheet_name}'...")
        spreadsheet = client.open(sheet_name)
    except gspread.exceptions.SpreadsheetNotFound:
        logger.warning(f"Spreadsheet '{sheet_name}' not found. Creating a new one...")
        spreadsheet = client.create(sheet_name)
        # Share the document with the service account itself so it can edit it.
        # Ideally, it should also be shared with your personal Google account.
        spreadsheet.share(client.auth.service_account_email, perm_type='user', role='writer')
        logger.info(f"Spreadsheet '{sheet_name}' created and access granted.")

    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
        logger.info(f"Worksheet '{worksheet_name}' found.")
    except gspread.exceptions.WorksheetNotFound:
        logger.warning(f"Worksheet '{worksheet_name}' not found. Creating a new one...")
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows="1000", cols="20")
        logger.info(f"Worksheet '{worksheet_name}' created.")

    return worksheet

def ensure_headers(worksheet: gspread.worksheet.Worksheet, headers: list):
    """
    Checks if headers exist on the worksheet and adds them if they are missing.
    """
    try:
        first_row = worksheet.row_values(1)
        if first_row != headers:
            logger.info("Headers are missing or incorrect. Adding standard headers.")
            worksheet.update('A1', [headers])
    except gspread.exceptions.APIError as e:
        # If the sheet is completely empty, the API might return an 'exceeds grid limits' error.
        if 'exceeds grid limits' in str(e):
            logger.info("Sheet is empty. Adding headers.")
            worksheet.update('A1', [headers])
        else:
            raise e

def append_data_to_sheet(worksheet: gspread.worksheet.Worksheet, rows_to_append: list):
    """
    Appends a list of rows to the Google Worksheet.
    """
    if not rows_to_append:
        return
    
    logger.info(f"Appending {len(rows_to_append)} rows to the worksheet.")
    worksheet.append_rows(rows_to_append, value_input_option='USER_ENTERED')
    logger.info("Rows appended successfully.")

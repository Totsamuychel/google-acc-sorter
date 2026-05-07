# -*- coding: utf-8 -*-
"""Configuration module."""

import os
from dotenv import load_dotenv

# Load variables from .env file if it exists
load_dotenv()

# --- CONSTANTS & SETTINGS ---

# Path to the directory with source .txt files
SOURCE_DIR = os.getenv('SOURCE_DIR', 'source_files')

# Path to the directory where processed files will be moved
ARCHIVE_DIR = os.getenv('ARCHIVE_DIR', 'archive')

# Path to the Google Service Account credentials JSON file
CREDENTIALS_FILE = os.getenv('CREDENTIALS_FILE', 'credentials.json')

# The name of the Google Sheet document
SHEET_NAME = os.getenv('SHEET_NAME', 'Учётные записи Google')

# The name of the specific worksheet inside the document
WORKSHEET_NAME = os.getenv('WORKSHEET_NAME', 'Аккаунты')

# The headers used in the Google Sheet
HEADERS = ['Логин', 'Пароль', 'Резервная почта', 'Статус']

# Ollama model used to parse complex/malformed lines
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'gpt-oss:20b')

# System prompt for Ollama
OLLAMA_SYSTEM_PROMPT = (
    "You are a data extraction expert. Your task is to extract the login, password, and "
    "backup email from the provided line. The data must match the format "
    "login:password:backup_mail. If there are multiple entries in the line, extract only "
    "the first valid one. The response must contain ONLY a string in the format 'login:password:backup_email'. "
    "If you can't extract the data, please answer in one word: 'ERROR'."
)

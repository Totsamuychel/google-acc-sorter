# -*- coding: utf-8 -*-
import os
import gspread
import pandas as pd
import ollama
import logging
from google.oauth2.service_account import Credentials

# --- НАСТРОЙКИ ---
# Путь к папке с исходными файлами
SOURCE_DIR = 'source_files'
# Имя файла с ключами доступа Google API
CREDENTIALS_FILE = 'credentials.json'
# Имя Google Таблицы, в которую будут сохраняться данные
SHEET_NAME = 'Учётные записи Google'
# Имя листа в таблице
WORKSHEET_NAME = 'Аккаунты'
# Заголовки для таблицы
HEADERS = ['Логин', 'Пароль', 'Резервная почта', '  ']
# Модель Ollama для разбора сложных строк
OLLAMA_MODEL = 'gpt-oss:20b'

# --- КОНФИГУРАЦИЯ ЛОГГИРОВАНИЯ ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def authenticate_gspread():
    """
    Аутентификация в Google Sheets с использованием сервисного аккаунта.
    Возвращает авторизованный клиент gspread.
    """
    logging.info("Попытка аутентификации в Google API...")
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
        client = gspread.authorize(creds)
        logging.info("Аутентификация прошла успешно.")
        return client
    except FileNotFoundError:
        logging.error(f"Файл '{CREDENTIALS_FILE}' не найден. Пожалуйста, следуйте инструкции в начале скрипта.")
        return None
    except Exception as e:
        logging.error(f"Произошла ошибка при аутентификации: {e}")
        return None

def get_or_create_worksheet(client, sheet_name, worksheet_name):
    """
    Получает или создает Google Таблицу и лист в ней.
    """
    try:
        logging.info(f"Открытие таблицы '{sheet_name}'...")
        spreadsheet = client.open(sheet_name)
    except gspread.exceptions.SpreadsheetNotFound:
        logging.warning(f"Таблица '{sheet_name}' не найдена. Создаю новую...")
        spreadsheet = client.create(sheet_name)
        # Важно: делимся правами на редактирование с самим собой (сервисным аккаунтом)
        spreadsheet.share(client.auth.service_account_email, perm_type='user', role='writer')
        logging.info(f"Таблица '{sheet_name}' создана и доступ предоставлен.")

    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
        logging.info(f"Лист '{worksheet_name}' найден.")
    except gspread.exceptions.WorksheetNotFound:
        logging.warning(f"Лист '{worksheet_name}' не найден. Создаю новый...")
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows="1000", cols="20")
        logging.info(f"Лист '{worksheet_name}' создан.")

    return worksheet

def ensure_headers(worksheet, headers):
    """
    Проверяет наличие заголовков на листе и добавляет их, если они отсутствуют.
    """
    try:
        first_row = worksheet.row_values(1)
        if first_row != headers:
            logging.info("Заголовки отсутствуют или некорректны. Добавляю стандартные заголовки.")
            worksheet.update('A1', [headers])
    except gspread.exceptions.APIError as e:
        # Если лист пустой, API может вернуть ошибку. В этом случае просто добавляем заголовки.
        if 'exceeds grid limits' in str(e):
            logging.info("Лист пустой. Добавляю заголовки.")
            worksheet.update('A1', [headers])
        else:
            raise e


def parse_with_ollama(line_content):
    """
    Использует модель Ollama для извлечения данных из строки сложного формата.
    """
    system_prompt = (
        "Ты — эксперт по извлечению данных. Твоя задача — извлечь логин, пароль и "
        "резервную почту из предоставленной строки. Данные должны соответствовать формату "
        "логин:пароль:резервная_почта. Если в строке несколько записей, извлеки только "
        "первую валидную. В ответе должна быть ТОЛЬКО строка в формате 'login:password:backup_email'. "
        "Если не удаётся извлечь данные, ответь одним словом: 'ERROR'."
    )
    
    try:
        logging.info(f"Строка слишком сложная, пробую распознать с помощью Ollama: '{line_content[:50]}...'")
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': line_content},
            ],
        )
        result = response['message']['content'].strip()
        
        if result != 'ERROR' and len(result.split(':')) == 3:
            logging.info(f"Ollama успешно распознала данные: {result}")
            return result.split(':')
        else:
            logging.warning("Ollama не смогла распознать данные в строке.")
            return None
    except Exception as e:
        logging.error(f"Ошибка при обращении к Ollama. Убедитесь, что сервер запущен. Ошибка: {e}")
        return None


def parse_data_line(line):
    """
    Парсит одну строку данных. Сначала пытается простым разделением,
    затем, в случае неудачи, обращается к Ollama.
    """
    line = line.strip()
    if not line:
        return None

    parts = line.split(':')
    # Простая проверка на стандартный формат login:password:email
    if len(parts) == 3 and '@' in parts[0] and '@' in parts[2]:
        return parts

    # Если простой парсинг не удался, используем "тяжелую артиллерию"
    return parse_with_ollama(line)


def main():
    """
    Главная функция скрипта.
    """
    # 1. Проверка наличия необходимых файлов и папок
    if not os.path.exists(SOURCE_DIR):
        logging.error(f"Папка '{SOURCE_DIR}' не найдена. Пожалуйста, создайте её и поместите в неё .txt файлы.")
        return
        
    if not os.path.exists(CREDENTIALS_FILE):
        logging.error(f"Файл '{CREDENTIALS_FILE}' не найден. Следуйте инструкции по настройке.")
        return

    # 2. Аутентификация и подготовка Google Таблицы
    client = authenticate_gspread()
    if not client:
        return
        
    worksheet = get_or_create_worksheet(client, SHEET_NAME, WORKSHEET_NAME)
    ensure_headers(worksheet, HEADERS)

    # 3. Чтение и парсинг данных из файлов
    all_accounts_data = []
    source_files = [f for f in os.listdir(SOURCE_DIR) if f.endswith('.txt')]

    if not source_files:
        logging.warning(f"В папке '{SOURCE_DIR}' не найдено файлов с расширением .txt.")
        return

    logging.info(f"Найдено {len(source_files)} текстовых файлов для обработки.")

    for filename in source_files:
        filepath = os.path.join(SOURCE_DIR, filename)
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parsed_data = parse_data_line(line)
                if parsed_data:
                    all_accounts_data.append(parsed_data)
                elif line.strip(): # Выводим предупреждение только для непустых строк
                    logging.warning(f"Не удалось разобрать строку: '{line.strip()}' в файле {filename}")

    # 4. Формирование и запись данных в таблицу
    if not all_accounts_data:
        logging.info("Новых данных для добавления в таблицу не найдено.")
        return

    logging.info(f"Подготовлено {len(all_accounts_data)} записей для добавления в Google Таблицу.")
    
    # Используем pandas для удобного формирования строк
    df = pd.DataFrame(all_accounts_data, columns=['Логин', 'Пароль', 'Резервная почта'])
    df['Статус'] = 'Добавлено' # Добавляем статус для каждой новой строки
    
    # Преобразуем DataFrame в список списков для gspread
    rows_to_append = df.values.tolist()
    
    # Добавляем все строки одним запросом для эффективности
    worksheet.append_rows(rows_to_append, value_input_option='USER_ENTERED')
    
    logging.info(f"Успешно добавлено {len(rows_to_append)} новых записей в таблицу '{SHEET_NAME}'.")


if __name__ == '__main__':
    main()
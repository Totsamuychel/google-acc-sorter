# -*- coding: utf-8 -*-
"""Module for parsing text lines to extract account data."""

import logging
import ollama

from sorter.config import OLLAMA_MODEL, OLLAMA_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

def parse_with_ollama(line_content: str) -> list:
    """
    Uses the Ollama model to extract data from a complex string.
    Returns a list: [login, password, backup_email] or None if parsing fails.
    """
    try:
        # Slice to avoid huge log lines
        logger.info(f"String too complex, trying to parse with Ollama: '{line_content[:50]}...'")
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {'role': 'system', 'content': OLLAMA_SYSTEM_PROMPT},
                {'role': 'user', 'content': line_content},
            ],
        )
        result = response['message']['content'].strip()
        
        if result != 'ERROR' and len(result.split(':')) == 3:
            logger.info(f"Ollama successfully parsed the data: {result}")
            return result.split(':')
        else:
            logger.warning("Ollama failed to parse the data in this line.")
            return None
    except Exception as e:
        logger.error(f"Error calling Ollama. Is the server running? Error: {e}")
        return None

def parse_data_line(line: str) -> list:
    """
    Parses a single line of data.
    First tries simple splitting. If that fails, falls back to Ollama.
    Returns a list: [login, password, backup_email] or None.
    """
    line = line.strip()
    if not line:
        return None

    parts = line.split(':')
    # Simple heuristic: we expect exactly 3 parts, and both login and backup_email should have '@'
    if len(parts) == 3 and '@' in parts[0] and '@' in parts[2]:
        return parts

    # If simple parsing fails, bring out the heavy artillery (Ollama)
    return parse_with_ollama(line)

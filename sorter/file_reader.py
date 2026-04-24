# -*- coding: utf-8 -*-
"""Module for handling file I/O operations and reading source files."""

import os
import shutil
import logging
from typing import List

from sorter.config import SOURCE_DIR, ARCHIVE_DIR

logger = logging.getLogger(__name__)

def ensure_directories_exist():
    """
    Checks if source and archive directories exist, and creates them if they don't.
    """
    for directory in [SOURCE_DIR, ARCHIVE_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory '{directory}'.")

def get_source_files() -> List[str]:
    """
    Returns a list of .txt files in the source directory.
    """
    if not os.path.exists(SOURCE_DIR):
        logger.error(f"Directory '{SOURCE_DIR}' not found.")
        return []
    
    files = [f for f in os.listdir(SOURCE_DIR) if f.endswith('.txt')]
    return files

def archive_file(filename: str):
    """
    Moves a processed file to the archive directory so it won't be processed again.
    """
    source_path = os.path.join(SOURCE_DIR, filename)
    archive_path = os.path.join(ARCHIVE_DIR, filename)
    
    try:
        shutil.move(source_path, archive_path)
        logger.info(f"File '{filename}' moved to '{ARCHIVE_DIR}'.")
    except Exception as e:
        logger.error(f"Failed to move file '{filename}' to archive: {e}")

# -*- coding: utf-8 -*-
import pytest
from sorter.parser import parse_data_line

def test_parse_simple_valid_line():
    line = "user@gmail.com:password123:backup@gmail.com"
    result = parse_data_line(line)
    assert result == ["user@gmail.com", "password123", "backup@gmail.com"]

def test_parse_empty_line():
    assert parse_data_line("") is None
    assert parse_data_line("   ") is None

# Note: Testing the Ollama fallback requires mocking the ollama.chat function
# to avoid actual network/local LLM calls during automated unit tests.
from unittest.mock import patch

@patch('sorter.parser.ollama.chat')
def test_parse_complex_line_with_ollama(mock_chat):
    # Setup mock response
    mock_chat.return_value = {
        'message': {
            'content': "complex_user@gmail.com:complex_pass:complex_backup@gmail.com"
        }
    }
    
    # A line that doesn't match the simple login:pass:backup check
    line = "Some text before user@gmail.com passwOrd backup@gmail.com and some text after"
    result = parse_data_line(line)
    
    assert result == ["complex_user@gmail.com", "complex_pass", "complex_backup@gmail.com"]
    mock_chat.assert_called_once()

@patch('sorter.parser.ollama.chat')
def test_parse_complex_line_ollama_failure(mock_chat):
    mock_chat.return_value = {
        'message': {
            'content': "ERROR"
        }
    }
    
    line = "Absolute garbage data with no emails"
    result = parse_data_line(line)
    
    assert result is None
    mock_chat.assert_called_once()

import pytest
import os
from unittest.mock import patch, MagicMock
from scripts.bridge import parse_decision, extract_skill_data, evaluate_utility

def test_parse_decision():
    # Promote
    assert parse_decision("DECISION: [PROMOTE]\nReasoning: ...") == "PROMOTE"
    assert parse_decision("DECISION: [promote]") == "PROMOTE"
    
    # Reject
    assert parse_decision("DECISION: [REJECT]") == "REJECT"
    assert parse_decision("Some text\nDECISION: [REJECT]\nMore text") == "REJECT"
    
    # Unknown
    assert parse_decision("No decision here") == "UNKNOWN"
    assert parse_decision(None) == "UNKNOWN"
    assert parse_decision("DECISION: [MAYBE]") == "UNKNOWN"

@pytest.fixture
def mock_skill_content():
    return """
    Some header
    This is a Skill called YouTube Analysis.
    It does things.
    """

@patch("os.path.exists")
@patch("builtins.open", new_callable=MagicMock)
def test_extract_skill_data(mock_open, mock_exists, mock_skill_content):
    mock_exists.return_value = True
    mock_open.return_value.__enter__.return_value.read.return_value = mock_skill_content
    
    from scripts.bridge import extract_skill_data
    # Found
    result = extract_skill_data("path", "YouTube Analysis")
    assert "YouTube Analysis" in result
    
    # Not found in content, returns full content
    result_not_found = extract_skill_data("path", "Other")
    assert result_not_found == mock_skill_content

@patch("scripts.bridge.call_ollama")
def test_evaluate_utility(mock_call):
    from scripts.bridge import evaluate_utility
    mock_call.return_value = "DECISION: [PROMOTE]"
    result = evaluate_utility("Skill", "Context")
    assert "DECISION: [PROMOTE]" in result


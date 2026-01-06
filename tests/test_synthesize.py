import pytest
import os
import re
from unittest.mock import MagicMock, patch
from scripts.synthesize import aggregate_library, synthesize_knowledge

@patch("os.listdir")
@patch("builtins.open", new_callable=MagicMock)
@patch("scripts.synthesize.LIBRARY_DIR", new=MagicMock())
def test_aggregate_library(mock_open, mock_listdir):
    from scripts.synthesize import LIBRARY_DIR
    LIBRARY_DIR.exists.return_value = True
    
    # 00_Index_ matches the index_pattern r'^\d+_Index_'
    mock_listdir.return_value = ["2026-01-01_test.md", "00_Index_Library.md", "other.txt"]
    
    # Mocking file content
    mock_file = MagicMock()
    mock_file.read.return_value = "tags: [topic/ai]\nContent here."
    mock_open.return_value.__enter__.return_value = mock_file
    
    # Test without category
    text = aggregate_library()
    assert "2026-01-01_test.md" in text
    assert "00_Index_Library.md" not in text
    assert "Content here" in text
    
    # Test with category match
    text_ai = aggregate_library(category="ai")
    assert "2026-01-01_test.md" in text_ai
    
    # Test with category mismatch
    text_diet = aggregate_library(category="diet")
    assert "2026-01-01_test.md" not in text_diet

@patch("scripts.synthesize.run_ollama_command")
def test_synthesize_knowledge(mock_run):
    mock_run.return_value = "```markdown\n# Master Strategy\nResult\n```"
    result = synthesize_knowledge("aggregated text", "AI")
    assert "# Master Strategy" in result
    assert "Result" in result

@patch("scripts.synthesize.run_ollama_command")
def test_synthesize_knowledge_raw(mock_run):
    mock_run.return_value = "# Master Strategy\nRaw Result"
    result = synthesize_knowledge("aggregated text", "AI")
    assert "Raw Result" in result

@patch("scripts.synthesize.run_ollama_command")
def test_synthesize_knowledge_timeout(mock_run):
    mock_run.side_effect = RuntimeError("Ollama command timed out")
    result = synthesize_knowledge("text", "Topic")
    assert result is None

@patch("os.listdir")
@patch("scripts.synthesize.LIBRARY_DIR", new=MagicMock())
def test_aggregate_library_no_md_files(mock_listdir):
    from scripts.synthesize import LIBRARY_DIR
    LIBRARY_DIR.exists.return_value = True
    mock_listdir.return_value = ["file.txt", "script.py"]
    assert aggregate_library() == ""


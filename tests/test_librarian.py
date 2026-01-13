import pytest
import subprocess
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
from scripts.librarian import clean_srt, get_video_data
from scripts.config import run_ollama_command

def test_clean_srt():
    srt_content = """1
00:00:01,000 --> 00:00:02,000
Hello <b>World</b>

2
00:00:03,000 --> 00:00:04,000
This is a test.

This is a test.
"""
    cleaned = clean_srt(srt_content)
    # Check timestamp removal
    assert "00:00" not in cleaned
    assert "-->" not in cleaned
    # Check index removal
    assert "1" not in cleaned.split()
    # Check HTML stripping
    assert "<b>" not in cleaned
    assert "World" in cleaned
    # Check deduplication
    assert cleaned.count("This is a test.") == 1
    # Check extra whitespace
    assert "  " not in cleaned

def test_clean_srt_complex():
    srt = """1
00:00:01,000 --> 00:00:02,000
Line 1
Line 1

2
00:00:02,000 --> 00:00:03,000
Line 2
<font color="red">Line 3</font>

3
00:00:03,000 --> 00:00:04,000
Line 2
"""
    cleaned = clean_srt(srt)
    # Deduplication across blocks
    assert "Line 1 Line 2 Line 3 Line 2" in cleaned

@pytest.mark.parametrize("srt,expected", [
    ("1\n00:00:01,000 --> 00:00:02,000\nHello", "Hello"),
    ("1\n00:00:01,000 --> 00:00:02,000\n<b>Hi</b>", "Hi"),
    ("1\n00:00:01,000 --> 00:00:02,000\nA\n1\n00:00:02,000 --> 00:00:03,000\nA", "A"),
])
def test_clean_srt_parameterized(srt, expected):
    assert clean_srt(srt) == expected

@patch("subprocess.run")
def test_run_ollama_command(mock_run):
    cmd = ["ollama", "run", "deepseek-r1:14b", "test prompt"]
    # Success case with <think> stripping
    mock_run.return_value = MagicMock(
        returncode=0, 
        stdout="<think>internal monologue</think>Actual response",
        stderr=""
    )
    response = run_ollama_command("test prompt")
    assert response == "Actual response"
    assert "<think>" not in response
    
    # Timeout case
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["ollama"], timeout=300)
    with pytest.raises(RuntimeError, match="timed out"):
        run_ollama_command("test prompt")
    
    # Failure case
    mock_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="Error message")
    with pytest.raises(RuntimeError, match="failed with exit code 1"):
        run_ollama_command("test prompt")

@patch("subprocess.run")
@patch("tempfile.TemporaryDirectory")
@patch("pathlib.Path.exists")
@patch("pathlib.Path.mkdir")
def test_get_video_data_failure_cleanup(mock_mkdir, mock_exists, mock_tempdir, mock_run):
    """Verify that cleanup (tempfile.TemporaryDirectory) is used even if subprocess.run fails."""
    mock_exists.return_value = True
    mock_run.return_value = MagicMock(returncode=1, stderr="metadata error")
    
    # Mock context manager behavior
    mock_temp_path = MagicMock()
    mock_tempdir.return_value.__enter__.return_value = str(mock_temp_path)
    
    data = get_video_data("https://youtube.com/watch?v=fail")
    
    assert data is None
    # Verify the context manager was entered
    assert mock_tempdir.called

@patch("subprocess.run")
@patch("os.listdir")
@patch("builtins.open", new_callable=MagicMock)
@patch("pathlib.Path.exists")
@patch("pathlib.Path.mkdir")
@patch("tempfile.TemporaryDirectory")
def test_get_video_data_success(mock_tempdir, mock_mkdir, mock_exists, mock_open, mock_listdir, mock_run):
    mock_exists.return_value = True
    mock_run.side_effect = [
        # First call: metadata
        MagicMock(returncode=0, stdout='{"title": "Test Title", "uploader": "Test Channel", "id": "123"}'),
        # Second call: subtitles
        MagicMock(returncode=0, stdout="", stderr="")
    ]
    
    # Mock context manager behavior
    mock_temp_path = "/tmp/fake_temp"
    mock_tempdir.return_value.__enter__.return_value = mock_temp_path
    
    mock_listdir.return_value = ["transcript.en.srt"]
    mock_open.return_value.__enter__.return_value.read.return_value = "1\n00:00:01,000 --> 00:00:02,000\nHello"
    
    data = get_video_data("https://youtube.com/watch?v=123")
    
    assert data["title"] == "Test Title"
    assert data["channel"] == "Test Channel"
    assert data["video_id"] == "123"
    assert "Hello" in data["transcript"]
    
    # Verify context manager was used
    assert mock_tempdir.called

    # Inverse Test Analysis:
    # 1. We don't test the actual library file content generated (only its presence and metadata).
    # 2. We don't test the Ollama prompt generation logic for synthesis.
    # 3. We don't test the --dry-run flag behavior in these unit tests.
    # 4. We don't test the actual yt-dlp binary output (only mocked responses).

@patch("subprocess.run")
@patch("tempfile.TemporaryDirectory")
@patch("pathlib.Path.mkdir")
def test_get_video_data_metadata_failure_simple(mock_mkdir, mock_tempdir, mock_run):
    mock_run.return_value = MagicMock(returncode=1, stderr="metadata error")
    
    # Mock context manager behavior
    mock_temp_path = "/tmp/fake_temp"
    mock_tempdir.return_value.__enter__.return_value = mock_temp_path
    
    data = get_video_data("https://youtube.com/watch?v=fail")
    assert data is None

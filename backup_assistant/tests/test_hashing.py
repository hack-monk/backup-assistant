"""Tests for hashing utilities."""

import pytest
import tempfile
import os
from pathlib import Path

from backup_assistant.utils.hashing import hash_file, hash_string


def test_hash_string():
    """Test hashing a string."""
    result = hash_string("test string")
    assert isinstance(result, str)
    assert len(result) == 64  # SHA256 produces 64 hex characters
    assert result == hash_string("test string")  # Deterministic


def test_hash_file():
    """Test hashing a file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("test content")
        temp_path = f.name
    
    try:
        hash1 = hash_file(temp_path)
        assert isinstance(hash1, str)
        assert len(hash1) == 64
        
        # Hash should be deterministic
        hash2 = hash_file(temp_path)
        assert hash1 == hash2
        
        # Hash should change with content
        with open(temp_path, 'w') as f:
            f.write("different content")
        hash3 = hash_file(temp_path)
        assert hash1 != hash3
    
    finally:
        os.unlink(temp_path)


def test_hash_file_not_found():
    """Test hashing a non-existent file."""
    with pytest.raises(FileNotFoundError):
        hash_file("/nonexistent/path/file.txt")


def test_hash_file_directory():
    """Test hashing a directory (should raise error)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with pytest.raises(ValueError):
            hash_file(temp_dir)



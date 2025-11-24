"""Tests for database manager."""

import pytest
import tempfile
import os
from pathlib import Path

from backup_assistant.db.db_manager import DBManager


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)
    
    db_manager = DBManager(db_path=db_path)
    yield db_manager
    
    db_manager.close()
    if db_path.exists():
        os.unlink(db_path)


def test_create_tables(temp_db):
    """Test that tables are created."""
    # Tables should be created automatically
    metadata = temp_db.get_metadata_for_path("test_path")
    assert metadata is None  # No data yet, but no error means tables exist


def test_upsert_file_metadata(temp_db):
    """Test inserting and updating file metadata."""
    file_path = "/test/path/file.txt"
    file_hash = "abc123"
    modified_time = 1234567890.0
    file_size = 1024
    
    # Insert
    temp_db.upsert_file_metadata(file_path, file_hash, modified_time, file_size)
    metadata = temp_db.get_metadata_for_path(file_path)
    
    assert metadata is not None
    assert metadata['file_path'] == file_path
    assert metadata['file_hash'] == file_hash
    assert metadata['modified_time'] == modified_time
    assert metadata['file_size'] == file_size
    
    # Update
    new_hash = "def456"
    new_time = 1234567891.0
    temp_db.upsert_file_metadata(file_path, new_hash, new_time, file_size)
    metadata = temp_db.get_metadata_for_path(file_path)
    
    assert metadata['file_hash'] == new_hash
    assert metadata['modified_time'] == new_time


def test_get_metadata_for_path(temp_db):
    """Test retrieving metadata."""
    # Non-existent path
    metadata = temp_db.get_metadata_for_path("/nonexistent")
    assert metadata is None
    
    # Existing path
    temp_db.upsert_file_metadata("/test/file.txt", "hash123", 1234567890.0, 512)
    metadata = temp_db.get_metadata_for_path("/test/file.txt")
    assert metadata is not None
    assert metadata['file_hash'] == "hash123"


def test_delete_metadata(temp_db):
    """Test deleting metadata."""
    file_path = "/test/file.txt"
    temp_db.upsert_file_metadata(file_path, "hash123", 1234567890.0, 512)
    
    assert temp_db.get_metadata_for_path(file_path) is not None
    
    temp_db.delete_metadata(file_path)
    
    assert temp_db.get_metadata_for_path(file_path) is None


def test_backup_session(temp_db):
    """Test backup session creation and update."""
    session_id = temp_db.create_backup_session("/source", "/dest")
    assert isinstance(session_id, int)
    assert session_id > 0
    
    temp_db.update_backup_session(session_id, files_copied=10, files_skipped=5, total_size=1024)
    # No exception means update succeeded



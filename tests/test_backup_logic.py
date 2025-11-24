"""Tests for backup logic (scanner and copier)."""

import pytest
import tempfile
import os
import shutil
from pathlib import Path

from backup_engine.scanner import FileScanner
from backup_engine.copier import FileCopier
from db.db_manager import DBManager
from utils.logger import BackupLogger


@pytest.fixture
def temp_dirs():
    """Create temporary source and destination directories."""
    source_dir = tempfile.mkdtemp()
    dest_dir = tempfile.mkdtemp()
    
    yield source_dir, dest_dir
    
    shutil.rmtree(source_dir, ignore_errors=True)
    shutil.rmtree(dest_dir, ignore_errors=True)


@pytest.fixture
def temp_db():
    """Create a temporary database."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)
    
    db_manager = DBManager(db_path=db_path)
    yield db_manager
    
    db_manager.close()
    if db_path.exists():
        os.unlink(db_path)


@pytest.fixture
def logger():
    """Create a logger instance."""
    return BackupLogger(log_to_file=False)


def test_scanner_scan_folder(temp_dirs):
    """Test scanning a folder."""
    source_dir, _ = temp_dirs
    
    # Create test files
    (Path(source_dir) / "file1.txt").write_text("content1")
    (Path(source_dir) / "file2.txt").write_text("content2")
    (Path(source_dir) / "subdir").mkdir()
    (Path(source_dir) / "subdir" / "file3.txt").write_text("content3")
    
    scanner = FileScanner()
    file_list = scanner.scan_folder(source_dir, calculate_hash=True)
    
    assert len(file_list) == 3
    assert all('path' in f for f in file_list)
    assert all('hash' in f for f in file_list)
    assert all('modified_time' in f for f in file_list)
    assert all('size' in f for f in file_list)


def test_scanner_exclude_patterns(temp_dirs):
    """Test that exclude patterns work."""
    source_dir, _ = temp_dirs
    
    (Path(source_dir) / "file.txt").write_text("content")
    (Path(source_dir) / ".DS_Store").write_text("ds_store")
    
    scanner = FileScanner()
    file_list = scanner.scan_folder(source_dir, calculate_hash=True)
    
    # .DS_Store should be excluded
    file_names = [Path(f['path']).name for f in file_list]
    assert ".DS_Store" not in file_names
    assert "file.txt" in file_names


def test_copier_should_copy_new_file(temp_db, logger):
    """Test that new files should be copied."""
    file_meta = {
        'path': '/test/file.txt',
        'hash': 'abc123',
        'modified_time': 1234567890.0,
        'size': 100
    }
    
    copier = FileCopier(temp_db, logger)
    should_copy = copier._should_copy_file(file_meta)
    
    assert should_copy is True  # New file should be copied


def test_copier_should_skip_unchanged_file(temp_db, logger):
    """Test that unchanged files should be skipped."""
    file_path = '/test/file.txt'
    file_hash = 'abc123'
    modified_time = 1234567890.0
    
    # Insert into DB
    temp_db.upsert_file_metadata(file_path, file_hash, modified_time, 100)
    
    # Same file metadata
    file_meta = {
        'path': file_path,
        'hash': file_hash,
        'modified_time': modified_time,
        'size': 100
    }
    
    copier = FileCopier(temp_db, logger)
    should_copy = copier._should_copy_file(file_meta)
    
    assert should_copy is False  # Unchanged file should be skipped


def test_copier_should_copy_changed_file(temp_db, logger):
    """Test that changed files should be copied."""
    file_path = '/test/file.txt'
    
    # Insert original into DB
    temp_db.upsert_file_metadata(file_path, 'old_hash', 1234567890.0, 100)
    
    # File with new hash
    file_meta = {
        'path': file_path,
        'hash': 'new_hash',
        'modified_time': 1234567890.0,
        'size': 100
    }
    
    copier = FileCopier(temp_db, logger)
    should_copy = copier._should_copy_file(file_meta)
    
    assert should_copy is True  # Changed file should be copied


def test_copier_dry_run(temp_dirs, temp_db, logger):
    """Test dry run mode (no actual copying)."""
    source_dir, dest_dir = temp_dirs
    
    # Create source file
    source_file = Path(source_dir) / "test.txt"
    source_file.write_text("test content")
    
    file_list = [{
        'path': str(source_file),
        'relative_path': 'test.txt',
        'hash': 'test_hash',
        'modified_time': source_file.stat().st_mtime,
        'size': source_file.stat().st_size
    }]
    
    copier = FileCopier(temp_db, logger)
    results = copier.copy_files(file_list, source_dir, dest_dir, dry_run=True)
    
    # File should not exist in destination
    dest_file = Path(dest_dir) / "test.txt"
    assert not dest_file.exists()
    
    # But results should show it would be copied
    assert results['files_copied'] == 1


def test_copier_actual_copy(temp_dirs, temp_db, logger):
    """Test actual file copying."""
    source_dir, dest_dir = temp_dirs
    
    # Create source file
    source_file = Path(source_dir) / "test.txt"
    source_file.write_text("test content")
    
    file_list = [{
        'path': str(source_file),
        'relative_path': 'test.txt',
        'hash': 'test_hash',
        'modified_time': source_file.stat().st_mtime,
        'size': source_file.stat().st_size
    }]
    
    copier = FileCopier(temp_db, logger)
    results = copier.copy_files(file_list, source_dir, dest_dir, dry_run=False)
    
    # File should exist in destination
    dest_file = Path(dest_dir) / "test.txt"
    assert dest_file.exists()
    assert dest_file.read_text() == "test content"
    
    # Metadata should be in DB
    metadata = temp_db.get_metadata_for_path(str(source_file))
    assert metadata is not None
    assert metadata['file_hash'] == 'test_hash'



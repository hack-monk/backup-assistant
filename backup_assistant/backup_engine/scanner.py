"""File traversal, hashing, and timestamp checking."""

import os
import fnmatch
import sys
from pathlib import Path
from typing import List, Dict, Optional, Callable

from ..utils.hashing import hash_file
from ..utils.config import EXCLUDE_PATTERNS, INCLUDE_PATTERNS, MAX_FILE_SIZE, MIN_FILE_SIZE, IS_WINDOWS


class FileScanner:
    """Scans directories and collects file metadata."""
    
    def __init__(self, progress_callback: Optional[Callable] = None):
        """
        Initialize file scanner.
        
        Args:
            progress_callback: Optional callback function(current, total) for progress updates
        """
        self.progress_callback = progress_callback
        self.scanned_count = 0
        self.total_files = 0
    
    def _should_include_file(self, file_path: Path) -> bool:
        """
        Check if file should be included based on patterns.
        Uses fnmatch for cross-platform pattern matching.
        
        Args:
            file_path: Path to check
        
        Returns:
            True if file should be included
        """
        file_name = file_path.name
        
        # Check exclude patterns using fnmatch for proper wildcard support
        if EXCLUDE_PATTERNS:
            for pattern in EXCLUDE_PATTERNS:
                if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(str(file_path), pattern):
                    return False
        
        # Check include patterns
        if INCLUDE_PATTERNS:
            for pattern in INCLUDE_PATTERNS:
                if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(str(file_path), pattern):
                    return True
            return False  # Not in include list
        
        return True  # No filters, include all
    
    def _should_skip_directory(self, dir_path: Path) -> bool:
        """
        Check if directory should be skipped.
        Platform-aware: skips system and hidden directories.
        
        Args:
            dir_path: Directory path to check
        
        Returns:
            True if directory should be skipped
        """
        dir_name = dir_path.name
        
        # Skip hidden directories (Unix/macOS/Linux)
        if dir_name.startswith('.'):
            return True
        
        # Skip Windows system directories
        if IS_WINDOWS:
            if dir_name in ['System Volume Information', '$RECYCLE.BIN', 'RECYCLER']:
                return True
        
        # Skip macOS system directories
        if sys.platform == 'darwin':
            if dir_name in ['.fseventsd', '.Spotlight-V100', '.TemporaryItems', '.Trashes']:
                return True
        
        return False
    
    def scan_folder(self, folder_path: str, calculate_hash: bool = True) -> List[Dict]:
        """
        Walk through folder and collect file metadata.
        
        Args:
            folder_path: Path to source directory
            calculate_hash: Whether to calculate SHA256 hash (can be slow for large files)
        
        Returns:
            List of dicts with keys: path, modified_time, hash, size
        """
        folder_path = Path(folder_path).resolve()
        
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        if not folder_path.is_dir():
            raise ValueError(f"Path is not a directory: {folder_path}")
        
        file_metadata = []
        self.scanned_count = 0
        
        # First pass: count total files for progress
        self.total_files = sum(1 for _ in folder_path.rglob('*') if _.is_file() and self._should_include_file(_))
        
        # Second pass: collect metadata
        for root, dirs, files in os.walk(folder_path):
            # Skip hidden directories and system directories (platform-aware)
            dirs[:] = [d for d in dirs if not self._should_skip_directory(Path(root) / d)]
            
            for file_name in files:
                file_path = Path(root) / file_name
                
                # Check if file should be included
                if not self._should_include_file(file_path):
                    continue
                
                try:
                    # Get file stats
                    stat = file_path.stat()
                    file_size = stat.st_size
                    modified_time = stat.st_mtime
                    
                    # Check size limits
                    if file_size < MIN_FILE_SIZE or file_size > MAX_FILE_SIZE:
                        continue
                    
                    # Calculate hash if requested
                    file_hash = None
                    if calculate_hash:
                        try:
                            file_hash = hash_file(file_path)
                        except (IOError, PermissionError) as e:
                            # Skip files that can't be read
                            continue
                    
                    # Store relative path from source folder
                    try:
                        relative_path = file_path.relative_to(folder_path)
                    except ValueError:
                        # Fallback to absolute path if relative fails
                        relative_path = file_path
                    
                    file_metadata.append({
                        'path': str(file_path),  # Absolute path
                        'relative_path': str(relative_path),  # Relative path
                        'modified_time': modified_time,
                        'hash': file_hash,
                        'size': file_size
                    })
                    
                    self.scanned_count += 1
                    if self.progress_callback:
                        self.progress_callback(self.scanned_count, self.total_files)
                
                except (OSError, PermissionError) as e:
                    # Skip files that can't be accessed
                    continue
        
        return file_metadata
    
    def get_file_metadata(self, file_path: str, calculate_hash: bool = True) -> Optional[Dict]:
        """
        Get metadata for a single file.
        
        Args:
            file_path: Path to file
            calculate_hash: Whether to calculate hash
        
        Returns:
            Dict with metadata or None if file doesn't exist
        """
        file_path = Path(file_path)
        
        if not file_path.exists() or not file_path.is_file():
            return None
        
        if not self._should_include_file(file_path):
            return None
        
        try:
            stat = file_path.stat()
            file_size = stat.st_size
            modified_time = stat.st_mtime
            
            file_hash = None
            if calculate_hash:
                file_hash = hash_file(file_path)
            
            return {
                'path': str(file_path),
                'relative_path': str(file_path),
                'modified_time': modified_time,
                'hash': file_hash,
                'size': file_size
            }
        except (OSError, IOError, PermissionError):
            return None



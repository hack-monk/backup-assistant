"""Responsible for actual file copying with deduplication."""

import shutil
import os
import stat
from pathlib import Path
from typing import List, Dict, Optional, Callable, Set

from db.db_manager import DBManager
from utils.logger import BackupLogger
from utils.config import IS_WINDOWS


class FileCopier:
    """Handles conditional file copying based on hash/timestamp comparison."""
    
    def __init__(self, db_manager: DBManager, logger: BackupLogger,
                 progress_callback: Optional[Callable] = None):
        """
        Initialize file copier.
        
        Args:
            db_manager: Database manager instance
            logger: Logger instance
            progress_callback: Optional callback function(current, total) for progress
        """
        self.db_manager = db_manager
        self.logger = logger
        self.progress_callback = progress_callback
        self.files_copied = 0
        self.files_skipped = 0
        self.duplicates_skipped = 0
        self.total_size = 0
    
    def _should_copy_file(self, file_metadata: Dict) -> bool:
        """
        Determine if file should be copied based on comparison with DB.
        
        Args:
            file_metadata: Dict with path, hash, modified_time, size
        
        Returns:
            True if file should be copied
        """
        file_path = file_metadata['path']
        stored_metadata = self.db_manager.get_metadata_for_path(file_path)
        
        # New file - always copy
        if stored_metadata is None:
            return True
        
        # Check if hash changed (content changed)
        if file_metadata['hash'] != stored_metadata['file_hash']:
            return True
        
        # Check if modification time changed (file was modified)
        if abs(file_metadata['modified_time'] - stored_metadata['modified_time']) > 1.0:
            return True
        
        # File hasn't changed - skip
        return False
    
    def copy_files(self, file_list: List[Dict], source_dir: str, dest_dir: str,
                   dry_run: bool = False, check_destination_duplicates: bool = True) -> Dict:
        """
        Copy new or changed files to destination.
        
        Args:
            file_list: List of file metadata dicts
            source_dir: Source directory path
            dest_dir: Destination directory path
            dry_run: If True, only log what would be copied without actually copying
            check_destination_duplicates: If True, check if file hash exists on destination
        
        Returns:
            Dict with stats: files_copied, files_skipped, files_duplicated, total_size, errors
        """
        source_dir = Path(source_dir).resolve()
        dest_dir = Path(dest_dir).resolve()
        dest_root = str(dest_dir)
        
        # Ensure destination exists
        if not dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)
        
        files_to_copy = []
        files_to_skip = []
        files_duplicated = []
        errors = []
        
        # Determine which files need copying (check source changes first)
        for file_meta in file_list:
            if self._should_copy_file(file_meta):
                files_to_copy.append(file_meta)
            else:
                files_to_skip.append(file_meta)
        
        self.logger.info(f"Found {len(files_to_copy)} files to copy, {len(files_to_skip)} to skip")
        
        # Check destination duplicates for files that need copying
        if check_destination_duplicates:
            self.logger.info("Checking for duplicates on destination drive...")
            for file_meta in files_to_copy[:]:  # Use slice to iterate over copy
                file_hash = file_meta.get('hash')
                if file_hash and self.db_manager.get_destination_hash_exists(dest_root, file_hash):
                    # File with this hash already exists on destination
                    dest_file_info = self.db_manager.get_destination_file_by_hash(dest_root, file_hash)
                    if dest_file_info:
                        self.logger.info(
                            f"Skipped (duplicate on destination): {file_meta.get('relative_path', file_meta['path'])} "
                            f"(exists as: {dest_file_info['file_path']})"
                        )
                    else:
                        self.logger.info(
                            f"Skipped (duplicate on destination): {file_meta.get('relative_path', file_meta['path'])}"
                        )
                    files_duplicated.append(file_meta)
                    files_to_copy.remove(file_meta)
                    self.duplicates_skipped += 1
            
            if files_duplicated:
                self.logger.info(f"Found {len(files_duplicated)} duplicates on destination, skipping copy")
        
        total_to_process = len(files_to_copy)
        
        # Copy files
        for idx, file_meta in enumerate(files_to_copy):
            try:
                source_path = Path(file_meta['path'])
                relative_path = file_meta.get('relative_path', source_path.name)
                dest_path = dest_dir / relative_path
                
                # Create destination directory if needed
                if not dry_run:
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                if dry_run:
                    self.logger.info(f"[DRY RUN] Would copy: {relative_path}")
                else:
                    # Handle platform-specific copying
                    try:
                        # Use copy2 to preserve metadata (timestamps, permissions)
                        shutil.copy2(source_path, dest_path)
                        
                        # On Unix systems, ensure file is readable
                        if not IS_WINDOWS:
                            try:
                                os.chmod(dest_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
                            except (OSError, PermissionError):
                                pass  # Non-critical if we can't set permissions
                        
                        self.logger.info(f"Copied: {relative_path}")
                    except PermissionError as e:
                        error_msg = f"Permission denied copying {relative_path}: {str(e)}"
                        self.logger.error(error_msg)
                        errors.append(error_msg)
                        if self.progress_callback:
                            self.progress_callback(idx + 1, total_to_process or 1)
                        continue
                    except OSError as e:
                        # Handle Windows long path issues
                        if IS_WINDOWS and "path too long" in str(e).lower():
                            error_msg = f"Path too long (Windows limitation): {relative_path}"
                            self.logger.error(error_msg)
                            errors.append(error_msg)
                            if self.progress_callback:
                                self.progress_callback(idx + 1, total_to_process or 1)
                            continue
                        raise
                
                # Update database
                if not dry_run:
                    # Update source file metadata
                    self.db_manager.upsert_file_metadata(
                        file_path=str(source_path),
                        file_hash=file_meta['hash'],
                        modified_time=file_meta['modified_time'],
                        file_size=file_meta['size']
                    )
                    
                    # Record file in destination catalog
                    if file_meta.get('hash'):
                        self.db_manager.upsert_destination_file(
                            dest_root=dest_root,
                            file_hash=file_meta['hash'],
                            file_path=str(relative_path),
                            file_size=file_meta['size']
                        )
                
                self.files_copied += 1
                self.total_size += file_meta['size']
                
                if self.progress_callback:
                    self.progress_callback(idx + 1, total_to_process)
            
            except Exception as e:
                error_msg = f"Error copying {file_meta.get('relative_path', file_meta['path'])}: {str(e)}"
                self.logger.error(error_msg)
                errors.append(error_msg)
        
        # Log skipped files
        for file_meta in files_to_skip:
            self.logger.info(f"Skipped (unchanged): {file_meta.get('relative_path', file_meta['path'])}")
            self.files_skipped += 1
        
        return {
            'files_copied': self.files_copied,
            'files_skipped': self.files_skipped,
            'files_duplicated': len(files_duplicated),
            'total_size': self.total_size,
            'errors': errors
        }
    
    def reset_stats(self):
        """Reset copy statistics."""
        self.files_copied = 0
        self.files_skipped = 0
        self.duplicates_skipped = 0
        self.total_size = 0



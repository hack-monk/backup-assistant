"""Scans destination drives to build a hash catalog for deduplication."""

import time
from pathlib import Path
from typing import Optional, Callable, Set

from backup_engine.scanner import FileScanner
from db.db_manager import DBManager
from utils.logger import BackupLogger


class DestinationScanner:
    """Scans destination drives and indexes files by hash for deduplication."""
    
    def __init__(self, db_manager: DBManager, logger: BackupLogger,
                 progress_callback: Optional[Callable] = None):
        """
        Initialize destination scanner.
        
        Args:
            db_manager: Database manager instance
            logger: Logger instance
            progress_callback: Optional callback function(current, total, message)
        """
        self.db_manager = db_manager
        self.logger = logger
        self.progress_callback = progress_callback
        self.scanner = FileScanner()
    
    def scan_destination(self, dest_root: str, force_rescan: bool = False, 
                       scan_entire_drive: bool = False) -> dict:
        """
        Scan destination drive and index all files by hash.
        
        Args:
            dest_root: Root path of destination drive/folder
            force_rescan: If True, rescan even if recently scanned
            scan_entire_drive: If True, scan the entire drive root instead of just the folder
        
        Returns:
            Dict with scan results: files_found, hashes_indexed, duration
        """
        dest_root = str(Path(dest_root).resolve())
        
        # If scan_entire_drive is True, find the drive root
        if scan_entire_drive:
            drive_root = self._get_drive_root(dest_root)
            if drive_root and drive_root != dest_root:
                self.logger.info(
                    f"Scanning entire drive: {drive_root} "
                    f"(destination folder: {dest_root})"
                )
                dest_root = drive_root
        start_time = time.time()
        
        # Check if we have recent scan data
        if not force_rescan:
            scan_info = self.db_manager.get_destination_scan_info(dest_root)
            if scan_info:
                self.logger.info(
                    f"Destination was last scanned {self._format_time_ago(scan_info['last_scan_time'])} "
                    f"({scan_info['files_count']} files). Use force_rescan=True to rescan."
                )
                return {
                    'files_found': scan_info['files_count'],
                    'hashes_indexed': scan_info['files_count'],
                    'duration': scan_info['scan_duration'],
                    'cached': True
                }
        
        self.logger.info(f"Scanning destination drive: {dest_root}")
        
        # Clear old destination files for this root
        self.db_manager.clear_destination_files(dest_root)
        
        # Scan destination folder
        def progress_cb(current, total):
            if self.progress_callback:
                self.progress_callback(current, total, f"Scanning destination: {current}/{total} files")
        
        self.scanner.progress_callback = progress_cb
        file_list = self.scanner.scan_folder(dest_root, calculate_hash=True)
        
        # Index files by hash
        hashes_indexed = set()
        files_indexed = 0
        
        for file_meta in file_list:
            file_hash = file_meta['hash']
            if file_hash:
                # Store relative path from destination root
                try:
                    relative_path = file_meta.get('relative_path', file_meta['path'])
                except KeyError:
                    relative_path = Path(file_meta['path']).name
                
                # Record in database
                self.db_manager.upsert_destination_file(
                    dest_root=dest_root,
                    file_hash=file_hash,
                    file_path=str(relative_path),
                    file_size=file_meta['size']
                )
                
                hashes_indexed.add(file_hash)
                files_indexed += 1
        
        duration = time.time() - start_time
        
        # Record scan completion
        self.db_manager.update_destination_scan(dest_root, files_indexed, duration)
        
        self.logger.info(
            f"Destination scan complete: {files_indexed} files indexed, "
            f"{len(hashes_indexed)} unique hashes, {duration:.2f}s"
        )
        
        return {
            'files_found': files_indexed,
            'hashes_indexed': len(hashes_indexed),
            'duration': duration,
            'cached': False
        }
    
    def get_destination_hashes(self, dest_root: str) -> Set[str]:
        """
        Get set of all file hashes that exist on the destination.
        This is a faster alternative to checking individual hashes.
        
        Args:
            dest_root: Root path of destination drive/folder
        
        Returns:
            Set of file hashes (SHA256 strings)
        """
        # For now, we'll query on-demand. For very large destinations,
        # we could cache this in memory, but that could use a lot of RAM.
        # Instead, we'll use the database index for fast lookups.
        return set()  # Return empty set - we'll use DB queries instead
    
    def _get_drive_root(self, path: str) -> Optional[str]:
        """
        Get the root of the drive/volume containing the given path.
        
        Args:
            path: Any path on the drive
        
        Returns:
            Root path of the drive, or None if cannot determine
        """
        path_obj = Path(path).resolve()
        
        # On Windows, drive root is like C:\
        import sys
        if sys.platform.startswith('win'):
            # Get the drive letter
            drive = path_obj.drive
            if drive:
                return str(Path(drive) / Path('/'))
        
        # On macOS/Linux, find the mount point
        # Walk up the path until we find a mount point
        current = path_obj
        while current != current.parent:
            try:
                # Check if this is a mount point by comparing with parent's device
                if current.is_mount():
                    return str(current)
                current = current.parent
            except (OSError, PermissionError):
                break
        
        # Fallback: return the original path if we can't find mount point
        return str(path_obj)
    
    def _format_time_ago(self, timestamp: float) -> str:
        """Format timestamp as human-readable time ago."""
        import time
        seconds_ago = time.time() - timestamp
        
        if seconds_ago < 60:
            return f"{int(seconds_ago)} seconds ago"
        elif seconds_ago < 3600:
            return f"{int(seconds_ago / 60)} minutes ago"
        elif seconds_ago < 86400:
            return f"{int(seconds_ago / 3600)} hours ago"
        else:
            return f"{int(seconds_ago / 86400)} days ago"


"""SQLite database interface for tracking backup metadata."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List

from utils.config import DB_PATH


class DBManager:
    """Manages SQLite database for backup metadata."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file (defaults to config DB_PATH)
        """
        self.db_path = db_path or DB_PATH
        self.connection: Optional[sqlite3.Connection] = None
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Ensure database file and directory exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_tables()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self.connection is None:
            # Use check_same_thread=False to allow connections from different threads
            # Each thread should create its own DBManager instance
            self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
        return self.connection
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Main file metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                file_hash TEXT NOT NULL,
                modified_time REAL NOT NULL,
                file_size INTEGER NOT NULL,
                last_backed_up REAL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        
        # Backup sessions table (optional, for tracking backup history)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backup_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_start REAL NOT NULL,
                session_end REAL,
                source_path TEXT NOT NULL,
                dest_path TEXT NOT NULL,
                files_copied INTEGER DEFAULT 0,
                files_skipped INTEGER DEFAULT 0,
                files_duplicated INTEGER DEFAULT 0,
                total_size INTEGER DEFAULT 0,
                status TEXT DEFAULT 'completed'
            )
        """)
        
        # Destination files table - tracks files by hash on destination drives
        # This enables deduplication across different source folders
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS destination_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dest_root TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                last_seen REAL NOT NULL,
                created_at REAL NOT NULL,
                UNIQUE(dest_root, file_hash, file_path)
            )
        """)
        
        # Destination scan history - tracks when destinations were last scanned
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS destination_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dest_root TEXT NOT NULL UNIQUE,
                last_scan_time REAL NOT NULL,
                files_count INTEGER DEFAULT 0,
                scan_duration REAL DEFAULT 0
            )
        """)
        
        # Create indexes for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_path ON file_metadata(file_path)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dest_hash ON destination_files(file_hash)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dest_root ON destination_files(dest_root)
        """)
        
        conn.commit()
    
    def upsert_file_metadata(self, file_path: str, file_hash: str, 
                            modified_time: float, file_size: int):
        """
        Insert or update file metadata.
        
        Args:
            file_path: Absolute path to the file
            file_hash: SHA256 hash of the file
            modified_time: File modification timestamp
            file_size: File size in bytes
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        
        cursor.execute("""
            INSERT INTO file_metadata 
            (file_path, file_hash, modified_time, file_size, last_backed_up, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                file_hash = excluded.file_hash,
                modified_time = excluded.modified_time,
                file_size = excluded.file_size,
                last_backed_up = excluded.last_backed_up,
                updated_at = excluded.updated_at
        """, (file_path, file_hash, modified_time, file_size, now, now, now))
        
        conn.commit()
    
    def get_metadata_for_path(self, file_path: str) -> Optional[Dict]:
        """
        Get metadata for a specific file path.
        
        Args:
            file_path: Absolute path to the file
        
        Returns:
            Dict with metadata or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT file_path, file_hash, modified_time, file_size, last_backed_up
            FROM file_metadata
            WHERE file_path = ?
        """, (file_path,))
        
        row = cursor.fetchone()
        if row:
            return {
                'file_path': row['file_path'],
                'file_hash': row['file_hash'],
                'modified_time': row['modified_time'],
                'file_size': row['file_size'],
                'last_backed_up': row['last_backed_up']
            }
        return None
    
    def get_all_metadata(self) -> List[Dict]:
        """Get all file metadata records."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT file_path, file_hash, modified_time, file_size, last_backed_up
            FROM file_metadata
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def delete_metadata(self, file_path: str):
        """Delete metadata for a file path."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM file_metadata WHERE file_path = ?", (file_path,))
        conn.commit()
    
    def create_backup_session(self, source_path: str, dest_path: str) -> int:
        """
        Create a new backup session record.
        
        Args:
            source_path: Source directory path
            dest_path: Destination directory path
        
        Returns:
            Session ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        
        cursor.execute("""
            INSERT INTO backup_sessions 
            (session_start, source_path, dest_path, status)
            VALUES (?, ?, ?, 'in_progress')
        """, (now, source_path, dest_path))
        
        conn.commit()
        return cursor.lastrowid
    
    def update_backup_session(self, session_id: int, files_copied: int = 0,
                             files_skipped: int = 0, files_duplicated: int = 0,
                             total_size: int = 0, status: str = 'completed'):
        """Update backup session with results."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        
        cursor.execute("""
            UPDATE backup_sessions
            SET session_end = ?, files_copied = ?, files_skipped = ?,
                files_duplicated = ?, total_size = ?, status = ?
            WHERE id = ?
        """, (now, files_copied, files_skipped, files_duplicated, total_size, status, session_id))
        
        conn.commit()
    
    def upsert_destination_file(self, dest_root: str, file_hash: str, 
                               file_path: str, file_size: int):
        """
        Record a file that exists on the destination drive.
        
        Args:
            dest_root: Root path of destination drive/folder
            file_hash: SHA256 hash of the file
            file_path: Relative or absolute path to file on destination
            file_size: File size in bytes
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        
        cursor.execute("""
            INSERT INTO destination_files 
            (dest_root, file_hash, file_path, file_size, last_seen, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(dest_root, file_hash, file_path) DO UPDATE SET
                last_seen = excluded.last_seen,
                file_size = excluded.file_size
        """, (dest_root, file_hash, file_path, file_size, now, now))
        
        conn.commit()
    
    def get_destination_hash_exists(self, dest_root: str, file_hash: str) -> bool:
        """
        Check if a file with this hash already exists on the destination.
        
        Args:
            dest_root: Root path of destination drive/folder
            file_hash: SHA256 hash to check
        
        Returns:
            True if a file with this hash exists on destination
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM destination_files
            WHERE dest_root = ? AND file_hash = ?
        """, (dest_root, file_hash))
        
        row = cursor.fetchone()
        return row['count'] > 0 if row else False
    
    def get_destination_file_by_hash(self, dest_root: str, file_hash: str) -> Optional[Dict]:
        """
        Get destination file info by hash.
        
        Args:
            dest_root: Root path of destination drive/folder
            file_hash: SHA256 hash to look up
        
        Returns:
            Dict with file info or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT file_path, file_size, last_seen
            FROM destination_files
            WHERE dest_root = ? AND file_hash = ?
            LIMIT 1
        """, (dest_root, file_hash))
        
        row = cursor.fetchone()
        if row:
            return {
                'file_path': row['file_path'],
                'file_size': row['file_size'],
                'last_seen': row['last_seen']
            }
        return None
    
    def clear_destination_files(self, dest_root: str):
        """
        Clear all destination file records for a specific destination root.
        Use this before a fresh scan.
        
        Args:
            dest_root: Root path of destination drive/folder
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM destination_files WHERE dest_root = ?", (dest_root,))
        conn.commit()
    
    def update_destination_scan(self, dest_root: str, files_count: int, scan_duration: float):
        """
        Record that a destination was scanned.
        
        Args:
            dest_root: Root path of destination drive/folder
            files_count: Number of files found
            scan_duration: Time taken to scan in seconds
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        
        cursor.execute("""
            INSERT INTO destination_scans 
            (dest_root, last_scan_time, files_count, scan_duration)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(dest_root) DO UPDATE SET
                last_scan_time = excluded.last_scan_time,
                files_count = excluded.files_count,
                scan_duration = excluded.scan_duration
        """, (dest_root, now, files_count, scan_duration))
        
        conn.commit()
    
    def get_destination_scan_info(self, dest_root: str) -> Optional[Dict]:
        """
        Get last scan information for a destination.
        
        Args:
            dest_root: Root path of destination drive/folder
        
        Returns:
            Dict with scan info or None if never scanned
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT last_scan_time, files_count, scan_duration
            FROM destination_scans
            WHERE dest_root = ?
        """, (dest_root,))
        
        row = cursor.fetchone()
        if row:
            return {
                'last_scan_time': row['last_scan_time'],
                'files_count': row['files_count'],
                'scan_duration': row['scan_duration']
            }
        return None
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()



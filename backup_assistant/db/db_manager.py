"""SQLite database interface for tracking backup metadata."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List

from ..utils.config import DB_PATH


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
                total_size INTEGER DEFAULT 0,
                status TEXT DEFAULT 'completed'
            )
        """)
        
        # Create index on file_path for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_path ON file_metadata(file_path)
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
                             files_skipped: int = 0, total_size: int = 0,
                             status: str = 'completed'):
        """Update backup session with results."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        
        cursor.execute("""
            UPDATE backup_sessions
            SET session_end = ?, files_copied = ?, files_skipped = ?,
                total_size = ?, status = ?
            WHERE id = ?
        """, (now, files_copied, files_skipped, total_size, status, session_id))
        
        conn.commit()
    
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



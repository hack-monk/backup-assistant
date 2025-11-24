"""Logging backup sessions and errors."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from utils import config


class BackupLogger:
    """Logger for backup operations with console, GUI, and file output."""
    
    def __init__(self, log_to_file: bool = False, log_file: Optional[Path] = None):
        """
        Initialize the backup logger.
        
        Args:
            log_to_file: Whether to write logs to a file
            log_file: Path to log file (if None, auto-generates based on timestamp)
        """
        self.log_entries: List[str] = []
        self.log_to_file = log_to_file
        self.log_file = log_file or (config.LOG_DIR / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        # Setup Python logging
        self.logger = logging.getLogger('BackupAssistant')
        self.logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Log platform info on initialization
        self.info(f"Backup Assistant initialized on {config.PLATFORM_NAME} {config.PLATFORM_VERSION}")
        
        # File handler (if enabled)
        if self.log_to_file:
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def info(self, message: str):
        """Log an info message."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] INFO: {message}"
        self.log_entries.append(log_entry)
        self.logger.info(message)
    
    def warning(self, message: str):
        """Log a warning message."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] WARNING: {message}"
        self.log_entries.append(log_entry)
        self.logger.warning(message)
    
    def error(self, message: str):
        """Log an error message."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] ERROR: {message}"
        self.log_entries.append(log_entry)
        self.logger.error(message)
    
    def get_logs(self) -> List[str]:
        """Get all log entries for GUI display."""
        return self.log_entries.copy()
    
    def clear_logs(self):
        """Clear all log entries."""
        self.log_entries.clear()
    
    def get_log_text(self) -> str:
        """Get all logs as a single string for display."""
        return '\n'.join(self.log_entries)



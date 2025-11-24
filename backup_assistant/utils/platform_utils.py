"""Platform-specific utilities for cross-platform compatibility."""

import sys
import os
import platform
from pathlib import Path
from typing import Optional

from .config import IS_WINDOWS, IS_MACOS, IS_LINUX


def normalize_path(path: str) -> Path:
    """
    Normalize a path for cross-platform compatibility.
    
    Args:
        path: Path string to normalize
    
    Returns:
        Normalized Path object
    """
    return Path(path).expanduser().resolve()


def get_user_data_dir() -> Path:
    """
    Get platform-specific user data directory.
    
    Returns:
        Path to user data directory
    """
    if IS_WINDOWS:
        appdata = os.environ.get('LOCALAPPDATA')
        if appdata:
            return Path(appdata) / "BackupAssistant"
        return Path.home() / "AppData" / "Local" / "BackupAssistant"
    elif IS_MACOS:
        return Path.home() / "Library" / "Application Support" / "BackupAssistant"
    elif IS_LINUX:
        xdg_data = os.environ.get('XDG_DATA_HOME')
        if xdg_data:
            return Path(xdg_data) / "backup-assistant"
        return Path.home() / ".local" / "share" / "backup-assistant"
    else:
        # Fallback for other Unix systems
        return Path.home() / ".backup-assistant"


def is_hidden_file(file_path: Path) -> bool:
    """
    Check if a file is hidden (platform-aware).
    
    Args:
        file_path: Path to check
    
    Returns:
        True if file is hidden
    """
    if IS_WINDOWS:
        # On Windows, check file attributes (optional win32api, fallback to name check)
        try:
            import win32api
            import win32con
            if file_path.exists():
                attrs = win32api.GetFileAttributes(str(file_path))
                return bool(attrs & win32con.FILE_ATTRIBUTE_HIDDEN)
        except (ImportError, AttributeError, OSError):
            # Fallback: check if name starts with dot
            pass
        return file_path.name.startswith('.')
    else:
        # Unix/macOS/Linux: files starting with . are hidden
        return file_path.name.startswith('.')


def get_long_path_support() -> bool:
    """
    Check if long path support is available (Windows).
    
    Returns:
        True if long paths are supported
    """
    if not IS_WINDOWS:
        return True  # Not an issue on Unix systems
    
    # Check Windows version and long path support
    # Windows 10 version 1607+ supports long paths if enabled
    try:
        version = platform.version()
        # This is a simplified check - actual implementation would need registry check
        return True  # Assume enabled, handle errors at runtime
    except Exception:
        return False


def format_path_for_display(path: Path, max_length: int = 60) -> str:
    """
    Format a path for display, truncating if too long.
    
    Args:
        path: Path to format
        max_length: Maximum display length
    
    Returns:
        Formatted path string
    """
    path_str = str(path)
    if len(path_str) <= max_length:
        return path_str
    
    # Truncate from the middle
    if max_length < 20:
        return "..." + path_str[-(max_length - 3):]
    
    half = (max_length - 3) // 2
    return path_str[:half] + "..." + path_str[-half:]


def get_platform_info() -> dict:
    """
    Get detailed platform information.
    
    Returns:
        Dictionary with platform information
    """
    return {
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'python_version': sys.version,
        'is_windows': IS_WINDOWS,
        'is_macos': IS_MACOS,
        'is_linux': IS_LINUX,
    }


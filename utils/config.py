"""Global settings, constants, and paths configuration."""

import os
import sys
import platform
from pathlib import Path

# Platform detection
IS_WINDOWS = sys.platform.startswith('win')
IS_MACOS = sys.platform == 'darwin'
IS_LINUX = sys.platform.startswith('linux')
IS_UNIX = IS_MACOS or IS_LINUX or sys.platform.startswith('unix')

# Base directory for the application (now at root level)
BASE_DIR = Path(__file__).parent.parent

# Data directory for storing database and logs
# Use platform-appropriate location
if IS_WINDOWS:
    # Windows: Use AppData\Local if available, otherwise project directory
    appdata = os.environ.get('LOCALAPPDATA')
    if appdata:
        DATA_DIR = Path(appdata) / "BackupAssistant" / "data"
    else:
        DATA_DIR = BASE_DIR / "data"
elif IS_MACOS:
    # macOS: Use ~/Library/Application Support
    home = Path.home()
    DATA_DIR = home / "Library" / "Application Support" / "BackupAssistant" / "data"
elif IS_LINUX:
    # Linux: Use ~/.local/share
    home = Path.home()
    DATA_DIR = home / ".local" / "share" / "backup-assistant" / "data"
else:
    # Fallback to project directory
    DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database file path
DB_PATH = DATA_DIR / "backup_metadata.db"

# Log file path (optional, for file-based logging)
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Default backup settings
DEFAULT_BACKUP_INTERVAL = 3600  # 1 hour in seconds
MAX_LOG_ENTRIES = 1000

# File size limits (in bytes)
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB default max
MIN_FILE_SIZE = 0  # No minimum

# Platform-specific exclude patterns
_WINDOWS_EXCLUDE = ['Thumbs.db', 'desktop.ini', '$RECYCLE.BIN', 'System Volume Information']
_MACOS_EXCLUDE = ['.DS_Store', '.AppleDouble', '.LSOverride', '.DocumentRevisions-V100',
                  '.fseventsd', '.Spotlight-V100', '.TemporaryItems', '.Trashes', '.VolumeIcon.icns']
_LINUX_EXCLUDE = ['.directory', '.Trash', '.thumbnails']
_COMMON_EXCLUDE = ['*.tmp', '*.swp', '*.bak', '*.cache', '*.log', '~$*']

# Combine platform-specific excludes
if IS_WINDOWS:
    EXCLUDE_PATTERNS = _WINDOWS_EXCLUDE + _COMMON_EXCLUDE
elif IS_MACOS:
    EXCLUDE_PATTERNS = _MACOS_EXCLUDE + _COMMON_EXCLUDE
elif IS_LINUX:
    EXCLUDE_PATTERNS = _LINUX_EXCLUDE + _COMMON_EXCLUDE
else:
    # Generic Unix/other platforms
    EXCLUDE_PATTERNS = _COMMON_EXCLUDE

# Supported file patterns (None means all files)
INCLUDE_PATTERNS = None  # Can be set to ['*.txt', '*.doc', etc.]

# Platform information for logging
PLATFORM_NAME = platform.system()
PLATFORM_VERSION = platform.version()



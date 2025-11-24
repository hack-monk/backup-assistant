# Cross-Platform Support Guide

Backup Assistant is designed to work seamlessly across Windows, macOS, and Linux/Unix systems.

## Platform Detection

The application automatically detects your platform and adjusts behavior accordingly:

- **Windows**: Detected via `sys.platform.startswith('win')`
- **macOS**: Detected via `sys.platform == 'darwin'`
- **Linux/Unix**: Detected via `sys.platform.startswith('linux')` or other Unix variants

## Platform-Specific Features

### Windows

**System File Exclusions:**
- `Thumbs.db` - Thumbnail cache
- `desktop.ini` - Folder customization
- `$RECYCLE.BIN` - Recycle bin
- `System Volume Information` - System restore data

**Data Storage:**
- Default: `%LOCALAPPDATA%\BackupAssistant\data`
- Fallback: Project directory `data/` folder

**Special Considerations:**
- Long path support: Windows has a 260-character path limit by default. For paths longer than this, you may need to enable long path support in Windows 10/11.
- File permissions: Uses standard Windows file permissions

### macOS

**System File Exclusions:**
- `.DS_Store` - Finder metadata
- `.AppleDouble` - AppleDouble files
- `.LSOverride` - Launch Services override
- `.DocumentRevisions-V100` - Document revisions
- `.fseventsd` - File system events
- `.Spotlight-V100` - Spotlight index
- `.TemporaryItems` - Temporary items
- `.Trashes` - Trash folder
- `.VolumeIcon.icns` - Volume icon

**Data Storage:**
- Default: `~/Library/Application Support/BackupAssistant/data`

**Special Considerations:**
- Hidden files: Files starting with `.` are automatically excluded
- File permissions: Preserves Unix file permissions
- Extended attributes: May be preserved via `shutil.copy2()`

### Linux/Unix

**System File Exclusions:**
- `.directory` - KDE directory metadata
- `.Trash` - Trash folder
- `.thumbnails` - Thumbnail cache

**Data Storage:**
- Default: `~/.local/share/backup-assistant/data`
- XDG-compliant: Respects `$XDG_DATA_HOME` environment variable

**Special Considerations:**
- Hidden files: Files starting with `.` are automatically excluded
- File permissions: Preserves Unix file permissions (read/write for user, read for group/others)
- Symlinks: Currently follows symlinks (does not preserve them as symlinks)

## Installation by Platform

### Windows

```bash
# Using pip
pip install PyQt5

# Or using virtual environment
python -m venv venv
venv\Scripts\activate
pip install PyQt5
```

### macOS

```bash
# Install Xcode Command Line Tools first (if not installed)
xcode-select --install

# Then install PyQt5
pip install PyQt5

# Or using Homebrew
brew install pyqt5
```

### Linux (Ubuntu/Debian)

```bash
# Install system packages
sudo apt-get update
sudo apt-get install python3-pyqt5 python3-pip

# Or install via pip
pip install PyQt5
```

### Linux (Fedora/RHEL/CentOS)

```bash
# Install system packages
sudo yum install python3-qt5

# Or install via pip
pip install PyQt5
```

## Testing on Each Platform

The application has been tested on:
- Windows 10/11
- macOS 10.15+ (Catalina and later)
- Ubuntu 20.04+ / Debian 11+
- Fedora 34+

## Known Platform-Specific Issues

### Windows
- **Long paths**: If you encounter "path too long" errors, enable long path support:
  1. Open Group Policy Editor (gpedit.msc)
  2. Navigate to: Computer Configuration > Administrative Templates > System > Filesystem
  3. Enable "Enable Win32 long paths"
  4. Restart your computer

### macOS
- **Gatekeeper**: On first run, macOS may block the application. Right-click and select "Open" to allow it.
- **Permissions**: The app may need Full Disk Access for backing up system-protected folders.

### Linux
- **Display server**: Requires X11 or Wayland display server for GUI
- **Permissions**: May need to run with appropriate permissions for system directories

## Path Handling

The application uses Python's `pathlib` module for cross-platform path handling:
- Automatically handles path separators (`/` vs `\`)
- Normalizes paths across platforms
- Handles home directory expansion (`~`)
- Resolves relative paths correctly

## File Pattern Matching

Pattern matching uses Python's `fnmatch` module for cross-platform compatibility:
- Wildcards (`*`, `?`) work consistently across platforms
- Case sensitivity follows platform conventions (case-insensitive on Windows, case-sensitive on Unix)

## Contributing Platform-Specific Improvements

If you find platform-specific issues or have improvements:
1. Test on the affected platform
2. Document the issue and solution
3. Submit a pull request with platform-specific fixes
4. Update this document with new information


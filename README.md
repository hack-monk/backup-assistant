# SmartSync - Backup Assistant

A cross-platform GUI-based Backup Assistant that helps users automatically copy only new or modified files to an external hard disk. It works like a Git-style deduplication and versioned backup tool. Works on **Windows, macOS, and Linux**.

## Features

- **Intelligent Deduplication**: Uses SHA256 hashing to detect file changes
- **Incremental Backups**: Only copies new or modified files
- **Destination Duplicate Detection**: Optionally scans the destination drive and skips files that already exist there
- **Metadata Tracking**: SQLite database tracks file history and modification times
- **User-Friendly GUI**: PyQt5-based interface with progress tracking
- **Session Logging**: Detailed logs of all backup operations
- **Thread-Safe**: Non-blocking backup operations using worker threads

## Requirements

- Python 3.7 or higher
- PyQt5 (cross-platform GUI framework)
- SQLite3 (included with Python)

### Platform-Specific Notes

- **Windows**: Works out of the box. May need to enable long path support for paths >260 characters.
- **macOS**: Requires Xcode Command Line Tools for PyQt5. Install with: `xcode-select --install`
- **Linux**: May need to install PyQt5 via package manager: `sudo apt-get install python3-pyqt5` (Ubuntu/Debian) or `sudo yum install python3-qt5` (Fedora/RHEL)

## Installation

1. Clone or download this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Running the Application

From the project root directory:

```bash
python app.py
```

Or use the launcher script:

```bash
./launch_gui.sh
```

Or if installed as a package:

```bash
backup-assistant
```

### Using the GUI

1. **Select Source Folder**: Click "Browse..." next to "Source Folder" and select the directory you want to backup
2. **Select Destination Folder**: Click "Browse..." next to "Destination Folder" and select where you want to store the backup (e.g., external hard disk)
3. **Start Backup**: Click "Start Backup" to begin the backup process
4. **(Optional) Deduplication**: Leave the "Skip files already on destination" checkbox enabled to scan the external drive before copying
5. **Monitor Progress**: Watch the progress bar and log window for real-time updates
6. **Review Results**: After completion, review the summary showing copied, skipped, and duplicate counts

### How It Works

1. **Scanning**: The application scans the source folder and calculates SHA256 hashes for all files
2. **Comparison**: Each file is compared against the database to check if it's new or modified
3. **Destination Dedup (optional)**: If enabled, the destination drive is scanned and duplicate hashes are skipped
4. **Copying**: Only new or modified (and non-duplicate) files are copied to the destination
5. **Tracking**: File metadata (hash, modification time, size) is stored in the database for future comparisons

## Project Structure

```
.
├── app.py                      # Main entry point
├── backup_engine/
│   ├── scanner.py             # File traversal and hashing
│   ├── copier.py              # Conditional file copying
│   └── snapshot.py            # Snapshot management
├── db/
│   └── db_manager.py          # SQLite database interface
├── gui/
│   └── main_window.py         # PyQt5 GUI
├── utils/
│   ├── hashing.py             # SHA256 hash generation
│   ├── logger.py              # Logging functionality
│   └── config.py              # Configuration settings
├── data/
│   └── backup_metadata.db     # SQLite database file
├── tests/
│   ├── test_hashing.py
│   ├── test_db_manager.py
│   └── test_backup_logic.py
├── requirements.txt           # Python dependencies
├── setup.py                   # Package setup
└── README.md                  # This file
```

## Configuration

Edit `utils/config.py` to customize:

- File size limits
- Include/exclude patterns
- Database and log paths
- Default backup settings

## Testing

Run the test suite:

```bash
pytest tests/
```

Or run specific test files:

```bash
pytest tests/test_hashing.py
pytest tests/test_db_manager.py
pytest tests/test_backup_logic.py
```

## Database Schema

The application uses SQLite to store file metadata:

- **file_metadata**: Stores file paths, hashes, modification times, and backup timestamps
- **backup_sessions**: Tracks backup session history

## Cross-Platform Support

This application is fully cross-platform and has been tested on:
- ✅ **Windows 10/11** - Full support with platform-specific exclusions (Thumbs.db, etc.)
- ✅ **macOS** - Full support with macOS-specific exclusions (.DS_Store, etc.)
- ✅ **Linux/Unix** - Full support with Linux-specific exclusions

### Platform-Specific Features

- **Automatic system file exclusion**: Skips platform-specific system files automatically
- **Platform-aware data storage**: Uses appropriate directories for each OS:
  - Windows: `%LOCALAPPDATA%\BackupAssistant\data`
  - macOS: `~/Library/Application Support/BackupAssistant/data`
  - Linux: `~/.local/share/backup-assistant/data`
- **Path normalization**: Handles path differences between platforms automatically

## Limitations

- Large files may take time to hash
- Network drives may have performance limitations
- Windows: Very long paths (>260 chars) may require long path support to be enabled
- Requires Python 3.7+ and PyQt5 (cross-platform)

## Future Enhancements

- Scheduled backups
- Snapshot restore functionality
- Compression support
- Cloud storage integration
- Email notifications
- Backup verification

## License

This project is provided as-is for educational and personal use.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Support

For issues or questions, please open an issue on the project repository.



# Backup Assistant - Architecture Document

## Overview

Backup Assistant is a GUI-based application that performs incremental backups by tracking file metadata (SHA256 hashes and modification times) in a SQLite database. It only copies files that are new or have been modified since the last backup, providing efficient deduplication similar to Git's approach.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                        │
│                    (PyQt5 MainWindow)                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backup Orchestration                      │
│                  (BackupWorker Thread)                      │
└───────┬───────────────────────────────┬─────────────────────┘
        │                               │
        ▼                               ▼
┌───────────────┐              ┌───────────────┐
│   Scanner     │              │    Copier     │
│  (File Scan)  │──────────────▶│ (Conditional │
│               │               │    Copy)     │
└───────┬───────┘               └───────┬───────┘
        │                               │
        ▼                               ▼
┌───────────────┐              ┌───────────────┐
│   Hashing     │              │  DB Manager   │
│  (SHA256)     │              │   (SQLite)    │
└───────────────┘              └───────┬───────┘
                                       │
                                       ▼
                              ┌───────────────┐
                              │   Database    │
                              │ (Metadata DB) │
                              └───────────────┘
```

## Component Breakdown

### 1. `app.py`
**Purpose**: Main entry point for launching the GUI application.

**Responsibilities**:
- Initialize PyQt5 QApplication
- Create and show MainWindow
- Handle application lifecycle

**Dependencies**: `gui.main_window`

---

### 2. `gui/main_window.py`
**Purpose**: PyQt5-based user interface for the application.

**Key Components**:
- **MainWindow**: Main application window class
- **BackupWorker**: QThread subclass for non-blocking backup operations

**UI Elements**:
- Source folder picker (QFileDialog)
- Destination folder picker (QFileDialog)
- Start Backup button
- Cancel button
- Progress bar (QProgressBar)
- Log display (QTextEdit)

**Responsibilities**:
- Display UI and handle user interactions
- Validate folder selections
- Launch backup operations in worker thread
- Display progress and logs
- Handle backup completion/cancellation

**Dependencies**: 
- `backup_engine.scanner`
- `backup_engine.copier`
- `db.db_manager`
- `utils.logger`

**Signals/Slots**:
- `progress_update(current, total)`: Updates progress bar
- `log_message(message)`: Appends to log display
- `finished(results)`: Handles backup completion

---

### 3. `backup_engine/scanner.py`
**Purpose**: File traversal, hashing, and metadata collection.

**Key Class**: `FileScanner`

**Methods**:
- `scan_folder(folder_path, calculate_hash=True)`: Recursively scans directory
- `get_file_metadata(file_path, calculate_hash=True)`: Gets metadata for single file
- `_should_include_file(file_path)`: Checks include/exclude patterns

**Responsibilities**:
- Walk through source directory recursively
- Calculate SHA256 hashes for files
- Collect file metadata (path, size, modification time, hash)
- Filter files based on include/exclude patterns
- Support progress callbacks for GUI updates

**Dependencies**: `utils.hashing`, `utils.config`

**Output**: List of dictionaries with file metadata:
```python
{
    'path': str,              # Absolute path
    'relative_path': str,     # Relative to source
    'modified_time': float,   # Unix timestamp
    'hash': str,             # SHA256 hash
    'size': int              # File size in bytes
}
```

---

### 4. `backup_engine/copier.py`
**Purpose**: Conditional file copying based on hash/timestamp comparison.

**Key Class**: `FileCopier`

**Methods**:
- `copy_files(file_list, source_dir, dest_dir, dry_run=False)`: Main copy operation
- `_should_copy_file(file_metadata)`: Determines if file needs copying
- `reset_stats()`: Resets copy statistics

**Responsibilities**:
- Compare file metadata with database records
- Determine which files are new or modified
- Copy files to destination preserving directory structure
- Update database after successful copies
- Log all operations (copied/skipped files)
- Support dry-run mode for testing

**Copy Logic**:
1. Query database for existing file metadata
2. If file not in DB → Copy (new file)
3. If hash changed → Copy (content modified)
4. If modification time changed → Copy (file modified)
5. Otherwise → Skip (unchanged)

**Dependencies**: 
- `db.db_manager`
- `utils.logger`

**Output**: Dictionary with statistics:
```python
{
    'files_copied': int,
    'files_skipped': int,
    'total_size': int,
    'errors': List[str]
}
```

---

### 5. `backup_engine/snapshot.py`
**Purpose**: Optional snapshot management and tagging (MVP placeholder).

**Key Class**: `SnapshotManager`

**Methods**:
- `create_snapshot(name, description)`: Create snapshot tag
- `list_snapshots()`: List all snapshots
- `restore_from_snapshot(snapshot_id, restore_path)`: Restore from snapshot

**Status**: Basic structure implemented, full functionality for future enhancement.

---

### 6. `db/db_manager.py`
**Purpose**: SQLite database interface for tracking backup metadata.

**Key Class**: `DBManager`

**Database Schema**:

**file_metadata table**:
- `id`: Primary key
- `file_path`: TEXT, UNIQUE (absolute file path)
- `file_hash`: TEXT (SHA256 hash)
- `modified_time`: REAL (Unix timestamp)
- `file_size`: INTEGER (bytes)
- `last_backed_up`: REAL (timestamp of last backup)
- `created_at`: REAL (record creation time)
- `updated_at`: REAL (last update time)

**backup_sessions table**:
- `id`: Primary key
- `session_start`: REAL (backup start time)
- `session_end`: REAL (backup end time)
- `source_path`: TEXT
- `dest_path`: TEXT
- `files_copied`: INTEGER
- `files_skipped`: INTEGER
- `total_size`: INTEGER
- `status`: TEXT ('in_progress', 'completed', 'cancelled')

**Key Methods**:
- `upsert_file_metadata(...)`: Insert or update file record
- `get_metadata_for_path(file_path)`: Retrieve file metadata
- `get_all_metadata()`: Get all file records
- `delete_metadata(file_path)`: Remove file record
- `create_backup_session(...)`: Create session record
- `update_backup_session(...)`: Update session with results

**Responsibilities**:
- Initialize database and create tables
- Provide CRUD operations for file metadata
- Track backup sessions
- Handle database connections (context manager support)

**Dependencies**: `utils.config` (for DB path)

---

### 7. `utils/hashing.py`
**Purpose**: SHA256 hash generation for file deduplication.

**Functions**:
- `hash_file(file_path, chunk_size=8192)`: Hash a file
- `hash_string(data)`: Hash a string

**Implementation**:
- Reads file in chunks for memory efficiency
- Uses Python's `hashlib.sha256()`
- Returns hexadecimal hash string (64 characters)

**Error Handling**:
- Raises `FileNotFoundError` for missing files
- Raises `ValueError` for directories
- Raises `IOError` for read errors

---

### 8. `utils/logger.py`
**Purpose**: Logging backup sessions and errors.

**Key Class**: `BackupLogger`

**Features**:
- Console logging (stdout)
- Optional file-based logging
- GUI log display support
- Timestamped log entries
- Multiple log levels (info, warning, error)

**Methods**:
- `info(message)`: Log info message
- `warning(message)`: Log warning
- `error(message)`: Log error
- `get_logs()`: Get all log entries
- `get_log_text()`: Get logs as string
- `clear_logs()`: Clear log buffer

**Output Format**:
```
[YYYY-MM-DD HH:MM:SS] LEVEL: message
```

---

### 9. `utils/config.py`
**Purpose**: Global settings, constants, and paths.

**Configuration Variables**:
- `BASE_DIR`: Application base directory
- `DATA_DIR`: Data storage directory
- `DB_PATH`: Database file path
- `LOG_DIR`: Log file directory
- `DEFAULT_BACKUP_INTERVAL`: Default backup interval (seconds)
- `MAX_FILE_SIZE`: Maximum file size to backup
- `MIN_FILE_SIZE`: Minimum file size
- `INCLUDE_PATTERNS`: File patterns to include (None = all)
- `EXCLUDE_PATTERNS`: File patterns to exclude

**Usage**: Imported by other modules for configuration access.

---

## Data Flow

### Backup Operation Flow

1. **User Action**: User clicks "Start Backup" in GUI
2. **Validation**: MainWindow validates source/dest paths
3. **Worker Thread**: BackupWorker thread is created and started
4. **Scanning Phase**:
   - FileScanner.scan_folder() walks source directory
   - For each file: calculate hash, get metadata
   - Progress updates sent to GUI via signals
5. **Comparison Phase**:
   - FileCopier compares each file with DB records
   - Determines which files need copying
6. **Copying Phase**:
   - For each file to copy:
     - Create destination directory structure
     - Copy file using shutil.copy2()
     - Update database with new metadata
     - Log operation
   - Progress updates sent to GUI
7. **Completion**:
   - Create backup session record
   - Update session with statistics
   - Emit finished signal with results
   - GUI displays summary

### Database Query Flow

```
FileScanner → File Metadata
     ↓
FileCopier._should_copy_file()
     ↓
DBManager.get_metadata_for_path()
     ↓
SQLite Query
     ↓
Return metadata or None
     ↓
FileCopier decides: copy or skip
```

## Threading Model

- **Main Thread**: GUI event loop (PyQt5)
- **Worker Thread**: BackupWorker (QThread) for backup operations
- **Communication**: PyQt5 signals/slots for thread-safe GUI updates

**Benefits**:
- Non-blocking UI during backup
- Responsive user interface
- Safe cancellation support

## Error Handling

- **File Access Errors**: Skipped with warning logged
- **Database Errors**: Logged, operation continues
- **Copy Errors**: Logged, added to errors list
- **User Cancellation**: Graceful shutdown, session marked as cancelled

## Performance Considerations

- **Hashing**: Large files read in chunks (8KB default)
- **Database**: Indexed on file_path for fast lookups
- **Progress Updates**: Throttled to avoid GUI lag
- **Memory**: File list kept in memory (consider streaming for very large backups)

## Security Considerations

- File paths stored as absolute paths
- No encryption of database (consider for sensitive data)
- No network operations (local files only)

## Testing Strategy

- **Unit Tests**: Individual components (hashing, DB, scanner, copier)
- **Integration Tests**: Full backup workflow with test directories
- **GUI Tests**: Use pytest-qt for PyQt5 testing

## Future Enhancements

1. **Snapshot System**: Full implementation of snapshot management
2. **Scheduling**: Automatic scheduled backups
3. **Compression**: Optional file compression
4. **Verification**: Post-backup file verification
5. **Restore**: Restore functionality from backups
6. **Cloud Integration**: Support for cloud storage backends
7. **Encryption**: Optional database and file encryption

## Dependencies

- **PyQt5**: GUI framework
- **SQLite3**: Database (standard library)
- **hashlib**: Hashing (standard library)
- **pathlib**: Path handling (standard library)
- **pytest**: Testing framework

## Deployment

For Windows deployment:
1. Use PyInstaller to create executable
2. Bundle with required DLLs
3. Include database initialization
4. Create installer (optional)

Example PyInstaller command:
```bash
pyinstaller --onefile --windowed --name BackupAssistant backup_assistant/app.py
```



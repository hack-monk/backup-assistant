# Backup Assistant - System Architecture Diagram

## High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                            │
│                    (PyQt5 MainWindow)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐     │
│  │ Source Picker│  │ Dest Picker  │  │  Start Backup    │     │
│  └──────────────┘  └──────────────┘  └──────────────────┘     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Progress Bar & Status                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Backup Log Display                          │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKUP WORKER THREAD                         │
│                  (QThread - Non-blocking)                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   SCANNER     │  │ DESTINATION   │  │    COPIER     │
│               │  │   SCANNER     │  │               │
│ - File walk   │  │ - Drive scan  │  │ - Compare     │
│ - Hash calc   │  │ - Hash index  │  │ - Copy files  │
│ - Metadata    │  │ - Catalog     │  │ - Update DB   │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      UTILITY MODULES                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐     │
│  │   Hashing    │  │   Logger     │  │    Config        │     │
│  │  (SHA256)    │  │  (Console/  │  │  (Settings)      │     │
│  │              │  │   GUI/File) │  │                  │     │
│  └──────────────┘  └──────────────┘  └──────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATABASE MANAGER                              │
│                    (SQLite Interface)                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  file_metadata: Source file tracking                      │   │
│  │  - file_path, file_hash, modified_time, file_size        │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  destination_files: Destination catalog                  │   │
│  │  - dest_root, file_hash, file_path, file_size           │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  backup_sessions: Backup history                         │   │
│  │  - session info, files_copied, files_skipped, etc.      │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  destination_scans: Scan history                         │   │
│  │  - last_scan_time, files_count, scan_duration           │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  SQLite DB    │
                    │  (Local File) │
                    └───────────────┘
```

## Detailed Component Interaction Flow

### Backup Process Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER ACTION                              │
│              "Start Backup" Button Click                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BackupWorker Thread                          │
│                    (Created in GUI Thread)                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  1. Create DB Connection (Thread)     │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  2. Scan Source Folder                │
        │     - FileScanner.scan_folder()       │
        │     - Calculate SHA256 hashes         │
        │     - Collect metadata                │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  3. Scan Destination Drive            │
        │     - DestinationScanner              │
        │     - Index all files by hash          │
        │     - Build catalog                    │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  4. Compare & Filter Files            │
        │     - Check source changes (DB)       │
        │     - Check destination duplicates     │
        │     - Determine files to copy          │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  5. Copy Files                         │
        │     - FileCopier.copy_files()         │
        │     - shutil.copy2()                   │
        │     - Update database                  │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  6. Record Session                     │
        │     - Create backup_sessions entry     │
        │     - Update statistics                │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  7. Emit Results Signal               │
        │     - finished.emit(results)          │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  8. GUI Updates                        │
        │     - Show summary dialog             │
        │     - Update log display              │
        │     - Re-enable controls              │
        └───────────────────────────────────────┘
```

## Data Flow Diagram

```
SOURCE FILES                    DESTINATION DRIVE
    │                                │
    │                                │
    ▼                                ▼
┌─────────┐                    ┌─────────────┐
│ File 1  │                    │ Existing    │
│ File 2  │                    │ File A      │
│ File 3  │                    │ File B      │
│ ...     │                    │ ...         │
└────┬────┘                    └──────┬──────┘
     │                                 │
     │  Scan & Hash                    │  Scan & Index
     │                                 │
     ▼                                 ▼
┌─────────────────┐          ┌──────────────────┐
│ Source Metadata │          │ Destination       │
│ - Hash: abc123  │          │ Catalog           │
│ - Hash: def456  │          │ - Hash: abc123 ✓  │
│ - Hash: ghi789  │          │ - Hash: xyz999 ✓  │
└────────┬────────┘          └─────────┬─────────┘
         │                             │
         └──────────┬──────────────────┘
                    │
                    ▼
         ┌──────────────────┐
         │  COMPARISON       │
         │                   │
         │  File 1: abc123   │───► Exists on dest → SKIP
         │  File 2: def456   │───► New → COPY
         │  File 3: ghi789   │───► New → COPY
         └──────────────────┘
                    │
                    ▼
         ┌──────────────────┐
         │  COPY OPERATION  │
         │  - File 2        │
         │  - File 3        │
         └──────────────────┘
                    │
                    ▼
         ┌──────────────────┐
         │  UPDATE DATABASE │
         │  - Record new     │
         │    files          │
         │  - Update catalog │
         └──────────────────┘
```

## Component Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│                        app.py                                │
│                    (Entry Point)                            │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    gui/main_window.py                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  MainWindow                                          │   │
│  │    ├── BackupWorker (QThread)                       │   │
│  │    └── UI Components                                 │   │
│  └──────────────────────────────────────────────────────┘   │
└───────┬───────────────────────┬─────────────────────────────┘
        │                       │
        │                       │
        ▼                       ▼
┌───────────────┐      ┌──────────────────────┐
│ backup_engine │      │   db/db_manager.py   │
│               │      │                      │
│ ├─ scanner.py │      │  ┌────────────────┐ │
│ ├─ copier.py  │◄─────┤  │  SQLite DB     │ │
│ └─ destination│      │  │  - file_meta   │ │
│    _scanner.py│      │  │  - dest_files  │ │
└───────┬───────┘      │  │  - sessions    │ │
        │              │  └────────────────┘ │
        │              └──────────────────────┘
        │
        ▼
┌───────────────┐
│    utils/     │
│               │
│ ├─ hashing.py │
│ ├─ logger.py  │
│ ├─ config.py  │
│ └─ platform_  │
│    utils.py   │
└───────────────┘
```

## Database Schema Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                    SQLite Database                           │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  file_metadata                                        │   │
│  │  ┌──────────┬──────────┬──────────┬──────────────┐  │   │
│  │  │file_path │file_hash │mod_time  │file_size     │  │   │
│  │  │(UNIQUE)  │          │          │              │  │   │
│  │  └──────────┴──────────┴──────────┴──────────────┘  │   │
│  │  Index: file_path                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  destination_files                                    │   │
│  │  ┌──────────┬──────────┬──────────┬──────────────┐  │   │
│  │  │dest_root │file_hash │file_path │file_size     │  │   │
│  │  │          │          │          │              │  │   │
│  │  └──────────┴──────────┴──────────┴──────────────┘  │   │
│  │  Index: file_hash, dest_root                         │   │
│  │  UNIQUE: (dest_root, file_hash, file_path)           │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  backup_sessions                                      │   │
│  │  ┌──────────┬──────────┬──────────┬──────────────┐  │   │
│  │  │session_id│source    │dest      │files_copied  │  │   │
│  │  │          │          │          │files_skipped │  │   │
│  │  └──────────┴──────────┴──────────┴──────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  destination_scans                                    │   │
│  │  ┌──────────┬──────────┬──────────┬──────────────┐  │   │
│  │  │dest_root │last_scan │files_    │scan_         │  │   │
│  │  │(UNIQUE)  │_time     │count     │duration      │  │   │
│  │  └──────────┴──────────┴──────────┴──────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Threading Model

```
┌─────────────────────────────────────────────────────────────┐
│                    MAIN THREAD (GUI)                         │
│  - PyQt5 Event Loop                                          │
│  - User Interactions                                          │
│  - UI Updates                                                 │
└───────────────────────────┬───────────────────────────────────┘
                            │
                            │ Signals/Slots
                            │ (Thread-safe communication)
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              WORKER THREAD (Backup Operations)               │
│  - File Scanning                                              │
│  - Hash Calculation                                           │
│  - File Copying                                               │
│  - Database Operations                                        │
│                                                               │
│  Signals Emitted:                                             │
│  ├── progress_update(current, total)                         │
│  ├── log_message(message)                                    │
│  └── finished(results)                                       │
└─────────────────────────────────────────────────────────────┘
```

## File Processing Pipeline

```
Source File
    │
    ▼
┌──────────────┐
│ Read File    │
│ (Chunked)    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Calculate    │
│ SHA256 Hash  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Get Metadata │
│ - Size       │
│ - Mod Time   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Check DB     │
│ - Changed?   │
│ - New?       │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Check Dest   │
│ - Duplicate? │
└──────┬───────┘
       │
       ├─── YES (Duplicate) ───► SKIP
       │
       └─── NO ───► COPY
                    │
                    ▼
            ┌──────────────┐
            │ Update DB     │
            │ - Record file │
            │ - Update dest │
            │   catalog     │
            └───────────────┘
```

## Platform-Specific Handling

```
┌─────────────────────────────────────────────────────────────┐
│                    Platform Detection                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ Windows  │  │  macOS   │  │  Linux   │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
│       │             │             │                         │
│       ▼             ▼             ▼                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                     │
│  │ Exclude │  │ Exclude │  │ Exclude │                     │
│  │Thumbs.db│  │.DS_Store│  │.directory│                    │
│  │desktop. │  │.fsevents│  │.Trash   │                     │
│  │ini      │  │d        │  │         │                     │
│  └─────────┘  └─────────┘  └─────────┘                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Data Storage Locations                                │  │
│  │  Windows: %LOCALAPPDATA%\BackupAssistant\data        │  │
│  │  macOS:   ~/Library/Application Support/...           │  │
│  │  Linux:   ~/.local/share/backup-assistant/data        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Summary

**Key Components:**
1. **GUI Layer**: PyQt5 interface for user interaction
2. **Worker Thread**: Handles all backup operations asynchronously
3. **Scanner**: Recursively scans and hashes files
4. **Destination Scanner**: Indexes destination drive for deduplication
5. **Copier**: Compares and copies files intelligently
6. **Database**: SQLite for metadata and catalog storage
7. **Utils**: Hashing, logging, configuration, platform utilities

**Key Features:**
- ✅ Cross-platform support (Windows, macOS, Linux)
- ✅ Incremental backups (only changed files)
- ✅ Destination-side deduplication (entire drive scan)
- ✅ Thread-safe operations (non-blocking GUI)
- ✅ Comprehensive logging and progress tracking


# Quick Start Guide - Cross-Platform

## Installation

### 1. Install Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Application

```bash
# From project root
python -m backup_assistant.app

# Or use the launcher script (macOS/Linux)
./launch_gui.sh
```

## First Backup

1. **Launch the application** - The GUI window will open
2. **Select Source Folder** - Click "Browse..." and choose the folder to backup
3. **Select Destination Folder** - Click "Browse..." and choose where to store the backup
4. **Start Backup** - Click "Start Backup" button
5. **Monitor Progress** - Watch the progress bar and log window
6. **Review Results** - Check the summary dialog when complete

## Platform-Specific Quick Tips

### Windows
- Database stored in: `%LOCALAPPDATA%\BackupAssistant\data`
- Automatically excludes: `Thumbs.db`, `desktop.ini`, `$RECYCLE.BIN`
- For long paths: Enable "Win32 long paths" in Group Policy

### macOS
- Database stored in: `~/Library/Application Support/BackupAssistant/data`
- Automatically excludes: `.DS_Store`, `.fseventsd`, `.Spotlight-V100`
- May need Xcode Command Line Tools: `xcode-select --install`

### Linux
- Database stored in: `~/.local/share/backup-assistant/data`
- Automatically excludes: `.directory`, `.Trash`, `.thumbnails`
- May need: `sudo apt-get install python3-pyqt5` (Ubuntu/Debian)

## Troubleshooting

### GUI Won't Launch
- **Windows**: Install PyQt5: `pip install PyQt5`
- **macOS**: Install Xcode Command Line Tools: `xcode-select --install`
- **Linux**: Install system package: `sudo apt-get install python3-pyqt5`

### Permission Errors
- Ensure you have read access to source folder
- Ensure you have write access to destination folder
- On macOS/Linux, may need to grant Full Disk Access

### Path Too Long (Windows)
- Enable long path support in Windows 10/11
- Or use shorter folder names

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Read [PLATFORMS.md](PLATFORMS.md) for platform-specific details
- Read [architecture.md](architecture.md) for technical details


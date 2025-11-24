"""PyQt5-based GUI: layout, signals, user interaction."""

import sys
from pathlib import Path
from typing import Optional
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QLabel, QProgressBar,
                             QTextEdit, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from backup_engine.scanner import FileScanner
from backup_engine.copier import FileCopier
from db.db_manager import DBManager
from utils.logger import BackupLogger


class BackupWorker(QThread):
    """Worker thread for backup operations to prevent GUI freezing."""
    
    progress_update = pyqtSignal(int, int)  # current, total
    log_message = pyqtSignal(str)
    finished = pyqtSignal(dict)  # results dict
    
    def __init__(self, source_dir: str, dest_dir: str, db_path: Path,
                 logger: BackupLogger):
        """
        Initialize backup worker.
        
        Args:
            source_dir: Source directory path
            dest_dir: Destination directory path
            db_path: Path to database file (will create new connection in thread)
            logger: Logger instance
        """
        super().__init__()
        self.source_dir = source_dir
        self.dest_dir = dest_dir
        self.db_path = db_path
        self.db_manager: Optional[DBManager] = None
        self.logger = logger
        self.is_cancelled = False
    
    def cancel(self):
        """Cancel the backup operation."""
        self.is_cancelled = True
    
    def run(self):
        """Execute backup operation."""
        try:
            # Create a new database connection in this thread
            # SQLite connections cannot be shared across threads
            self.db_manager = DBManager(db_path=self.db_path)
            
            # Update progress callback to emit signals
            def progress_callback(current, total):
                self.progress_update.emit(current, total)
            
            # Scan source folder
            self.log_message.emit("Scanning source folder...")
            scanner = FileScanner(progress_callback=progress_callback)
            file_list = scanner.scan_folder(self.source_dir, calculate_hash=True)
            
            if self.is_cancelled:
                if self.db_manager:
                    self.db_manager.close()
                return
            
            self.log_message.emit(f"Found {len(file_list)} files to analyze")
            
            # Copy files
            self.log_message.emit("Starting backup...")
            copier = FileCopier(self.db_manager, self.logger, progress_callback=progress_callback)
            results = copier.copy_files(file_list, self.source_dir, self.dest_dir, dry_run=False)
            
            if self.is_cancelled:
                if self.db_manager:
                    self.db_manager.close()
                return
            
            # Create backup session record
            session_id = self.db_manager.create_backup_session(self.source_dir, self.dest_dir)
            self.db_manager.update_backup_session(
                session_id,
                files_copied=results['files_copied'],
                files_skipped=results['files_skipped'],
                total_size=results['total_size'],
                status='completed' if not self.is_cancelled else 'cancelled'
            )
            
            self.log_message.emit("Backup completed!")
            
            # Close database connection
            if self.db_manager:
                self.db_manager.close()
            
            self.finished.emit(results)
        
        except Exception as e:
            self.log_message.emit(f"Error during backup: {str(e)}")
            if self.db_manager:
                self.db_manager.close()
            self.finished.emit({'error': str(e)})


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        """Initialize main window."""
        super().__init__()
        self.source_dir = ""
        self.dest_dir = ""
        self.db_manager = DBManager()
        self.logger = BackupLogger(log_to_file=False)
        self.backup_worker: Optional[BackupWorker] = None
        
        self.init_ui()
        self.update_log_display()
    
    def init_ui(self):
        """Initialize UI components."""
        self.setWindowTitle("Backup Assistant")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Source folder selection
        source_layout = QHBoxLayout()
        source_label = QLabel("Source Folder:")
        source_label.setFixedWidth(120)
        self.source_line_edit = QLineEdit()
        self.source_line_edit.setReadOnly(True)
        self.source_browse_btn = QPushButton("Browse...")
        self.source_browse_btn.clicked.connect(self.browse_source_folder)
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_line_edit)
        source_layout.addWidget(self.source_browse_btn)
        main_layout.addLayout(source_layout)
        
        # Destination folder selection
        dest_layout = QHBoxLayout()
        dest_label = QLabel("Destination Folder:")
        dest_label.setFixedWidth(120)
        self.dest_line_edit = QLineEdit()
        self.dest_line_edit.setReadOnly(True)
        self.dest_browse_btn = QPushButton("Browse...")
        self.dest_browse_btn.clicked.connect(self.browse_dest_folder)
        dest_layout.addWidget(dest_label)
        dest_layout.addWidget(self.dest_line_edit)
        dest_layout.addWidget(self.dest_browse_btn)
        main_layout.addLayout(dest_layout)
        
        # Buttons layout
        button_layout = QHBoxLayout()
        self.start_backup_btn = QPushButton("Start Backup")
        self.start_backup_btn.clicked.connect(self.start_backup)
        self.start_backup_btn.setEnabled(False)
        self.cancel_backup_btn = QPushButton("Cancel")
        self.cancel_backup_btn.clicked.connect(self.cancel_backup)
        self.cancel_backup_btn.setEnabled(False)
        button_layout.addWidget(self.start_backup_btn)
        button_layout.addWidget(self.cancel_backup_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)
        
        # Log display
        log_label = QLabel("Backup Log:")
        main_layout.addWidget(log_label)
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setFontFamily("Courier")
        main_layout.addWidget(self.log_text_edit)
        
        # Check if folders are selected
        self.update_ui_state()
    
    def browse_source_folder(self):
        """Open dialog to select source folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder")
        if folder:
            self.source_dir = folder
            self.source_line_edit.setText(folder)
            self.update_ui_state()
    
    def browse_dest_folder(self):
        """Open dialog to select destination folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if folder:
            self.dest_dir = folder
            self.dest_line_edit.setText(folder)
            self.update_ui_state()
    
    def update_ui_state(self):
        """Update UI state based on current selections."""
        has_source = bool(self.source_dir)
        has_dest = bool(self.dest_dir)
        self.start_backup_btn.setEnabled(has_source and has_dest and self.backup_worker is None)
    
    def start_backup(self):
        """Start backup operation."""
        if not self.source_dir or not self.dest_dir:
            QMessageBox.warning(self, "Error", "Please select both source and destination folders.")
            return
        
        # Validate paths
        source_path = Path(self.source_dir)
        dest_path = Path(self.dest_dir)
        
        if not source_path.exists():
            QMessageBox.warning(self, "Error", "Source folder does not exist.")
            return
        
        if source_path == dest_path:
            QMessageBox.warning(self, "Error", "Source and destination folders cannot be the same.")
            return
        
        # Clear previous logs
        self.logger.clear_logs()
        self.log_text_edit.clear()
        self.progress_bar.setValue(0)
        
        # Disable UI
        self.start_backup_btn.setEnabled(False)
        self.cancel_backup_btn.setEnabled(True)
        self.source_browse_btn.setEnabled(False)
        self.dest_browse_btn.setEnabled(False)
        self.status_label.setText("Backup in progress...")
        
        # Start backup worker thread
        # Pass DB path instead of DBManager instance to avoid threading issues
        self.backup_worker = BackupWorker(self.source_dir, self.dest_dir,
                                         self.db_manager.db_path, self.logger)
        self.backup_worker.progress_update.connect(self.update_progress)
        self.backup_worker.log_message.connect(self.append_log)
        self.backup_worker.finished.connect(self.backup_finished)
        self.backup_worker.start()
        
        self.logger.info(f"Starting backup from '{self.source_dir}' to '{self.dest_dir}'")
        self.update_log_display()
    
    def cancel_backup(self):
        """Cancel ongoing backup operation."""
        if self.backup_worker and self.backup_worker.isRunning():
            self.backup_worker.cancel()
            self.logger.warning("Backup cancelled by user")
            self.update_log_display()
            self.status_label.setText("Cancelling...")
    
    def update_progress(self, current: int, total: int):
        """Update progress bar."""
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
            self.status_label.setText(f"Progress: {current}/{total} files")
    
    def append_log(self, message: str):
        """Append message to log display."""
        self.log_text_edit.append(message)
        # Auto-scroll to bottom
        scrollbar = self.log_text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def update_log_display(self):
        """Update log display from logger."""
        logs = self.logger.get_logs()
        if logs:
            self.log_text_edit.setPlainText('\n'.join(logs))
    
    def backup_finished(self, results: dict):
        """Handle backup completion."""
        # Re-enable UI
        self.start_backup_btn.setEnabled(True)
        self.cancel_backup_btn.setEnabled(False)
        self.source_browse_btn.setEnabled(True)
        self.dest_browse_btn.setEnabled(True)
        
        if 'error' in results:
            self.status_label.setText(f"Backup failed: {results['error']}")
            QMessageBox.critical(self, "Backup Error", f"Backup failed:\n{results['error']}")
        else:
            files_copied = results.get('files_copied', 0)
            files_skipped = results.get('files_skipped', 0)
            total_size = results.get('total_size', 0)
            size_mb = total_size / (1024 * 1024)
            
            self.status_label.setText(
                f"Backup complete! Copied: {files_copied}, Skipped: {files_skipped}, "
                f"Size: {size_mb:.2f} MB"
            )
            self.logger.info(
                f"Backup complete: {files_copied} files copied, {files_skipped} skipped, "
                f"{size_mb:.2f} MB total"
            )
            self.update_log_display()
            
            QMessageBox.information(
                self, "Backup Complete",
                f"Backup completed successfully!\n\n"
                f"Files copied: {files_copied}\n"
                f"Files skipped: {files_skipped}\n"
                f"Total size: {size_mb:.2f} MB"
            )
        
        self.progress_bar.setValue(100)
        self.backup_worker = None
        self.update_ui_state()
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.backup_worker and self.backup_worker.isRunning():
            reply = QMessageBox.question(
                self, "Backup in Progress",
                "A backup is currently running. Do you want to cancel and exit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.backup_worker.cancel()
                self.backup_worker.wait(3000)  # Wait up to 3 seconds
            else:
                event.ignore()
                return
        
        self.db_manager.close()
        event.accept()



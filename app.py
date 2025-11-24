"""Main entry point for launching the GUI application."""

import sys
from PyQt5.QtWidgets import QApplication

from gui.main_window import MainWindow


def main():
    """Launch the Backup Assistant application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Backup Assistant")
    app.setOrganizationName("BackupAssistant")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()



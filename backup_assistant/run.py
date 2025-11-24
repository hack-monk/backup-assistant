#!/usr/bin/env python3
"""Simple launcher script for Backup Assistant."""

import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import backup_assistant
sys.path.insert(0, str(Path(__file__).parent.parent))

from backup_assistant.app import main

if __name__ == "__main__":
    main()



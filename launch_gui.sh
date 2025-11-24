#!/bin/bash
# Simple launcher script for Backup Assistant GUI

cd "$(dirname "$0")"
source venv/bin/activate
python -m backup_assistant.app


"""Functions to generate SHA256 hashes for file deduplication."""

import hashlib
import os
from pathlib import Path


def hash_file(file_path, chunk_size=8192):
    """
    Generate SHA256 hash for a file.
    
    Args:
        file_path: Path to the file to hash
        chunk_size: Size of chunks to read (default 8KB)
    
    Returns:
        str: Hexadecimal SHA256 hash of the file
    
    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    sha256_hash = hashlib.sha256()
    
    try:
        with open(file_path, 'rb') as f:
            # Read file in chunks to handle large files efficiently
            while chunk := f.read(chunk_size):
                sha256_hash.update(chunk)
    except IOError as e:
        raise IOError(f"Error reading file {file_path}: {e}")
    
    return sha256_hash.hexdigest()


def hash_string(data):
    """
    Generate SHA256 hash for a string.
    
    Args:
        data: String to hash
    
    Returns:
        str: Hexadecimal SHA256 hash
    """
    return hashlib.sha256(data.encode('utf-8')).hexdigest()



"""Cache key generation for document processing."""

import hashlib
import json
from pathlib import Path


def generate_cache_key(file_path: Path, config: dict) -> str:
    """
    Generate a cache key for a file and configuration.

    Args:
        file_path: Path to the file
        config: Processing configuration dictionary

    Returns:
        MD5 hash string as cache key
    """
    # Create a hash of file path, modification time, and config
    key_data = {
        "file_path": str(file_path),
        "mtime": file_path.stat().st_mtime,
        "config": config,
    }

    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()

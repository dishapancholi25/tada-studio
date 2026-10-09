"""Cache manager for document processing results."""

import json
import logging
from pathlib import Path
from typing import Optional

from ..config import DEFAULT_CACHE_DIR
from ..exceptions import CacheError
from .key_generator import generate_cache_key


logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching of document processing results."""

    def __init__(self, cache_dir: Path = DEFAULT_CACHE_DIR):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory for cache storage
        """
        self.cache_dir = Path(cache_dir)
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """Create cache directory if it doesn't exist."""
        try:
            self.cache_dir.mkdir(exist_ok=True, parents=True)
            logger.debug(f"[DOC-CACHE] Cache directory ready: {self.cache_dir}")
        except OSError as e:
            logger.warning(f"[DOC-CACHE] Failed to create cache directory: {e}")
            raise CacheError(f"Failed to create cache directory: {e}")

    def get(self, file_path: Path, config: dict) -> Optional[dict]:
        """
        Get cached processing result if available.

        Args:
            file_path: Path to the file
            config: Processing configuration

        Returns:
            Cached result dictionary, or None if not found
        """
        cache_key = generate_cache_key(file_path, config)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            logger.debug(f"[DOC-CACHE] Cache miss for {file_path.name}")
            return None

        try:
            with open(cache_file, "r") as f:
                result = json.load(f)
            logger.info(f"[DOC-CACHE] Cache hit for {file_path.name}")
            return result

        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"[DOC-CACHE] Failed to load cache: {e}")
            return None

    def set(self, file_path: Path, config: dict, result: dict):
        """
        Cache processing result.

        Args:
            file_path: Path to the file
            config: Processing configuration
            result: Processing result to cache
        """
        cache_key = generate_cache_key(file_path, config)
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            with open(cache_file, "w") as f:
                json.dump(result, f, default=str)
            logger.debug(f"[DOC-CACHE] Cached result for {file_path.name}")

        except (OSError, TypeError) as e:
            logger.warning(f"[DOC-CACHE] Failed to cache result: {e}")
            # Don't raise exception - caching failure shouldn't break processing

    def clear(self):
        """Clear all cached results."""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            logger.info("[DOC-CACHE] Cache cleared")

        except OSError as e:
            logger.warning(f"[DOC-CACHE] Failed to clear cache: {e}")
            raise CacheError(f"Failed to clear cache: {e}")

"""
Deduplication and history tracking manager.
"""
import os
import json
import logging
from typing import Set

logger = logging.getLogger("dedup")


class DeduplicationManager:
    """Tracks processed article and quiz URLs to avoid duplicate processing."""

    def __init__(self, storage_path: str = "output/processed.json"):
        self.storage_path = storage_path
        self.processed_urls: Set[str] = set()
        self.load()

    def load(self):
        """Load seen URLs from storage file."""
        if not os.path.exists(self.storage_path):
            self.processed_urls = set()
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self.processed_urls = set(data)
                elif isinstance(data, dict):
                    self.processed_urls = set(data.get("urls", []))
        except Exception as e:
            logger.warning(f"Could not load deduplication cache from {self.storage_path}: {e}")
            self.processed_urls = set()

    def save(self):
        """Save seen URLs back to storage file."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(sorted(list(self.processed_urls)), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to persist deduplication cache to {self.storage_path}: {e}")

    def is_processed(self, url: str) -> bool:
        """Check if a URL has already been processed."""
        clean_url = url.strip().split("?")[0].rstrip("/")
        return clean_url in self.processed_urls

    def mark_processed(self, url: str):
        """Add a URL to the processed cache."""
        clean_url = url.strip().split("?")[0].rstrip("/")
        self.processed_urls.add(clean_url)

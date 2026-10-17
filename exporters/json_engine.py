"""
Structured JSON exporter for daily digests.
"""
import os
import json
import logging
from core.models import DailyDigest

logger = logging.getLogger("json_exporter")


class JSONExporter:
    """Exports DailyDigest to clean JSON files."""

    def __init__(self, output_dir: str = "output/data"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def export(self, digest: DailyDigest) -> str:
        filepath = os.path.join(self.output_dir, f"compendium_{digest.date}.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(digest.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"Exported JSON compendium to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to export JSON compendium: {e}")
            raise

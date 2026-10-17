"""
Discord webhook broadcaster for daily compendium.
"""
import os
import logging
import requests
from typing import Optional
from core.models import DailyDigest

logger = logging.getLogger("discord_notifier")


class DiscordNotifier:
    """Delivers daily digests and PDF files to Discord via Webhook."""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")

    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url and self.webhook_url.startswith("http"))

    def send_digest(self, digest: DailyDigest, pdf_path: Optional[str] = None) -> bool:
        if not self.is_configured:
            logger.info("Discord Webhook not configured. Skipping.")
            return False

        fields = []
        for a in digest.articles[:6]:
            fields.append({
                "name": f"[{a.gs_paper}] {a.title[:50]}",
                "value": f"**Source:** {a.source} | [Read Online]({a.url})",
                "inline": False,
            })

        embed = {
            "title": f"📚 Civil Services Daily Review — {digest.date}",
            "description": (
                f"Curated {len(digest.articles)} high-yield editorials and {len(digest.quizzes)} practice questions "
                f"from The Hindu, Indian Express, Loksatta, and GKToday."
            ),
            "color": 0x1E3A5F,
            "fields": fields,
            "footer": {"text": "UPSC & MPSC Daily Digest Suite"},
        }

        payload = {"embeds": [embed]}

        try:
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
                    r = requests.post(self.webhook_url, data={"payload_json": requests.compat.json.dumps(payload)}, files=files, timeout=60)
            else:
                r = requests.post(self.webhook_url, json=payload, timeout=20)

            if r.status_code in [200, 204]:
                logger.info("Successfully dispatched digest to Discord.")
                return True
            else:
                logger.error(f"Discord webhook failed: {r.status_code} - {r.text}")
                return False
        except Exception as e:
            logger.error(f"Exception posting to Discord: {e}")
            return False

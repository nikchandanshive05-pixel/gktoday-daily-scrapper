"""
Telegram notification and PDF delivery broadcaster.
"""
import os
import logging
import requests
from typing import Optional
from core.models import DailyDigest

logger = logging.getLogger("telegram_notifier")


class TelegramNotifier:
    """Delivers daily digests and PDFs to Telegram."""

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.api_url = f"https://api.telegram.org/bot{self.token}" if self.token else None

    @property
    def is_configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send_digest_summary(self, digest: DailyDigest) -> bool:
        if not self.is_configured:
            logger.info("Telegram not configured. Skipping.")
            return False

        # Build clean HTML message
        sources = {}
        for a in digest.articles:
            sources[a.source] = sources.get(a.source, 0) + 1

        src_lines = "\n".join([f"  • <b>{k}</b>: {v} articles" for k, v in sources.items()])

        msg = (
            f"📰 <b>Civil Services Daily Review — {digest.date}</b>\n\n"
            f"<b>Coverage Overview:</b>\n{src_lines}\n"
            f"  • <b>Practice MCQs</b>: {len(digest.quizzes)} questions\n\n"
            f"<b>High-Yield Editorials Mapped:</b>\n"
        )

        for a in digest.articles[:6]:
            flag = "🇮🇳" if a.language == "mr" else "🌐"
            msg += f"{flag} <b>[{a.gs_paper}]</b> <a href=\"{a.url}\">{a.title[:65]}</a> (<i>{a.source}</i>)\n"

        msg += "\n📥 <i>Full Magazine PDF & Markdown notes attached below.</i>"
        return self._send_message(msg)

    def send_pdf(self, pdf_path: str, caption: str = "") -> bool:
        if not self.is_configured or not os.path.exists(pdf_path):
            return False

        url = f"{self.api_url}/sendDocument"
        try:
            with open(pdf_path, "rb") as f:
                files = {"document": f}
                data = {
                    "chat_id": self.chat_id,
                    "caption": caption[:1024] or "📚 UPSC/MPSC Daily Compendium",
                    "parse_mode": "HTML",
                }
                r = requests.post(url, data=data, files=files, timeout=60)
                if r.status_code == 200:
                    logger.info("Successfully sent PDF to Telegram.")
                    return True
                else:
                    logger.error(f"Telegram upload failed: {r.status_code} - {r.text}")
                    return False
        except Exception as e:
            logger.error(f"Exception sending PDF to Telegram: {e}")
            return False

    def _send_message(self, text: str) -> bool:
        url = f"{self.api_url}/sendMessage"
        # Telegram has a 4096 character limit
        chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]
        success = True
        for chunk in chunks:
            try:
                r = requests.post(
                    url,
                    json={
                        "chat_id": self.chat_id,
                        "text": chunk,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                    timeout=20,
                )
                if r.status_code != 200:
                    logger.error(f"Telegram send message failed: {r.status_code} - {r.text}")
                    success = False
            except Exception as e:
                logger.error(f"Exception sending message to Telegram: {e}")
                success = False
        return success

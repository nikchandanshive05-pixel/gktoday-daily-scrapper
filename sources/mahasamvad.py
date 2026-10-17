"""
Maharashtra Mahasamvad (महाराष्ट्र महासंवाद - DGIPR) Scraper.
Official Government of Maharashtra public policy, cabinet decisions, and state administrative schemes.
Essential primary source for MPSC State Services (राज्यसेवा) and Combined exams.
100% Cloudflare-immune.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List

from core.base_scraper import BaseScraper
from core.models import Article
from core.network import fetch_feed_entries, fetch_html, extract_clean_text

logger = logging.getLogger("mahasamvad")

MAHASAMVAD_FEED = "https://mahasamvad.in/feed/"


class MahasamvadScraper(BaseScraper):
    """Scraper for official Maharashtra State Government policy and cabinet releases."""

    def __init__(self):
        super().__init__(name="Mahasamvad (DGIPR)", source_id="mahasamvad")

    def fetch_articles(self, days: int = 1) -> List[Article]:
        articles: List[Article] = []
        seen_urls = set()
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(days, 7), hours=8)

        entries = fetch_feed_entries(MAHASAMVAD_FEED)
        logger.info(f"Mahasamvad DGIPR feed yielded {len(entries)} entries.")

        for entry in entries:
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

            if pub_date and pub_date < cutoff:
                continue

            date_str = pub_date.strftime("%Y-%m-%d") if pub_date else datetime.now(timezone.utc).strftime("%Y-%m-%d")
            link = getattr(entry, "link", "").strip()
            title = getattr(entry, "title", "").strip()

            if not link or not title or link in seen_urls:
                continue
            seen_urls.add(link)

            html = fetch_html(link)
            body = extract_clean_text(html) if html else ""
            if not body or len(body.strip()) < 100:
                summary = getattr(entry, "summary", "")
                body = summary if len(summary.strip()) > 80 else body

            if not body or len(body.strip()) < 80:
                continue

            art = Article(
                title=title,
                url=link,
                source="Mahasamvad (DGIPR)",
                published_date=date_str,
                full_text=body.strip(),
                language="mr",
                author="माहिती व जनसंपर्क महासंचालनालय (DGIPR)",
                category="शासकीय धोरणे व निर्णय",
                gs_paper="MPSC-State",
            )
            articles.append(art)

        logger.info(f"Mahasamvad Scraper extracted {len(articles)} official government articles.")
        return articles

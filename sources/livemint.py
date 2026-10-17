"""
LiveMint Opinion & Economy Scraper.
Extracts high-yield economic editorials, fiscal policy, infrastructure, and governance analyses for UPSC GS-3 & GS-2.
100% Cloudflare-immune from datacenter and cloud runners.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List

from core.base_scraper import BaseScraper
from core.models import Article
from core.network import fetch_feed_entries, fetch_html, extract_clean_text

logger = logging.getLogger("livemint")

FEED_URL = "https://www.livemint.com/rss/opinion"


class LiveMintScraper(BaseScraper):
    """Scraper for LiveMint Opinion & Economic Editorials."""

    def __init__(self):
        super().__init__(name="LiveMint", source_id="livemint")

    def fetch_articles(self, days: int = 1) -> List[Article]:
        articles: List[Article] = []
        seen_urls = set()
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(days, 2), hours=4)

        entries = fetch_feed_entries(FEED_URL)
        logger.info(f"LiveMint Opinion feed yielded {len(entries)} entries.")

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
            if not body or len(body.strip()) < 150:
                summary = getattr(entry, "summary", "")
                body = summary if len(summary.strip()) > 100 else body

            if not body or len(body.strip()) < 120:
                continue

            author = getattr(entry, "author", "Mint Opinion Desk")
            art = Article(
                title=title,
                url=link,
                source="LiveMint",
                published_date=date_str,
                full_text=body.strip(),
                language="en",
                author=author,
                category="Opinion & Economy",
                gs_paper="GS-3",
            )
            articles.append(art)

        logger.info(f"LiveMint Scraper extracted {len(articles)} high-yield economic articles.")
        return articles

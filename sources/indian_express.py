"""
Indian Express Explained and Opinion Scraper.
Uses official RSS feeds and resilient network extractors to bypass Cloudflare WAF.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List

from core.base_scraper import BaseScraper
from core.models import Article
from core.network import fetch_feed_entries, fetch_html, extract_clean_text

logger = logging.getLogger("indian_express")

FEEDS = [
    ("Explained", "https://indianexpress.com/section/explained/feed/"),
    ("Editorial", "https://indianexpress.com/section/opinion/editorials/feed/"),
    ("Columns", "https://indianexpress.com/section/opinion/columns/feed/"),
]


class IndianExpressScraper(BaseScraper):
    """Scraper for Indian Express Explained, Editorials, and Opinion Columns."""

    def __init__(self):
        super().__init__(name="Indian Express", source_id="indian_express")

    def fetch_articles(self, days: int = 1) -> List[Article]:
        articles: List[Article] = []
        seen_urls = set()
        # Ensure a generous 48-hour window so no article is missed across UTC/IST date lines
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(days, 2), hours=4)

        for category, feed_url in FEEDS:
            entries = fetch_feed_entries(feed_url)
            logger.info(f"Indian Express {category} feed yielded {len(entries)} entries.")

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

                # Fetch full article with Cloudflare bypass
                html = fetch_html(link)
                body = extract_clean_text(html) if html else ""
                if not body or len(body.strip()) < 150:
                    summary = getattr(entry, "summary", "")
                    body = summary if len(summary.strip()) > 100 else body

                if not body or len(body.strip()) < 100:
                    continue

                author = getattr(entry, "author", "Indian Express Desk")
                art = Article(
                    title=title,
                    url=link,
                    source="Indian Express",
                    published_date=date_str,
                    full_text=body.strip(),
                    language="en",
                    author=author,
                    category=category,
                )
                articles.append(art)

        logger.info(f"Indian Express Scraper extracted {len(articles)} high-yield articles.")
        return articles

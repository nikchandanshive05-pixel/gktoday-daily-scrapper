"""
Indian Express Explained and Opinion Scraper.
Uses official RSS feeds and Trafilatura for clean editorial extraction.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List
import feedparser
import trafilatura

from core.base_scraper import BaseScraper
from core.models import Article

logger = logging.getLogger("indian_express")

FEEDS = [
    ("Explained", "https://indianexpress.com/section/explained/feed/"),
    ("Editorial", "https://indianexpress.com/section/opinion/editorials/feed/"),
]


class IndianExpressScraper(BaseScraper):
    """Scraper for Indian Express Explained and Editorials."""

    def __init__(self):
        super().__init__(name="Indian Express", source_id="indian_express")

    def fetch_articles(self, days: int = 1) -> List[Article]:
        articles: List[Article] = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        for category, feed_url in FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                logger.info(f"Indian Express {category} feed yielded {len(feed.entries)} entries.")
            except Exception as e:
                logger.error(f"Error fetching Indian Express feed '{feed_url}': {e}")
                continue

            for entry in feed.entries:
                pub_date = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                if pub_date and pub_date < cutoff:
                    continue

                date_str = pub_date.strftime("%Y-%m-%d") if pub_date else datetime.now(timezone.utc).strftime("%Y-%m-%d")
                link = entry.get("link", "").strip()
                title = entry.get("title", "").strip()

                if not link or not title:
                    continue

                try:
                    downloaded = trafilatura.fetch_url(link)
                    body = trafilatura.extract(downloaded, include_comments=False) if downloaded else None
                    if not body or len(body.strip()) < 150:
                        body = entry.get("summary", "")
                except Exception as e:
                    logger.warning(f"Trafilatura failed for {link}: {e}")
                    body = entry.get("summary", "")

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

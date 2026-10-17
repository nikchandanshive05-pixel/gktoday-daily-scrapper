"""
The Hindu Editorial and Op-Ed Scraper.
Uses official RSS feeds for discovery and Trafilatura for clean text extraction.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List
import feedparser
import trafilatura

from core.base_scraper import BaseScraper
from core.models import Article

logger = logging.getLogger("the_hindu")

FEEDS = [
    "https://www.thehindu.com/opinion/editorial/feeder/default.rss",
    "https://www.thehindu.com/opinion/op-ed/feeder/default.rss",
]


class HinduScraper(BaseScraper):
    """Scraper for The Hindu Editorials and Op-Eds."""

    def __init__(self):
        super().__init__(name="The Hindu", source_id="the_hindu")

    def fetch_articles(self, days: int = 1) -> List[Article]:
        articles: List[Article] = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        for feed_url in FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                logger.info(f"The Hindu feed '{feed_url}' yielded {len(feed.entries)} entries.")
            except Exception as e:
                logger.error(f"Error fetching The Hindu feed '{feed_url}': {e}")
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

                # Extract full clean article content
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

                author = getattr(entry, "author", "The Hindu Editorial")
                art = Article(
                    title=title,
                    url=link,
                    source="The Hindu",
                    published_date=date_str,
                    full_text=body.strip(),
                    language="en",
                    author=author,
                    category="Editorial",
                )
                articles.append(art)

        logger.info(f"The Hindu Scraper extracted {len(articles)} high-yield editorials.")
        return articles

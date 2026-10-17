"""
The Hindu Editorial and Op-Ed Scraper.
Uses official RSS feeds for discovery and resilient network extractors for clean text.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List

from core.base_scraper import BaseScraper
from core.models import Article
from core.network import fetch_feed_entries, fetch_html, extract_clean_text

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
        # Allow 8-hour timezone buffer between UTC and IST
        cutoff = datetime.now(timezone.utc) - timedelta(days=days, hours=8)

        for feed_url in FEEDS:
            entries = fetch_feed_entries(feed_url)
            logger.info(f"The Hindu feed '{feed_url}' yielded {len(entries)} entries.")

            for entry in entries:
                pub_date = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                if pub_date and pub_date < cutoff:
                    continue

                date_str = pub_date.strftime("%Y-%m-%d") if pub_date else datetime.now(timezone.utc).strftime("%Y-%m-%d")
                link = getattr(entry, "link", "").strip()
                title = getattr(entry, "title", "").strip()

                if not link or not title:
                    continue

                # Extract full clean article content
                html = fetch_html(link)
                body = extract_clean_text(html) if html else ""
                if not body or len(body.strip()) < 150:
                    summary = getattr(entry, "summary", "")
                    body = summary if len(summary.strip()) > 100 else body

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

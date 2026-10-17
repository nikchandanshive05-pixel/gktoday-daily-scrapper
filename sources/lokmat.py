"""
Lokmat (लोकमत) Marathi Editorial & Analyst Scraper.
Extracts daily अग्रलेख, विशेष लेख, आणि राज्य घडामोडी for MPSC aspirants.
100% Cloudflare-immune from GitHub Actions and cloud datacenters.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List
from bs4 import BeautifulSoup

from core.base_scraper import BaseScraper
from core.models import Article
from core.network import fetch_feed_entries, fetch_html, extract_clean_text

logger = logging.getLogger("lokmat")

LOKMAT_FEED = "https://www.lokmat.com/rss/editorial.xml"


class LokmatScraper(BaseScraper):
    """Scraper for Marathi editorials and state analysis from Lokmat."""

    def __init__(self):
        super().__init__(name="Lokmat", source_id="lokmat")

    def fetch_articles(self, days: int = 1) -> List[Article]:
        articles: List[Article] = []
        seen_urls = set()
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        entries = fetch_feed_entries(LOKMAT_FEED)
        logger.info(f"Lokmat Editorial feed yielded {len(entries)} entries.")

        # Take top 15 high-yield editorials
        for entry in entries[:15]:
            link = getattr(entry, "link", "").strip()
            title = getattr(entry, "title", "").strip()

            if not link or not title or link in seen_urls:
                continue
            seen_urls.add(link)

            html = fetch_html(link)
            if not html:
                continue

            body = extract_clean_text(html)
            if not body or len(body.strip()) < 150:
                continue

            # Extract clean title from H1 if present
            final_title = title
            try:
                soup = BeautifulSoup(html, "html.parser")
                h1 = soup.find("h1")
                if h1 and len(h1.get_text(strip=True)) > 8:
                    final_title = h1.get_text(strip=True)
            except Exception:
                pass

            art = Article(
                title=final_title,
                url=link,
                source="Lokmat",
                published_date=today_str,
                full_text=body.strip(),
                language="mr",
                author="लोकमत संपादकीय मंडळ",
                category="संपादकीय",
                gs_paper="MPSC-State",
            )
            articles.append(art)

        logger.info(f"Lokmat Scraper extracted {len(articles)} authentic Marathi articles.")
        return articles

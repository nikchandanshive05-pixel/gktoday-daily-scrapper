"""
Loksatta (लोकसत्ता) Marathi Editorial and Analyst Scraper.
Extracts daily अग्रलेख, अन्वयार्थ, and विश्लेषक articles for MPSC aspirants.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Set
import requests
from bs4 import BeautifulSoup
import trafilatura

from core.base_scraper import BaseScraper
from core.models import Article

logger = logging.getLogger("loksatta")

SECTIONS = [
    ("संपादकीय", "https://www.loksatta.com/sampadkiya/"),
    ("विश्लेषक", "https://www.loksatta.com/vishesh/"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "mr,en-US,en;q=0.9",
}


class LoksattaScraper(BaseScraper):
    """Scraper for Marathi editorials and state explainer articles from Loksatta."""

    def __init__(self):
        super().__init__(name="Loksatta", source_id="loksatta")

    def fetch_articles(self, days: int = 1) -> List[Article]:
        articles: List[Article] = []
        seen_urls: Set[str] = set()
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        for cat_name, section_url in SECTIONS:
            try:
                resp = requests.get(section_url, headers=HEADERS, timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"Failed to fetch {section_url} (HTTP {resp.status_code})")
                    continue
                
                soup = BeautifulSoup(resp.text, "html.parser")
                candidates = []

                # Find article hyperlinks within the section
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"].split("?")[0].rstrip("/") + "/"
                    text = a_tag.get_text().strip()

                    # Valid article paths typically have deeper path segments and title text
                    if href.startswith("https://www.loksatta.com/") and len(text) > 15:
                        if "/sampadkiya/" in href or "/vishesh/" in href:
                            if href not in seen_urls and href != section_url.rstrip("/") + "/":
                                seen_urls.add(href)
                                candidates.append((href, text))

                logger.info(f"Discovered {len(candidates)} candidate articles in Loksatta {cat_name}.")

                # Extract content for up to 8 top candidate articles per section
                for link, preliminary_title in candidates[:8]:
                    try:
                        downloaded = trafilatura.fetch_url(link)
                        body = trafilatura.extract(downloaded, include_comments=False) if downloaded else None
                    except Exception as e:
                        logger.warning(f"Trafilatura failed on Loksatta article {link}: {e}")
                        body = None

                    if not body or len(body.strip()) < 150:
                        continue

                    art = Article(
                        title=preliminary_title,
                        url=link,
                        source="Loksatta",
                        published_date=today_str,
                        full_text=body.strip(),
                        language="mr",
                        author="लोकसत्ता संपादकीय मंडळ",
                        category=cat_name,
                        gs_paper="MPSC-State",
                    )
                    articles.append(art)

            except Exception as e:
                logger.error(f"Error scraping Loksatta section {section_url}: {e}")

        logger.info(f"Loksatta Scraper extracted {len(articles)} Marathi articles.")
        return articles

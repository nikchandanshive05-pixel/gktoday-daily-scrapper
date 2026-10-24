"""
Loksatta Scraper for Marathi Editorials, Agralekh, and Vishleshak.
Extracts high-yield articles for MPSC Civil Services preparation.
"""
import time
import logging
from datetime import datetime, timezone
from typing import List

import requests
from bs4 import BeautifulSoup
import trafilatura

from core.base_scraper import BaseScraper
from core.models import Article

logger = logging.getLogger("loksatta")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class LoksattaScraper(BaseScraper):
    """Scraper for Loksatta Marathi editorials (अग्रलेख / संपादकीय)."""

    def __init__(self, request_delay: float = 0.5):
        super().__init__(name="Loksatta", source_id="loksatta")
        self.base_url = "https://www.loksatta.com"
        self.request_delay = request_delay

    def fetch_articles(self, days: int = 1) -> List[Article]:
        articles: List[Article] = []
        editorial_url = f"{self.base_url}/editorial/"

        logger.info(f"Fetching Loksatta editorial index from {editorial_url}...")
        try:
            resp = requests.get(editorial_url, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                logger.error(f"Loksatta returned HTTP {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            found_links = []

            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/editorial/" in href and href != editorial_url:
                    text = a.get_text(strip=True)
                    if len(text) > 10 and not any(href == item[1] for item in found_links):
                        found_links.append((text, href))

            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            for title_text, url in found_links[:10]:
                try:
                    time.sleep(self.request_delay)
                    downloaded = trafilatura.fetch_url(url)
                    if not downloaded:
                        continue
                    text = trafilatura.extract(downloaded)
                    if not text or len(text) < 150:
                        continue

                    art_soup = BeautifulSoup(downloaded, "html.parser")
                    author = None
                    auth_tag = art_soup.find("div", class_=lambda c: c and "author" in c)
                    if auth_tag:
                        author = auth_tag.get_text(strip=True)

                    articles.append(
                        Article(
                            title=title_text,
                            url=url,
                            source="Loksatta",
                            published_date=today_str,
                            full_text=text.strip(),
                            language="mr",
                            author=author,
                            category="संपादकीय (Editorial)",
                            gs_paper="MPSC-State",
                        )
                    )
                except Exception as ex:
                    logger.warning(f"Error extracting Loksatta article {url}: {ex}")

        except Exception as e:
            logger.error(f"Error scraping Loksatta: {e}")

        logger.info(f"Loksatta scraped {len(articles)} Marathi editorials.")
        return articles

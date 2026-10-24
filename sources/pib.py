"""
PIB (Press Information Bureau) Scraper.
Scrapes official government press releases, policy announcements, and ministry briefs.
"""
import time
import logging
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List

import requests
from bs4 import BeautifulSoup
import trafilatura

from core.base_scraper import BaseScraper
from core.models import Article

logger = logging.getLogger("pib")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class PIBScraper(BaseScraper):
    """Scraper for PIB Press Releases."""

    def __init__(self, request_delay: float = 0.5):
        super().__init__(name="PIB", source_id="pib")
        self.base_url = "https://pib.gov.in"
        self.request_delay = request_delay

    def fetch_articles(self, days: int = 1) -> List[Article]:
        articles: List[Article] = []
        rss_url = f"{self.base_url}/RssMain.aspx?ModId=6&Lang=1"
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        logger.info(f"Ingesting PIB RSS feed from {rss_url}...")
        try:
            req = urllib.request.Request(rss_url, headers=HEADERS)
            data = urllib.request.urlopen(req, timeout=12).read()
            root = ET.fromstring(data)
            items = root.findall(".//item")

            for item in items[:10]:
                try:
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    if title_elem is None or link_elem is None:
                        continue
                    title = title_elem.text.strip()
                    url = link_elem.text.strip()

                    time.sleep(self.request_delay)
                    iframe_url = url.replace("PressReleaseDetail.aspx", "PressReleaseIframePage.aspx")
                    resp = requests.get(iframe_url, headers=HEADERS, timeout=12)
                    if resp.status_code != 200:
                        resp = requests.get(url, headers=HEADERS, timeout=12)

                    text = ""
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        content_div = (
                            soup.find("div", class_="innner-page-main-about-us-content-right-part")
                            or soup.find("div", class_="content-area")
                            or soup.find("div", class_="ReleaseContent")
                        )
                        if content_div:
                            text = content_div.get_text(separator="\n", strip=True)
                        else:
                            extracted = trafilatura.extract(resp.text)
                            if extracted:
                                text = extracted

                    if not text or len(text) < 120:
                        continue

                    articles.append(
                        Article(
                            title=title,
                            url=url,
                            source="PIB",
                            published_date=today_str,
                            full_text=text.strip(),
                            language="en" if all(ord(c) < 128 for c in title[:10]) else "hi",
                            category="Government Policies & Schemes",
                            gs_paper="GS-2",
                            exam_stage="Both",
                        )
                    )
                except Exception as ex:
                    logger.warning(f"Error parsing PIB item {url}: {ex}")

        except Exception as e:
            logger.error(f"Error scraping PIB feed: {e}")

        logger.info(f"PIB scraped {len(articles)} official press releases.")
        return articles

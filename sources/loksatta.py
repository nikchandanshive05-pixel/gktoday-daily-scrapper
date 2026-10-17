"""
Loksatta (लोकसत्ता) Marathi Editorial and Analyst Scraper.
Extracts daily अग्रलेख, अन्वयार्थ, and विश्लेषक articles for MPSC aspirants.
Uses resilient network headers with Googlebot crawler fallbacks to bypass Cloudflare.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Set
from bs4 import BeautifulSoup

from core.base_scraper import BaseScraper
from core.models import Article
from core.network import fetch_html, extract_clean_text

logger = logging.getLogger("loksatta")

SECTIONS = [
    ("संपादकीय", "https://www.loksatta.com/sampadkiya/"),
    ("विश्लेषक", "https://www.loksatta.com/vishesh/"),
]


class LoksattaScraper(BaseScraper):
    """Scraper for Marathi editorials and state explainer articles from Loksatta."""

    def __init__(self):
        super().__init__(name="Loksatta", source_id="loksatta")

    def fetch_articles(self, days: int = 1) -> List[Article]:
        articles: List[Article] = []
        seen_urls: Set[str] = set()
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        for cat_name, section_url in SECTIONS:
            html = fetch_html(section_url)
            if not html:
                logger.warning(f"Failed to fetch Loksatta section {section_url}")
                continue

            soup = BeautifulSoup(html, "html.parser")
            candidates = []

            # Find article hyperlinks within the section
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].split("?")[0].rstrip("/") + "/"
                text = a_tag.get_text().strip()

                if href.startswith("https://www.loksatta.com/") and len(text) > 15:
                    if "/sampadkiya/" in href or "/vishesh/" in href:
                        if href not in seen_urls and href != section_url.rstrip("/") + "/":
                            seen_urls.add(href)
                            candidates.append((href, text))

            logger.info(f"Discovered {len(candidates)} candidate articles in Loksatta {cat_name}.")

            # Extract content for candidate articles per section
            for link, preliminary_title in candidates[:10]:
                art_html = fetch_html(link)
                if not art_html:
                    continue

                body = extract_clean_text(art_html)
                if not body or len(body.strip()) < 150:
                    continue

                # Extract precise title and date from article DOM
                final_title = preliminary_title
                pub_date = today_str
                try:
                    art_soup = BeautifulSoup(art_html, "html.parser")
                    h1 = art_soup.find("h1")
                    if h1 and len(h1.get_text(strip=True)) > 8:
                        final_title = h1.get_text(strip=True)

                    time_meta = (
                        art_soup.find("meta", property="article:published_time")
                        or art_soup.find("meta", attrs={"name": "publish-date"})
                    )
                    if time_meta and time_meta.get("content"):
                        pub_date = time_meta["content"][:10]
                except Exception:
                    pass

                art = Article(
                    title=final_title,
                    url=link,
                    source="Loksatta",
                    published_date=pub_date,
                    full_text=body.strip(),
                    language="mr",
                    author="लोकसत्ता संपादकीय मंडळ",
                    category=cat_name,
                    gs_paper="MPSC-State",
                )
                articles.append(art)

        logger.info(f"Loksatta Scraper extracted {len(articles)} Marathi articles.")
        return articles

#!/usr/bin/env python3
"""
GKToday Scraper v10+ (Production-Grade Multi-Channel Edition)

Features:
  - Robust DOM & Fallback Article Extraction with UPSC Classification
  - Upgraded DOM-based Quiz & MCQ Scraping with Options, Answers & Explanations
  - Resilient Date Parsing (supporting ranges like "September 13-14, 2026")
  - Unicode & Special Character Sanitization (Rupee symbols, dashes, quotes)
  - Magazine-Quality PDF Generation (Combined, Separate, Test Mode with Answer Key)
  - NumberedCanvas (Page X of Y) + PDF Bookmarks / Outline Navigation
  - Multi-Channel Delivery: Telegram Bot + Discord Webhooks
  - JSON Data Export for downstream note-taking/APIs (Anki, Obsidian, Web apps)
  - CLI Interface with rich arguments & built-in .env support
  - Incremental Deduplication via processed.json history

Usage:
  python gktoday_scraper_v10.py --help
  python gktoday_scraper_v10.py --days 2 --mode both
  python gktoday_scraper_v10.py --dry-run
"""

import os
import sys
import re
import time
import json
import random
import logging
import argparse
from datetime import datetime, timedelta, timezone
from functools import wraps

import requests
from bs4 import BeautifulSoup

# PDF Generation Imports
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    HRFlowable, PageTemplate, Frame, KeepTogether, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas as pdfcanvas

# ==================== LOGGING SETUP ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("gktoday_scraper")


# ==================== ENV LOADER ====================
def load_dotenv_custom(dotenv_path=".env"):
    """Load key-value pairs from .env file into os.environ if not already set."""
    if not os.path.exists(dotenv_path):
        return
    try:
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception as e:
        logger.debug("Custom .env loader notice: %s", e)

# Try python-dotenv first, fallback to custom loader
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    load_dotenv_custom()


# ==================== PALETTE & THEME ====================
PALETTE = {
    "primary":       "#1e3a5f",  # Deep Navy
    "secondary":     "#2563eb",  # Royal Blue
    "accent":        "#dc2626",  # Crimson Red
    "success":       "#059669",  # Emerald Green
    "warning":       "#d97706",  # Amber
    "text":          "#1f2937",  # Dark Charcoal
    "muted":         "#4b5563",  # Slate Gray
    "light_gray":    "#94a3b8",  # Cool Gray
    "border":        "#e2e8f0",  # Light Border
    "bg_blue":       "#f0f9ff",  # Soft Blue Tint
    "border_blue":   "#bae6fd",  # Sky Border
    "bg_cover":      "#f8fafc",  # Crisp Slate White
    "bg_green":      "#ecfdf5",  # Soft Green
    "border_green":  "#a7f3d0",  # Mint Border
    "bg_quiz":       "#fdf4ff",  # Soft Purple Tint
    "border_quiz":   "#f5d0fe",  # Lilac Border
}

CATEGORY_COLORS = {
    "Economy":              "#059669",
    "Science & Technology": "#7c3aed",
    "Environment":          "#16a34a",
    "Sports":               "#ea580c",
    "Defence":              "#dc2626",
    "International":        "#2563eb",
    "Awards & Persons":     "#db2777",
    "National":             "#4f46e5",
    "General":              "#64748b",
    "Quiz":                 "#7c3aed",
}

CATEGORY_KEYWORDS = {
    "Economy": ["gdp", "economy", "budget", "rbi", "inflation", "fiscal", "trade", "wto", "tax", "scheme", "sebi", "npci", "banking", "rupee", "forex", "fdi"],
    "Science & Technology": ["isro", "satellite", "exoplanet", "telescope", "research", "spacecraft", "technology", "ai", "artificial intelligence", "drdo", "nuclear", "genome", "quantum", "supercomputer", "semiconductor"],
    "Environment": ["climate", "biodiversity", "wildlife", "forest", "conservation", "species", "pollution", "carbon", "renewable", "wetland", "cop", "unep", "tiger reserve", "national park"],
    "Sports": ["games", "olympic", "paralympics", "tournament", "championship", "medal", "athletes", "cricket", "world cup", "grand slam", "fifa"],
    "Defence": ["drdo", "missile", "army", "navy", "air force", "defence", "border", "military", "exercise", "warship", "submarine", "frigate"],
    "International": ["united nations", "wto", "who", "imf", "world bank", "prime minister", "president", "bilateral", "summit", "g20", "brics", "asean", "treaty", "diplomacy"],
    "Awards & Persons": ["award", "appointed", "minister", "elected", "career", "honour", "padma", "bharat ratna", "nobel", "sahitya akademi", "obituary"],
    "National": ["government", "ministry", "cabinet", "delhi", "state", "india", "parliament", "lok sabha", "rajya sabha", "supreme court", "high court", "constitution", "judiciary"],
}

STOP_MARKERS = [
    "Your email address will not be published",
    "Leave a Reply",
    "Cancel reply",
    "Post Comment",
]

JUNK_MARKERS = [
    "Daily MCQs", "Monthly MCQs", "Current Affairs Quiz",
    "Topic Wise CA MCQs", "CA MCQs in Other Languages",
    "SSC/RRB/States Level MCQs", "Current Affairs Monthly 240 MCQs",
    "CA Articles+MCQs", "Previous Months Quiz",
    "Read Also", "Click Here", "Download PDF",
]

JUNK_EXACT = {"Comment*", "Name*", "Email*", "∆", "Home", "", "Submit", "Share this:", "Tweet"}


# ==================== UTILITIES ====================
def retry(max_retries=3, backoff=2):
    """Decorator for retrying functions with exponential backoff and jitter."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    sleep_time = (backoff ** attempt) + random.uniform(0.5, 1.5)
                    logger.warning("Retry %d/%d for %s after %.1fs: %s", attempt + 1, max_retries, func.__name__, sleep_time, e)
                    time.sleep(sleep_time)
        return wrapper
    return decorator


def sanitize_text(text):
    """Normalize unicode characters for PDF fonts and consoles."""
    if not text:
        return ""
    text = str(text)
    replacements = {
        "\u20b9": "Rs. ",      # Indian Rupee symbol
        "\u2018": "'",         # Left single quote
        "\u2019": "'",         # Right single quote
        "\u201c": '"',         # Left double quote
        "\u201d": '"',         # Right double quote
        "\u2013": " - ",       # En-dash
        "\u2014": " -- ",      # Em-dash
        "\u2026": "...",       # Ellipsis
        "\u00a0": " ",         # Non-breaking space
        "\u2022": "*",         # Bullet
        "\u25aa": "*",         # Black small square
        "\u25a0": "*",         # Black square
        "\u25c6": "*",         # Black diamond
        "\u2032": "'",         # Prime
        "\u2033": '"',         # Double prime
    }
    for char, rep in replacements.items():
        text = text.replace(char, rep)
    
    # Remove surrogate pairs and unprintable control chars
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()


def sanitize_xml(text):
    """Escape XML characters for ReportLab Paragraphs."""
    if not text:
        return ""
    text = sanitize_text(text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text.replace("\n\n", "<br/><br/>").replace("\n", " ")


def parse_date_flexible(date_str):
    """Parse date strings including single dates and hyphenated ranges."""
    if not date_str:
        return None
    date_str = date_str.strip()

    # Handle date ranges like "September 13-14, 2026" or "September 13 - 14, 2026"
    range_match = re.search(r"([A-Za-z]+)\s+(\d{1,2})\s*[-–—]\s*(\d{1,2}),?\s*(\d{4})", date_str)
    if range_match:
        month, d1, d2, year = range_match.groups()
        # Return the latter date of the range
        try:
            return datetime.strptime(f"{month} {d2}, {year}", "%B %d, %Y").date()
        except ValueError:
            try:
                return datetime.strptime(f"{month} {d2}, {year}", "%b %d, %Y").date()
            except ValueError:
                pass

    patterns = [
        "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y",
        "%B %d %Y", "%b %d %Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"
    ]
    # Clean trailing dots or commas
    clean_str = re.sub(r"[,\.]+$", "", date_str)
    for p in patterns:
        try:
            return datetime.strptime(clean_str, p).date()
        except ValueError:
            continue

    # Regex search within string
    m = re.search(r"([A-Za-z]+ \d{1,2},? \d{4})", date_str)
    if m:
        for p in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"):
            try:
                return datetime.strptime(m.group(1).replace(",", ""), p.replace(",", "")).date()
            except ValueError:
                continue

    m_digits = re.search(r"(\d{1,2})[\-/](\d{1,2})[\-/](\d{4})", date_str)
    if m_digits:
        try:
            return datetime(int(m_digits.group(3)), int(m_digits.group(2)), int(m_digits.group(1))).date()
        except ValueError:
            pass

    return None


# ==================== NUMBERED CANVAS WITH BOOKMARKS ====================
class NumberedBookmarkCanvas(pdfcanvas.Canvas):
    """
    Two-pass canvas that calculates total pages for 'Page X of Y' footers
    and generates hierarchical PDF bookmarks for table of contents.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self._bookmark_count = 0
        self.section_name = "GKToday Deep Digest"
        self.display_date = ""

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            pdfcanvas.Canvas.showPage(self)
        pdfcanvas.Canvas.save(self)

    def bookmark_section(self, title, level=0):
        key = f"sec-{self._bookmark_count}"
        self.bookmarkPage(key)
        self.addOutlineEntry(title, key, level=level, closed=(level > 0))
        self._bookmark_count += 1

    def draw_page_decorations(self, page_count):
        # Skip header and footer on cover page (page 1)
        if self._pageNumber == 1:
            return

        self.saveState()

        # Running Top Header
        self.setStrokeColor(HexColor(PALETTE["border"]))
        self.setLineWidth(0.6)
        self.line(18 * mm, A4[1] - 14 * mm, A4[0] - 18 * mm, A4[1] - 14 * mm)

        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(HexColor(PALETTE["primary"]))
        self.drawString(18 * mm, A4[1] - 12 * mm, self.section_name.upper())

        if self.display_date:
            self.setFont("Helvetica", 8)
            self.setFillColor(HexColor(PALETTE["muted"]))
            self.drawRightString(A4[0] - 18 * mm, A4[1] - 12 * mm, self.display_date)

        # Running Bottom Footer
        self.line(18 * mm, 15 * mm, A4[0] - 18 * mm, 15 * mm)

        self.setFont("Helvetica", 8)
        self.setFillColor(HexColor(PALETTE["light_gray"]))
        self.drawString(18 * mm, 10 * mm, "GKToday Current Affairs & Quiz Digest")

        page_str = f"Page {self._pageNumber} of {page_count}"
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(HexColor(PALETTE["primary"]))
        self.drawRightString(A4[0] - 18 * mm, 10 * mm, page_str)

        self.restoreState()


# ==================== ARTICLE SCRAPER ====================
class GKTodayScraper:
    BASE_URL = "https://www.gktoday.in"

    def __init__(self, max_days_old=2):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        ist_offset = timezone(timedelta(hours=5, minutes=30))
        self.today = datetime.now(ist_offset).date()
        self.cutoff_date = self.today - timedelta(days=max_days_old)
        logger.info("Article Scraper initialized. Today: %s | Cutoff: %s", self.today, self.cutoff_date)

    @retry(max_retries=3, backoff=2)
    def fetch(self, url):
        r = self.session.get(url, timeout=30)
        r.raise_for_status()
        return r.text

    def scrape_articles(self, skip_urls=None):
        skip_urls = skip_urls or set()
        logger.info("Fetching GKToday homepage for articles...")
        try:
            html = self.fetch(self.BASE_URL)
        except Exception as e:
            logger.error("Failed to fetch homepage: %s", e)
            return []

        soup = BeautifulSoup(html, "html.parser")
        article_links = []
        seen_urls = set()

        for heading in soup.find_all(["h2", "h3"]):
            link_tag = heading.find("a")
            if not link_tag:
                continue
            title = sanitize_text(link_tag.get_text(strip=True))
            url = link_tag.get("href", "").strip()
            if not title or len(title) < 10 or not url:
                continue

            # Skip navigation / portal links
            if any(s in title.lower() for s in ["gk today", "home", "about", "contact", "quiz", "archives", "mcq", "target", "upsc prelims test"]):
                continue

            if not url.startswith("http"):
                url = self.BASE_URL + url

            if url in seen_urls or url in skip_urls:
                continue

            seen_urls.add(url)
            article_links.append({"title": title, "url": url})

        logger.info("Found %d potential article links to inspect.", len(article_links))

        full_articles = []
        for i, item in enumerate(article_links):
            logger.info("[%d/%d] Scraping article: %s", i + 1, len(article_links), item["title"][:55])
            time.sleep(random.uniform(0.8, 1.8))

            try:
                article_html = self.fetch(item["url"])
                parsed = self._parse_article(article_html, item["title"], item["url"])
                if parsed:
                    if parsed["parsed_date"] and parsed["parsed_date"] >= self.cutoff_date:
                        full_articles.append(parsed)
                        logger.info("  -> Added (%s) [%s]", parsed["category"], parsed["date_str"])
                    elif not parsed["parsed_date"]:
                        # If date could not be parsed, keep conservatively if from homepage
                        full_articles.append(parsed)
                        logger.info("  -> Added (date unverified) [%s]", parsed["category"])
                    else:
                        logger.info("  -> Skipped outdated: %s (Cutoff: %s)", parsed["date_str"], self.cutoff_date)
            except Exception as e:
                logger.error("  -> Error scraping %s: %s", item["url"], e)

        return full_articles

    def _strip_chrome(self, container):
        for tag in ["script", "style", "nav", "header", "footer", "aside", "iframe", "form", "button"]:
            for t in container.find_all(tag):
                t.decompose()
        
        # Remove widgets, share boxes, sidebars
        junk_classes = re.compile(r"(sharedaddy|jp-relatedposts|related-articles|comment|respond|widget|sidebar|breadcrumb|post-navigation|entry-footer|tags|social|share|menu|navbar|quiz-nav|advertisement|ad-box|a2a_kit|gktoday-share-box)", re.I)
        for t in container.find_all(attrs={"class": junk_classes}):
            t.decompose()
        for t in container.find_all(attrs={"id": junk_classes}):
            t.decompose()

    def _find_content_container(self, soup):
        candidates = [
            soup.find("div", class_="content-area"),
            soup.find("div", class_="main_content"),
            soup.find(attrs={"itemprop": "articleBody"}),
            soup.find("div", class_="entry-content"),
            soup.find("article"),
        ]
        for c in candidates:
            if c is not None:
                return c
        return soup.find("body")

    def _parse_article(self, html, title, url):
        soup = BeautifulSoup(html, "html.parser")

        # 1. Date Extraction
        date_str = ""
        parsed_date = None

        # Check post-update-notice or meta
        update_notice = soup.find("div", class_="post-update-notice")
        if update_notice:
            txt = update_notice.get_text(" ", strip=True)
            m = re.search(r"(?:written on|modified on|published on)\s*([A-Z][a-z]+ \d{1,2},? \d{4})", txt, re.I)
            if m:
                date_str = m.group(1)
                parsed_date = parse_date_flexible(date_str)

        if not parsed_date:
            for meta_sel in ["entry-meta", "post-meta", "single-cgs-book-meta", "post-info"]:
                meta_div = soup.find("div", class_=meta_sel)
                if meta_div:
                    m = re.search(r"([A-Z][a-z]+ \d{1,2},? \d{4})", meta_div.get_text(" ", strip=True))
                    if m:
                        date_str = m.group(1)
                        parsed_date = parse_date_flexible(date_str)
                        break

        # 2. Main Content Extraction
        container = self._find_content_container(soup)
        if container is None:
            return None

        self._strip_chrome(container)

        elements = container.find_all(["p", "ul", "ol", "h4", "h3"])
        texts = []
        for el in elements:
            txt = sanitize_text(el.get_text(" ", strip=True))
            if not txt:
                continue
            if any(marker in txt for marker in STOP_MARKERS):
                break
            if txt == title or self._is_junk(txt, title):
                continue
            texts.append(txt)

        full_content = "\n\n".join(texts).strip()
        full_content = re.sub(r"\n{3,}", "\n\n", full_content)

        if not full_content or len(full_content) < 100:
            return None

        # If date still not found, search in first 200 chars of content
        if not parsed_date:
            m_first = re.search(r"([A-Z][a-z]+ \d{1,2},? \d{4})", full_content[:200])
            if m_first:
                date_str = m_first.group(1)
                parsed_date = parse_date_flexible(date_str)

        category = self._infer_category(title + " " + full_content)

        return {
            "title": title,
            "url": url,
            "date_str": date_str or (parsed_date.strftime("%B %d, %Y") if parsed_date else "N/A"),
            "parsed_date": parsed_date,
            "category": category,
            "content": full_content,
            "key_points": self._key_points(full_content),
            "relevance": self._relevance(title + " " + full_content),
        }

    @staticmethod
    def _is_junk(text, title):
        if not text or text in JUNK_EXACT or len(text) > 6000:
            return True
        if text.count("■") > 3 or text.lower().count("mcqs") >= 3:
            return True
        if any(marker in text for marker in JUNK_MARKERS):
            return True
        squished = text.replace(" ", "")
        if squished.startswith("Home") and title.replace(" ", "") in squished:
            return True
        return False

    def _infer_category(self, text):
        t = text.lower()
        scores = {}
        for cat, keywords in CATEGORY_KEYWORDS.items():
            score = sum(t.count(k) for k in keywords)
            if score:
                scores[cat] = score
        return max(scores, key=scores.get) if scores else "General"

    def _key_points(self, text):
        flat_text = text.replace("\n", " ")
        pts = []
        indicators = [
            "first", "largest", "launched", "approved", "appointed", "signed",
            "budget", "gdp", "supreme court", "isro", "only", "biggest", "highest",
            "new", "introduced", "passed", "unveiled", "inaugurated", "initiative",
            "bilateral", "aims to", "established", "ranked"
        ]
        for s in re.split(r"(?<=[.!?])\s+", flat_text):
            s_clean = s.strip()
            if sum(1 for ind in indicators if ind in s_clean.lower()) >= 1 and 35 < len(s_clean) < 280:
                pts.append(s_clean)
        return pts[:4]

    def _relevance(self, text):
        t = text.lower()
        high_yield_keywords = [
            "constitution", "parliament", "supreme court", "scheme", "yojana",
            "gdp", "rbi", "climate", "biodiversity", "isro", "drdo", "cabinet",
            "amendment", "bill", "treaty", "prelims", "upsc", "act"
        ]
        matched = [k for k in high_yield_keywords if k in t]
        level = "HIGH" if len(matched) >= 2 else "MEDIUM" if len(matched) == 1 else "STANDARD"
        return {"level": level, "matched_keywords": matched[:3]}

    def close(self):
        self.session.close()


# ==================== QUIZ SCRAPER ====================
class QuizScraper:
    QUIZ_LISTING_URL = "https://www.gktoday.in/gk-current-affairs-quiz-questions-answers/"

    def __init__(self, max_days_old=2):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "DNT": "1",
            "Connection": "keep-alive",
        })
        ist_offset = timezone(timedelta(hours=5, minutes=30))
        self.today = datetime.now(ist_offset).date()
        self.cutoff_date = self.today - timedelta(days=max_days_old)
        logger.info("Quiz Scraper initialized. Today: %s | Cutoff: %s", self.today, self.cutoff_date)

    @retry(max_retries=3, backoff=2)
    def fetch(self, url):
        r = self.session.get(url, timeout=30)
        r.raise_for_status()
        return r.text

    def scrape_quizzes(self, skip_urls=None):
        skip_urls = skip_urls or set()
        logger.info("Fetching GKToday quiz listing page...")
        try:
            html = self.fetch(self.QUIZ_LISTING_URL)
        except Exception as e:
            logger.error("Failed to fetch quiz listing: %s", e)
            return []

        quiz_links = self._extract_quiz_links(html)
        logger.info("Found %d quiz links matching date criteria.", len(quiz_links))

        all_quizzes = []
        for i, item in enumerate(quiz_links):
            if item["url"] in skip_urls:
                logger.info("Skipping already processed quiz: %s", item["title"])
                continue

            logger.info("[%d/%d] Scraping quiz: %s", i + 1, len(quiz_links), item["title"])
            time.sleep(random.uniform(1.0, 2.2))

            try:
                page_html = self.fetch(item["url"])
                questions = self._parse_quiz_page(page_html)
                if questions:
                    all_quizzes.append({
                        "title": item["title"],
                        "date": item["date"].strftime("%B %d, %Y") if item["date"] else "N/A",
                        "parsed_date": item["date"],
                        "url": item["url"],
                        "question_count": len(questions),
                        "questions": questions
                    })
                    logger.info("  -> Extracted %d MCQs successfully", len(questions))
                else:
                    logger.warning("  -> No questions found on %s", item["url"])
            except Exception as e:
                logger.error("  -> Error scraping quiz %s: %s", item["url"], e)

        return all_quizzes

    def _extract_quiz_links(self, html):
        soup = BeautifulSoup(html, "html.parser")
        links = []
        seen = set()

        for heading in soup.find_all(["h2", "h3"]):
            link_tag = heading.find("a")
            if not link_tag:
                continue
            title = sanitize_text(link_tag.get_text(strip=True))
            href = link_tag.get("href", "").strip()

            if "Current Affairs Quiz" not in title or not href:
                continue

            quiz_date = parse_date_flexible(title)
            if quiz_date and quiz_date < self.cutoff_date:
                continue

            url = href if href.startswith("http") else f"https://www.gktoday.in{href}"
            if url in seen:
                continue

            seen.add(url)
            links.append({"title": title, "url": url, "date": quiz_date})

        return links

    def _parse_quiz_page(self, html):
        soup = BeautifulSoup(html, "html.parser")

        # Approach 1: Modern DOM-based parsing using wp_quiz_question
        q_divs = soup.find_all("div", class_="wp_quiz_question")
        if q_divs:
            questions = []
            for i, q_div in enumerate(q_divs):
                parent = q_div.parent or q_div
                raw_q = sanitize_text(q_div.get_text(" ", strip=True))
                
                # Extract number and question text
                m_num = re.match(r"^(\d+)\.\s*(.*)$", raw_q)
                if m_num:
                    q_num = int(m_num.group(1))
                    q_text = m_num.group(2).strip()
                else:
                    q_num = i + 1
                    q_text = raw_q

                # Options
                options = {}
                opt_div = parent.find("div", class_="wp_quiz_question_options")
                if opt_div:
                    opt_text = sanitize_text(opt_div.get_text("\n", strip=True))
                    for line in opt_text.split("\n"):
                        m_opt = re.match(r"^\[?([A-D])\]?\s*(.*)$", line.strip())
                        if m_opt:
                            options[m_opt.group(1)] = m_opt.group(2).strip()

                # Answer & Explanation
                ans_div = parent.find("div", class_="wp_basic_quiz_answer") or parent.find("div", class_=lambda c: c and "ques_answer" in c)
                correct = None
                correct_text = ""
                explanation = ""

                if ans_div:
                    ans_raw = sanitize_text(ans_div.get_text("\n", strip=True))
                    m_ans = re.search(r"Correct Answer:\s*([A-D])(?:\s*\[([^\]]+)\])?", ans_raw)
                    if m_ans:
                        correct = m_ans.group(1)
                        correct_text = m_ans.group(2).strip() if m_ans.group(2) else ""

                    m_exp = re.search(r"(?:Notes?|Explanation):\s*(.*)", ans_raw, re.DOTALL)
                    if m_exp:
                        explanation = re.sub(r"\s+", " ", m_exp.group(1).strip())

                if q_text and (options or correct):
                    questions.append({
                        "number": q_num,
                        "question": q_text,
                        "options": options,
                        "correct": correct,
                        "correct_text": correct_text,
                        "explanation": explanation
                    })

            if questions:
                questions.sort(key=lambda x: x["number"])
                return questions

        # Approach 2: Fallback Regex parsing on raw content text
        content = soup.find("div", class_="content-area") or soup.find("div", class_="main_content") or soup.find("body")
        if not content:
            return []

        all_text = sanitize_text(content.get_text("\n", strip=True))
        return self._parse_quiz_regex(all_text)

    def _parse_quiz_regex(self, text):
        questions = []
        text = re.sub(r"\n{2,}", "\n", text)
        blocks = re.split(r"\n(?=\d+\.\s)", text)

        for block in blocks:
            block = block.strip()
            if not block or not re.match(r"^\d+\.", block):
                continue

            q_match = re.match(r"(\d+)\.\s*(.*?)(?=\s*\[A\]|$)", block, re.DOTALL)
            if not q_match:
                continue

            q_num = int(q_match.group(1))
            q_text = re.sub(r"\s+", " ", q_match.group(2).strip())
            if len(q_text) < 10:
                continue

            options = {}
            for opt in ["A", "B", "C", "D"]:
                opt_pattern = rf"\[{opt}\]\s*(.*?)(?=\s*\[[A-D]\]|\s*Show Answer|Correct Answer|$)"
                opt_match = re.search(opt_pattern, block, re.DOTALL)
                if opt_match:
                    opt_text = re.sub(r"\s+", " ", opt_match.group(1).strip())
                    if opt_text:
                        options[opt] = opt_text

            correct = None
            correct_text = ""
            ans_match = re.search(r"Correct Answer:\s*([A-D])(?:\s*\[([^\]]+)\])?", block)
            if ans_match:
                correct = ans_match.group(1)
                correct_text = ans_match.group(2).strip() if ans_match.group(2) else ""

            explanation = ""
            notes_match = re.search(r"(?:Notes?|Explanation):\s*(.*?)(?=\n\d+\.|$)", block, re.DOTALL)
            if notes_match:
                explanation = re.sub(r"\s+", " ", notes_match.group(1).strip())

            questions.append({
                "number": q_num,
                "question": q_text,
                "options": options,
                "correct": correct,
                "correct_text": correct_text,
                "explanation": explanation
            })

        questions.sort(key=lambda x: x["number"])
        return questions

    def close(self):
        self.session.close()


# ==================== PDF GENERATOR ENGINE ====================
class PDFGenerator:
    def __init__(self, output_dir="output/pdfs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.styles = self._make_styles()

    def _make_styles(self):
        s = getSampleStyleSheet()

        s.add(ParagraphStyle(
            "CoverTitle",
            parent=s["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=32,
            textColor=HexColor(PALETTE["primary"]),
            alignment=TA_CENTER,
            spaceAfter=6,
            leading=38
        ))
        s.add(ParagraphStyle(
            "CoverSub",
            parent=s["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=HexColor(PALETTE["secondary"]),
            alignment=TA_CENTER,
            spaceAfter=18,
            leading=16
        ))
        s.add(ParagraphStyle(
            "CoverMeta",
            parent=s["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=HexColor(PALETTE["muted"]),
            alignment=TA_CENTER,
            spaceAfter=25,
            leading=14
        ))
        s.add(ParagraphStyle(
            "CoverTocHead",
            parent=s["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=HexColor(PALETTE["primary"]),
            alignment=TA_CENTER,
            spaceBefore=10,
            spaceAfter=10,
            leading=14
        ))
        s.add(ParagraphStyle(
            "CoverTocItem",
            parent=s["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            textColor=HexColor(PALETTE["text"]),
            alignment=TA_LEFT,
            leftIndent=40,
            rightIndent=40,
            spaceAfter=5,
            leading=13
        ))

        # Section Headers
        s.add(ParagraphStyle(
            "GKSecHead",
            parent=s["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=HexColor(PALETTE["primary"]),
            spaceBefore=16,
            spaceAfter=8,
            leading=18,
            borderColor=HexColor(PALETTE["secondary"]),
            borderWidth=1.5,
            borderPadding=6,
            borderRadius=3,
            backColor=HexColor(PALETTE["bg_blue"])
        ))
        s.add(ParagraphStyle(
            "QuizSecHead",
            parent=s["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=HexColor(PALETTE["secondary"]),
            spaceBefore=16,
            spaceAfter=8,
            leading=18,
            borderColor=HexColor(PALETTE["border_quiz"]),
            borderWidth=1.5,
            borderPadding=6,
            borderRadius=3,
            backColor=HexColor(PALETTE["bg_quiz"])
        ))

        # Badges & Meta
        s.add(ParagraphStyle(
            "BadgeHighYield",
            parent=s["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            textColor=colors.white,
            backColor=HexColor(PALETTE["accent"]),
            spaceAfter=4,
            spaceBefore=2,
            alignment=TA_CENTER,
            leading=10,
            borderRadius=3
        ))
        s.add(ParagraphStyle(
            "GKArtTitle",
            parent=s["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            textColor=HexColor(PALETTE["primary"]),
            spaceBefore=6,
            spaceAfter=3,
            leading=15
        ))
        s.add(ParagraphStyle(
            "GKMeta",
            parent=s["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            textColor=HexColor(PALETTE["light_gray"]),
            spaceAfter=6,
            leading=10
        ))
        s.add(ParagraphStyle(
            "GKKeyPoints",
            parent=s["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            textColor=HexColor(PALETTE["primary"]),
            backColor=HexColor(PALETTE["bg_blue"]),
            borderColor=HexColor(PALETTE["border_blue"]),
            borderWidth=0.8,
            borderPadding=8,
            spaceAfter=8,
            spaceBefore=3,
            leading=13,
            leftIndent=4,
            rightIndent=4,
            borderRadius=4
        ))
        s.add(ParagraphStyle(
            "GKContent",
            parent=s["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            textColor=HexColor(PALETTE["text"])
        ))

        # Quiz Elements
        s.add(ParagraphStyle(
            "QuizCardHeader",
            parent=s["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=HexColor(PALETTE["primary"]),
            spaceBefore=12,
            spaceAfter=6,
            leading=15,
            backColor=HexColor(PALETTE["bg_quiz"]),
            borderColor=HexColor(PALETTE["border_quiz"]),
            borderWidth=0.8,
            borderPadding=6,
            borderRadius=4
        ))
        s.add(ParagraphStyle(
            "QuizQuestion",
            parent=s["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            textColor=HexColor(PALETTE["text"]),
            spaceBefore=8,
            spaceAfter=4,
            leading=13.5,
            leftIndent=6
        ))
        s.add(ParagraphStyle(
            "QuizOption",
            parent=s["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=HexColor(PALETTE["muted"]),
            spaceAfter=2,
            leading=12,
            leftIndent=18
        ))
        s.add(ParagraphStyle(
            "QuizAnswer",
            parent=s["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            textColor=HexColor(PALETTE["success"]),
            backColor=HexColor(PALETTE["bg_green"]),
            borderColor=HexColor(PALETTE["border_green"]),
            borderWidth=0.6,
            borderPadding=5,
            spaceBefore=3,
            spaceAfter=4,
            leading=11.5,
            leftIndent=10,
            rightIndent=10,
            borderRadius=3
        ))
        s.add(ParagraphStyle(
            "QuizExplanation",
            parent=s["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=HexColor(PALETTE["muted"]),
            spaceAfter=6,
            leading=11.5,
            leftIndent=10,
            rightIndent=10
        ))

        return s

    def generate_combined(self, data, path=None):
        path = path or os.path.join(self.output_dir, f"GKToday_{data['date']}.pdf")
        doc = SimpleDocTemplate(
            path,
            pagesize=A4,
            rightMargin=16 * mm,
            leftMargin=16 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            canvasmaker=NumberedBookmarkCanvas
        )
        doc.section_name = "GK Today Deep Digest"
        doc.display_date = data.get("display_date", "")

        frame = Frame(16 * mm, 18 * mm, A4[0] - 32 * mm, A4[1] - 36 * mm, id="normal")
        template = PageTemplate(id="main", frames=frame)
        doc.addPageTemplates([template])

        story = []
        self._build_cover(story, data)
        self._build_articles(story, data)
        self._build_quizzes(story, data)

        doc.build(story)
        logger.info("Generated Combined PDF: %s", path)
        return path

    def generate_quiz_only(self, data, hide_answers=False, path=None):
        suffix = "_Test" if hide_answers else ""
        path = path or os.path.join(self.output_dir, f"GKToday_Quiz_{data['date']}{suffix}.pdf")
        doc = SimpleDocTemplate(
            path,
            pagesize=A4,
            rightMargin=16 * mm,
            leftMargin=16 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            canvasmaker=NumberedBookmarkCanvas
        )
        doc.section_name = "GK Today Quiz Bank"
        doc.display_date = data.get("display_date", "")

        frame = Frame(16 * mm, 18 * mm, A4[0] - 32 * mm, A4[1] - 36 * mm, id="normal")
        template = PageTemplate(id="main", frames=frame)
        doc.addPageTemplates([template])

        story = []
        # Cover Banner
        story.append(Spacer(1, 30))
        story.append(Paragraph("<b>GK TODAY</b>", self.styles["CoverTitle"]))
        story.append(Paragraph("DAILY CURRENT AFFAIRS QUIZ BANK", self.styles["CoverSub"]))
        total_q = sum(q["question_count"] for q in data.get("quizzes", []))
        story.append(Paragraph(
            f"<b>Date:</b> {data['display_date']}<br/>"
            f"<b>Coverage:</b> {len(data.get('quizzes', []))} Quiz Sets &bull; {total_q} MCQs Total",
            self.styles["CoverMeta"]
        ))
        if hide_answers:
            story.append(Paragraph(
                "<font color='#dc2626'><b>[ TEST MODE: ANSWERS HIDDEN FOR SELF-ASSESSMENT ]</b></font>",
                self.styles["CoverMeta"]
            ))
        story.append(PageBreak())

        self._build_quizzes(story, data, hide_answers=hide_answers)

        # If hide_answers was False, or user wants answer key at end
        doc.build(story)
        logger.info("Generated Quiz PDF: %s (hide_answers=%s)", path, hide_answers)
        return path

    def _build_cover(self, story, data):
        story.append(Spacer(1, 25))
        story.append(Paragraph("<b>GK TODAY</b>", self.styles["CoverTitle"]))
        story.append(Paragraph("CURRENT AFFAIRS DEEP DIGEST", self.styles["CoverSub"]))
        total_q = sum(q["question_count"] for q in data.get("quizzes", []))
        story.append(Paragraph(
            f"<b>Date:</b> {data['display_date']}<br/>"
            f"<b>Includes:</b> {data['total_articles']} Articles &bull; {len(data.get('quizzes', []))} Quiz Sets &bull; {total_q} MCQs",
            self.styles["CoverMeta"]
        ))

        story.append(HRFlowable(width="60%", thickness=1, color=HexColor(PALETTE["border"]), spaceAfter=15, spaceBefore=5))
        story.append(Paragraph("&mdash; TABLE OF CONTENTS &mdash;", self.styles["CoverTocHead"]))

        for sec in data.get("sections", []):
            story.append(Paragraph(
                f"&bull; <b>{sec['title']}</b> &mdash; {sec['article_count']} article(s)",
                self.styles["CoverTocItem"]
            ))
        if data.get("quizzes"):
            story.append(Paragraph(
                f"&bull; <b>Daily Current Affairs Quizzes</b> &mdash; {len(data['quizzes'])} set(s), {total_q} MCQs",
                self.styles["CoverTocItem"]
            ))

        story.append(PageBreak())

    def _build_articles(self, story, data):
        for sec in data.get("sections", []):
            sec_title = f"{sec['title']} ({sec['article_count']})"
            story.append(Paragraph(sanitize_xml(sec_title), self.styles["GKSecHead"]))

            for art in sec["articles"]:
                block = []
                if art.get("relevance", {}).get("level") == "HIGH":
                    block.append(Paragraph("&#9733; UPSC HIGH-YIELD TOPIC", self.styles["BadgeHighYield"]))

                block.append(Paragraph(f"<b>{sanitize_xml(art['title'])}</b>", self.styles["GKArtTitle"]))

                cat_color = CATEGORY_COLORS.get(art.get("category"), PALETTE["muted"])
                meta = (
                    f"<font color='white' backColor='{cat_color}' size='7'>  {art.get('category', 'General').upper()}  </font>"
                    f"<font size='7.5' color='{PALETTE['light_gray']}'>  &bull;  {art.get('date_str', 'N/A')}  &bull;  {art['url'][:55]}...</font>"
                )
                block.append(Paragraph(meta, self.styles["GKMeta"]))

                if art.get("key_points"):
                    kp_items = "<br/>&bull; ".join([""] + [sanitize_xml(p) for p in art["key_points"]])
                    block.append(Paragraph(f"<b>Key Takeaways:</b>{kp_items}", self.styles["GKKeyPoints"]))

                block.append(Paragraph(sanitize_xml(art["content"]), self.styles["GKContent"]))
                block.append(HRFlowable(
                    width="100%", thickness=0.5, color=HexColor(PALETTE["border"]),
                    spaceAfter=8, spaceBefore=4
                ))
                story.append(KeepTogether(block))

    def _build_quizzes(self, story, data, hide_answers=False):
        quizzes = data.get("quizzes", [])
        if not quizzes:
            return

        story.append(PageBreak())
        story.append(Paragraph("DAILY CURRENT AFFAIRS QUIZZES", self.styles["QuizSecHead"]))
        story.append(Spacer(1, 6))

        for quiz in quizzes:
            story.append(Paragraph(
                f"<b>{sanitize_xml(quiz['title'])}</b> &mdash; {quiz['question_count']} MCQs",
                self.styles["QuizCardHeader"]
            ))

            for q in quiz["questions"]:
                block = []
                q_text = f"<b>Q{q['number']}.</b> {sanitize_xml(q['question'])}"
                block.append(Paragraph(q_text, self.styles["QuizQuestion"]))

                for key in ["A", "B", "C", "D"]:
                    if key in q.get("options", {}):
                        block.append(Paragraph(
                            f"<b>[{key}]</b> {sanitize_xml(q['options'][key])}",
                            self.styles["QuizOption"]
                        ))

                if not hide_answers and q.get("correct"):
                    ans_line = f"<b>Correct Answer:</b> [{q['correct']}]"
                    if q.get("correct_text"):
                        ans_line += f" &mdash; {sanitize_xml(q['correct_text'])}"
                    block.append(Paragraph(ans_line, self.styles["QuizAnswer"]))

                if not hide_answers and q.get("explanation"):
                    block.append(Paragraph(
                        f"<b>Explanation:</b> {sanitize_xml(q['explanation'])}",
                        self.styles["QuizExplanation"]
                    ))

                block.append(HRFlowable(
                    width="85%", thickness=0.4, color=HexColor(PALETTE["border"]),
                    spaceAfter=5, spaceBefore=3, hAlign="CENTER"
                ))
                story.append(KeepTogether(block))

            story.append(Spacer(1, 10))


# ==================== TELEGRAM DELIVERY ====================
class TelegramDelivery:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.base = f"https://api.telegram.org/bot{token}"

    def send_message(self, text):
        try:
            r = requests.post(
                f"{self.base}/sendMessage",
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"},
                timeout=30
            )
            result = r.json()
            if not result.get("ok"):
                logger.error("Telegram message failed: %s", result)
                return False
            logger.info("Telegram message delivered.")
            return True
        except Exception as e:
            logger.error("Telegram message error: %s", e)
            return False

    def send_document(self, file_path, caption=""):
        try:
            with open(file_path, "rb") as f:
                r = requests.post(
                    f"{self.base}/sendDocument",
                    files={"document": f},
                    data={"chat_id": self.chat_id, "caption": caption, "parse_mode": "HTML"},
                    timeout=120
                )
            result = r.json()
            if not result.get("ok"):
                logger.error("Telegram document failed: %s", result)
                return False
            logger.info("Telegram document delivered: %s", os.path.basename(file_path))
            return True
        except Exception as e:
            logger.error("Telegram document error: %s", e)
            return False


# ==================== DISCORD WEBHOOK DELIVERY ====================
class DiscordDelivery:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def send_notification(self, data, files=None):
        if not self.webhook_url:
            return False
        try:
            total_q = data.get("total_questions", 0)
            fields = [
                {"name": "Articles Scraped", "value": str(data.get("total_articles", 0)), "inline": True},
                {"name": "Quiz Sets", "value": str(data.get("total_quizzes", 0)), "inline": True},
                {"name": "Total MCQs", "value": str(total_q), "inline": True},
            ]

            embed = {
                "title": f"GKToday Current Affairs Digest ({data['display_date']})",
                "description": "Daily UPSC & General Studies Digest with Articles and Quizzes.",
                "color": 0x1E3A5F,
                "fields": fields,
                "footer": {"text": "GKToday Automated Digest Pipeline"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            payload = {"embeds": [embed]}

            # Send embed message
            r = requests.post(self.webhook_url, json=payload, timeout=30)
            r.raise_for_status()
            logger.info("Discord notification embed sent.")

            # Send files if any
            if files:
                for fpath in files:
                    with open(fpath, "rb") as f:
                        rf = requests.post(
                            self.webhook_url,
                            files={"file": (os.path.basename(fpath), f, "application/pdf")},
                            timeout=120
                        )
                        rf.raise_for_status()
                    logger.info("Discord file uploaded: %s", os.path.basename(fpath))
                    time.sleep(1)

            return True
        except Exception as e:
            logger.error("Discord delivery error: %s", e)
            return False


# ==================== MAIN PIPELINE ====================
class Pipeline:
    def __init__(self, args):
        self.args = args
        self.output_dir = args.output_dir
        self.max_days_old = args.days
        self.quiz_mode = args.mode
        self.hide_answers = args.hide_answers
        self.dry_run = args.dry_run
        self.force = args.force

        self.scraper = GKTodayScraper(max_days_old=self.max_days_old)
        self.quiz_scraper = QuizScraper(max_days_old=self.max_days_old)
        self.generator = PDFGenerator(os.path.join(self.output_dir, "pdfs"))

        # Directories
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "pdfs"), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "data"), exist_ok=True)

        # History
        self.history_file = os.path.join(self.output_dir, "processed.json")
        self.processed = set() if self.force else self._load_history()

        # Delivery Channels
        self.tg = None
        tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        if not args.no_telegram and tg_token and tg_chat:
            self.tg = TelegramDelivery(tg_token, tg_chat)

        self.discord = None
        discord_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
        if not args.no_discord and discord_url:
            self.discord = DiscordDelivery(discord_url)

    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception as e:
                logger.warning("Could not read processed history: %s", e)
                return set()
        return set()

    def _save_history(self):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(list(self.processed), f, indent=2)
        except Exception as e:
            logger.warning("Failed to save history: %s", e)

    def run(self):
        generated_files = []
        try:
            logger.info("=" * 60)
            logger.info("GKToday Pipeline Started | Mode: %s | Days: %d", self.quiz_mode, self.max_days_old)
            logger.info("=" * 60)

            # Phase 1: Article Scraping
            logger.info("[1/4] Scraping Articles...")
            articles = self.scraper.scrape_articles(skip_urls=self.processed)

            # Phase 2: Quiz Scraping
            logger.info("[2/4] Scraping Quizzes...")
            quizzes = self.quiz_scraper.scrape_quizzes(skip_urls=self.processed)

            new_urls = {a["url"] for a in articles} | {q["url"] for q in quizzes}

            if not articles and not quizzes:
                logger.info("No new articles or quizzes found. Everything is up to date.")
                if self.tg:
                    self.tg.send_message("<b>GKToday Scraper:</b> No new articles or quizzes found today.")
                return []

            # Prepare structured dataset
            sections = {}
            for a in articles:
                sections.setdefault(a.get("category", "General"), []).append(a)

            section_list = [
                {"title": cat, "articles": arts, "article_count": len(arts)}
                for cat, arts in sections.items()
            ]
            section_list.sort(key=lambda x: x["article_count"], reverse=True)

            total_q = sum(q["question_count"] for q in quizzes)
            date_key = self.scraper.today.strftime("%Y-%m-%d")
            display_date = self.scraper.today.strftime("%B %d, %Y")

            data = {
                "success": True,
                "date": date_key,
                "display_date": display_date,
                "total_articles": len(articles),
                "sections": section_list,
                "total_quizzes": len(quizzes),
                "total_questions": total_q,
                "quizzes": quizzes,
            }

            # Export structured JSON
            json_file = os.path.join(self.output_dir, "data", f"gktoday_{date_key}.json")
            # Custom JSON serializer for dates
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            logger.info("Structured JSON saved: %s", json_file)

            if self.dry_run or self.quiz_mode == "json-only":
                logger.info("Dry-run/JSON-only completed without PDF generation.")
                return [json_file]

            # Phase 3: PDF Generation
            logger.info("[3/4] Generating PDFs...")
            if self.quiz_mode in ("combined", "both"):
                comb_path = self.generator.generate_combined(data)
                generated_files.append(comb_path)

            if self.quiz_mode in ("separate", "both"):
                quiz_path = self.generator.generate_quiz_only(data, hide_answers=self.hide_answers)
                generated_files.append(quiz_path)
                if not self.hide_answers:
                    # Also create a test-mode copy for self-practice
                    test_path = self.generator.generate_quiz_only(
                        data, hide_answers=True,
                        path=os.path.join(self.generator.output_dir, f"GKToday_Quiz_{date_key}_Test.pdf")
                    )
                    generated_files.append(test_path)

            # Update history
            for u in new_urls:
                self.processed.add(u)
            self._save_history()

            # Phase 4: Delivery
            logger.info("[4/4] Multi-Channel Delivery...")
            if self.tg and generated_files:
                self._deliver_telegram(data, generated_files)
            if self.discord:
                self.discord.send_notification(data, files=generated_files)

            logger.info("=" * 60)
            logger.info("Pipeline Finished Successfully!")
            logger.info("Output Files: %s", [os.path.basename(f) for f in generated_files])
            logger.info("=" * 60)
            return generated_files

        finally:
            self.scraper.close()
            self.quiz_scraper.close()

    def _deliver_telegram(self, data, files):
        total_q = data.get("total_questions", 0)
        msg = (
            f"&#128218; <b>GKToday Deep Digest &bull; {data['display_date']}</b>\n\n"
            f"&#128221; <b>Articles:</b> {data['total_articles']} stories\n"
            f"&#127919; <b>Quizzes:</b> {data['total_quizzes']} sets ({total_q} MCQs)\n"
            f"&#128202; <b>Categories:</b> {len(data['sections'])} domains\n"
        )
        self.tg.send_message(msg)

        for fpath in files:
            fname = os.path.basename(fpath)
            caption = f"&#128196; <b>{fname}</b>"
            if "Test" in fname:
                caption += "\n&#128274; <i>Test Mode &mdash; Answers hidden for practice</i>"
            self.tg.send_document(fpath, caption=caption)
            time.sleep(1)


# ==================== CLI PARSER ====================
def build_cli():
    parser = argparse.ArgumentParser(
        description="GKToday Automated Scraper & Digest Suite",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--days", type=int, default=int(os.environ.get("MAX_DAYS_OLD", "2")),
        help="Number of days back to scrape articles and quizzes."
    )
    parser.add_argument(
        "--mode", choices=["combined", "separate", "both", "json-only"],
        default=os.environ.get("QUIZ_MODE", "both").lower(),
        help="PDF output mode (combined articles+quiz, separate files, both, or json-only)."
    )
    parser.add_argument(
        "--hide-answers", action="store_true",
        default=os.environ.get("HIDE_ANSWERS", "false").lower() == "true",
        help="Hide quiz answers in standard quiz PDF (Test Mode)."
    )
    parser.add_argument(
        "--output-dir", default=os.environ.get("OUTPUT_DIR", "output"),
        help="Directory to save generated PDFs, JSON, and history cache."
    )
    parser.add_argument(
        "--no-telegram", action="store_true",
        help="Disable Telegram delivery even if tokens are set."
    )
    parser.add_argument(
        "--no-discord", action="store_true",
        help="Disable Discord delivery even if webhook is set."
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force re-scraping and ignore processed.json history cache."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Scrape and parse data without creating PDFs or sending messages."
    )
    return parser


if __name__ == "__main__":
    cli = build_cli()
    args = cli.parse_args()
    pipeline = Pipeline(args)
    pipeline.run()

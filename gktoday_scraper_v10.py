#!/usr/bin/env python3
"""
GKToday Scraper v10 (Production-Ready Edition with Quiz Integration)

Features:
  - Full Article Extraction with UPSC Relevance Scoring
  - Daily Current Affairs Quiz Scraping (Q + Options + Answers + Explanations)
  - Date Filtering (Last N Days)
  - Deduplication via processed.json history
  - PRODUCTION-READY PDF Generation (Combined Articles + Quizzes)
  - Optional Separate Quiz-Only PDF with Answer Key Toggle
  - Telegram Delivery with rich captions
  - Retry logic, rate limiting, anti-detection headers

Environment Variables:
  TELEGRAM_TOKEN      - Bot token for Telegram delivery
  TELEGRAM_CHAT_ID    - Target chat/channel ID
  MAX_DAYS_OLD        - How many days back to scrape (default: 2)
  QUIZ_MODE           - "combined" (default) or "separate" or "both"
  HIDE_ANSWERS        - "true" to generate quiz PDF without answers (test mode)
  OUTPUT_DIR          - Output directory (default: output)
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re
import os
import sys
import time
import json
import random
from functools import wraps

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    HRFlowable, PageTemplate, Frame, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas as pdfcanvas

import logging

# ==================== LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ==================== ENVIRONMENT ====================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
MAX_DAYS_OLD = int(os.environ.get("MAX_DAYS_OLD", "2"))
QUIZ_MODE = os.environ.get("QUIZ_MODE", "combined").strip().lower()  # combined | separate | both
HIDE_ANSWERS = os.environ.get("HIDE_ANSWERS", "false").strip().lower() == "true"
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "output")

logger.info("=" * 55)
logger.info("ENVIRONMENT CONFIGURATION")
logger.info("TELEGRAM_TOKEN present: %s | len: %d", bool(TELEGRAM_TOKEN), len(TELEGRAM_TOKEN))
logger.info("TELEGRAM_CHAT_ID present: %s | len: %d", bool(TELEGRAM_CHAT_ID), len(TELEGRAM_CHAT_ID))
logger.info("MAX_DAYS_OLD: %d | QUIZ_MODE: %s | HIDE_ANSWERS: %s", MAX_DAYS_OLD, QUIZ_MODE, HIDE_ANSWERS)
logger.info("=" * 55)

# ==================== PRODUCTION PALETTE ====================
PALETTE = {
    "primary":    "#1e3a5f",
    "secondary":  "#2563eb",
    "accent":     "#dc2626",
    "success":    "#059669",
    "warning":    "#d97706",
    "text":       "#1f2937",
    "muted":      "#6b7280",
    "light_gray": "#94a3b8",
    "border":     "#e5e7eb",
    "bg_blue":    "#f0f9ff",
    "border_blue":"#bae6fd",
    "bg_cover":   "#f8fafc",
    "bg_green":   "#ecfdf5",
    "border_green":"#a7f3d0",
    "bg_quiz":    "#faf5ff",
    "border_quiz":"#e9d5ff",
}

CATEGORY_COLORS = {
    "Economy": "#059669",
    "Science & Technology": "#7c3aed",
    "Environment": "#16a34a",
    "Sports": "#ea580c",
    "Defence": "#dc2626",
    "International": "#2563eb",
    "Awards & Persons": "#db2777",
    "National": "#4f46e5",
    "General": "#6b7280",
    "Quiz": "#7c3aed",
}

# ==================== CONSTANTS ====================
STOP_MARKERS = [
    "Your email address will not be published",
    "Leave a Reply",
    "Cancel reply",
]

JUNK_MARKERS = [
    "Daily MCQs", "Monthly MCQs", "Current Affairs Quiz",
    "Topic Wise CA MCQs", "CA MCQs in Other Languages",
    "SSC/RRB/States Level MCQs", "Current Affairs Monthly 240 MCQs",
    "CA Articles+MCQs", "Previous Months Quiz",
]

JUNK_EXACT = {"Comment*", "Name*", "Email*", "∆", "Home", "", "Submit"}

JUNK_SELECTORS = [
    {"class_": re.compile(r"(sharedaddy|jp-relatedposts|related-post|comment|respond|widget|"
                           r"sidebar|breadcrumb|post-navigation|entry-footer|tags|social|"
                           r"share|menu|navbar|quiz-nav|advertisement|ad-box)", re.I)},
]

CATEGORY_KEYWORDS = {
    "Economy": ["gdp", "economy", "budget", "rbi", "inflation", "fiscal", "trade", "wto", "tax", "scheme", "sebi", "npci", "banking"],
    "Science & Technology": ["isro", "satellite", "exoplanet", "telescope", "research", "spacecraft", "technology", "ai", "artificial intelligence", "drdo", "nuclear", "genome"],
    "Environment": ["climate", "biodiversity", "wildlife", "forest", "conservation", "species", "pollution", "carbon", "renewable"],
    "Sports": ["games", "olympic", "tournament", "championship", "medal", "athletes", "cricket", "world cup"],
    "Defence": ["drdo", "missile", "army", "navy", "air force", "defence", "border", "military", "exercise"],
    "International": ["united nations", "wto", "prime minister", "president", "hamas", "ceasefire", "united kingdom", "parliament", "bilateral", "summit"],
    "Awards & Persons": ["award", "appointed", "minister", "elected", "career", "honour", "padma", "bharat ratna", "nobel"],
    "National": ["government", "ministry", "cabinet", "delhi", "state", "india", "parliament", "lok sabha", "rajya sabha", "supreme court"],
}

# ==================== UTILITIES ====================
def retry(max_retries=3, backoff=2):
    """Decorator for retrying functions with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    sleep_time = backoff ** attempt + random.uniform(0, 1)
                    logger.warning("Retry %d/%d for %s after %.1fs: %s", attempt + 1, max_retries, func.__name__, sleep_time, e)
                    time.sleep(sleep_time)
        return wrapper
    return decorator


def parse_date_flexible(date_str):
    """Parse date string with multiple format fallbacks."""
    if not date_str:
        return None
    date_str = date_str.strip()
    patterns = [
        "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y",
        "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%B %d %Y",
    ]
    for p in patterns:
        try:
            return datetime.strptime(date_str, p).date()
        except ValueError:
            continue
    m = re.search(r"(\d{1,2})[\-/](\d{1,2})[\-/](\d{4})", date_str)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).date()
        except ValueError:
            pass
    return None


# ==================== CUSTOM CANVAS ====================
class BookmarkCanvas(pdfcanvas.Canvas):
    """Canvas with PDF bookmark/outline support."""
    def __init__(self, filename, pagesize=A4, **kwargs):
        super().__init__(filename, pagesize=pagesize, **kwargs)
        self._bookmark_count = 0
        self.section_name = "GK Today Deep Digest"
        self.display_date = ""

    def bookmark_section(self, title, level=0):
        key = f"sec-{self._bookmark_count}"
        self.bookmarkPage(key)
        self.addOutlineEntry(title, key, level=level, closed=(level > 0))
        self._bookmark_count += 1


# ==================== HEADER / FOOTER ====================
def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(HexColor(PALETTE["border"]))
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, A4[1] - 16 * mm, A4[0] - 18 * mm, A4[1] - 16 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(HexColor(PALETTE["light_gray"]))
    canvas.drawString(18 * mm, A4[1] - 14 * mm, getattr(doc, "section_name", "GK Today Deep Digest"))
    if getattr(doc, "display_date", ""):
        canvas.drawRightString(A4[0] - 18 * mm, A4[1] - 14 * mm, doc.display_date)
    canvas.line(18 * mm, 16 * mm, A4[0] - 18 * mm, 16 * mm)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(HexColor(PALETTE["primary"]))
    canvas.drawCentredString(A4[0] / 2, 12 * mm, f"— {doc.page} —")
    canvas.restoreState()


# ==================== ARTICLE SCRAPER ====================
class GKTodayScraper:
    BASE_URL = "https://www.gktoday.in"

    def __init__(self, max_days_old=2):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        ist_offset = timezone(timedelta(hours=5, minutes=30))
        self.today = datetime.now(ist_offset).date()
        self.cutoff_date = self.today - timedelta(days=max_days_old)
        logger.info("Article Scraper initialized. Cutoff: %s", self.cutoff_date)

    @retry(max_retries=3, backoff=2)
    def fetch(self, url):
        r = self.session.get(url, timeout=30)
        r.raise_for_status()
        return r.text

    def scrape_articles(self, skip_urls=None):
        skip_urls = skip_urls or set()
        logger.info("Fetching homepage for article links...")
        html = self.fetch(self.BASE_URL)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        article_links = []
        seen_titles = set()

        headings = soup.find_all(["h3", "h2"])
        for heading in headings:
            link_tag = heading.find("a")
            if not link_tag:
                continue
            title = link_tag.get_text(strip=True)
            url = link_tag.get("href", "")
            if not title or len(title) < 10 or title in seen_titles:
                continue
            if any(s in title.lower() for s in ["gk today", "home", "about", "contact", "quiz", "archives", "mcq"]):
                continue
            seen_titles.add(title)
            if not url.startswith("http"):
                url = self.BASE_URL + url
            if url in skip_urls:
                continue
            article_links.append({"title": title, "url": url})

        logger.info("Found %d new article links to scrape.", len(article_links))

        full_articles = []
        for i, link_data in enumerate(article_links):
            logger.info("[%d/%d] Scraping: %s...", i + 1, len(article_links), link_data["title"][:60])
            time.sleep(random.uniform(1.0, 2.5))

            article_html = self.fetch(link_data["url"])
            if not article_html:
                continue
            parsed = self._parse_article(article_html, link_data["title"], link_data["url"])
            if parsed:
                if parsed["parsed_date"] and parsed["parsed_date"] >= self.cutoff_date:
                    full_articles.append(parsed)
                elif not parsed["parsed_date"]:
                    full_articles.append(parsed)
                else:
                    logger.info("Skipping outdated: %s", parsed["date_str"])

        return full_articles

    @staticmethod
    def _is_junk(text, title):
        if not text or text in JUNK_EXACT:
            return True
        if len(text) > 5000:
            return True
        if text.count("■") > 3:
            return True
        if text.lower().count("mcqs") >= 3:
            return True
        if text.count("General Studies (") >= 3:
            return True
        if any(marker in text for marker in JUNK_MARKERS):
            return True
        squished = text.replace(" ", "")
        if squished.startswith("Home") and title.replace(" ", "") in squished:
            return True
        return False

    def _strip_chrome(self, container):
        for tag in ["script", "style", "nav", "header", "footer", "aside", "iframe", "form"]:
            for t in container.find_all(tag):
                t.decompose()
        for sel in JUNK_SELECTORS:
            for t in container.find_all(attrs={"class": sel["class_"]}):
                t.decompose()
            for t in container.find_all(attrs={"id": sel["class_"]}):
                t.decompose()

    def _find_content_container(self, soup):
        candidates = [
            soup.find(attrs={"itemprop": "articleBody"}),
            soup.find("div", class_="entry-content"),
            soup.find("article"),
        ]
        for c in candidates:
            if c is not None:
                return c
        return soup.find("div", class_=lambda c: c and ("content" in c.lower() or "entry" in c.lower())) or soup.find("body")

    def _parse_article(self, html, title, url):
        soup = BeautifulSoup(html, "html.parser")

        date_str = ""
        parsed_date = None
        meta_div = soup.find("div", class_="entry-meta")
        if meta_div:
            meta_text = meta_div.get_text(separator=" ", strip=True)
            date_match = re.search(r"([A-Z][a-z]+ \d{1,2},? \d{4})", meta_text)
            if date_match:
                date_str = date_match.group(1)
                parsed_date = parse_date_flexible(date_str)

        main_content = self._find_content_container(soup)
        if main_content is None:
            return None

        self._strip_chrome(main_content)

        elements = main_content.find_all(["p", "ul", "h4", "h3"])
        texts = []
        for el in elements:
            txt = el.get_text(strip=True)
            if not txt:
                continue
            if any(marker in txt for marker in STOP_MARKERS):
                break
            if txt == title:
                continue
            if self._is_junk(txt, title):
                continue
            texts.append(txt)

        full_content = "\n\n".join(texts).strip()
        full_content = re.sub(r"\n{3,}", "\n\n", full_content)

        if not full_content or len(full_content) < 100:
            return None

        return {
            "title": title,
            "url": url,
            "date_str": date_str,
            "parsed_date": parsed_date,
            "category": self._infer_category(full_content),
            "content": full_content,
            "key_points": self._key_points(full_content),
            "relevance": self._relevance(title + " " + full_content)
        }

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
        indicators = ["first", "largest", "launched", "approved", "appointed", "signed",
                      "budget", "gdp", "supreme court", "isro", "only", "biggest", "highest",
                      "new", "introduced", "passed", "unveiled", "inaugurated"]
        for s in re.split(r"(?<=[.!?])\s+", flat_text):
            if sum(1 for ind in indicators if ind in s.lower()) >= 1 and 30 < len(s) < 300:
                pts.append(s.strip())
        return pts[:5]

    def _relevance(self, text):
        t = text.lower()
        high = ["constitution", "parliament", "supreme court", "scheme", "yojana",
                "gdp", "rbi", "climate", "environment", "isro", "drdo", "minister",
                "cabinet", "policy", "amendment", "bill", "act"]
        hs = sum(1 for k in high if k in t)
        level = "HIGH" if hs >= 2 else "MEDIUM" if hs == 1 else "LOW"
        matched = [k for k in high if k in t][:3]
        return {"level": level, "matched_keywords": matched}

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
            "Accept-Language": "en-US,en;q=0.5",
            "DNT": "1",
            "Connection": "keep-alive",
        })
        ist_offset = timezone(timedelta(hours=5, minutes=30))
        self.today = datetime.now(ist_offset).date()
        self.cutoff_date = self.today - timedelta(days=max_days_old)
        logger.info("Quiz Scraper initialized. Cutoff: %s", self.cutoff_date)

    @retry(max_retries=3, backoff=2)
    def fetch(self, url):
        r = self.session.get(url, timeout=30)
        r.raise_for_status()
        return r.text

    def scrape_quizzes(self, skip_urls=None):
        skip_urls = skip_urls or set()
        logger.info("Fetching quiz listing page...")
        try:
            html = self.fetch(self.QUIZ_LISTING_URL)
        except Exception as e:
            logger.error("Failed to fetch quiz listing: %s", e)
            return []

        quiz_links = self._extract_quiz_links(html)
        logger.info("Found %d quiz entries within date range.", len(quiz_links))

        all_quizzes = []
        for i, link in enumerate(quiz_links):
            if link["url"] in skip_urls:
                logger.info("Skipping already processed quiz: %s", link["title"])
                continue
            logger.info("[%d/%d] Scraping quiz: %s", i + 1, len(quiz_links), link["title"])
            time.sleep(random.uniform(1.5, 3.0))

            try:
                page_html = self.fetch(link["url"])
                questions = self._parse_quiz_page(page_html)
                if questions:
                    all_quizzes.append({
                        "title": link["title"],
                        "date": link["date"].strftime("%B %d, %Y") if link["date"] else "N/A",
                        "url": link["url"],
                        "question_count": len(questions),
                        "questions": questions
                    })
                    logger.info("  -> Extracted %d questions", len(questions))
                else:
                    logger.warning("  -> No questions extracted from %s", link["url"])
            except Exception as e:
                logger.error("  -> Failed: %s", e)

        return all_quizzes

    def _extract_quiz_links(self, html):
        soup = BeautifulSoup(html, "html.parser")
        links = []
        seen = set()

        for heading in soup.find_all(["h3", "h2"]):
            link_tag = heading.find("a")
            if not link_tag:
                continue
            title = link_tag.get_text(strip=True)
            href = link_tag.get("href", "")

            if "Daily Current Affairs Quiz" not in title:
                continue

            date_match = re.search(r"([A-Z][a-z]+ \d{1,2},? \d{4})", title)
            quiz_date = None
            if date_match:
                quiz_date = parse_date_flexible(date_match.group(1))

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
        content = self._find_content_container(soup)
        if not content:
            return []

        for tag in ["script", "style", "nav", "aside", "iframe", "form", "header", "footer"]:
            for t in content.find_all(tag):
                t.decompose()

        all_text = content.get_text("\n", strip=True)
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
            q_text = q_match.group(2).strip()
            q_text = re.sub(r"\s+", " ", q_text)

            if len(q_text) < 10:
                continue

            options = {}
            for opt in ["A", "B", "C", "D"]:
                opt_pattern = rf"\[{opt}\]\s*(.*?)(?=\s*\[[A-D]\]|\s*Show Answer|Correct Answer|$)"
                opt_match = re.search(opt_pattern, block, re.DOTALL)
                if opt_match:
                    opt_text = opt_match.group(1).strip()
                    opt_text = re.sub(r"\s+", " ", opt_text)
                    if opt_text:
                        options[opt] = opt_text

            if len(options) < 2:
                continue

            correct = None
            correct_text = ""
            ans_match = re.search(r"Correct Answer:\s*([A-D])(?:\s*\[([^\]]+)\])?", block)
            if ans_match:
                correct = ans_match.group(1)
                correct_text = ans_match.group(2).strip() if ans_match.group(2) else ""

            explanation = ""
            notes_patterns = [
                r"Notes?:\s*(.*?)(?=\n\d+\.|$)",
                r"Explanation:?\s*(.*?)(?=\n\d+\.|$)",
            ]
            for pattern in notes_patterns:
                notes_match = re.search(pattern, block, re.DOTALL)
                if notes_match:
                    explanation = notes_match.group(1).strip()
                    explanation = re.sub(r"\s+", " ", explanation)
                    if len(explanation) > 10:
                        break

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

    def _find_content_container(self, soup):
        candidates = [
            soup.find(attrs={"itemprop": "articleBody"}),
            soup.find("div", class_="entry-content"),
            soup.find("article"),
            soup.find("div", class_=lambda c: c and "content" in c.lower()),
        ]
        for c in candidates:
            if c is not None:
                return c
        return soup.find("body")

    def close(self):
        self.session.close()


# ==================== PDF GENERATOR ====================
class PDFGenerator:
    def __init__(self, output_dir="output/pdfs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.styles = self._make_styles()

    def _make_styles(self):
        s = getSampleStyleSheet()

        s.add(ParagraphStyle("CoverTitle",
            parent=s["Heading1"], fontSize=36, textColor=HexColor(PALETTE["primary"]),
            alignment=TA_CENTER, spaceAfter=8, leading=42))
        s.add(ParagraphStyle("CoverSub",
            parent=s["Normal"], fontSize=14, textColor=HexColor(PALETTE["muted"]),
            alignment=TA_CENTER, spaceAfter=30, leading=18))
        s.add(ParagraphStyle("CoverMeta",
            parent=s["Normal"], fontSize=11, textColor=HexColor(PALETTE["light_gray"]),
            alignment=TA_CENTER, spaceAfter=50, leading=14))
        s.add(ParagraphStyle("CoverToc",
            parent=s["Normal"], fontSize=10, textColor=HexColor(PALETTE["text"]),
            alignment=TA_CENTER, spaceAfter=6, leading=14))

        s.add(ParagraphStyle("GKSecHead",
            parent=s["Heading2"], fontSize=16, textColor=HexColor(PALETTE["primary"]),
            spaceBefore=20, spaceAfter=12, leading=20,
            borderColor=HexColor(PALETTE["secondary"]), borderWidth=2,
            borderPadding=5, leftIndent=0, borderRadius=3))

        s.add(ParagraphStyle("QuizSecHead",
            parent=s["Heading2"], fontSize=16, textColor=HexColor(PALETTE["secondary"]),
            spaceBefore=20, spaceAfter=12, leading=20,
            borderColor=HexColor(PALETTE["secondary"]), borderWidth=2,
            borderPadding=5, leftIndent=0, borderRadius=3))

        s.add(ParagraphStyle("GKBadgeH",
            parent=s["Normal"], fontSize=7, textColor=colors.white,
            backColor=HexColor(PALETTE["accent"]), spaceAfter=6, spaceBefore=4,
            alignment=TA_CENTER, leading=10, borderRadius=4))

        s.add(ParagraphStyle("GKArtTitle",
            parent=s["Heading3"], fontSize=12, textColor=HexColor(PALETTE["primary"]),
            spaceBefore=8, spaceAfter=4, leading=16))
        s.add(ParagraphStyle("GKMeta",
            parent=s["Normal"], fontSize=7, textColor=HexColor(PALETTE["light_gray"]),
            spaceAfter=6, leading=10))
        s.add(ParagraphStyle("GKKeyPoints",
            parent=s["Normal"], fontSize=9, textColor=HexColor(PALETTE["primary"]),
            backColor=HexColor(PALETTE["bg_blue"]), borderColor=HexColor(PALETTE["border_blue"]),
            borderWidth=1, borderPadding=10, spaceAfter=10, spaceBefore=4,
            leading=14, leftIndent=5, rightIndent=5, borderRadius=6))
        s.add(ParagraphStyle("GKContent",
            parent=s["Normal"], fontSize=10, leading=15, alignment=TA_JUSTIFY,
            spaceAfter=8, textColor=HexColor(PALETTE["text"])))

        s.add(ParagraphStyle("QuizHeader",
            parent=s["Heading3"], fontSize=13, textColor=HexColor(PALETTE["primary"]),
            spaceBefore=14, spaceAfter=6, leading=17,
            backColor=HexColor(PALETTE["bg_quiz"]),
            borderColor=HexColor(PALETTE["border_quiz"]),
            borderWidth=1, borderPadding=6, leftIndent=0, borderRadius=4))

        s.add(ParagraphStyle("QuizQuestion",
            parent=s["Normal"], fontSize=10, textColor=HexColor(PALETTE["text"]),
            spaceBefore=10, spaceAfter=3, leading=14, leftIndent=8))

        s.add(ParagraphStyle("QuizOption",
            parent=s["Normal"], fontSize=9, textColor=HexColor(PALETTE["muted"]),
            spaceAfter=1, leading=12, leftIndent=22))

        s.add(ParagraphStyle("QuizAnswer",
            parent=s["Normal"], fontSize=9, textColor=HexColor(PALETTE["success"]),
            backColor=HexColor(PALETTE["bg_green"]),
            borderColor=HexColor(PALETTE["border_green"]),
            borderWidth=0.5, borderPadding=6, spaceAfter=6, leading=12,
            leftIndent=10, rightIndent=10, borderRadius=4))

        s.add(ParagraphStyle("QuizExplanation",
            parent=s["Normal"], fontSize=8, textColor=HexColor(PALETTE["muted"]),
            spaceAfter=8, leading=12, leftIndent=10, rightIndent=10))

        return s

    def _clean(self, text):
        text = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return text.replace("\n\n", "<br/><br/>").replace("\n", " ")

    def generate_combined(self, data, path=None):
        path = path or os.path.join(self.output_dir, f"GKToday_{data['date']}.pdf")
        doc = SimpleDocTemplate(
            path, pagesize=A4,
            rightMargin=18 * mm, leftMargin=18 * mm,
            topMargin=18 * mm, bottomMargin=18 * mm,
            canvasmaker=BookmarkCanvas
        )
        doc.section_name = "GK Today Deep Digest"
        doc.display_date = data.get("display_date", "")

        frame = Frame(18 * mm, 18 * mm, A4[0] - 36 * mm, A4[1] - 36 * mm, id="normal")
        template = PageTemplate(id="main", frames=frame, onPage=header_footer)
        doc.addPageTemplates([template])

        story = []
        self._build_cover(story, data)
        self._build_articles(story, data)
        self._build_quizzes(story, data)

        doc.build(story)
        logger.info("Combined PDF generated: %s", path)
        return path

    def generate_quiz_only(self, data, hide_answers=False, path=None):
        path = path or os.path.join(self.output_dir, f"GKToday_Quiz_{data['date']}.pdf")
        doc = SimpleDocTemplate(
            path, pagesize=A4,
            rightMargin=18 * mm, leftMargin=18 * mm,
            topMargin=18 * mm, bottomMargin=18 * mm,
            canvasmaker=BookmarkCanvas
        )
        doc.section_name = "GK Today Quiz Bank"
        doc.display_date = data.get("display_date", "")

        frame = Frame(18 * mm, 18 * mm, A4[0] - 36 * mm, A4[1] - 36 * mm, id="normal")
        template = PageTemplate(id="main", frames=frame, onPage=header_footer)
        doc.addPageTemplates([template])

        story = []
        story.append(Spacer(1, 50))
        story.append(Paragraph("<b>GK TODAY</b>", self.styles["CoverTitle"]))
        story.append(Paragraph("DAILY QUIZ BANK", self.styles["CoverSub"]))
        total_q = sum(q["question_count"] for q in data.get("quizzes", []))
        story.append(Paragraph(
            f"{data['display_date']}<br/>{len(data.get('quizzes', []))} Quizzes &bull; {total_q} MCQs",
            self.styles["CoverMeta"]))
        if hide_answers:
            story.append(Paragraph(
                "<font color='#dc2626'><b>TEST MODE</b></font> &mdash; Answers hidden for self-assessment",
                self.styles["CoverMeta"]))
        story.append(PageBreak())

        self._build_quizzes(story, data, hide_answers=hide_answers)

        doc.build(story)
        logger.info("Quiz PDF generated: %s (answers hidden=%s)", path, hide_answers)
        return path

    def _build_cover(self, story, data):
        story.append(Spacer(1, 40))
        story.append(Paragraph("<b>GK TODAY</b>", self.styles["CoverTitle"]))
        story.append(Paragraph("DEEP DIGEST", self.styles["CoverSub"]))
        total_q = sum(q["question_count"] for q in data.get("quizzes", []))
        story.append(Paragraph(
            f"{data['display_date']}<br/>"
            f"{data['total_articles']} Articles &bull; {len(data.get('quizzes', []))} Quizzes &bull; {total_q} MCQs",
            self.styles["CoverMeta"]))

        story.append(Paragraph("&mdash; CONTENTS &mdash;", self.styles["CoverSub"]))
        for sec in data.get("sections", []):
            story.append(Paragraph(
                f"&bull; {sec['title']} ({sec['article_count']} articles)",
                self.styles["CoverToc"]))
        if data.get("quizzes"):
            story.append(Paragraph(
                f"&bull; Daily Quizzes ({len(data['quizzes'])} sets, {total_q} MCQs)",
                self.styles["CoverToc"]))
        story.append(PageBreak())

    def _build_articles(self, story, data):
        for sec in data.get("sections", []):
            sec_title = f"{sec['title']} ({sec['article_count']})"
            story.append(Paragraph(sec_title, self.styles["GKSecHead"]))

            for art in sec["articles"]:
                block = []
                if art["relevance"]["level"] == "HIGH":
                    block.append(Paragraph("&#9733; HIGH YIELD", self.styles["GKBadgeH"]))

                block.append(Paragraph(f"<b>{self._clean(art['title'])}</b>", self.styles["GKArtTitle"]))

                cat_color = CATEGORY_COLORS.get(art["category"], PALETTE["muted"])
                meta = (
                    f"<font color='white' backColor='{cat_color}' size='7'>  {art['category'].upper()}  </font>"
                    f"<font size='7' color='{PALETTE['light_gray']}'>  &bull;  {art.get('date_str', 'N/A')}  &bull;  {art['url'][:55]}...</font>"
                )
                block.append(Paragraph(meta, self.styles["GKMeta"]))

                if art.get("key_points"):
                    kp = "<br/>&bull; ".join([""] + art["key_points"])
                    block.append(Paragraph(f"<b>&#127919; Key Points:</b>{kp}", self.styles["GKKeyPoints"]))

                block.append(Paragraph(self._clean(art["content"]), self.styles["GKContent"]))
                block.append(HRFlowable(width="100%", thickness=0.5, color=HexColor(PALETTE["border"]),
                                        spaceAfter=10, spaceBefore=6))
                story.append(KeepTogether(block))

    def _build_quizzes(self, story, data, hide_answers=False):
        quizzes = data.get("quizzes", [])
        if not quizzes:
            return

        story.append(PageBreak())
        story.append(Paragraph("&#128221; DAILY CURRENT AFFAIRS QUIZ", self.styles["QuizSecHead"]))
        story.append(Spacer(1, 8))

        for quiz in quizzes:
            story.append(Paragraph(
                f"<b>{self._clean(quiz['title'])}</b> ({quiz['question_count']} MCQs)",
                self.styles["QuizHeader"]))

            for q in quiz["questions"]:
                block = []
                q_text = f"<b>{q['number']}.</b> {self._clean(q['question'])}"
                block.append(Paragraph(q_text, self.styles["QuizQuestion"]))

                for key in ["A", "B", "C", "D"]:
                    if key in q["options"]:
                        block.append(Paragraph(f"[{key}] {self._clean(q['options'][key])}", self.styles["QuizOption"]))

                if not hide_answers and q.get("correct"):
                    ans_line = f"<b>Correct Answer:</b> [{q['correct']}]"
                    if q.get("correct_text"):
                        ans_line += f" &mdash; {self._clean(q['correct_text'])}"
                    block.append(Paragraph(ans_line, self.styles["QuizAnswer"]))

                if not hide_answers and q.get("explanation"):
                    block.append(Paragraph(f"&#128161; {self._clean(q['explanation'])}", self.styles["QuizExplanation"]))

                block.append(HRFlowable(width="80%", thickness=0.3, color=HexColor(PALETTE["border"]),
                                        spaceAfter=6, spaceBefore=4, hAlign="CENTER"))
                story.append(KeepTogether(block))

            story.append(Spacer(1, 12))


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
            else:
                logger.info("Telegram message sent.")
            return result.get("ok")
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
            else:
                logger.info("Telegram document sent.")
            return result.get("ok")
        except Exception as e:
            logger.error("Telegram document error: %s", e)
            return False


# ==================== PIPELINE ====================
class Pipeline:
    def __init__(self, output_dir=OUTPUT_DIR, telegram_token=None, telegram_chat_id=None):
        self.scraper = GKTodayScraper(max_days_old=MAX_DAYS_OLD)
        self.quiz_scraper = QuizScraper(max_days_old=MAX_DAYS_OLD)
        self.generator = PDFGenerator(os.path.join(output_dir, "pdfs"))
        self.output_dir = output_dir
        self.tg = None
        if telegram_token and telegram_chat_id:
            self.tg = TelegramDelivery(telegram_token, telegram_chat_id)

        self.history_file = os.path.join(output_dir, "processed.json")
        self.processed = self._load_history()
        os.makedirs(output_dir, exist_ok=True)

    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception:
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
            logger.info("=" * 55)
            logger.info("PHASE 1: ARTICLE SCRAPING")
            logger.info("=" * 55)
            articles = self.scraper.scrape_articles(skip_urls=self.processed)

            logger.info("=" * 55)
            logger.info("PHASE 2: QUIZ SCRAPING")
            logger.info("=" * 55)
            quizzes = self.quiz_scraper.scrape_quizzes(skip_urls=self.processed)

            new_urls = set()
            for art in articles:
                new_urls.add(art["url"])
            for qz in quizzes:
                new_urls.add(qz["url"])

            if not articles and not quizzes:
                logger.info("No new content found. Exiting.")
                self._send_status("&#128229; No new articles or quizzes found today.")
                return []

            sections = {}
            for a in articles:
                sections.setdefault(a.get("category", "General"), []).append(a)
            section_list = [{"title": cat, "articles": arts, "article_count": len(arts)}
                            for cat, arts in sections.items()]
            section_list.sort(key=lambda x: x["article_count"], reverse=True)

            total_q = sum(q["question_count"] for q in quizzes)
            data = {
                "success": True,
                "date": self.scraper.today.strftime("%Y-%m-%d"),
                "display_date": self.scraper.today.strftime("%B %d, %Y"),
                "sections": section_list,
                "total_articles": len(articles),
                "quizzes": quizzes,
                "total_quizzes": len(quizzes),
                "total_questions": total_q,
            }

            logger.info("=" * 55)
            logger.info("PHASE 3: PDF GENERATION")
            logger.info("=" * 55)

            if QUIZ_MODE in ("combined", "both"):
                combined_path = self.generator.generate_combined(data)
                generated_files.append(combined_path)

            if QUIZ_MODE in ("separate", "both"):
                quiz_path = self.generator.generate_quiz_only(data, hide_answers=HIDE_ANSWERS)
                generated_files.append(quiz_path)
                if not HIDE_ANSWERS:
                    quiz_ans_path = self.generator.generate_quiz_only(
                        data, hide_answers=False,
                        path=os.path.join(self.generator.output_dir, f"GKToday_Quiz_{data['date']}_Answers.pdf")
                    )
                    generated_files.append(quiz_ans_path)

            for url in new_urls:
                self.processed.add(url)
            self._save_history()

            if self.tg:
                logger.info("=" * 55)
                logger.info("PHASE 4: TELEGRAM DELIVERY")
                logger.info("=" * 55)
                self._deliver_telegram(data, generated_files)
            else:
                logger.warning("Telegram credentials not provided. PDFs saved locally only.")

            logger.info("=" * 55)
            logger.info("PIPELINE COMPLETE")
            logger.info("Files: %s", generated_files)
            logger.info("=" * 55)
            return generated_files

        finally:
            self.scraper.close()
            self.quiz_scraper.close()

    def _deliver_telegram(self, data, files):
        total_q = data.get("total_questions", 0)
        msg = (
            f"&#128218; <b>GKToday Deep Digest: {data['display_date']}</b>\n\n"
            f"&#128221; <b>Articles:</b> {data['total_articles']}\n"
            f"&#127919; <b>Quizzes:</b> {data['total_quizzes']} sets\n"
            f"&#10067; <b>MCQs:</b> {total_q}\n"
        )
        self.tg.send_message(msg)

        for fpath in files:
            fname = os.path.basename(fpath)
            caption = f"&#128196; <b>{fname}</b>"
            if "Quiz" in fname and HIDE_ANSWERS:
                caption += "\n&#128274; <i>Test mode &mdash; answers hidden</i>"
            self.tg.send_document(fpath, caption=caption)
            time.sleep(1)

    def _send_status(self, msg):
        if self.tg:
            self.tg.send_message(msg)


# ==================== MAIN ====================
if __name__ == "__main__":
    p = Pipeline(
        output_dir=OUTPUT_DIR,
        telegram_token=TELEGRAM_TOKEN,
        telegram_chat_id=TELEGRAM_CHAT_ID
    )
    p.run()

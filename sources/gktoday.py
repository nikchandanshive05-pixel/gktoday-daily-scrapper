"""
GKToday Scraper for Daily Current Affairs & Quiz MCQs.
Preserves high-accuracy DOM-based MCQ and article extraction.
"""
import re
import time
import random
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Set, Dict, Any

import requests
from bs4 import BeautifulSoup

from core.base_scraper import BaseScraper
from core.models import Article, QuizQuestion

logger = logging.getLogger("gktoday")

STOP_MARKERS = [
    "Month-wise Current Affairs",
    "Category-wise Current Affairs",
    "Latest Current Affairs Updates",
    "About GKToday",
    "Comment Navigation",
    "Leave a Reply",
    "Recent Current Affairs Questions",
    "Related Articles",
]

JUNK_MARKERS = [
    "advertisement", "click here", "subscribe to our telegram",
    "download mobile app", "follow us on twitter", "join our whatsapp",
    "share this post", "affairscloud", "all rights reserved",
    "wp_quiz_question", "wp_basic_quiz_answer", "wp_quiz_question_options",
    "category-wise current affairs", "month-wise current affairs"
]

JUNK_EXACT = {
    "GKToday", "Current Affairs", "General Knowledge Today",
    "Navigation", "Menu", "Home", "Share", "Tags:", "Categories:",
    "Leave a Reply", "Post Navigation", "Recent Posts"
}

UNICODE_REPLACEMENTS = [
    ("\u20b9", "Rs. "),
    ("\u2013", "-"),
    ("\u2014", "-"),
    ("\u2018", "'"),
    ("\u2019", "'"),
    ("\u201c", '"'),
    ("\u201d", '"'),
    ("\u2026", "..."),
    ("\u00a0", " "),
    ("\u2022", "*"),
    ("\u25aa", "*"),
    ("\u25cf", "*"),
    ("\u25fe", "*"),
    ("\u200b", ""),
    ("\ufeff", ""),
]


def sanitize_text(text: str) -> str:
    if not text:
        return ""
    for char, rep in UNICODE_REPLACEMENTS:
        text = text.replace(char, rep)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()


def parse_date_flexible(date_str: str) -> Optional[datetime.date]:
    if not date_str:
        return None
    date_str = date_str.strip()

    range_match = re.search(r"([A-Za-z]+)\s+(\d{1,2})\s*[-–—]\s*(\d{1,2}),?\s*(\d{4})", date_str)
    if range_match:
        month, d1, d2, year = range_match.groups()
        try:
            return datetime.strptime(f"{month} {d2}, {year}", "%B %d, %Y").date()
        except ValueError:
            pass

    patterns = [
        "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y",
        "%B %d %Y", "%b %d %Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"
    ]
    clean_str = re.sub(r"[,\.]+$", "", date_str)
    for p in patterns:
        try:
            return datetime.strptime(clean_str, p).date()
        except ValueError:
            continue

    m = re.search(r"([A-Za-z]+ \d{1,2},? \d{4})", date_str)
    if m:
        for p in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"):
            try:
                return datetime.strptime(m.group(1).replace(",", ""), p.replace(",", "")).date()
            except ValueError:
                continue

    return None


class GKTodayScraper(BaseScraper):
    """Scraper for GKToday daily one-liners and current affairs quizzes."""

    BASE_URL = "https://www.gktoday.in"
    QUIZ_LISTING_URL = "https://www.gktoday.in/gk-current-affairs-quiz-questions-answers/"

    def __init__(self):
        super().__init__(name="GKToday", source_id="gktoday")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def fetch_articles(self, days: int = 2) -> List[Article]:
        ist_offset = timezone(timedelta(hours=5, minutes=30))
        today = datetime.now(ist_offset).date()
        cutoff_date = today - timedelta(days=days)

        logger.info(f"Fetching GKToday articles (Cutoff: {cutoff_date})...")
        try:
            r = self.session.get(self.BASE_URL, timeout=25)
            r.raise_for_status()
            html = r.text
        except Exception as e:
            logger.error(f"Failed to fetch GKToday homepage: {e}")
            return []

        soup = BeautifulSoup(html, "html.parser")
        article_links = []
        seen = set()

        for heading in soup.find_all(["h2", "h3"]):
            link_tag = heading.find("a")
            if not link_tag:
                continue
            title = sanitize_text(link_tag.get_text(strip=True))
            url = link_tag.get("href", "").strip()
            if not title or len(title) < 10 or not url:
                continue

            if any(s in title.lower() for s in ["quiz", "archives", "mcq", "target", "upsc prelims test"]):
                continue

            if not url.startswith("http"):
                url = self.BASE_URL + url

            if url in seen:
                continue
            seen.add(url)
            article_links.append((title, url))

        articles: List[Article] = []
        for i, (title, url) in enumerate(article_links[:15]):
            time.sleep(random.uniform(0.5, 1.2))
            try:
                resp = self.session.get(url, timeout=25)
                if resp.status_code != 200:
                    continue
                parsed = self._parse_article(resp.text, title, url, cutoff_date)
                if parsed:
                    articles.append(parsed)
            except Exception as e:
                logger.warning(f"Error scraping GKToday article {url}: {e}")

        logger.info(f"GKToday Scraper extracted {len(articles)} articles.")
        return articles

    def fetch_quizzes(self, days: int = 2) -> List[QuizQuestion]:
        ist_offset = timezone(timedelta(hours=5, minutes=30))
        today = datetime.now(ist_offset).date()
        cutoff_date = today - timedelta(days=days)

        logger.info(f"Fetching GKToday quiz listing (Cutoff: {cutoff_date})...")
        try:
            resp = self.session.get(self.QUIZ_LISTING_URL, timeout=25)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            logger.error(f"Failed to fetch GKToday quiz listing: {e}")
            return []

        soup = BeautifulSoup(html, "html.parser")
        quiz_pages = []
        seen = set()

        for heading in soup.find_all(["h2", "h3"]):
            link_tag = heading.find("a")
            if not link_tag:
                continue
            title = sanitize_text(link_tag.get_text(strip=True))
            href = link_tag.get("href", "").strip()

            if "Current Affairs Quiz" not in title or not href:
                continue

            q_date = parse_date_flexible(title)
            if q_date and q_date < cutoff_date:
                continue

            url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
            if url in seen:
                continue
            seen.add(url)
            quiz_pages.append((title, url, q_date))

        all_questions: List[QuizQuestion] = []
        for title, url, q_date in quiz_pages[:3]:
            time.sleep(random.uniform(0.8, 1.5))
            try:
                r = self.session.get(url, timeout=25)
                if r.status_code != 200:
                    continue
                qs = self._parse_quiz_page(r.text, url, q_date)
                all_questions.extend(qs)
            except Exception as e:
                logger.error(f"Error scraping quiz {url}: {e}")

        logger.info(f"GKToday Scraper extracted {len(all_questions)} quiz MCQs.")
        return all_questions

    def _parse_article(self, html: str, title: str, url: str, cutoff_date: datetime.date) -> Optional[Article]:
        soup = BeautifulSoup(html, "html.parser")

        # Date extraction
        date_str = ""
        parsed_date = None
        update_notice = soup.find("div", class_="post-update-notice")
        if update_notice:
            m = re.search(r"(?:written on|published on|modified on)\s*([A-Z][a-z]+ \d{1,2},? \d{4})", update_notice.get_text(), re.I)
            if m:
                date_str = m.group(1)
                parsed_date = parse_date_flexible(date_str)

        if not parsed_date:
            for meta_sel in ["entry-meta", "post-meta", "post-info"]:
                meta_div = soup.find("div", class_=meta_sel)
                if meta_div:
                    m = re.search(r"([A-Z][a-z]+ \d{1,2},? \d{4})", meta_div.get_text())
                    if m:
                        date_str = m.group(1)
                        parsed_date = parse_date_flexible(date_str)
                        break

        if parsed_date and parsed_date < cutoff_date:
            return None

        # Content container
        container = (
            soup.find("div", class_="content-area")
            or soup.find("div", class_="main_content")
            or soup.find(attrs={"itemprop": "articleBody"})
            or soup.find("div", class_="entry-content")
            or soup.find("article")
        )
        if not container:
            return None

        for t in container.find_all(["script", "style", "nav", "aside", "form"]):
            t.decompose()

        elements = container.find_all(["p", "ul", "ol", "h4", "h3"])
        texts = []
        for el in elements:
            txt = sanitize_text(el.get_text(" ", strip=True))
            if not txt or any(stop in txt for stop in STOP_MARKERS):
                break
            if txt == title or len(txt) > 6000:
                continue
            texts.append(txt)

        body = "\n\n".join(texts).strip()
        if len(body) < 100:
            return None

        final_date = parsed_date.strftime("%Y-%m-%d") if parsed_date else datetime.now().strftime("%Y-%m-%d")
        return Article(
            title=title,
            url=url,
            source="GKToday",
            published_date=final_date,
            full_text=body,
            language="en",
            author="GKToday Team",
            category="Current Affairs",
            gs_paper="GS-2",
        )

    def _parse_quiz_page(self, html: str, url: str, q_date: Optional[datetime.date]) -> List[QuizQuestion]:
        soup = BeautifulSoup(html, "html.parser")
        q_divs = soup.find_all("div", class_="wp_quiz_question")
        questions: List[QuizQuestion] = []
        date_str = q_date.strftime("%Y-%m-%d") if q_date else datetime.now().strftime("%Y-%m-%d")

        for i, q_div in enumerate(q_divs):
            parent = q_div.parent or q_div
            raw_q = sanitize_text(q_div.get_text(" ", strip=True))
            m_num = re.match(r"^(\d+)\.\s*(.*)$", raw_q)
            q_num = int(m_num.group(1)) if m_num else i + 1
            q_text = m_num.group(2).strip() if m_num else raw_q

            # Options
            options = {}
            opt_div = parent.find("div", class_="wp_quiz_question_options")
            if opt_div:
                for line in sanitize_text(opt_div.get_text("\n", strip=True)).split("\n"):
                    m_opt = re.match(r"^\[?([A-D])\]?\s*(.*)$", line.strip())
                    if m_opt:
                        options[m_opt.group(1)] = m_opt.group(2).strip()

            # Answer & Notes
            ans_div = parent.find("div", class_="wp_basic_quiz_answer") or parent.find("div", class_=lambda c: c and "ques_answer" in c)
            correct = None
            explanation = ""
            if ans_div:
                ans_raw = sanitize_text(ans_div.get_text("\n", strip=True))
                m_ans = re.search(r"Correct Answer:\s*([A-D])", ans_raw)
                if m_ans:
                    correct = m_ans.group(1)
                m_exp = re.search(r"(?:Notes?|Explanation):\s*(.*)", ans_raw, re.DOTALL)
                if m_exp:
                    explanation = re.sub(r"\s+", " ", m_exp.group(1).strip())

            if q_text and (options or correct):
                questions.append(
                    QuizQuestion(
                        question_num=q_num,
                        question_text=q_text,
                        options=options,
                        correct_option=correct,
                        explanation=explanation,
                        source_url=url,
                        date=date_str,
                    )
                )

        return questions

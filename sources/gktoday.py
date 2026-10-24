"""
GKToday Scraper for Daily Current Affairs & Quiz MCQs.
Directly fetches from GKToday daily quiz and current affairs endpoints with fallback resilience.
"""
import re
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
import trafilatura

from core.base_scraper import BaseScraper
from core.models import Article, QuizQuestion

logger = logging.getLogger("gktoday")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def clean_text(text: str) -> str:
    if not text:
        return ""
    replacements = [
        ("\u20b9", "Rs. "),
        ("\u2013", "-"),
        ("\u2014", "-"),
        ("\u2018", "'"),
        ("\u2019", "'"),
        ("\u201c", '"'),
        ("\u201d", '"'),
        ("\u00a0", " "),
        ("\u2022", "*"),
    ]
    for orig, rep in replacements:
        text = text.replace(orig, rep)
    return re.sub(r"\s+", " ", text).strip()


class GKTodayScraper(BaseScraper):
    """Production scraper for GKToday Quiz MCQs & Daily Current Affairs."""

    def __init__(self, request_delay: float = 0.5):
        super().__init__(name="GKToday", source_id="gktoday")
        self.base_url = "https://www.gktoday.in"
        self.request_delay = request_delay

    def fetch_articles(self, days: int = 1) -> List[Article]:
        """Fetches latest individual current affairs briefs from GKToday."""
        logger.info("Scraping GKToday high-yield current affairs...")
        try:
            resp = requests.get(self.base_url, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                return []
        except Exception as e:
            logger.error(f"Error connecting to GKToday: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        article_links: List[str] = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "gktoday.in/" in href and not any(x in href for x in ["category", "tag", "page", "quiz", "pdf", "account", "about", "contact", "#"]):
                t = a.get_text(strip=True)
                if len(t) > 15 and href not in article_links:
                    article_links.append(href)

        articles: List[Article] = []
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        for url in article_links[:15]:
            try:
                time.sleep(self.request_delay)
                downloaded = trafilatura.fetch_url(url)
                if not downloaded:
                    continue
                extracted_text = trafilatura.extract(downloaded)
                if not extracted_text or len(extracted_text) < 120:
                    continue

                sub_soup = BeautifulSoup(downloaded, "html.parser")
                h1 = sub_soup.find("h1")
                title = clean_text(h1.get_text()) if h1 else "GKToday Current Affairs"

                articles.append(
                    Article(
                        title=title,
                        url=url,
                        source="GKToday",
                        published_date=today_str,
                        full_text=clean_text(extracted_text),
                        language="en",
                        category="Current Affairs",
                        gs_paper="GS-3",
                        exam_stage="Prelims",
                    )
                )
            except Exception as e:
                logger.warning(f"Failed extracting GKToday article at {url}: {e}")

        logger.info(f"GKToday scraped {len(articles)} current affairs articles.")
        return articles

    def fetch_quizzes(self, days: int = 1) -> List[QuizQuestion]:
        """Fetches daily quiz questions from gk-current-affairs-quiz-questions-answers or monthly index."""
        logger.info("Scraping GKToday daily quizzes...")
        quiz_list_url = f"{self.base_url}/gk-current-affairs-quiz-questions-answers/"
        try:
            resp = requests.get(quiz_list_url, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                logger.warning(f"GKToday quiz landing returned status {resp.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error accessing GKToday quiz landing: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        quiz_post_urls: List[str] = []
        for h in soup.find_all(["h1", "h2", "h3"]):
            a = h.find("a")
            if a and a.get("href") and "daily-current-affairs-quiz" in a["href"]:
                url = a["href"]
                if url not in quiz_post_urls:
                    quiz_post_urls.append(url)

        if not quiz_post_urls:
            now = datetime.now(timezone.utc)
            m_url = f"{self.base_url}/quizbase/current-affairs-quiz-{now.strftime('%B').lower()}-{now.year}"
            quiz_post_urls.append(m_url)

        all_quizzes: List[QuizQuestion] = []
        for q_url in quiz_post_urls[:3]:
            try:
                time.sleep(self.request_delay)
                r = requests.get(q_url, headers=HEADERS, timeout=12)
                if r.status_code != 200:
                    continue
                q_soup = BeautifulSoup(r.text, "html.parser")
                questions = q_soup.find_all("div", class_="wp_quiz_question")
                for q_el in questions:
                    parsed = self._parse_single_mcq(q_el, source_url=q_url)
                    if parsed:
                        all_quizzes.append(parsed)
                    if len(all_quizzes) >= 20:
                        break
            except Exception as e:
                logger.warning(f"Failed parsing quiz page {q_url}: {e}")
            if len(all_quizzes) >= 20:
                break

        logger.info(f"GKToday scraped {len(all_quizzes)} MCQs.")
        return all_quizzes

    def _parse_single_mcq(self, q_el, source_url: str) -> Optional[QuizQuestion]:
        q_raw = q_el.get_text(separator=" ", strip=True)
        m = re.match(r"^(\d+)[\.\s]+(.*)$", q_raw)
        if m:
            num = int(m.group(1))
            q_text = clean_text(m.group(2))
        else:
            num = 1
            q_text = clean_text(q_raw)

        options: dict = {}
        parent = q_el.parent
        opts_el = parent.find("div", class_="wp_quiz_question_options") or q_el.find_next_sibling("div", class_="wp_quiz_question_options")
        if opts_el:
            opts_text = opts_el.get_text(separator=" ", strip=True)
            matches = list(re.finditer(r"\[([A-D])\]\s*([^\[]+)", opts_text))
            for match in matches:
                opt_key = match.group(1).upper()
                opt_val = clean_text(match.group(2))
                options[opt_key] = opt_val

        ans_el = parent.find("div", class_=lambda c: c and "wp_basic_quiz_answer" in c)
        if not ans_el:
            ans_el = q_el.find_next_sibling("div", class_=lambda c: c and "wp_basic_quiz_answer" in c)

        correct_opt = None
        explanation = None
        if ans_el:
            ans_text = clean_text(ans_el.get_text(separator=" ", strip=True))
            corr_match = re.search(r"Correct Answer:\s*([A-D])", ans_text, re.IGNORECASE)
            if corr_match:
                correct_opt = corr_match.group(1).upper()
            notes_match = re.search(r"Notes:\s*(.*)$", ans_text, re.DOTALL | re.IGNORECASE)
            if notes_match:
                explanation = clean_text(notes_match.group(1))
            else:
                explanation = ans_text

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return QuizQuestion(
            question_num=num,
            question_text=q_text,
            options=options,
            correct_option=correct_opt,
            explanation=explanation,
            source_url=source_url,
            date=today_str,
        )

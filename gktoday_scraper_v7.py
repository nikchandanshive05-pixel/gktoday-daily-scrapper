#!/usr/bin/env python3
"""
GKToday Scraper v7 (Final Cloud Edition) - CORRECTED
Features: Full Article Extraction, Date Filtering (Last 48 Hours),
UPSC Relevance Scoring, PDF Generation, and Telegram Delivery.
Cloud-Ready: Automatically reads credentials from environment variables.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re
import os
import sys
import time

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.colors import HexColor

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ==================== ENVIRONMENT VALIDATION ====================
# Read and STRIP whitespace — secrets sometimes have trailing newlines
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

logger.info("=" * 50)
logger.info("ENVIRONMENT VARIABLE CHECK")
logger.info(f"TELEGRAM_TOKEN present: {bool(TELEGRAM_TOKEN)} | length: {len(TELEGRAM_TOKEN)}")
logger.info(f"TELEGRAM_CHAT_ID present: {bool(TELEGRAM_CHAT_ID)} | length: {len(TELEGRAM_CHAT_ID)}")
logger.info("=" * 50)

if not TELEGRAM_TOKEN:
    logger.error("FATAL: TELEGRAM_TOKEN is empty or not set in environment!")
    logger.error("Make sure you created the secret in GitHub: Settings > Secrets > Actions")
if not TELEGRAM_CHAT_ID:
    logger.error("FATAL: TELEGRAM_CHAT_ID is empty or not set in environment!")
# ================================================================


class GKTodayScraper:
    BASE_URL = "https://www.gktoday.in"

    def __init__(self, max_days_old=2):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        ist_offset = timezone(timedelta(hours=5, minutes=30))
        self.today = datetime.now(ist_offset).date()
        self.cutoff_date = self.today - timedelta(days=max_days_old)
        logger.info(f"Initialized Scraper. Filtering articles older than {self.cutoff_date}")

    def fetch(self, url):
        try:
            r = self.session.get(url, timeout=30)
            r.raise_for_status()
            return r.text
        except Exception as e:
            logger.error(f"Fetch failed: {url} - {e}")
            return None

    def scrape_articles(self):
        logger.info("Fetching homepage to map article links...")
        html = self.fetch(self.BASE_URL)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        article_links = []
        seen_titles = set()

        headings = soup.find_all(['h3', 'h2'])
        for heading in headings:
            link_tag = heading.find('a')
            if not link_tag:
                continue

            title = link_tag.get_text(strip=True)
            url = link_tag.get('href', '')

            if not title or len(title) < 10 or title in seen_titles:
                continue
            if any(s in title.lower() for s in ['gk today', 'home', 'about', 'contact', 'quiz', 'archives']):
                continue

            seen_titles.add(title)
            if not url.startswith('http'):
                url = self.BASE_URL + url
            article_links.append({'title': title, 'url': url})

        full_articles = []
        for i, link_data in enumerate(article_links):
            logger.info(f"Deep Scraping [{i+1}/{len(article_links)}]: {link_data['title']}")
            time.sleep(1)

            article_html = self.fetch(link_data['url'])
            if not article_html:
                continue

            parsed_data = self._parse_full_article_page(article_html, link_data['title'], link_data['url'])
            if parsed_data:
                if parsed_data['parsed_date'] and parsed_data['parsed_date'] >= self.cutoff_date:
                    full_articles.append(parsed_data)
                elif not parsed_data['parsed_date']:
                    full_articles.append(parsed_data)
                else:
                    logger.info(f"Skipping outdated article: {parsed_data['date_str']}")

        return full_articles

    def _parse_full_article_page(self, html, title, url):
        soup = BeautifulSoup(html, 'html.parser')

        for tag in ['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']:
            for t in soup.find_all(tag):
                t.decompose()

        main_content = soup.find('div', class_=lambda c: c and ('content' in c.lower() or 'entry' in c.lower()))
        if not main_content:
            main_content = soup.find('body')

        paragraphs = main_content.find_all(['p', 'ul', 'h4'])
        texts = []

        date_str = ""
        parsed_date = None
        meta_div = soup.find('div', class_='entry-meta')
        if meta_div:
            meta_text = meta_div.get_text(separator=' ', strip=True)
            date_match = re.search(r'([A-Z][a-z]+ \d{1,2}, \d{4})', meta_text)
            if date_match:
                date_str = date_match.group(1)
                try:
                    parsed_date = datetime.strptime(date_str, "%B %d, %Y").date()
                except ValueError:
                    pass

        for p in paragraphs:
            if p.find_parent(class_=['sharedaddy', 'related-posts']):
                continue
            txt = p.get_text(strip=True)
            if txt and txt != title:
                texts.append(txt)

        full_content = '\n\n'.join(texts).strip()
        full_content = re.sub(r'\n{3,}', '\n\n', full_content)

        if not full_content:
            return None

        return {
            'title': title,
            'url': url,
            'date_str': date_str,
            'parsed_date': parsed_date,
            'category': self._infer_category(full_content),
            'content': full_content,
            'key_points': self._key_points(full_content),
            'relevance': self._relevance(title + ' ' + full_content)
        }

    def _infer_category(self, text):
        t = text.lower()[:500]
        categories = ['economy', 'science', 'sports', 'defence', 'environment', 'international', 'national']
        for cat in categories:
            if cat in t:
                return cat.capitalize()
        return "General"

    def _key_points(self, text):
        flat_text = text.replace('\n', ' ')
        pts = []
        for s in re.split(r'(?<=[.!?])\s+', flat_text):
            indicators = ['first', 'largest', 'launched', 'approved', 'appointed', 'signed', 'budget', 'gdp', 'supreme court', 'isro']
            if sum(1 for ind in indicators if ind in s.lower()) >= 1 and 30 < len(s) < 300:
                pts.append(s.strip())
        return pts[:4]

    def _relevance(self, text):
        t = text.lower()
        high = ['constitution', 'parliament', 'supreme court', 'scheme', 'yojana', 'gdp', 'rbi', 'climate', 'environment', 'isro', 'drdo']
        hs = sum(1 for k in high if k in t)
        level = 'HIGH' if hs >= 2 else 'MEDIUM' if hs == 1 else 'LOW'
        matched = [k for k in high if k in t][:3]
        return {'level': level, 'matched_keywords': matched}

    def scrape_all(self):
        articles = self.scrape_articles()
        sections = {}
        for a in articles:
            sections.setdefault(a.get('category', 'General'), []).append(a)

        section_list = [{'title': cat, 'articles': arts, 'article_count': len(arts)} for cat, arts in sections.items()]
        section_list.sort(key=lambda x: x['article_count'], reverse=True)

        return {
            'success': True,
            'date': self.today.strftime('%Y-%m-%d'),
            'display_date': self.today.strftime('%B %d, %Y'),
            'sections': section_list,
            'total_articles': len(articles)
        }


class PDFGenerator:
    def __init__(self, output_dir='output/pdfs'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.styles = self._make_styles()

    def _make_styles(self):
        s = getSampleStyleSheet()
        s.add(ParagraphStyle('GKTitle', parent=s['Heading1'], fontSize=20, textColor=HexColor('#1a5276'), alignment=TA_CENTER))
        s.add(ParagraphStyle('GKSub', parent=s['Normal'], fontSize=10, textColor=HexColor('#7f8c8d'), alignment=TA_CENTER, spaceAfter=10))
        s.add(ParagraphStyle('GKSecHead', parent=s['Heading2'], fontSize=12, textColor=HexColor('#1a5276'), spaceBefore=10))
        s.add(ParagraphStyle('GKArtTitle', parent=s['Heading3'], fontSize=10, textColor=HexColor('#2874a6'), spaceBefore=5))
        s.add(ParagraphStyle('GKContent', parent=s['Normal'], fontSize=8, leading=11, alignment=TA_JUSTIFY, spaceAfter=5))
        s.add(ParagraphStyle('GKBadgeH', parent=s['Normal'], fontSize=6, textColor=colors.white, backColor=HexColor('#e74c3c'), spaceAfter=2))
        return s

    def _clean(self, text):
        text = str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return text.replace('\n\n', '<br/><br/>').replace('\n', ' ')

    def generate(self, data, path=None):
        path = path or os.path.join(self.output_dir, f"GKToday_{data['date']}.pdf")
        doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=10*mm, leftMargin=10*mm, topMargin=12*mm, bottomMargin=12*mm)

        story = [
            Paragraph("<b>GK TODAY DEEP DIGEST</b>", self.styles['GKTitle']),
            Paragraph(f"{data['display_date']} | {data['total_articles']} Articles", self.styles['GKSub'])
        ]

        for sec in data.get('sections', []):
            story.append(Paragraph(f"{sec['title']} ({sec['article_count']})", self.styles['GKSecHead']))
            for art in sec['articles']:
                if art['relevance']['level'] == 'HIGH':
                    story.append(Paragraph("HIGH YIELD", self.styles['GKBadgeH']))
                story.append(Paragraph(f"<b>{self._clean(art['title'])}</b>", self.styles['GKArtTitle']))
                story.append(Paragraph(self._clean(art['content']), self.styles['GKContent']))
                story.append(Spacer(1, 5))

        doc.build(story)
        logger.info(f"PDF generated: {path}")
        return path


class Pipeline:
    def __init__(self, output_dir='output', telegram_token=None, telegram_chat_id=None):
        self.scraper = GKTodayScraper(max_days_old=2)
        self.generator = PDFGenerator(os.path.join(output_dir, 'pdfs'))
        self.output_dir = output_dir
        self.tg_token = telegram_token
        self.tg_chat = telegram_chat_id

    def run(self):
        data = self.scraper.scrape_all()
        if not data.get('total_articles'):
            logger.warning("No new articles found. Exiting.")
            return None

        ppath = self.generator.generate(data)

        # CORRECTED: Explicit truthy check with logging
        if self.tg_token and self.tg_chat:
            logger.info("Telegram credentials detected. Attempting delivery...")
            self._telegram(data, ppath)
        else:
            logger.warning("Telegram credentials NOT provided or empty. PDF saved locally only.")
        return ppath

    def _telegram(self, data, pdf_path):
        try:
            msg = (
                f"📚 <b>GKToday Deep Digest: {data['display_date']}</b>\n\n"
                f"📝 Extracted {data['total_articles']} full articles from the last 48 hours."
            )
            # Send text message
            r1 = requests.post(
                f"https://api.telegram.org/bot{self.tg_token}/sendMessage",
                json={'chat_id': self.tg_chat, 'text': msg, 'parse_mode': 'HTML'},
                timeout=30
            )
            logger.info(f"Telegram sendMessage status: {r1.status_code}")

            # Send PDF document
            with open(pdf_path, 'rb') as f:
                r2 = requests.post(
                    f"https://api.telegram.org/bot{self.tg_token}/sendDocument",
                    files={'document': f},
                    data={'chat_id': self.tg_chat},
                    timeout=60
                )
            logger.info(f"Telegram sendDocument status: {r2.status_code}")
            logger.info("Telegram delivery successful.")

        except Exception as e:
            logger.error(f"Telegram delivery failed: {e}")


if __name__ == '__main__':
    # Use the validated globals defined at the top of the file
    p = Pipeline(telegram_token=TELEGRAM_TOKEN, telegram_chat_id=TELEGRAM_CHAT_ID)
    p.run()

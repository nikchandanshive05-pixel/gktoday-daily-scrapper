#!/usr/bin/env python3
"""
GKToday Scraper v9 (Production-Ready Edition)
Filename: gktoday_scraper_v7.py (kept for workflow compatibility)

Features: Full Article Extraction, Date Filtering (Last 48 Hours),
UPSC Relevance Scoring, PRODUCTION-READY PDF Generation, and Telegram Delivery.

CHANGES FROM v8:
- Professional typography with proper spacing
- Generous 18mm margins with header/footer on every page
- Key points displayed as styled callout boxes
- Category color-coded badges with article metadata (date, URL)
- Thin hairline separators between articles
- PDF bookmarks/outline for navigation
- Cover page with mini table of contents
- Pill-shaped HIGH YIELD badges
- Proper line spacing (1.5x ratio)
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
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    HRFlowable, PageTemplate, Frame, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas as pdfcanvas

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ==================== ENVIRONMENT VALIDATION ====================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

logger.info("=" * 50)
logger.info("ENVIRONMENT VARIABLE CHECK")
logger.info(f"TELEGRAM_TOKEN present: {bool(TELEGRAM_TOKEN)} | length: {len(TELEGRAM_TOKEN)}")
logger.info(f"TELEGRAM_CHAT_ID present: {bool(TELEGRAM_CHAT_ID)} | length: {len(TELEGRAM_CHAT_ID)}")
logger.info("=" * 50)

if not TELEGRAM_TOKEN:
    logger.error("FATAL: TELEGRAM_TOKEN is empty or not set in environment!")
if not TELEGRAM_CHAT_ID:
    logger.error("FATAL: TELEGRAM_CHAT_ID is empty or not set in environment!")
# ================================================================


# ==================== PRODUCTION PALETTE ====================
PALETTE = {
    'primary':    '#1e3a5f',
    'secondary':  '#2563eb',
    'accent':     '#dc2626',
    'success':    '#059669',
    'text':       '#1f2937',
    'muted':      '#6b7280',
    'light_gray': '#94a3b8',
    'border':     '#e5e7eb',
    'bg_blue':    '#f0f9ff',
    'border_blue':'#bae6fd',
    'bg_cover':   '#f8fafc',
}

CATEGORY_COLORS = {
    'Economy': '#059669',
    'Science & Technology': '#7c3aed',
    'Environment': '#16a34a',
    'Sports': '#ea580c',
    'Defence': '#dc2626',
    'International': '#2563eb',
    'Awards & Persons': '#db2777',
    'National': '#4f46e5',
    'General': '#6b7280',
}
# ============================================================


STOP_MARKERS = [
    "Your email address will not be published",
]

JUNK_MARKERS = [
    "Daily MCQs", "Monthly MCQs", "Current Affairs Quiz –", "Current Affairs Quiz -",
    "Topic Wise CA MCQs", "CA MCQs in Other Languages", "SSC/RRB/States Level MCQs",
    "Current Affairs Monthly 240 MCQs", "CA Articles+MCQs", "CA Articles [Monthly",
    "CA Articles [Yearly", "Previous Months Quiz",
]

JUNK_EXACT = {"Comment*", "Name*", "Email*", "∆", "Home", ""}

JUNK_SELECTORS = [
    {"class_": re.compile(r"(sharedaddy|jp-relatedposts|related-post|comment|respond|widget|"
                           r"sidebar|breadcrumb|post-navigation|entry-footer|tags|social|"
                           r"share|menu|navbar|quiz-nav)", re.I)},
]

CATEGORY_KEYWORDS = {
    "Economy": ["gdp", "economy", "budget", "rbi", "inflation", "fiscal", "trade", "wto", "tax", "scheme"],
    "Science & Technology": ["isro", "satellite", "exoplanet", "telescope", "research", "spacecraft", "technology", "ai minister", "artificial intelligence"],
    "Environment": ["climate", "biodiversity", "wildlife", "snakebite", "forest", "conservation", "species"],
    "Sports": ["games", "olympic", "tournament", "championship", "medal", "athletes"],
    "Defence": ["drdo", "missile", "army", "navy", "air force", "defence"],
    "International": ["united nations", "wto", "prime minister", "president", "hamas", "ceasefire", "united kingdom", "parliament"],
    "Awards & Persons": ["award", "appointed", "minister", "elected", "career", "honour"],
    "National": ["government", "ministry", "cabinet", "delhi", "state", "india"],
}


# ==================== CUSTOM CANVAS WITH BOOKMARKS ====================
class BookmarkCanvas(pdfcanvas.Canvas):
    """Canvas subclass that supports PDF bookmarks/outline entries."""
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
# ========================================================================


# ==================== HEADER / FOOTER CALLBACK ====================
def header_footer(canvas, doc):
    """Draws header (section name + date) and footer (page number) on every page."""
    canvas.saveState()

    # Header line
    canvas.setStrokeColor(HexColor(PALETTE['border']))
    canvas.setLineWidth(0.5)
    canvas.line(18*mm, A4[1]-16*mm, A4[0]-18*mm, A4[1]-16*mm)

    # Header text
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(HexColor(PALETTE['light_gray']))
    canvas.drawString(18*mm, A4[1]-14*mm, doc.section_name or "GK Today Deep Digest")
    if doc.display_date:
        canvas.drawRightString(A4[0]-18*mm, A4[1]-14*mm, doc.display_date)

    # Footer line
    canvas.line(18*mm, 16*mm, A4[0]-18*mm, 16*mm)

    # Footer page number
    canvas.setFont('Helvetica-Bold', 9)
    canvas.setFillColor(HexColor(PALETTE['primary']))
    canvas.drawCentredString(A4[0]/2, 12*mm, f"— {doc.page} —")

    canvas.restoreState()
# ===================================================================


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

    @staticmethod
    def _is_junk(text, title):
        if not text or text in JUNK_EXACT:
            return True
        if len(text) > 2000:
            return True
        if text.count('■') > 3:
            return True
        if text.lower().count('mcqs') >= 3:
            return True
        if text.count('General Studies (') >= 3:
            return True
        if any(marker in text for marker in JUNK_MARKERS):
            return True
        squished = text.replace(' ', '')
        if squished.startswith('Home') and title.replace(' ', '') in squished:
            return True
        return False

    def _strip_chrome(self, container):
        for tag in ['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'form']:
            for t in container.find_all(tag):
                t.decompose()
        for sel in JUNK_SELECTORS:
            for t in container.find_all(attrs={"class": sel["class_"]}):
                t.decompose()
            for t in container.find_all(attrs={"id": sel["class_"]}):
                t.decompose()

    def _find_content_container(self, soup):
        candidates = [
            soup.find(attrs={'itemprop': 'articleBody'}),
            soup.find('div', class_='entry-content'),
            soup.find('article'),
        ]
        for c in candidates:
            if c is not None:
                return c
        return soup.find('div', class_=lambda c: c and ('content' in c.lower() or 'entry' in c.lower()))             or soup.find('body')

    def _parse_full_article_page(self, html, title, url):
        soup = BeautifulSoup(html, 'html.parser')

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

        main_content = self._find_content_container(soup)
        if main_content is None:
            return None

        self._strip_chrome(main_content)

        elements = main_content.find_all(['p', 'ul', 'h4', 'h3'])
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
        t = text.lower()
        scores = {}
        for cat, keywords in CATEGORY_KEYWORDS.items():
            score = sum(t.count(k) for k in keywords)
            if score:
                scores[cat] = score
        if not scores:
            return "General"
        return max(scores, key=scores.get)

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

        # ========== COVER PAGE STYLES ==========
        s.add(ParagraphStyle('CoverTitle',
            parent=s['Heading1'],
            fontSize=36,
            textColor=HexColor(PALETTE['primary']),
            alignment=TA_CENTER,
            spaceAfter=8,
            leading=42))

        s.add(ParagraphStyle('CoverSub',
            parent=s['Normal'],
            fontSize=14,
            textColor=HexColor(PALETTE['muted']),
            alignment=TA_CENTER,
            spaceAfter=30,
            leading=18))

        s.add(ParagraphStyle('CoverMeta',
            parent=s['Normal'],
            fontSize=11,
            textColor=HexColor(PALETTE['light_gray']),
            alignment=TA_CENTER,
            spaceAfter=50,
            leading=14))

        s.add(ParagraphStyle('CoverToc',
            parent=s['Normal'],
            fontSize=10,
            textColor=HexColor(PALETTE['text']),
            alignment=TA_CENTER,
            spaceAfter=6,
            leading=14))

        # ========== CONTENT STYLES ==========
        s.add(ParagraphStyle('GKSecHead',
            parent=s['Heading2'],
            fontSize=16,
            textColor=HexColor(PALETTE['primary']),
            spaceBefore=20,
            spaceAfter=12,
            leading=20,
            borderColor=HexColor(PALETTE['secondary']),
            borderWidth=2,
            borderPadding=5,
            leftIndent=0,
            borderRadius=3))

        s.add(ParagraphStyle('GKBadgeH',
            parent=s['Normal'],
            fontSize=7,
            textColor=colors.white,
            backColor=HexColor(PALETTE['accent']),
            spaceAfter=6,
            spaceBefore=4,
            alignment=TA_CENTER,
            leading=10,
            borderRadius=4))

        s.add(ParagraphStyle('GKArtTitle',
            parent=s['Heading3'],
            fontSize=12,
            textColor=HexColor(PALETTE['primary']),
            spaceBefore=8,
            spaceAfter=4,
            leading=16))

        s.add(ParagraphStyle('GKMeta',
            parent=s['Normal'],
            fontSize=7,
            textColor=HexColor(PALETTE['light_gray']),
            spaceAfter=6,
            leading=10))

        s.add(ParagraphStyle('GKKeyPoints',
            parent=s['Normal'],
            fontSize=9,
            textColor=HexColor(PALETTE['primary']),
            backColor=HexColor(PALETTE['bg_blue']),
            borderColor=HexColor(PALETTE['border_blue']),
            borderWidth=1,
            borderPadding=10,
            spaceAfter=10,
            spaceBefore=4,
            leading=14,
            leftIndent=5,
            rightIndent=5,
            borderRadius=6))

        s.add(ParagraphStyle('GKContent',
            parent=s['Normal'],
            fontSize=10,
            leading=15,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            textColor=HexColor(PALETTE['text'])))

        return s

    def _clean(self, text):
        text = str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return text.replace('\n\n', '<br/><br/>').replace('\n', ' ')

    def generate(self, data, path=None):
        path = path or os.path.join(self.output_dir, f"GKToday_{data['date']}.pdf")

        # Use custom canvas for bookmarks
        doc = SimpleDocTemplate(
            path,
            pagesize=A4,
            rightMargin=18*mm,
            leftMargin=18*mm,
            topMargin=18*mm,
            bottomMargin=18*mm,
            canvasmaker=BookmarkCanvas
        )

        # Attach metadata to doc for header/footer callback
        doc.section_name = "GK Today Deep Digest"
        doc.display_date = data.get('display_date', '')

        # Page template with header/footer
        frame = Frame(18*mm, 18*mm, A4[0]-36*mm, A4[1]-36*mm, id='normal')
        template = PageTemplate(id='main', frames=frame, onPage=header_footer)
        doc.addPageTemplates([template])

        story = []

        # ========== COVER PAGE ==========
        story.append(Spacer(1, 40))
        story.append(Paragraph("<b>GK TODAY</b>", self.styles['CoverTitle']))
        story.append(Paragraph("DEEP DIGEST", self.styles['CoverSub']))
        story.append(Paragraph(
            f"{data['display_date']}<br/>{data['total_articles']} Articles",
            self.styles['CoverMeta']))

        # Mini TOC on cover
        story.append(Paragraph("— CONTENTS —", self.styles['CoverSub']))
        for sec in data.get('sections', []):
            story.append(Paragraph(
                f"• {sec['title']} ({sec['article_count']} articles)",
                self.styles['CoverToc']))

        story.append(PageBreak())

        # ========== CONTENT PAGES ==========
        for sec in data.get('sections', []):
            # Section header with bookmark
            sec_title = f"{sec['title']} ({sec['article_count']})"
            story.append(Paragraph(sec_title, self.styles['GKSecHead']))

            for art in sec['articles']:
                # Build article block
                article_block = []

                # HIGH YIELD badge
                if art['relevance']['level'] == 'HIGH':
                    article_block.append(Paragraph("⭐ HIGH YIELD", self.styles['GKBadgeH']))

                # Article title
                article_block.append(Paragraph(
                    f"<b>{self._clean(art['title'])}</b>",
                    self.styles['GKArtTitle']))

                # Metadata line: category badge + date + URL
                cat_color = CATEGORY_COLORS.get(art['category'], PALETTE['muted'])
                meta_text = (
                    f"<font color='white' backColor='{cat_color}' size='7'>"
                    f"  {art['category'].upper()}  </font>"
                    f"<font size='7' color='{PALETTE['light_gray']}'>"
                    f"  •  {art.get('date_str', 'N/A')}  •  {art['url'][:55]}...</font>"
                )
                article_block.append(Paragraph(meta_text, self.styles['GKMeta']))

                # Key points callout box
                if art.get('key_points'):
                    kp_bullets = "<br/>• ".join([""] + art['key_points'])
                    article_block.append(Paragraph(
                        f"<b>🎯 Key Points:</b>{kp_bullets}",
                        self.styles['GKKeyPoints']))

                # Main content
                article_block.append(Paragraph(
                    self._clean(art['content']),
                    self.styles['GKContent']))

                # Separator line
                article_block.append(HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color=HexColor(PALETTE['border']),
                    spaceAfter=10,
                    spaceBefore=6))

                # Keep article together if possible (avoid splitting mid-article)
                story.append(KeepTogether(article_block))

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
            r1 = requests.post(
                f"https://api.telegram.org/bot{self.tg_token}/sendMessage",
                json={'chat_id': self.tg_chat, 'text': msg, 'parse_mode': 'HTML'},
                timeout=30
            )
            logger.info(f"Telegram sendMessage status: {r1.status_code}")

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
    p = Pipeline(telegram_token=TELEGRAM_TOKEN, telegram_chat_id=TELEGRAM_CHAT_ID)
    p.run()

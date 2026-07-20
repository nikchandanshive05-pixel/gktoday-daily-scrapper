#!/usr/bin/env python3
"""
GKToday Daily Scraper + Professional PDF Generator
====================================================
Fixed version: Scrapes GKToday homepage for current articles
and individual article pages for full content.
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import re
import os
from typing import List, Dict, Optional
import logging
import sys

# PDF Generation
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether, ListFlowable, ListItem
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class GKTodayScraper:
    """Scrapes GKToday content from homepage and article pages"""

    BASE_URL = "https://www.gktoday.in"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def get_homepage(self) -> Optional[BeautifulSoup]:
        """Fetch and parse GKToday homepage"""
        logger.info(f"Fetching homepage: {self.BASE_URL}")

        try:
            response = self.session.get(self.BASE_URL, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Failed to fetch homepage: {e}")
            return None

    def extract_date_from_page(self, soup: BeautifulSoup) -> str:
        """Extract the date from the homepage content"""
        # Look for date patterns in article dates
        date_patterns = [
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
            r'\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
        ]

        text = soup.get_text()
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        return datetime.now().strftime('%B %d, %Y')

    def scrape_articles(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract all articles from the homepage"""
        articles = []

        # GKToday uses article/entry structure
        # Try multiple selectors to find article containers
        article_selectors = [
            'article.post',
            'article',
            '.post',
            '.entry',
            'div[class*="post"]',
            'div[class*="article"]',
        ]

        article_elements = []
        for selector in article_selectors:
            found = soup.select(selector)
            if found:
                article_elements = found
                logger.info(f"Found {len(found)} articles with selector: {selector}")
                break

        if not article_elements:
            # Fallback: look for h3/h2 headings with links (article titles)
            logger.info("Trying fallback article detection...")
            headings = soup.find_all(['h2', 'h3'])
            for heading in headings:
                link = heading.find('a')
                if link and link.get('href'):
                    article_url = link.get('href')
                    if 'gktoday.in' in article_url or article_url.startswith('/'):
                        article_elements.append(heading.find_parent())

        for elem in article_elements:
            article = self._parse_article_element(elem)
            if article:
                articles.append(article)

        logger.info(f"Total articles extracted: {len(articles)}")
        return articles

    def _parse_article_element(self, elem) -> Optional[Dict]:
        """Parse a single article element"""
        try:
            # Find title
            title_elem = elem.find(['h2', 'h3', 'h1'])
            if not title_elem:
                return None

            title_link = title_elem.find('a')
            title = title_elem.get_text(strip=True)
            article_url = title_link.get('href') if title_link else None

            if not title or len(title) < 10:
                return None

            # Find date
            date_elem = elem.find(['time', 'span', 'div'], class_=re.compile(r'date|time|published', re.I))
            date_text = date_elem.get_text(strip=True) if date_elem else ''

            # Find category
            category_elem = elem.find(['span', 'a'], class_=re.compile(r'category|cat|tag', re.I))
            category = category_elem.get_text(strip=True) if category_elem else 'General'

            # Find summary/excerpt
            summary_elem = elem.find(['div', 'p'], class_=re.compile(r'excerpt|summary|content|entry', re.I))
            if not summary_elem:
                # Try next sibling paragraphs
                summary_elem = elem.find_next_sibling('p')

            summary = summary_elem.get_text(strip=True) if summary_elem else ''

            # Find image
            img_elem = elem.find('img')
            image_url = img_elem.get('src') if img_elem else None

            # Try to fetch full article content
            full_content = ''
            if article_url:
                full_content = self._fetch_article_content(article_url)

            content = full_content if full_content else summary

            # Extract key points from content
            key_points = self._extract_key_points(content)

            # Assess relevance
            relevance = self._assess_relevance(title + ' ' + content)

            return {
                'title': title,
                'url': article_url,
                'date': date_text,
                'category': category,
                'summary': summary,
                'content': content,
                'key_points': key_points,
                'image_url': image_url,
                'word_count': len(content.split()),
                'relevance': relevance,
            }
        except Exception as e:
            logger.warning(f"Error parsing article: {e}")
            return None

    def _fetch_article_content(self, url: str) -> str:
        """Fetch full article content from article page"""
        try:
            if url.startswith('/'):
                url = self.BASE_URL + url

            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find main content area
            content_selectors = [
                '.entry-content',
                '.post-content',
                'article .content',
                '.single-content',
                'div[itemprop="articleBody"]',
            ]

            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # Remove scripts, ads, etc.
                    for script in content_elem.find_all(['script', 'style', 'nav', 'aside']):
                        script.decompose()

                    text = content_elem.get_text(separator='\n', strip=True)
                    # Clean up
                    text = re.sub(r'\n+', '\n', text)
                    return text.strip()

            # Fallback: all paragraphs after title
            paragraphs = soup.find_all('p')
            text = '\n'.join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50)
            return text

        except Exception as e:
            logger.warning(f"Failed to fetch article content from {url}: {e}")
            return ''

    def _extract_key_points(self, text: str) -> List[str]:
        """Extract key points from article text"""
        points = []

        if not text:
            return points

        # Split into sentences and look for key fact indicators
        sentences = re.split(r'(?<=[.!?])\s+', text)

        key_indicators = [
            'first', 'largest', 'only', 'signed', 'launched', 'announced',
            'approved', 'inaugurated', 'appointed', 'elected', 'unveiled',
            'approved', 'banned', 'introduced', 'passed', 'ratified',
            'agreement', 'treaty', 'scheme', 'programme', 'mission',
            'billion', 'million', 'crore', 'percent', '%',
            'minister', 'president', 'prime minister', 'chief minister',
            'state', 'union', 'government', 'cabinet',
        ]

        for sent in sentences:
            sent_lower = sent.lower()
            score = sum(1 for indicator in key_indicators if indicator in sent_lower)
            if score >= 2 and len(sent) > 30 and len(sent) < 300:
                points.append(sent.strip())

        # Limit to top 5 points
        return points[:5]

    def _assess_relevance(self, text: str) -> Dict:
        """Assess exam relevance for MPSC/UPSC"""
        text_lower = text.lower()

        high_keywords = [
            'maharashtra', 'mumbai', 'pune', 'nagpur', 'thane', 'nashik',
            'solapur', 'kolhapur', 'aurangabad', 'nagpur',
            'constitution', 'parliament', 'supreme court', 'amendment',
            'article', 'schedule', 'fundamental', 'directive',
            'scheme', 'policy', 'mission', 'programme', 'yojana',
            'gdp', 'inflation', 'budget', 'reserve bank', 'rbi',
            'agriculture', 'farmer', 'crop', 'msp', 'irrigation',
            'climate', 'environment', 'pollution', 'renewable',
            'defence', 'missile', 'satellite', 'space', 'isro', 'drdo',
            'appointment', 'election', 'cabinet', 'minister', 'governor',
            'welfare', 'social', 'health', 'education', 'digital',
            'india', 'bharat', 'union',
        ]

        medium_keywords = [
            'world', 'country', 'international', 'summit', 'treaty',
            'bank', 'finance', 'economy', 'trade', 'export', 'import',
            'technology', 'digital', 'ai', 'cyber', 'internet',
            'health', 'disease', 'vaccine', 'medical',
            'education', 'university', 'school', 'student',
            'sports', 'olympic', 'cricket', 'tournament',
            'award', 'honour', 'prize', 'recognition',
        ]

        high_score = sum(1 for kw in high_keywords if kw in text_lower)
        medium_score = sum(1 for kw in medium_keywords if kw in text_lower)

        total_score = high_score * 2 + medium_score

        if total_score >= 5:
            level = 'HIGH'
        elif total_score >= 2:
            level = 'MEDIUM'
        else:
            level = 'LOW'

        return {
            'level': level,
            'score': total_score,
            'matched_keywords': [kw for kw in high_keywords + medium_keywords if kw in text_lower][:5]
        }

    def scrape_daily(self, target_date: datetime = None) -> Dict:
        """Scrape daily content from GKToday"""
        if not target_date:
            target_date = datetime.now()

        logger.info(f"Starting scrape for {target_date.strftime('%Y-%m-%d')}")

        soup = self.get_homepage()
        if not soup:
            return {
                'success': False,
                'error': 'Failed to fetch homepage',
                'date': target_date.strftime('%Y-%m-%d')
            }

        page_date = self.extract_date_from_page(soup)
        articles = self.scrape_articles(soup)

        # Group articles by category
        sections = {}
        for article in articles:
            category = article.get('category', 'General')
            if category not in sections:
                sections[category] = []
            sections[category].append(article)

        # Convert to list format
        section_list = []
        for category, cat_articles in sections.items():
            section_list.append({
                'title': category,
                'articles': cat_articles,
                'article_count': len(cat_articles)
            })

        # Sort sections by article count (most important first)
        section_list.sort(key=lambda x: x['article_count'], reverse=True)

        return {
            'success': True,
            'date': target_date.strftime('%Y-%m-%d'),
            'display_date': page_date,
            'url': self.BASE_URL,
            'scraped_at': datetime.now().isoformat(),
            'sections': section_list,
            'total_articles': len(articles),
            'total_mcqs': 0,
            'mcqs': []
        }


class ExamPDFGenerator:
    """Generates professional exam-oriented PDFs"""

    COLORS = {
        'primary': HexColor('#1a5276'),
        'secondary': HexColor('#2874a6'),
        'accent': HexColor('#e74c3c'),
        'highlight': HexColor('#f39c12'),
        'success': HexColor('#27ae60'),
        'text': HexColor('#2c3e50'),
        'light_text': HexColor('#7f8c8d'),
        'bg_light': HexColor('#f8f9fa'),
        'border': HexColor('#bdc3c7'),
    }

    def __init__(self, output_dir: str = 'output/pdfs'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.styles = self._create_styles()

    def _create_styles(self) -> Dict:
        styles = getSampleStyleSheet()

        styles.add(ParagraphStyle(
            'ExamTitle',
            parent=styles['Heading1'],
            fontSize=26,
            leading=32,
            textColor=self.COLORS['primary'],
            alignment=TA_CENTER,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        ))

        styles.add(ParagraphStyle(
            'DateSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            leading=16,
            textColor=self.COLORS['light_text'],
            alignment=TA_CENTER,
            spaceAfter=20,
            fontName='Helvetica'
        ))

        styles.add(ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            leading=18,
            textColor=self.COLORS['primary'],
            spaceBefore=16,
            spaceAfter=8,
            fontName='Helvetica-Bold',
            borderColor=self.COLORS['primary'],
            borderWidth=1,
            borderPadding=4,
            leftIndent=0,
        ))

        styles.add(ParagraphStyle(
            'ArticleTitle',
            parent=styles['Heading3'],
            fontSize=11,
            leading=15,
            textColor=self.COLORS['secondary'],
            spaceBefore=10,
            spaceAfter=4,
            fontName='Helvetica-Bold'
        ))

        styles.add(ParagraphStyle(
            'ArticleContent',
            parent=styles['Normal'],
            fontSize=9,
            leading=13,
            textColor=self.COLORS['text'],
            alignment=TA_JUSTIFY,
            spaceAfter=6,
            fontName='Helvetica'
        ))

        styles.add(ParagraphStyle(
            'KeyPoint',
            parent=styles['Normal'],
            fontSize=8,
            leading=12,
            textColor=self.COLORS['text'],
            leftIndent=15,
            spaceAfter=3,
            fontName='Helvetica'
        ))

        styles.add(ParagraphStyle(
            'RelevanceHigh',
            parent=styles['Normal'],
            fontSize=7,
            leading=9,
            textColor=colors.white,
            backColor=self.COLORS['accent'],
            alignment=TA_CENTER,
            spaceAfter=3,
            fontName='Helvetica-Bold'
        ))

        styles.add(ParagraphStyle(
            'RelevanceMedium',
            parent=styles['Normal'],
            fontSize=7,
            leading=9,
            textColor=colors.white,
            backColor=self.COLORS['highlight'],
            alignment=TA_CENTER,
            spaceAfter=3,
            fontName='Helvetica-Bold'
        ))

        styles.add(ParagraphStyle(
            'RelevanceLow',
            parent=styles['Normal'],
            fontSize=7,
            leading=9,
            textColor=colors.white,
            backColor=self.COLORS['light_text'],
            alignment=TA_CENTER,
            spaceAfter=3,
            fontName='Helvetica-Bold'
        ))

        styles.add(ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=7,
            leading=10,
            textColor=self.COLORS['light_text'],
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))

        return styles

    def _clean_text(self, text: str) -> str:
        """Clean text for PDF rendering"""
        if not text:
            return ''
        # Replace problematic characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('\n', '<br/>')
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        return text.strip()

    def generate_pdf(self, data: Dict, output_path: Optional[str] = None) -> str:
        if not output_path:
            date_str = data['date']
            output_path = f"{self.output_dir}/GKToday_{date_str}.pdf"

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=12*mm,
            leftMargin=12*mm,
            topMargin=15*mm,
            bottomMargin=15*mm
        )

        story = []
        story.extend(self._build_header(data))
        story.extend(self._build_summary(data))
        story.append(Spacer(1, 15))

        for section in data.get('sections', []):
            story.extend(self._build_section(section))

        story.extend(self._build_footer(data))

        doc.build(story, onFirstPage=self._add_page_decorations, onLaterPages=self._add_page_decorations)

        logger.info(f"PDF generated: {output_path}")
        return output_path

    def _build_header(self, data: Dict) -> List:
        elements = []

        title = Paragraph(
            f'<b>GK TODAY</b><br/><font size=14>Current Affairs Daily Digest</font>',
            self.styles['ExamTitle']
        )
        elements.append(title)

        date_para = Paragraph(
            f"{data.get('display_date', data['date'])} | {data['total_articles']} Articles | Source: GKToday.in",
            self.styles['DateSubtitle']
        )
        elements.append(date_para)

        elements.append(Spacer(1, 8))
        line_table = Table([['']], colWidths=[186*mm])
        line_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, 0), 2, self.COLORS['primary']),
            ('TOPPADDING', (0, 0), (-1, 0), 0),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
        ]))
        elements.append(line_table)
        elements.append(Spacer(1, 12))

        return elements

    def _build_summary(self, data: Dict) -> List:
        elements = []

        high_count = sum(
            1 for s in data.get('sections', [])
            for a in s.get('articles', [])
            if a.get('relevance', {}).get('level') == 'HIGH'
        )
        medium_count = sum(
            1 for s in data.get('sections', [])
            for a in s.get('articles', [])
            if a.get('relevance', {}).get('level') == 'MEDIUM'
        )
        low_count = sum(
            1 for s in data.get('sections', [])
            for a in s.get('articles', [])
            if a.get('relevance', {}).get('level') == 'LOW'
        )

        summary_data = [
            ['📊 EXAM RELEVANCE SUMMARY', '', '', ''],
            ['', '', '', ''],
            ['🔴 HIGH Priority', str(high_count), '🟡 MEDIUM Priority', str(medium_count)],
            ['🟢 LOW Priority', str(low_count), '📰 Total Articles', str(data['total_articles'])],
        ]

        summary_table = Table(summary_data, colWidths=[47*mm, 22*mm, 47*mm, 22*mm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('SPAN', (0, 0), (-1, 0)),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 2), (-1, -1), self.COLORS['bg_light']),
            ('TEXTCOLOR', (0, 2), (-1, -1), self.COLORS['text']),
            ('FONTNAME', (0, 2), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 2), (-1, -1), 8),
            ('ALIGN', (0, 2), (0, -1), 'LEFT'),
            ('ALIGN', (1, 2), (1, -1), 'CENTER'),
            ('ALIGN', (2, 2), (2, -1), 'LEFT'),
            ('ALIGN', (3, 2), (3, -1), 'CENTER'),
            ('TOPPADDING', (0, 2), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 2), (-1, -1), 5),
            ('LEFTPADDING', (0, 2), (-1, -1), 6),
            ('RIGHTPADDING', (0, 2), (-1, -1), 6),
            ('GRID', (0, 1), (-1, -1), 0.5, self.COLORS['border']),
            ('BOX', (0, 0), (-1, -1), 1, self.COLORS['primary']),
        ]))

        elements.append(summary_table)
        return elements

    def _build_section(self, section: Dict) -> List:
        elements = []

        section_title = f"📌 {section['title']} ({section['article_count']} articles)"
        header = Paragraph(section_title, self.styles['SectionHeader'])
        elements.append(header)
        elements.append(Spacer(1, 6))

        for article in section.get('articles', []):
            elements.extend(self._build_article(article))

        elements.append(Spacer(1, 10))
        return elements

    def _build_article(self, article: Dict) -> List:
        elements = []

        relevance = article.get('relevance', {})
        level = relevance.get('level', 'LOW')

        if level == 'HIGH':
            badge_style = 'RelevanceHigh'
            badge_text = '⭐ HIGH PRIORITY'
        elif level == 'MEDIUM':
            badge_style = 'RelevanceMedium'
            badge_text = 'MEDIUM PRIORITY'
        else:
            badge_style = 'RelevanceLow'
            badge_text = 'LOW PRIORITY'

        badge = Paragraph(badge_text, self.styles[badge_style])
        elements.append(badge)

        title = self._clean_text(article.get('title', 'Untitled'))
        title_para = Paragraph(f"<b>{title}</b>", self.styles['ArticleTitle'])
        elements.append(title_para)

        # Key points
        key_points = article.get('key_points', [])
        if key_points:
            elements.append(Paragraph("<b>Key Points:</b>", self.styles['ArticleContent']))
            for point in key_points:
                clean_point = self._clean_text(point)
                if clean_point:
                    elements.append(Paragraph(f"• {clean_point}", self.styles['KeyPoint']))

        # Content
        content = article.get('content', '')
        if len(content) > 400:
            content = content[:400] + "..."
        clean_content = self._clean_text(content)
        if clean_content:
            content_para = Paragraph(clean_content, self.styles['ArticleContent'])
            elements.append(content_para)

        # Tags
        keywords = relevance.get('matched_keywords', [])
        if keywords:
            keywords_text = ', '.join(keywords)
            keywords_para = Paragraph(
                f"<i>Tags: {keywords_text}</i>",
                ParagraphStyle(
                    'Keywords',
                    parent=self.styles['Normal'],
                    fontSize=6,
                    textColor=self.COLORS['light_text'],
                    spaceAfter=8
                )
            )
            elements.append(keywords_para)

        elements.append(Spacer(1, 4))
        sep = Table([['']], colWidths=[186*mm])
        sep.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, self.COLORS['border']),
        ]))
        elements.append(sep)
        elements.append(Spacer(1, 4))

        return elements

    def _build_footer(self, data: Dict) -> List:
        elements = []
        elements.append(Spacer(1, 15))

        footer_text = f"""
        <i>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</i><br/>
        <i>Source: GKToday.in | For exam preparation purposes only</i><br/>
        <i>Visit original source for detailed analysis</i>
        """
        footer = Paragraph(footer_text, self.styles['Footer'])
        elements.append(footer)

        return elements

    def _add_page_decorations(self, canvas, doc):
        canvas.saveState()

        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(self.COLORS['light_text'])
        canvas.drawRightString(195*mm, 10*mm, text)

        if page_num > 1:
            canvas.setStrokeColor(self.COLORS['primary'])
            canvas.setLineWidth(0.5)
            canvas.line(12*mm, 280*mm, 198*mm, 280*mm)
            canvas.setFont('Helvetica-Bold', 7)
            canvas.setFillColor(self.COLORS['primary'])
            canvas.drawString(12*mm, 282*mm, "GKToday Daily Digest")

        canvas.restoreState()


class GKTodayPipeline:
    """Complete pipeline"""

    def __init__(self, output_dir: str = 'output', github_repo: str = None, telegram_token: str = None, telegram_chat_id: str = None):
        self.scraper = GKTodayScraper()
        self.generator = ExamPDFGenerator(f'{output_dir}/pdfs')
        self.output_dir = output_dir
        self.github_repo = github_repo
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id

        os.makedirs(f'{output_dir}/json', exist_ok=True)
        os.makedirs(f'{output_dir}/pdfs', exist_ok=True)

    def run_daily(self, target_date: datetime = None) -> Dict:
        if not target_date:
            target_date = datetime.now()

        logger.info(f"Starting daily pipeline for {target_date.strftime('%Y-%m-%d')}")

        # 1. Scrape
        data = self.scraper.scrape_daily(target_date)

        if not data.get('success'):
            logger.error(f"Scraping failed: {data.get('error')}")
            return data

        # 2. Save JSON
        json_path = f"{self.output_dir}/json/GKToday_{data['date']}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # 3. Generate PDF
        pdf_path = f"{self.output_dir}/pdfs/GKToday_{data['date']}.pdf"
        self.generator.generate_pdf(data, pdf_path)

        # 4. Commit to GitHub
        if self.github_repo:
            self._commit_to_github(data['date'], json_path, pdf_path)

        # 5. Send Telegram
        if self.telegram_token and self.telegram_chat_id:
            self._send_telegram(data, pdf_path)

        return {
            'success': True,
            'date': data['date'],
            'articles': data['total_articles'],
            'pdf_path': pdf_path,
            'json_path': json_path
        }

    def _commit_to_github(self, date_str: str, json_path: str, pdf_path: str):
        import subprocess
        try:
            repo_json = f"{self.github_repo}/data/json/{date_str}.json"
            repo_pdf = f"{self.github_repo}/data/pdfs/{date_str}.pdf"

            os.makedirs(os.path.dirname(repo_json), exist_ok=True)
            os.makedirs(os.path.dirname(repo_pdf), exist_ok=True)

            import shutil
            shutil.copy(json_path, repo_json)
            shutil.copy(pdf_path, repo_pdf)

            subprocess.run(['git', '-C', self.github_repo, 'add', '.'], check=True)
            subprocess.run([
                'git', '-C', self.github_repo, 'commit', '-m',
                f"GKToday digest: {date_str}"
            ], check=True)
            subprocess.run(['git', '-C', self.github_repo, 'push'], check=True)

            logger.info(f"Committed to GitHub: {date_str}")
        except Exception as e:
            logger.error(f"GitHub commit failed: {e}")

    def _send_telegram(self, data: Dict, pdf_path: str):
        import requests as req
        try:
            # Send notification
            message = f"""📰 GKToday Daily Digest: {data.get('display_date', data['date'])}

📊 {data['total_articles']} Articles
🔗 Source: GKToday.in

PDF attached below."""

            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            req.post(url, json={
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }, timeout=30)

            # Send PDF
            with open(pdf_path, 'rb') as f:
                url = f"https://api.telegram.org/bot{self.telegram_token}/sendDocument"
                req.post(url, files={'document': f}, data={
                    'chat_id': self.telegram_chat_id,
                    'caption': f'📰 GKToday_{data["date"]}.pdf'
                }, timeout=60)

            logger.info("Telegram notification sent")
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='GKToday Daily Scraper')
    parser.add_argument('--daily', action='store_true', help='Run for today')
    parser.add_argument('--date', type=str, help='Specific date (YYYY-MM-DD)')
    parser.add_argument('--output', default='output', help='Output directory')
    parser.add_argument('--github', help='GitHub repo path')
    parser.add_argument('--telegram', help='Telegram bot token')
    parser.add_argument('--chat-id', help='Telegram chat ID')

    args = parser.parse_args()

    pipeline = GKTodayPipeline(
        output_dir=args.output,
        github_repo=args.github,
        telegram_token=args.telegram,
        telegram_chat_id=args.chat_id
    )

    if args.date:
        date = datetime.strptime(args.date, '%Y-%m-%d')
        result = pipeline.run_daily(date)
    else:
        result = pipeline.run_daily()

    print(json.dumps(result, indent=2))

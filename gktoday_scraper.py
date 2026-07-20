
"""
GKToday Daily Scraper + Professional PDF Generator
=================================================
Architecture:
- Scraper: Extracts structured data from GKToday daily pages
- Analyzer: Tags content by exam relevance (MPSC/UPSC syllabus mapping)
- Formatter: Generates professional PDF with exam-oriented structure
- Publisher: Commits to GitHub + sends via Telegram
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import re
import os
from typing import List, Dict, Optional
import logging

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
        logging.FileHandler('gktoday_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GKTodayScraper:
    """Scrapes GKToday daily content with structured extraction"""

    BASE_URL = "https://www.gktoday.in/current-affairs/"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })

    def get_daily_url(self, date: datetime) -> str:
        """Generate GKToday URL for specific date"""
        return f"{self.BASE_URL}{date.strftime('%B').lower()}-{date.day}-{date.year}/"

    def scrape_day(self, date: datetime) -> Dict:
        """Scrape a single day's content"""
        url = self.get_daily_url(date)
        logger.info(f"Scraping: {url}")

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract date from page
        date_header = self._extract_date(soup)

        # Extract all news sections
        sections = self._extract_sections(soup)

        # Extract MCQs if present
        mcqs = self._extract_mcqs(soup)

        return {
            'date': date.strftime('%Y-%m-%d'),
            'display_date': date_header or date.strftime('%B %d, %Y'),
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'sections': sections,
            'mcqs': mcqs,
            'total_articles': sum(len(s['articles']) for s in sections),
            'total_mcqs': len(mcqs)
        }

    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the date displayed on the page"""
        # Try multiple selectors
        selectors = [
            'h1.entry-title',
            'h1.post-title',
            '.page-title',
            'article h1',
            'h1'
        ]
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)
        return None

    def _extract_sections(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract categorized news sections"""
        sections = []

        # GKToday typically uses h2 or h3 for section headers
        # followed by article divs
        content_area = soup.select_one('.entry-content, .post-content, article, .content-area')

        if not content_area:
            logger.warning("Could not find main content area")
            return sections

        current_section = None
        current_articles = []

        for elem in content_area.find_all(['h2', 'h3', 'h4', 'div', 'p']):
            text = elem.get_text(strip=True)

            # Check if this is a section header (typically bold, short, uppercase pattern)
            if elem.name in ['h2', 'h3', 'h4'] or self._is_section_header(elem):
                # Save previous section if exists
                if current_section and current_articles:
                    sections.append({
                        'title': current_section,
                        'articles': current_articles,
                        'article_count': len(current_articles)
                    })

                current_section = text
                current_articles = []

            # Check if this is an article (has title + content pattern)
            elif self._is_article(elem):
                article = self._parse_article(elem)
                if article:
                    current_articles.append(article)

        # Don't forget last section
        if current_section and current_articles:
            sections.append({
                'title': current_section,
                'articles': current_articles,
                'article_count': len(current_articles)
            })

        # If no sections found, try alternative parsing
        if not sections:
            sections = self._fallback_parse(content_area)

        return sections

    def _is_section_header(self, elem) -> bool:
        """Detect if element is a section header"""
        text = elem.get_text(strip=True)
        # Section headers are typically short, may contain keywords
        section_keywords = [
            'national', 'international', 'economy', 'science', 'environment',
            'polity', 'defence', 'art', 'culture', 'sports', 'important days',
            'persons in news', 'appointments', 'awards', 'obituaries',
            'banking', 'technology', 'agriculture', 'health', 'education'
        ]
        return any(kw in text.lower() for kw in section_keywords) and len(text) < 100

    def _is_article(self, elem) -> bool:
        """Detect if element contains a news article"""
        text = elem.get_text(strip=True)
        # Articles typically have substantial content
        return len(text) > 100 and len(text) < 5000

    def _parse_article(self, elem) -> Optional[Dict]:
        """Parse a single article from HTML element"""
        text = elem.get_text(strip=True)

        # Try to extract title (first sentence or bold text)
        title = self._extract_title(elem)

        # Extract key points (bullet lists or numbered items)
        key_points = self._extract_key_points(elem)

        # Extract main content (paragraphs)
        content = self._extract_content(elem)

        # Try to identify exam relevance
        relevance = self._assess_relevance(text)

        return {
            'title': title or text[:100] + '...',
            'content': content,
            'key_points': key_points,
            'word_count': len(text.split()),
            'relevance': relevance,
            'has_numbers': bool(re.search(r'\d+', text)),
            'has_quotes': '"' in text or "'" in text
        }

    def _extract_title(self, elem) -> Optional[str]:
        """Extract article title from element"""
        # Try bold text first
        bold = elem.find(['b', 'strong'])
        if bold:
            return bold.get_text(strip=True)

        # Try first sentence
        text = elem.get_text(strip=True)
        sentences = text.split('.')
        if sentences:
            first = sentences[0].strip()
            if 20 < len(first) < 200:
                return first

        return None

    def _extract_key_points(self, elem) -> List[str]:
        """Extract bullet points or key facts"""
        points = []

        # Find bullet lists
        for li in elem.find_all('li'):
            text = li.get_text(strip=True)
            if text and len(text) > 20:
                points.append(text)

        # Find numbered items
        for num in elem.find_all(['ol li', '.numbered']):
            text = num.get_text(strip=True)
            if text and len(text) > 20:
                points.append(text)

        # If no structured list, extract sentences with key indicators
        if not points:
            text = elem.get_text(strip=True)
            sentences = re.split(r'(?<=[.!?])\s+', text)
            for sent in sentences:
                if any(kw in sent.lower() for kw in ['first', 'largest', 'only', 'signed', 'launched', 'announced', 'approved', 'inaugurated']):
                    points.append(sent.strip())

        return points[:5]  # Limit to top 5 points

    def _extract_content(self, elem) -> str:
        """Extract clean article content"""
        # Remove scripts, styles
        for script in elem.find_all(['script', 'style']):
            script.decompose()

        text = elem.get_text(separator='\n', strip=True)
        # Clean up excessive whitespace
        text = re.sub(r'\n+', '\n', text)
        return text.strip()

    def _assess_relevance(self, text: str) -> Dict:
        """Assess exam relevance for MPSC/UPSC"""
        text_lower = text.lower()

        # High relevance keywords
        high_keywords = [
            'maharashtra', 'mumbai', 'pune', 'nagpur', 'thane', 'nashik',
            'constitution', 'parliament', 'supreme court', 'amendment',
            'scheme', 'policy', 'mission', 'programme', 'yojana',
            'gdp', 'inflation', 'budget', 'reserve bank', 'rbi',
            'agriculture', 'farmer', 'crop', 'msp', 'irrigation',
            'climate', 'environment', 'pollution', 'renewable',
            'defence', 'missile', 'satellite', 'space', 'isro',
            'appointment', 'election', 'cabinet', 'minister'
        ]

        # Medium relevance
        medium_keywords = [
            'india', 'state', 'government', 'union', 'ministry',
            'world', 'country', 'international', 'summit', 'treaty',
            'bank', 'finance', 'economy', 'trade', 'export', 'import',
            'technology', 'digital', 'ai', 'cyber', 'internet',
            'health', 'disease', 'vaccine', 'medical',
            'education', 'university', 'school', 'student',
            'sports', 'olympic', 'cricket', 'tournament'
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

    def _fallback_parse(self, content_area) -> List[Dict]:
        """Fallback parsing when standard structure not detected"""
        sections = []
        all_text = content_area.get_text(separator='\n', strip=True)
        paragraphs = [p.strip() for p in all_text.split('\n') if len(p.strip()) > 50]

        # Group into generic section
        articles = []
        for i, para in enumerate(paragraphs):
            articles.append({
                'title': para[:100] + '...' if len(para) > 100 else para,
                'content': para,
                'key_points': [para[:200]],
                'word_count': len(para.split()),
                'relevance': self._assess_relevance(para),
                'has_numbers': bool(re.search(r'\d+', para)),
                'has_quotes': '"' in para
            })

        sections.append({
            'title': 'Current Affairs',
            'articles': articles,
            'article_count': len(articles)
        })

        return sections

    def _extract_mcqs(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract MCQs if present on the page"""
        mcqs = []

        # Look for MCQ containers
        mcq_containers = soup.find_all(['div', 'section'], class_=re.compile(r'mcq|quiz|question', re.I))

        for container in mcq_containers:
            questions = container.find_all(['div', 'p'], class_=re.compile(r'question', re.I))
            for q in questions:
                text = q.get_text(strip=True)
                if '?' in text:
                    # Extract options
                    options = []
                    for opt in q.find_all(['li', 'div'], class_=re.compile(r'option', re.I)):
                        options.append(opt.get_text(strip=True))

                    mcqs.append({
                        'question': text,
                        'options': options,
                        'has_answer': 'answer' in text.lower() or bool(q.find(class_=re.compile(r'answer', re.I)))
                    })

        return mcqs

    def scrape_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Scrape multiple days"""
        results = []
        current = start_date

        while current <= end_date:
            day_data = self.scrape_day(current)
            if day_data:
                results.append(day_data)
            current += timedelta(days=1)

        return results


class ExamPDFGenerator:
    """Generates professional exam-oriented PDFs from scraped data"""

    # Color scheme - professional, easy on eyes
    COLORS = {
        'primary': HexColor('#1a5276'),      # Deep blue
        'secondary': HexColor('#2874a6'),   # Medium blue
        'accent': HexColor('#e74c3c'),      # Red for important
        'highlight': HexColor('#f39c12'),   # Orange for key points
        'success': HexColor('#27ae60'),     # Green for positive
        'text': HexColor('#2c3e50'),        # Dark gray
        'light_text': HexColor('#7f8c8d'),  # Light gray
        'bg_light': HexColor('#f8f9fa'),    # Very light gray
        'border': HexColor('#bdc3c7'),      # Border gray
    }

    def __init__(self, output_dir: str = 'pdfs'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.styles = self._create_styles()

    def _create_styles(self) -> Dict:
        """Create professional paragraph styles"""
        styles = getSampleStyleSheet()

        # Title style
        styles.add(ParagraphStyle(
            'ExamTitle',
            parent=styles['Heading1'],
            fontSize=24,
            leading=30,
            textColor=self.COLORS['primary'],
            alignment=TA_CENTER,
            spaceAfter=20,
            fontName='Helvetica-Bold'
        ))

        # Date subtitle
        styles.add(ParagraphStyle(
            'DateSubtitle',
            parent=styles['Normal'],
            fontSize=14,
            leading=18,
            textColor=self.COLORS['light_text'],
            alignment=TA_CENTER,
            spaceAfter=30,
            fontName='Helvetica'
        ))

        # Section header
        styles.add(ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=16,
            leading=20,
            textColor=self.COLORS['primary'],
            spaceBefore=20,
            spaceAfter=12,
            borderColor=self.COLORS['primary'],
            borderWidth=2,
            borderPadding=5,
            leftIndent=0,
            fontName='Helvetica-Bold'
        ))

        # Article title
        styles.add(ParagraphStyle(
            'ArticleTitle',
            parent=styles['Heading3'],
            fontSize=12,
            leading=16,
            textColor=self.COLORS['secondary'],
            spaceBefore=12,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))

        # Article content
        styles.add(ParagraphStyle(
            'ArticleContent',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=self.COLORS['text'],
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            fontName='Helvetica'
        ))

        # Key points
        styles.add(ParagraphStyle(
            'KeyPoint',
            parent=styles['Normal'],
            fontSize=9,
            leading=13,
            textColor=self.COLORS['text'],
            leftIndent=20,
            spaceAfter=4,
            fontName='Helvetica'
        ))

        # Relevance badge
        styles.add(ParagraphStyle(
            'RelevanceHigh',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.white,
            backColor=self.COLORS['accent'],
            alignment=TA_CENTER,
            spaceAfter=4,
            fontName='Helvetica-Bold'
        ))

        styles.add(ParagraphStyle(
            'RelevanceMedium',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.white,
            backColor=self.COLORS['highlight'],
            alignment=TA_CENTER,
            spaceAfter=4,
            fontName='Helvetica-Bold'
        ))

        styles.add(ParagraphStyle(
            'RelevanceLow',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.white,
            backColor=self.COLORS['light_text'],
            alignment=TA_CENTER,
            spaceAfter=4,
            fontName='Helvetica-Bold'
        ))

        # Footer
        styles.add(ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=self.COLORS['light_text'],
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))

        # MCQ style
        styles.add(ParagraphStyle(
            'MCQQuestion',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=self.COLORS['text'],
            spaceBefore=10,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))

        styles.add(ParagraphStyle(
            'MCQOption',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=self.COLORS['text'],
            leftIndent=20,
            spaceAfter=2,
            fontName='Helvetica'
        ))

        return styles

    def generate_pdf(self, data: Dict, output_path: Optional[str] = None) -> str:
        """Generate professional PDF from scraped data"""

        if not output_path:
            date_str = data['date']
            output_path = f"{self.output_dir}/GKToday_{date_str}.pdf"

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )

        story = []

        # ===== HEADER SECTION =====
        story.extend(self._build_header(data))

        # ===== SUMMARY TABLE =====
        story.extend(self._build_summary(data))

        story.append(Spacer(1, 20))

        # ===== CONTENT SECTIONS =====
        for section in data['sections']:
            story.extend(self._build_section(section))

        # ===== MCQ SECTION =====
        if data.get('mcqs'):
            story.extend(self._build_mcq_section(data['mcqs']))

        # ===== FOOTER =====
        story.extend(self._build_footer(data))

        # Build PDF
        doc.build(story, onFirstPage=self._add_page_decorations, onLaterPages=self._add_page_decorations)

        logger.info(f"PDF generated: {output_path}")
        return output_path

    def _build_header(self, data: Dict) -> List:
        """Build professional header"""
        elements = []

        # Main title
        title = Paragraph(
            f'<b>GK TODAY</b><br/><font size=16>Current Affairs Daily Digest</font>',
            self.styles['ExamTitle']
        )
        elements.append(title)

        # Date
        date_para = Paragraph(
            f"{data['display_date']} | {data['total_articles']} Articles | {data['total_mcqs']} MCQs",
            self.styles['DateSubtitle']
        )
        elements.append(date_para)

        # Decorative line
        elements.append(Spacer(1, 10))
        line_table = Table([['']], colWidths=[180*mm])
        line_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, 0), 2, self.COLORS['primary']),
            ('TOPPADDING', (0, 0), (-1, 0), 0),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
        ]))
        elements.append(line_table)
        elements.append(Spacer(1, 15))

        return elements

    def _build_summary(self, data: Dict) -> List:
        """Build summary statistics table"""
        elements = []

        # Count articles by relevance
        high_count = sum(1 for s in data['sections'] for a in s['articles'] if a['relevance']['level'] == 'HIGH')
        medium_count = sum(1 for s in data['sections'] for a in s['articles'] if a['relevance']['level'] == 'MEDIUM')
        low_count = sum(1 for s in data['sections'] for a in s['articles'] if a['relevance']['level'] == 'LOW')

        summary_data = [
            ['📊 EXAM RELEVANCE SUMMARY', '', '', ''],
            ['', '', '', ''],
            ['🔴 HIGH Priority', str(high_count), '🟡 MEDIUM Priority', str(medium_count)],
            ['🟢 LOW Priority', str(low_count), '📰 Total Articles', str(data['total_articles'])],
            ['📝 Total MCQs', str(data['total_mcqs']), '🔗 Source', 'GKToday.in'],
        ]

        summary_table = Table(summary_data, colWidths=[45*mm, 25*mm, 45*mm, 25*mm])
        summary_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('SPAN', (0, 0), (-1, 0)),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),

            # Data rows
            ('BACKGROUND', (0, 2), (-1, -1), self.COLORS['bg_light']),
            ('TEXTCOLOR', (0, 2), (-1, -1), self.COLORS['text']),
            ('FONTNAME', (0, 2), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 2), (-1, -1), 9),
            ('ALIGN', (0, 2), (0, -1), 'LEFT'),
            ('ALIGN', (1, 2), (1, -1), 'CENTER'),
            ('ALIGN', (2, 2), (2, -1), 'LEFT'),
            ('ALIGN', (3, 2), (3, -1), 'CENTER'),
            ('TOPPADDING', (0, 2), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 2), (-1, -1), 6),
            ('LEFTPADDING', (0, 2), (-1, -1), 8),
            ('RIGHTPADDING', (0, 2), (-1, -1), 8),

            # Grid
            ('GRID', (0, 1), (-1, -1), 0.5, self.COLORS['border']),
            ('BOX', (0, 0), (-1, -1), 1, self.COLORS['primary']),
        ]))

        elements.append(summary_table)
        return elements

    def _build_section(self, section: Dict) -> List:
        """Build a news section"""
        elements = []

        # Section header with badge
        section_title = f"📌 {section['title']} ({section['article_count']} articles)"
        header = Paragraph(section_title, self.styles['SectionHeader'])
        elements.append(header)
        elements.append(Spacer(1, 8))

        # Articles
        for article in section['articles']:
            elements.extend(self._build_article(article))

        elements.append(Spacer(1, 15))
        return elements

    def _build_article(self, article: Dict) -> List:
        """Build a single article block"""
        elements = []

        # Relevance badge
        relevance = article['relevance']
        if relevance['level'] == 'HIGH':
            badge_style = 'RelevanceHigh'
            badge_text = '⭐ HIGH PRIORITY'
        elif relevance['level'] == 'MEDIUM':
            badge_style = 'RelevanceMedium'
            badge_text = 'MEDIUM'
        else:
            badge_style = 'RelevanceLow'
            badge_text = 'LOW'

        badge = Paragraph(badge_text, self.styles[badge_style])
        elements.append(badge)

        # Article title
        title = Paragraph(f"<b>{article['title']}</b>", self.styles['ArticleTitle'])
        elements.append(title)

        # Key points (if available)
        if article['key_points']:
            elements.append(Paragraph("<b>Key Points:</b>", self.styles['ArticleContent']))
            for point in article['key_points']:
                # Clean up the point text for PDF
                clean_point = point.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                elements.append(Paragraph(f"• {clean_point}", self.styles['KeyPoint']))

        # Main content (truncated if too long, since key points are prioritized)
        content = article['content']
        if len(content) > 500:
            content = content[:500] + "..."

        # Clean content for PDF
        clean_content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        content_para = Paragraph(clean_content, self.styles['ArticleContent'])
        elements.append(content_para)

        # Relevance keywords
        if relevance['matched_keywords']:
            keywords_text = ', '.join(relevance['matched_keywords'])
            keywords_para = Paragraph(
                f"<i>Tags: {keywords_text}</i>",
                ParagraphStyle(
                    'Keywords',
                    parent=self.styles['Normal'],
                    fontSize=7,
                    textColor=self.COLORS['light_text'],
                    spaceAfter=10
                )
            )
            elements.append(keywords_para)

        # Separator line
        elements.append(Spacer(1, 5))
        sep = Table([['']], colWidths=[180*mm])
        sep.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, self.COLORS['border']),
        ]))
        elements.append(sep)
        elements.append(Spacer(1, 5))

        return elements

    def _build_mcq_section(self, mcqs: List[Dict]) -> List:
        """Build MCQ section"""
        elements = []

        elements.append(PageBreak())

        # Section header
        mcq_header = Paragraph("<b>📝 PRACTICE MCQs</b>", self.styles['SectionHeader'])
        elements.append(mcq_header)
        elements.append(Paragraph("<i>Test your understanding of today's current affairs</i>", self.styles['DateSubtitle']))
        elements.append(Spacer(1, 15))

        for i, mcq in enumerate(mcqs, 1):
            # Question
            question_text = f"Q{i}. {mcq['question']}"
            clean_q = question_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            elements.append(Paragraph(clean_q, self.styles['MCQQuestion']))

            # Options
            for j, option in enumerate(mcq['options'], 1):
                clean_opt = option.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                elements.append(Paragraph(f"   {chr(64+j)}. {clean_opt}", self.styles['MCQOption']))

            elements.append(Spacer(1, 10))

        return elements

    def _build_footer(self, data: Dict) -> List:
        """Build footer"""
        elements = []

        elements.append(Spacer(1, 20))

        footer_text = f"""
        <i>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</i><br/>
        <i>Source: GKToday.in | This is an automated digest for exam preparation purposes</i><br/>
        <i>For detailed analysis, visit the original source</i>
        """
        footer = Paragraph(footer_text, self.styles['Footer'])
        elements.append(footer)

        return elements

    def _add_page_decorations(self, canvas, doc):
        """Add page numbers and decorations"""
        canvas.saveState()

        # Page number
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(self.COLORS['light_text'])
        canvas.drawRightString(195*mm, 10*mm, text)

        # Header line on later pages
        if page_num > 1:
            canvas.setStrokeColor(self.COLORS['primary'])
            canvas.setLineWidth(0.5)
            canvas.line(15*mm, 280*mm, 195*mm, 280*mm)

            # Small header text
            canvas.setFont('Helvetica-Bold', 8)
            canvas.setFillColor(self.COLORS['primary'])
            canvas.drawString(15*mm, 282*mm, "GKToday Daily Digest")

        canvas.restoreState()


class GKTodayPipeline:
    """Complete pipeline: Scrape → Analyze → PDF → GitHub → Telegram"""

    def __init__(self, output_dir: str = 'output', github_repo: str = None, telegram_token: str = None):
        self.scraper = GKTodayScraper()
        self.generator = ExamPDFGenerator(output_dir)
        self.output_dir = output_dir
        self.github_repo = github_repo
        self.telegram_token = telegram_token

        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(f'{output_dir}/json', exist_ok=True)
        os.makedirs(f'{output_dir}/pdfs', exist_ok=True)

    def run_daily(self, date: datetime = None) -> Dict:
        """Run complete daily pipeline"""
        if not date:
            date = datetime.now() - timedelta(days=1)  # Yesterday's content

        logger.info(f"Starting daily pipeline for {date.strftime('%Y-%m-%d')}")

        # 1. Scrape
        data = self.scraper.scrape_day(date)
        if not data:
            logger.error("Scraping failed")
            return {'success': False, 'error': 'Scraping failed'}

        # 2. Save JSON
        json_path = f"{self.output_dir}/json/GKToday_{data['date']}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # 3. Generate PDF
        pdf_path = f"{self.output_dir}/pdfs/GKToday_{data['date']}.pdf"
        self.generator.generate_pdf(data, pdf_path)

        # 4. Commit to GitHub (if configured)
        if self.github_repo:
            self._commit_to_github(data['date'], json_path, pdf_path)

        # 5. Send Telegram notification (if configured)
        if self.telegram_token:
            self._send_telegram(data, pdf_path)

        return {
            'success': True,
            'date': data['date'],
            'articles': data['total_articles'],
            'mcqs': data['total_mcqs'],
            'pdf_path': pdf_path,
            'json_path': json_path
        }

    def run_batch(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Run batch for date range"""
        results = []
        current = start_date

        while current <= end_date:
            result = self.run_daily(current)
            results.append(result)
            current += timedelta(days=1)

        return results

    def _commit_to_github(self, date_str: str, json_path: str, pdf_path: str):
        """Commit files to GitHub"""
        import subprocess

        try:
            # Copy to repo
            repo_json = f"{self.github_repo}/data/json/{date_str}.json"
            repo_pdf = f"{self.github_repo}/data/pdfs/{date_str}.pdf"

            os.makedirs(os.path.dirname(repo_json), exist_ok=True)
            os.makedirs(os.path.dirname(repo_pdf), exist_ok=True)

            import shutil
            shutil.copy(json_path, repo_json)
            shutil.copy(pdf_path, repo_pdf)

            # Git commit
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
        """Send PDF via Telegram"""
        import requests as req

        try:
            # Send notification message
            message = f"""📰 GKToday Daily Digest: {data['display_date']}

📊 {data['total_articles']} Articles | {data['total_mcqs']} MCQs
🔗 Source: GKToday.in

PDF attached below."""

            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            req.post(url, json={
                'chat_id': 'YOUR_CHAT_ID',
                'text': message,
                'parse_mode': 'HTML'
            })

            # Send PDF
            with open(pdf_path, 'rb') as f:
                url = f"https://api.telegram.org/bot{self.telegram_token}/sendDocument"
                req.post(url, files={'document': f}, data={
                    'chat_id': 'YOUR_CHAT_ID',
                    'caption': f'GKToday_{data["date"]}.pdf'
                })

            logger.info("Telegram notification sent")
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")


# ===== SCHEDULER FOR OLD LAPTOP =====
"""
Add to crontab (Linux/Mac) or Task Scheduler (Windows):

# Daily at 8 AM
0 8 * * * cd /path/to/project && /usr/bin/python3 gktoday_scraper.py --daily

# Or use GitHub Actions for cloud scheduling (free)
"""

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='GKToday Daily Scraper')
    parser.add_argument('--daily', action='store_true', help='Run for yesterday')
    parser.add_argument('--date', type=str, help='Specific date (YYYY-MM-DD)')
    parser.add_argument('--range', nargs=2, metavar=('START', 'END'), help='Date range (YYYY-MM-DD YYYY-MM-DD)')
    parser.add_argument('--output', default='output', help='Output directory')
    parser.add_argument('--github', help='GitHub repo path')
    parser.add_argument('--telegram', help='Telegram bot token')

    args = parser.parse_args()

    pipeline = GKTodayPipeline(
        output_dir=args.output,
        github_repo=args.github,
        telegram_token=args.telegram
    )

    if args.daily:
        result = pipeline.run_daily()
        print(json.dumps(result, indent=2))
    elif args.date:
        date = datetime.strptime(args.date, '%Y-%m-%d')
        result = pipeline.run_daily(date)
        print(json.dumps(result, indent=2))
    elif args.range:
        start = datetime.strptime(args.range[0], '%Y-%m-%d')
        end = datetime.strptime(args.range[1], '%Y-%m-%d')
        results = pipeline.run_batch(start, end)
        print(f"Processed {len(results)} days")
    else:
        # Default: run for yesterday
        result = pipeline.run_daily()
        print(json.dumps(result, indent=2))

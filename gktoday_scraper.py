#!/usr/bin/env python3
"""
GKToday Scraper v4 - Clean extraction, no duplicates, proper structure
"""

import requests
from bs4 import BeautifulSoup, NavigableString, Comment
import json
from datetime import datetime
import re
import os
import sys
import time

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
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


class GKTodayScraper:
    BASE_URL = "https://www.gktoday.in"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch(self, url):
        try:
            r = self.session.get(url, timeout=30)
            r.raise_for_status()
            return r.text
        except Exception as e:
            logger.error("Fetch failed: %s - %s", url, e)
            return None
    
    def scrape_articles(self):
        html = self.fetch(self.BASE_URL)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove ALL junk: scripts, styles, nav, ads, sidebars, comments
        for tag in ['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'iframe']:
            for t in soup.find_all(tag):
                t.decompose()
        
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Find main content area
        main_content = None
        selectors = [
            'div.site-content',
            'div.content-area',
            'main',
            'div#main',
            'div.entry-content',
            'article',
        ]
        
        for sel in selectors:
            found = soup.select(sel)
            if found:
                main_content = found[0]
                logger.info("Main content: %s", sel)
                break
        
        if not main_content:
            main_content = soup.find('body')
        
        # Find h3 headings with links = actual articles
        articles = []
        seen_titles = set()
        
        headings = main_content.find_all(['h3', 'h2'])
        logger.info("Found %d headings", len(headings))
        
        for heading in headings:
            article = self._parse_article_clean(heading, seen_titles)
            if article:
                articles.append(article)
        
        logger.info("Parsed %d unique articles", len(articles))
        return articles
    
    def _parse_article_clean(self, heading, seen_titles):
        """Parse single article with clean extraction from parent container"""
        try:
            link = heading.find('a')
            if not link:
                return None
            
            title = link.get_text(strip=True)
            url = link.get('href', '')
            
            if not title or len(title) < 10:
                return None
            
            # Skip duplicates
            if title in seen_titles:
                return None
            seen_titles.add(title)
            
            # Skip non-articles
            skip = ['gk today', 'home', 'about', 'contact', 'privacy', 'subscribe', 'categories', 'tags', 'archives', 'search']
            if any(s in title.lower() for s in skip):
                return None
            
            if not url.startswith('http'):
                url = self.BASE_URL + url if url.startswith('/') else self.BASE_URL + '/' + url
            
            # Find the article's parent container
            container = heading.find_parent(['article', 'div', 'section'])
            
            content_text = ""
            category = "General"
            date_text = ""
            
            if container:
                # Get text from container, excluding nested headings
                texts = []
                for elem in container.find_all(['p', 'div', 'span']):
                    # Skip if inside sidebar/nav
                    if elem.find_parent(['aside', 'nav', 'header', 'footer']):
                        continue
                    
                    txt = elem.get_text(strip=True)
                    if txt and len(txt) > 30 and txt != title:
                        # Check category/date
                        if len(txt) < 80 and any(c in txt.lower() for c in ['current affairs', 'national', 'international', 'economy', 'science', 'sports', 'defence', 'legal', 'government', 'art', 'culture', 'environment', 'persons', 'awards', 'banking', 'technology', 'agriculture', 'health', 'education']):
                            category = txt
                        elif re.search(r'\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}', txt, re.IGNORECASE):
                            date_text = txt
                        elif txt not in texts:  # Avoid duplicates
                            texts.append(txt)
                
                content_text = ' '.join(texts)
            
            # Fallback: siblings if no container
            if not content_text:
                sibling = heading.next_sibling
                texts = []
                while sibling:
                    if isinstance(sibling, NavigableString):
                        t = str(sibling).strip()
                        if t and len(t) > 30:
                            texts.append(t)
                    elif sibling.name and sibling.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'script', 'style']:
                        t = sibling.get_text(strip=True)
                        if t and len(t) > 30 and t != title and t not in texts:
                            texts.append(t)
                    
                    sibling = sibling.next_sibling if hasattr(sibling, 'next_sibling') else None
                    if len(' '.join(texts)) > 1500:
                        break
                
                content_text = ' '.join(texts)
            
            # Clean up
            content_text = re.sub(r'\s+', ' ', content_text).strip()
            content_text = content_text.replace(title, '').strip()
            
            if len(content_text) > 1000:
                content_text = content_text[:1000] + "..."
            
            return {
                'title': title,
                'url': url,
                'date': date_text,
                'category': category,
                'content': content_text,
                'key_points': self._key_points(content_text),
                'relevance': self._relevance(title + ' ' + content_text)
            }
            
        except Exception as e:
            logger.warning("Error: %s", e)
            return None
    
    def _key_points(self, text):
        if not text:
            return []
        pts = []
        for s in re.split(r'(?<=[.!?])\s+', text):
            indicators = ['first', 'largest', 'only', 'signed', 'launched', 'announced', 'approved', 'inaugurated', 'appointed', 'elected', 'unveiled', 'banned', 'introduced', 'passed', 'agreement', 'treaty', 'scheme', 'programme', 'mission', 'yojana', 'billion', 'million', 'crore', 'percent', 'minister', 'president', 'prime minister', 'chief minister', 'state', 'union', 'government', 'cabinet', 'parliament', 'constitution', 'amendment', 'supreme court', 'budget', 'gdp', 'inflation', 'rbi', 'isro', 'drdo', 'space', 'satellite', 'missile', 'defence', 'agriculture', 'farmer', 'crop', 'msp', 'climate', 'environment', 'pollution', 'appointment', 'election', 'welfare', 'health', 'education']
            score = sum(1 for ind in indicators if ind in s.lower())
            if score >= 2 and 30 < len(s) < 300:
                pts.append(s.strip())
        return pts[:5]
    
    def _relevance(self, text):
        t = text.lower()
        high = ['maharashtra', 'mumbai', 'pune', 'nagpur', 'thane', 'nashik', 'solapur', 'kolhapur', 'aurangabad', 'constitution', 'parliament', 'supreme court', 'amendment', 'article', 'schedule', 'fundamental', 'directive', 'scheme', 'policy', 'mission', 'programme', 'yojana', 'gdp', 'inflation', 'budget', 'reserve bank', 'rbi', 'agriculture', 'farmer', 'crop', 'msp', 'irrigation', 'climate', 'environment', 'pollution', 'renewable', 'defence', 'missile', 'satellite', 'space', 'isro', 'drdo', 'appointment', 'election', 'cabinet', 'minister', 'governor', 'welfare', 'social', 'health', 'education', 'digital', 'india', 'bharat', 'union']
        med = ['world', 'country', 'international', 'summit', 'treaty', 'bank', 'finance', 'economy', 'trade', 'export', 'import', 'technology', 'ai', 'cyber', 'internet', 'disease', 'vaccine', 'medical', 'university', 'school', 'student', 'sports', 'olympic', 'cricket', 'tournament', 'award', 'honour', 'prize', 'recognition']
        hs = sum(1 for k in high if k in t)
        ms = sum(1 for k in med if k in t)
        ts = hs * 2 + ms
        level = 'HIGH' if ts >= 5 else 'MEDIUM' if ts >= 2 else 'LOW'
        matched = [k for k in high + med if k in t][:5]
        return {'level': level, 'score': ts, 'matched_keywords': matched}
    
    def scrape_quiz(self):
        # Find quiz link on homepage
        home_html = self.fetch(self.BASE_URL)
        if not home_html:
            return []
        
        soup = BeautifulSoup(home_html, 'html.parser')
        
        quiz_url = None
        for a in soup.find_all('a', href=True):
            href = a.get('href', '').lower()
            text = a.get_text(strip=True).lower()
            if 'quiz' in href or 'quiz' in text:
                quiz_url = href if href.startswith('http') else self.BASE_URL + href if href.startswith('/') else self.BASE_URL + '/' + href
                logger.info("Quiz link: %s", quiz_url)
                break
        
        if not quiz_url:
            logger.warning("No quiz link found")
            return []
        
        # Fetch quiz
        quiz_html = self.fetch(quiz_url)
        if not quiz_html:
            return []
        
        questions = self._parse_quiz_page(quiz_html)
        
        # Check pagination
        quiz_soup = BeautifulSoup(quiz_html, 'html.parser')
        page_links = []
        for a in quiz_soup.find_all('a', href=True):
            href = a.get('href', '')
            text = a.get_text(strip=True)
            if text.isdigit() and int(text) > 1:
                page_url = href if href.startswith('http') else self.BASE_URL + href if href.startswith('/') else self.BASE_URL + '/' + href
                if page_url not in page_links:
                    page_links.append(page_url)
        
        logger.info("Quiz pages: %d", len(page_links) + 1)
        
        for page_url in page_links[:4]:
            time.sleep(1)
            page_html = self.fetch(page_url)
            if page_html:
                pq = self._parse_quiz_page(page_html)
                questions.extend(pq)
                logger.info("Page questions: %d", len(pq))
        
        logger.info("Total quiz: %d", len(questions))
        return questions
    
    def _parse_quiz_page(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        for tag in ['script', 'style', 'nav', 'header', 'footer']:
            for t in soup.find_all(tag):
                t.decompose()
        
        questions = []
        text = soup.get_text()
        
        # Split by question numbers
        q_blocks = re.split(r'(Q\.?\s*\d+\s*[\.:]?)', text, flags=re.IGNORECASE)
        
        if len(q_blocks) > 1:
            for i in range(1, len(q_blocks), 2):
                if i + 1 < len(q_blocks):
                    q_num_match = re.search(r'\d+', q_blocks[i])
                    q_num = int(q_num_match.group()) if q_num_match else 0
                    q_block = q_blocks[i] + q_blocks[i + 1]
                    
                    q = self._parse_quiz_block(q_num, q_block)
                    if q:
                        questions.append(q)
        
        return questions
    
    def _parse_quiz_block(self, q_num, block):
        # Extract question text
        q_match = re.search(r'Q\.?\s*\d+\s*[\.:]?\s*(.*?)(?=[a-d]\)|[A-D]\)|Answer|Explanation|$)', block, re.DOTALL | re.IGNORECASE)
        q_text = q_match.group(1).strip() if q_match else ""
        
        if not q_text or len(q_text) < 20:
            return None
        
        # Extract options
        options = []
        for letter in ['a', 'b', 'c', 'd']:
            pattern = re.compile(r'[\n\r\s]' + letter + r'[\)\.\s]\s*(.*?)(?=[\n\r\s][b-d][\)\.\s]|[\n\r\s]Answer|[\n\r\s]Explanation|$)', re.DOTALL | re.IGNORECASE)
            match = pattern.search(block)
            if match:
                options.append(match.group(1).strip()[:200])
        
        # Extract answer
        ans_match = re.search(r'Answer[\s:\.]+([a-dA-D])', block, re.IGNORECASE)
        answer = ans_match.group(1).upper() if ans_match else ''
        
        # Extract explanation
        exp_match = re.search(r'Explanation[\s:\.]+(.*?)(?=Q\.?\s*\d+|Question\s*\d+|$)', block, re.DOTALL | re.IGNORECASE)
        explanation = exp_match.group(1).strip()[:500] if exp_match else ''
        
        return {
            'number': q_num,
            'question': q_text[:300],
            'options': options,
            'answer': answer,
            'explanation': explanation
        }
    
    def scrape_all(self):
        articles = self.scrape_articles()
        quiz = self.scrape_quiz()
        
        sections = {}
        for a in articles:
            cat = a.get('category', 'General')
            sections.setdefault(cat, []).append(a)
        
        section_list = []
        for cat, arts in sections.items():
            section_list.append({'title': cat, 'articles': arts, 'article_count': len(arts)})
        section_list.sort(key=lambda x: x['article_count'], reverse=True)
        
        return {
            'success': True,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'display_date': datetime.now().strftime('%B %d, %Y'),
            'url': self.BASE_URL,
            'scraped_at': datetime.now().isoformat(),
            'sections': section_list,
            'total_articles': len(articles),
            'quiz': {'total_questions': len(quiz), 'questions': quiz},
            'total_mcqs': len(quiz)
        }


class PDFGenerator:
    def __init__(self, output_dir='output/pdfs'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.styles = self._make_styles()
    
    def _make_styles(self):
        s = getSampleStyleSheet()
        
        s.add(ParagraphStyle('GKTitle', parent=s['Heading1'], fontSize=24, leading=30,
            textColor=HexColor('#1a5276'), alignment=TA_CENTER, spaceAfter=6, fontName='Helvetica-Bold'))
        
        s.add(ParagraphStyle('GKSub', parent=s['Normal'], fontSize=10, leading=13,
            textColor=HexColor('#7f8c8d'), alignment=TA_CENTER, spaceAfter=16, fontName='Helvetica'))
        
        s.add(ParagraphStyle('GKSecHead', parent=s['Heading2'], fontSize=12, leading=16,
            textColor=HexColor('#1a5276'), spaceBefore=12, spaceAfter=4, fontName='Helvetica-Bold'))
        
        s.add(ParagraphStyle('GKArtTitle', parent=s['Heading3'], fontSize=9, leading=12,
            textColor=HexColor('#2874a6'), spaceBefore=6, spaceAfter=2, fontName='Helvetica-Bold'))
        
        s.add(ParagraphStyle('GKContent', parent=s['Normal'], fontSize=7, leading=10,
            textColor=HexColor('#2c3e50'), alignment=TA_JUSTIFY, spaceAfter=3, fontName='Helvetica'))
        
        s.add(ParagraphStyle('GKKeyPt', parent=s['Normal'], fontSize=6, leading=9,
            textColor=HexColor('#2c3e50'), leftIndent=10, spaceAfter=1, fontName='Helvetica'))
        
        s.add(ParagraphStyle('GKBadgeH', parent=s['Normal'], fontSize=5, leading=7,
            textColor=colors.white, backColor=HexColor('#e74c3c'), alignment=TA_CENTER,
            spaceAfter=1, fontName='Helvetica-Bold'))
        
        s.add(ParagraphStyle('GKBadgeM', parent=s['Normal'], fontSize=5, leading=7,
            textColor=colors.white, backColor=HexColor('#f39c12'), alignment=TA_CENTER,
            spaceAfter=1, fontName='Helvetica-Bold'))
        
        s.add(ParagraphStyle('GKBadgeL', parent=s['Normal'], fontSize=5, leading=7,
            textColor=colors.white, backColor=HexColor('#95a5a6'), alignment=TA_CENTER,
            spaceAfter=1, fontName='Helvetica-Bold'))
        
        s.add(ParagraphStyle('GKQuizHead', parent=s['Heading2'], fontSize=13, leading=17,
            textColor=HexColor('#1a5276'), spaceBefore=12, spaceAfter=8, alignment=TA_CENTER,
            fontName='Helvetica-Bold'))
        
        s.add(ParagraphStyle('GKQText', parent=s['Normal'], fontSize=8, leading=11,
            textColor=HexColor('#2c3e50'), spaceBefore=8, spaceAfter=3, fontName='Helvetica-Bold'))
        
        s.add(ParagraphStyle('GKQOpt', parent=s['Normal'], fontSize=7, leading=10,
            textColor=HexColor('#2c3e50'), leftIndent=12, spaceAfter=1, fontName='Helvetica'))
        
        s.add(ParagraphStyle('GKQAns', parent=s['Normal'], fontSize=7, leading=10,
            textColor=HexColor('#27ae60'), leftIndent=12, spaceAfter=3, fontName='Helvetica-Bold'))
        
        s.add(ParagraphStyle('GKQExp', parent=s['Normal'], fontSize=6, leading=9,
            textColor=HexColor('#7f8c8d'), leftIndent=12, spaceAfter=6, fontName='Helvetica-Oblique'))
        
        s.add(ParagraphStyle('GKFoot', parent=s['Normal'], fontSize=5, leading=8,
            textColor=HexColor('#7f8c8d'), alignment=TA_CENTER, fontName='Helvetica'))
        
        return s
    
    def _clean(self, text):
        if not text:
            return ''
        text = str(text)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('\n', '<br/>')
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        return text.strip()
    
    def generate(self, data, path=None):
        if not path:
            path = os.path.join(self.output_dir, "GKToday_" + data['date'] + ".pdf")
        
        doc = SimpleDocTemplate(path, pagesize=A4,
            rightMargin=10*mm, leftMargin=10*mm, topMargin=12*mm, bottomMargin=12*mm)
        
        story = []
        story.extend(self._header(data))
        story.extend(self._summary(data))
        story.append(Spacer(1, 10))
        
        for sec in data.get('sections', []):
            story.extend(self._section(sec))
        
        quiz = data.get('quiz', {})
        if quiz and quiz.get('questions'):
            story.extend(self._quiz(quiz))
        
        story.extend(self._footer())
        
        doc.build(story, onFirstPage=self._page_dec, onLaterPages=self._page_dec)
        logger.info("PDF generated: %s", path)
        return path
    
    def _header(self, data):
        els = []
        els.append(Paragraph("<b>GK TODAY</b><br/><font size=10>Current Affairs Daily Digest</font>", self.styles['GKTitle']))
        qc = data.get('quiz', {}).get('total_questions', 0)
        els.append(Paragraph("%s | %d Articles | %d Quiz Questions | Source: GKToday.in" % (data.get('display_date', data['date']), data['total_articles'], qc), self.styles['GKSub']))
        els.append(Spacer(1, 4))
        
        line = Table([['']], colWidths=[190*mm])
        line.setStyle(TableStyle([('LINEBELOW', (0,0), (-1,0), 1.5, HexColor('#1a5276'))]))
        els.append(line)
        els.append(Spacer(1, 8))
        return els
    
    def _summary(self, data):
        els = []
        h = sum(1 for s in data.get('sections',[]) for a in s.get('articles',[]) if a.get('relevance',{}).get('level')=='HIGH')
        m = sum(1 for s in data.get('sections',[]) for a in s.get('articles',[]) if a.get('relevance',{}).get('level')=='MEDIUM')
        l = sum(1 for s in data.get('sections',[]) for a in s.get('articles',[]) if a.get('relevance',{}).get('level')=='LOW')
        qc = data.get('quiz', {}).get('total_questions', 0)
        
        tbl = Table([
            ['EXAM RELEVANCE SUMMARY', '', '', ''],
            ['', '', '', ''],
            ['HIGH', str(h), 'MEDIUM', str(m)],
            ['LOW', str(l), 'Articles', str(data['total_articles'])],
            ['Quiz', str(qc), 'Source', 'GKToday.in'],
        ], colWidths=[48*mm, 22*mm, 48*mm, 22*mm])
        
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), HexColor('#1a5276')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 8),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('SPAN', (0,0), (-1,0)),
            ('TOPPADDING', (0,0), (-1,0), 4),
            ('BOTTOMPADDING', (0,0), (-1,0), 4),
            ('BACKGROUND', (0,2), (-1,-1), HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0,2), (-1,-1), HexColor('#2c3e50')),
            ('FONTNAME', (0,2), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,2), (-1,-1), 6),
            ('ALIGN', (0,2), (0,-1), 'LEFT'),
            ('ALIGN', (1,2), (1,-1), 'CENTER'),
            ('ALIGN', (2,2), (2,-1), 'LEFT'),
            ('ALIGN', (3,2), (3,-1), 'CENTER'),
            ('TOPPADDING', (0,2), (-1,-1), 3),
            ('BOTTOMPADDING', (0,2), (-1,-1), 3),
            ('LEFTPADDING', (0,2), (-1,-1), 4),
            ('RIGHTPADDING', (0,2), (-1,-1), 4),
            ('GRID', (0,1), (-1,-1), 0.5, HexColor('#bdc3c7')),
            ('BOX', (0,0), (-1,-1), 1, HexColor('#1a5276')),
        ]))
        
        els.append(tbl)
        return els
    
    def _section(self, sec):
        els = []
        els.append(Paragraph("%s (%d articles)" % (sec['title'], sec['article_count']), self.styles['GKSecHead']))
        els.append(Spacer(1, 2))
        
        for art in sec.get('articles', []):
            rel = art.get('relevance', {})
            lvl = rel.get('level', 'LOW')
            
            if lvl == 'HIGH':
                els.append(Paragraph("HIGH PRIORITY", self.styles['GKBadgeH']))
            elif lvl == 'MEDIUM':
                els.append(Paragraph("MEDIUM PRIORITY", self.styles['GKBadgeM']))
            else:
                els.append(Paragraph("LOW PRIORITY", self.styles['GKBadgeL']))
            
            els.append(Paragraph("<b>%s</b>" % self._clean(art.get('title', '')), self.styles['GKArtTitle']))
            
            kps = art.get('key_points', [])
            if kps:
                els.append(Paragraph("<b>Key Points:</b>", self.styles['GKContent']))
                for kp in kps:
                    els.append(Paragraph("- %s" % self._clean(kp), self.styles['GKKeyPt']))
            
            c = art.get('content', '')
            if c:
                els.append(Paragraph(self._clean(c), self.styles['GKContent']))
            
            kws = rel.get('matched_keywords', [])
            if kws:
                tag_style = ParagraphStyle('tag', parent=self.styles['GKContent'], fontSize=4, textColor=HexColor('#7f8c8d'), spaceAfter=4)
                els.append(Paragraph("<i>Tags: %s</i>" % ', '.join(kws), tag_style))
            
            els.append(Spacer(1, 2))
            sep = Table([['']], colWidths=[190*mm])
            sep.setStyle(TableStyle([('LINEBELOW', (0,0), (-1,0), 0.5, HexColor('#bdc3c7'))]))
            els.append(sep)
            els.append(Spacer(1, 2))
        
        els.append(Spacer(1, 6))
        return els
    
    def _quiz(self, quiz_data):
        els = []
        els.append(PageBreak())
        els.append(Paragraph("<b>DAILY CURRENT AFFAIRS QUIZ</b><br/><font size=9>%d Questions</font>" % quiz_data['total_questions'], self.styles['GKQuizHead']))
        els.append(Spacer(1, 6))
        
        for q in quiz_data.get('questions', []):
            qn = q.get('number', 0)
            qt = self._clean(q.get('question', ''))
            if not qt:
                continue
            
            els.append(Paragraph("Q%d. %s" % (qn, qt), self.styles['GKQText']))
            
            for i, opt in enumerate(q.get('options', [])):
                ol = chr(65 + i)
                els.append(Paragraph("   %s. %s" % (ol, self._clean(opt)), self.styles['GKQOpt']))
            
            ans = q.get('answer', '')
            if ans:
                els.append(Paragraph("Answer: %s" % ans, self.styles['GKQAns']))
            
            exp = q.get('explanation', '')
            if exp:
                els.append(Paragraph(self._clean(exp), self.styles['GKQExp']))
            
            els.append(Spacer(1, 4))
        
        return els
    
    def _footer(self):
        els = []
        els.append(Spacer(1, 10))
        els.append(Paragraph("Generated on %s | Source: GKToday.in | For exam preparation only" % datetime.now().strftime('%B %d, %Y'), self.styles['GKFoot']))
        return els
    
    def _page_dec(self, canvas, doc):
        canvas.saveState()
        pn = canvas.getPageNumber()
        canvas.setFont('Helvetica', 5)
        canvas.setFillColor(HexColor('#7f8c8d'))
        canvas.drawRightString(197*mm, 8*mm, "Page %d" % pn)
        if pn > 1:
            canvas.setStrokeColor(HexColor('#1a5276'))
            canvas.setLineWidth(0.5)
            canvas.line(10*mm, 282*mm, 200*mm, 282*mm)
            canvas.setFont('Helvetica-Bold', 5)
            canvas.setFillColor(HexColor('#1a5276'))
            canvas.drawString(10*mm, 284*mm, "GKToday Daily Digest")
        canvas.restoreState()


class Pipeline:
    def __init__(self, output_dir='output', telegram_token=None, telegram_chat_id=None):
        self.scraper = GKTodayScraper()
        self.generator = PDFGenerator(os.path.join(output_dir, 'pdfs'))
        self.output_dir = output_dir
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        os.makedirs(os.path.join(output_dir, 'json'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'pdfs'), exist_ok=True)
    
    def run(self):
        logger.info("Starting pipeline")
        data = self.scraper.scrape_all()
        
        if not data.get('success'):
            logger.error("Scraping failed")
            return data
        
        jpath = os.path.join(self.output_dir, 'json', 'GKToday_' + data['date'] + '.json')
        with open(jpath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        ppath = self.generator.generate(data)
        
        if self.telegram_token and self.telegram_chat_id:
            self._telegram(data, ppath)
        
        return {
            'success': True,
            'date': data['date'],
            'articles': data['total_articles'],
            'quiz': data.get('quiz', {}).get('total_questions', 0),
            'pdf_path': ppath,
            'json_path': jpath
        }
    
    def _telegram(self, data, pdf_path):
        import requests as req
        try:
            qc = data.get('quiz', {}).get('total_questions', 0)
            msg = "GKToday Daily Digest: %s\n\n%d Articles\n%d Quiz Questions\n\nSource: GKToday.in\n\nPDF attached." % (data.get('display_date', data['date']), data['total_articles'], qc)
            
            req.post("https://api.telegram.org/bot%s/sendMessage" % self.telegram_token,
                json={'chat_id': self.telegram_chat_id, 'text': msg, 'parse_mode': 'HTML'}, timeout=30)
            
            with open(pdf_path, 'rb') as f:
                req.post("https://api.telegram.org/bot%s/sendDocument" % self.telegram_token,
                    files={'document': f}, data={'chat_id': self.telegram_chat_id, 'caption': 'GKToday_%s.pdf' % data['date']}, timeout=60)
            
            logger.info("Telegram sent")
        except Exception as e:
            logger.error("Telegram failed: %s", e)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--daily', action='store_true')
    parser.add_argument('--output', default='output')
    parser.add_argument('--telegram', default=None)
    parser.add_argument('--chat-id', default=None)
    args = parser.parse_args()
    
    p = Pipeline(output_dir=args.output, telegram_token=args.telegram, telegram_chat_id=args.chat_id)
    result = p.run()
    print(json.dumps(result, indent=2))

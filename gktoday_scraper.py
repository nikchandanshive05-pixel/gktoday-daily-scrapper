#!/usr/bin/env python3
"""
GKToday Daily Scraper + Quiz + PDF Generator
"""

import requests
from bs4 import BeautifulSoup, NavigableString
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
        for s in soup.find_all(['script', 'style', 'nav']):
            s.decompose()
        
        articles = []
        headings = soup.find_all(['h3', 'h2'])
        logger.info("Found %d headings", len(headings))
        
        for h in headings:
            a = self._parse_article(h)
            if a:
                articles.append(a)
        
        logger.info("Parsed %d articles", len(articles))
        return articles
    
    def _parse_article(self, heading):
        link = heading.find('a')
        if not link:
            return None
        
        title = link.get_text(strip=True)
        url = link.get('href', '')
        
        if not title or len(title) < 10:
            return None
        
        skip = ['gk today', 'home', 'about', 'contact', 'privacy', 'subscribe']
        if any(s in title.lower() for s in skip):
            return None
        
        if not url.startswith('http'):
            url = self.BASE_URL + url if url.startswith('/') else self.BASE_URL + '/' + url
        
        img = None
        date = ""
        category = "General"
        content_parts = []
        
        for img_cand in [heading.find_previous('img'), heading.find_next('img')]:
            if img_cand:
                src = img_cand.get('src') or img_cand.get('data-src', '')
                if src and not src.startswith('data:'):
                    img = src
                    break
        
        sibling = heading.next_sibling
        collected = 0
        while sibling and collected < 2000:
            if isinstance(sibling, NavigableString):
                t = str(sibling).strip()
                if t and len(t) > 20:
                    content_parts.append(t)
                    collected += len(t)
            elif sibling.name and sibling.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'script', 'style']:
                t = sibling.get_text(strip=True)
                if t and len(t) > 20:
                    if re.search(r'January|February|March|April|May|June|July|August|September|October|November|December', t):
                        date = t
                    elif any(c in t.lower() for c in ['current affairs', 'national', 'international', 'economy', 'science', 'sports', 'defence', 'legal', 'government', 'art', 'culture', 'environment', 'persons', 'awards', 'banking', 'technology', 'agriculture', 'health', 'education']) and len(t) < 100:
                        category = t
                    else:
                        content_parts.append(t)
                        collected += len(t)
            sibling = sibling.next_sibling if hasattr(sibling, 'next_sibling') else None
            if not sibling:
                break
        
        content = ' '.join(content_parts)
        content = re.sub(r'\s+', ' ', content).strip()
        
        return {
            'title': title,
            'url': url,
            'date': date,
            'category': category,
            'content': content[:800] if len(content) > 800 else content,
            'key_points': self._key_points(content),
            'image_url': img,
            'word_count': len(content.split()),
            'relevance': self._relevance(title + ' ' + content)
        }
    
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
        urls = [
            self.BASE_URL + "/current-affairs-quiz",
            self.BASE_URL + "/quiz",
        ]
        
        quiz_html = None
        for u in urls:
            h = self.fetch(u)
            if h and 'question' in h.lower():
                quiz_html = h
                logger.info("Quiz found at: %s", u)
                break
            time.sleep(1)
        
        if not quiz_html:
            home = self.fetch(self.BASE_URL)
            if home:
                soup = BeautifulSoup(home, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a.get('href', '').lower()
                    txt = a.get_text(strip=True).lower()
                    if 'quiz' in href or 'quiz' in txt:
                        url = href if href.startswith('http') else self.BASE_URL + href if href.startswith('/') else self.BASE_URL + '/' + href
                        h = self.fetch(url)
                        if h and 'question' in h.lower():
                            quiz_html = h
                            logger.info("Quiz found via link: %s", url)
                            break
        
        if not quiz_html:
            logger.warning("No quiz found")
            return []
        
        questions = self._parse_quiz(quiz_html)
        
        pages = self._quiz_pages(quiz_html)
        for p in pages[:4]:
            time.sleep(1)
            h = self.fetch(p)
            if h:
                pq = self._parse_quiz(h)
                questions.extend(pq)
                logger.info("Found %d questions on page: %s", len(pq), p)
        
        logger.info("Total quiz questions: %d", len(questions))
        return questions
    
    def _quiz_pages(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        pages = []
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            txt = a.get_text(strip=True)
            if txt.isdigit() and int(txt) > 1 and 'quiz' in href.lower():
                url = href if href.startswith('http') else self.BASE_URL + href if href.startswith('/') else self.BASE_URL + '/' + href
                if url not in pages:
                    pages.append(url)
        return pages
    
    def _parse_quiz(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        for s in soup.find_all(['script', 'style']):
            s.decompose()
        
        questions = []
        text = soup.get_text()
        
        pattern = re.compile(r'Q\.?\s*(\d+)\s*[\.:]?\s*(.*?)(?=[a-d]\)|[A-D]\))', re.DOTALL | re.IGNORECASE)
        matches = pattern.findall(text)
        
        if not matches:
            pattern = re.compile(r'Question\s*(\d+)\s*[\.:]?\s*(.*?)(?=[a-d]\)|[A-D]\))', re.DOTALL | re.IGNORECASE)
            matches = pattern.findall(text)
        
        for m in matches:
            q_num = int(m[0]) if m[0].isdigit() else 0
            q_text = m[1].strip()
            
            full_q = 'Q' + m[0] + '. ' + q_text
            opts = self._extract_options(text, full_q)
            ans = self._extract_answer(text, full_q)
            exp = self._extract_explanation(text, full_q)
            
            if q_text and len(q_text) > 20:
                questions.append({
                    'number': q_num,
                    'question': q_text[:300],
                    'options': opts,
                    'answer': ans,
                    'explanation': exp
                })
        
        if not questions:
            containers = soup.find_all(['div', 'article'], class_=re.compile(r'quiz|question', re.I))
            if not containers:
                containers = soup.find_all(['div', 'p'])
            
            for c in containers:
                q = self._parse_quiz_container(c)
                if q:
                    questions.append(q)
        
        return questions
    
    def _extract_options(self, text, question_marker):
        opts = []
        idx = text.find(question_marker)
        if idx < 0:
            return opts
        
        segment = text[idx:idx + 1500]
        for letter in ['a', 'b', 'c', 'd']:
            pattern = re.compile(r'[\n\r\s]' + letter + r'[\)\.\s]\s*(.*?)(?=[\n\r\s][b-d][\)\.\s]|[\n\r\s]Answer|[\n\r\s]Explanation|$)', re.DOTALL | re.IGNORECASE)
            match = pattern.search(segment)
            if match:
                opts.append(match.group(1).strip()[:200])
        return opts
    
    def _extract_answer(self, text, question_marker):
        idx = text.find(question_marker)
        if idx < 0:
            return ''
        segment = text[idx:idx + 1500]
        match = re.search(r'Answer[\s:\.]+([a-dA-D])', segment, re.IGNORECASE)
        return match.group(1).upper() if match else ''
    
    def _extract_explanation(self, text, question_marker):
        idx = text.find(question_marker)
        if idx < 0:
            return ''
        segment = text[idx:idx + 2000]
        match = re.search(r'Explanation[\s:\.]+(.*?)(?=Q\.?\s*\d+|Question\s*\d+|$)', segment, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip()[:500] if match else ''
    
    def _parse_quiz_container(self, container):
        text = container.get_text(separator='\n', strip=True)
        q_match = re.search(r'Q\.?\s*(\d+)|Question\s*(\d+)', text, re.IGNORECASE)
        if not q_match:
            return None
        
        q_num = int(q_match.group(1) or q_match.group(2))
        lines = text.split('\n')
        q_text = ''
        opts = []
        ans = ''
        exp = ''
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if re.match(r'Q\.?\s*\d+|Question\s*\d+', line, re.IGNORECASE):
                q_text = re.sub(r'Q\.?\s*\d+\s*[\.:]?\s*', '', line, flags=re.IGNORECASE)
            elif re.match(r'[a-d]\)|[A-D]\)', line):
                opts.append(re.sub(r'^[a-d]\)|[A-D]\)\s*', '', line)[:200])
            elif re.match(r'Answer', line, re.IGNORECASE):
                ans_match = re.search(r'Answer[\s:\.]+([a-dA-D])', line, re.IGNORECASE)
                ans = ans_match.group(1).upper() if ans_match else ''
            elif re.match(r'Explanation', line, re.IGNORECASE):
                exp = re.sub(r'^Explanation[\s:\.]+', '', line, flags=re.IGNORECASE)[:500]
        
        if q_text and len(q_text) > 20:
            return {'number': q_num, 'question': q_text[:300], 'options': opts, 'answer': ans, 'explanation': exp}
        return None
    
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
        
        # UNIQUE names with GK prefix - no collisions with built-in styles
        s.add(ParagraphStyle('GKTitle', parent=s['Heading1'], fontSize=24, leading=30,
            textColor=HexColor('#1a5276'), alignment=TA_CENTER, spaceAfter=8, fontName='Helvetica-Bold'))
        
        s.add(ParagraphStyle('GKSub', parent=s['Normal'], fontSize=11, leading=14,
            textColor=HexColor('#7f8c8d'), alignment=TA_CENTER, spaceAfter=18, fontName='Helvetica'))
        
        s.add(ParagraphStyle('GKSecHead', parent=s['Heading2'], fontSize=13, leading=17,
            textColor=HexColor('#1a5276'), spaceBefore=14, spaceAfter=6, fontName='Helvetica-Bold'))
        
        s.add(ParagraphStyle('GKArtTitle', parent=s['Heading3'], fontSize=10, leading=14,
            textColor=HexColor('#2874a6'), spaceBefore=8, spaceAfter=3, fontName='Helvetica-Bold'))
        
        s.add(ParagraphStyle('GKContent', parent=s['Normal'], fontSize=8, leading=12,
            textColor=HexColor('#2c3e50'), alignment=TA_JUSTIFY, spaceAfter=4, fontName='Helvetica'))
        
        s.add(ParagraphStyle('GKKeyPt', parent=s['Normal'], fontSize=7, leading=11,
            textColor=HexColor('#2c3e50'), leftIndent=12, spaceAfter=2, fontName='Helvetica'))
        
        s.add(ParagraphStyle('GKBadgeH', parent=s['Normal'], fontSize=6, leading=8,
            textColor=colors.white, backColor=HexColor('#e74c3c'), alignment=TA_CENTER,
            spaceAfter=2, fontName='Helvetica-Bold'))
        
        s.add(ParagraphStyle('GKBadgeM', parent=s['Normal'], fontSize=6, leading=8,
            textColor=colors.white, backColor=HexColor('#f39c12'), alignment=TA_CENTER,
            spaceAfter=2, fontName='Helvetica-Bold'))
        
        s.add(ParagraphStyle('GKBadgeL', parent=s['Normal'], fontSize=6, leading=8,
            textColor=colors.white, backColor=HexColor('#95a5a6'), alignment=TA_CENTER,
            spaceAfter=2, fontName='Helvetica-Bold'))
        
        s.add(ParagraphStyle('GKQuizHead', parent=s['Heading2'], fontSize=15, leading=19,
            textColor=HexColor('#1a5276'), spaceBefore=16, spaceAfter=10, alignment=TA_CENTER,
            fontName='Helvetica-Bold'))
        
        s.add(ParagraphStyle('GKQText', parent=s['Normal'], fontSize=9, leading=13,
            textColor=HexColor('#2c3e50'), spaceBefore=10, spaceAfter=4, fontName='Helvetica-Bold'))
        
        s.add(ParagraphStyle('GKQOpt', parent=s['Normal'], fontSize=8, leading=12,
            textColor=HexColor('#2c3e50'), leftIndent=15, spaceAfter=1, fontName='Helvetica'))
        
        s.add(ParagraphStyle('GKQAns', parent=s['Normal'], fontSize=8, leading=12,
            textColor=HexColor('#27ae60'), leftIndent=15, spaceAfter=4, fontName='Helvetica-Bold'))
        
        s.add(ParagraphStyle('GKQExp', parent=s['Normal'], fontSize=7, leading=11,
            textColor=HexColor('#7f8c8d'), leftIndent=15, spaceAfter=8, fontName='Helvetica-Oblique'))
        
        s.add(ParagraphStyle('GKFoot', parent=s['Normal'], fontSize=6, leading=9,
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
            rightMargin=12*mm, leftMargin=12*mm, topMargin=14*mm, bottomMargin=14*mm)
        
        story = []
        story.extend(self._header(data))
        story.extend(self._summary(data))
        story.append(Spacer(1, 12))
        
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
        els.append(Paragraph("<b>GK TODAY</b><br/><font size=12>Current Affairs Daily Digest</font>", self.styles['GKTitle']))
        qc = data.get('quiz', {}).get('total_questions', 0)
        els.append(Paragraph("%s | %d Articles | %d Quiz Questions | Source: GKToday.in" % (data.get('display_date', data['date']), data['total_articles'], qc), self.styles['GKSub']))
        els.append(Spacer(1, 6))
        
        line = Table([['']], colWidths=[186*mm])
        line.setStyle(TableStyle([('LINEBELOW', (0,0), (-1,0), 2, HexColor('#1a5276'))]))
        els.append(line)
        els.append(Spacer(1, 10))
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
            ['HIGH Priority', str(h), 'MEDIUM Priority', str(m)],
            ['LOW Priority', str(l), 'Total Articles', str(data['total_articles'])],
            ['Quiz Questions', str(qc), 'Source', 'GKToday.in'],
        ], colWidths=[47*mm, 22*mm, 47*mm, 22*mm])
        
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), HexColor('#1a5276')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('SPAN', (0,0), (-1,0)),
            ('TOPPADDING', (0,0), (-1,0), 5),
            ('BOTTOMPADDING', (0,0), (-1,0), 5),
            ('BACKGROUND', (0,2), (-1,-1), HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0,2), (-1,-1), HexColor('#2c3e50')),
            ('FONTNAME', (0,2), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,2), (-1,-1), 7),
            ('ALIGN', (0,2), (0,-1), 'LEFT'),
            ('ALIGN', (1,2), (1,-1), 'CENTER'),
            ('ALIGN', (2,2), (2,-1), 'LEFT'),
            ('ALIGN', (3,2), (3,-1), 'CENTER'),
            ('TOPPADDING', (0,2), (-1,-1), 4),
            ('BOTTOMPADDING', (0,2), (-1,-1), 4),
            ('LEFTPADDING', (0,2), (-1,-1), 5),
            ('RIGHTPADDING', (0,2), (-1,-1), 5),
            ('GRID', (0,1), (-1,-1), 0.5, HexColor('#bdc3c7')),
            ('BOX', (0,0), (-1,-1), 1, HexColor('#1a5276')),
        ]))
        
        els.append(tbl)
        return els
    
    def _section(self, sec):
        els = []
        els.append(Paragraph("%s (%d articles)" % (sec['title'], sec['article_count']), self.styles['GKSecHead']))
        els.append(Spacer(1, 4))
        
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
            if len(c) > 350:
                c = c[:350] + "..."
            if c:
                els.append(Paragraph(self._clean(c), self.styles['GKContent']))
            
            kws = rel.get('matched_keywords', [])
            if kws:
                tag_style = ParagraphStyle('tag', parent=self.styles['GKContent'], fontSize=5, textColor=HexColor('#7f8c8d'), spaceAfter=6)
                els.append(Paragraph("<i>Tags: %s</i>" % ', '.join(kws), tag_style))
            
            els.append(Spacer(1, 3))
            sep = Table([['']], colWidths=[186*mm])
            sep.setStyle(TableStyle([('LINEBELOW', (0,0), (-1,0), 0.5, HexColor('#bdc3c7'))]))
            els.append(sep)
            els.append(Spacer(1, 3))
        
        els.append(Spacer(1, 8))
        return els
    
    def _quiz(self, quiz_data):
        els = []
        els.append(PageBreak())
        els.append(Paragraph("<b>DAILY CURRENT AFFAIRS QUIZ</b><br/><font size=11>%d Questions</font>" % quiz_data['total_questions'], self.styles['GKQuizHead']))
        els.append(Spacer(1, 8))
        
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
            
            els.append(Spacer(1, 6))
        
        return els
    
    def _footer(self):
        els = []
        els.append(Spacer(1, 12))
        els.append(Paragraph("Generated on %s | Source: GKToday.in | For exam preparation only" % datetime.now().strftime('%B %d, %Y'), self.styles['GKFoot']))
        return els
    
    def _page_dec(self, canvas, doc):
        canvas.saveState()
        pn = canvas.getPageNumber()
        canvas.setFont('Helvetica', 6)
        canvas.setFillColor(HexColor('#7f8c8d'))
        canvas.drawRightString(195*mm, 10*mm, "Page %d" % pn)
        if pn > 1:
            canvas.setStrokeColor(HexColor('#1a5276'))
            canvas.setLineWidth(0.5)
            canvas.line(12*mm, 280*mm, 198*mm, 280*mm)
            canvas.setFont('Helvetica-Bold', 6)
            canvas.setFillColor(HexColor('#1a5276'))
            canvas.drawString(12*mm, 282*mm, "GKToday Daily Digest")
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

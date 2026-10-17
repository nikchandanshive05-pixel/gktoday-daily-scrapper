"""
Magazine-grade PDF Compendium Exporter using ReportLab.
Includes NumberedCanvas (Page X of Y), embedded outline bookmarks,
and native Devanagari font support for Marathi (Lokmat / Mahasamvad / Loksatta) articles.
Renders full, unabridged article bodies categorized by GS paper without artificial truncation.
"""
import os
import re
import html
import logging
from typing import List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    HRFlowable, Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from core.models import DailyDigest, Article, QuizQuestion

logger = logging.getLogger("pdf_engine")

PALETTE = {
    "primary": "#1e3a5f",       # Deep Navy
    "secondary": "#2563eb",     # Royal Blue
    "accent": "#dc2626",        # Crimson Red
    "success": "#059669",       # Emerald Green
    "warning": "#d97706",       # Amber
    "text": "#1f2937",          # Dark Charcoal
    "muted": "#4b5563",         # Slate Gray
    "light_gray": "#94a3b8",    # Cool Gray
    "border": "#cbd5e1",        # Light Border
    "bg_cover": "#f8fafc",      # Crisp Slate White
    "bg_card": "#ffffff",
    "bg_marathi": "#fefce8",    # Warm Cream tint for Marathi
    "border_marathi": "#fef08a",
    "bg_banner_en": "#f1f5f9",  # Soft slate header
    "border_banner_en": "#cbd5e1",
    "bg_quiz": "#fdf4ff",       # Soft Purple Tint
    "border_quiz": "#f5d0fe",
}

# Register Devanagari Font (Mukta - supports full Latin + Devanagari scripts natively)
FONT_REGISTERED = False
DEVANAGARI_FONT = "Helvetica"
DEVANAGARI_BOLD = "Helvetica-Bold"

mukta_pairs = [
    (
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fonts", "Mukta-Regular.ttf")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fonts", "Mukta-Bold.ttf")),
    ),
    (
        os.path.abspath("fonts/Mukta-Regular.ttf"),
        os.path.abspath("fonts/Mukta-Bold.ttf"),
    ),
]

for reg_path, bold_path in mukta_pairs:
    if os.path.exists(reg_path):
        try:
            pdfmetrics.registerFont(TTFont("Devanagari", reg_path))
            if os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont("Devanagari-Bold", bold_path))
                pdfmetrics.registerFontFamily("Devanagari", normal="Devanagari", bold="Devanagari-Bold", italic="Devanagari", boldItalic="Devanagari-Bold")
                DEVANAGARI_BOLD = "Devanagari-Bold"
            else:
                pdfmetrics.registerFontFamily("Devanagari", normal="Devanagari", bold="Devanagari", italic="Devanagari", boldItalic="Devanagari")
                DEVANAGARI_BOLD = "Devanagari"
            FONT_REGISTERED = True
            DEVANAGARI_FONT = "Devanagari"
            logger.info(f"Registered Devanagari font from {reg_path}")
            break
        except Exception as e:
            logger.warning(f"Could not load Mukta font: {e}")

if not FONT_REGISTERED:
    # Fallback to NotoSans or Windows fonts
    for candidate in [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fonts", "NotoSansDevanagari-Regular.ttf")),
        os.path.abspath("fonts/NotoSansDevanagari-Regular.ttf"),
        "C:/Windows/Fonts/Nirmala.ttf",
        "C:/Windows/Fonts/mangal.ttf",
    ]:
        if os.path.exists(candidate):
            try:
                pdfmetrics.registerFont(TTFont("Devanagari", candidate))
                pdfmetrics.registerFontFamily("Devanagari", normal="Devanagari", bold="Devanagari", italic="Devanagari", boldItalic="Devanagari")
                FONT_REGISTERED = True
                DEVANAGARI_FONT = "Devanagari"
                DEVANAGARI_BOLD = "Devanagari"
                logger.info(f"Registered fallback font from {candidate}")
                break
            except Exception as e:
                logger.warning(f"Could not load fallback font: {e}")


def has_devanagari(text: str) -> bool:
    """Check if string contains any Devanagari characters (U+0900 - U+097F)."""
    return bool(re.search(r"[\u0900-\u097f]", text))


class NumberedCanvas(pdfcanvas.Canvas):
    """Calculates total page count and draws running headers and footers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self._bookmarks = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            pdfcanvas.Canvas.showPage(self)
        pdfcanvas.Canvas.save(self)

    def draw_decorations(self, total_pages: int):
        if self._pageNumber == 1:
            return  # Skip cover

        self.saveState()
        # Top Header
        self.setStrokeColor(HexColor(PALETTE["border"]))
        self.setLineWidth(0.6)
        self.line(16 * mm, A4[1] - 14 * mm, A4[0] - 16 * mm, A4[1] - 14 * mm)

        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(HexColor(PALETTE["primary"]))
        self.drawString(16 * mm, A4[1] - 11 * mm, "UPSC & MPSC DAILY COMPENDIUM")

        # Bottom Footer
        self.line(16 * mm, 14 * mm, A4[0] - 16 * mm, 14 * mm)
        self.setFont("Helvetica", 8)
        self.setFillColor(HexColor(PALETTE["light_gray"]))
        self.drawString(16 * mm, 9 * mm, "The Hindu | LiveMint | Lokmat | Mahasamvad | GKToday")

        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(HexColor(PALETTE["primary"]))
        self.drawRightString(A4[0] - 16 * mm, 9 * mm, page_str)
        self.restoreState()


class PDFExporter:
    """Compiles DailyDigest into high-yield magazine-quality PDFs with unabridged text."""

    def __init__(self, output_dir: str = "output/pdf"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.styles = self._init_styles()

    def _init_styles(self):
        norm_font = DEVANAGARI_FONT if FONT_REGISTERED else "Helvetica"
        bold_font = DEVANAGARI_FONT if FONT_REGISTERED else "Helvetica-Bold"

        return {
            # English styles
            "CoverTitle": ParagraphStyle(
                "CoverTitle",
                fontName="Helvetica-Bold",
                fontSize=26,
                leading=32,
                textColor=HexColor(PALETTE["primary"]),
                alignment=TA_CENTER,
            ),
            "CoverSubtitle": ParagraphStyle(
                "CoverSubtitle",
                fontName=norm_font,
                fontSize=12,
                leading=17,
                textColor=HexColor(PALETTE["secondary"]),
                alignment=TA_CENTER,
            ),
            "SectionHeader": ParagraphStyle(
                "SectionHeader",
                fontName=bold_font,
                fontSize=15,
                leading=20,
                textColor=HexColor(PALETTE["primary"]),
                spaceAfter=4,
            ),
            "ArticleTitleEn": ParagraphStyle(
                "ArticleTitleEn",
                fontName="Helvetica-Bold",
                fontSize=12.5,
                leading=16.5,
                textColor=HexColor(PALETTE["primary"]),
                spaceAfter=3,
            ),
            "ArticleTitleMr": ParagraphStyle(
                "ArticleTitleMr",
                fontName=norm_font,
                fontSize=13,
                leading=18,
                textColor=HexColor(PALETTE["primary"]),
                spaceAfter=3,
            ),
            "MetaEn": ParagraphStyle(
                "MetaEn",
                fontName="Helvetica",
                fontSize=8.5,
                leading=12,
                textColor=HexColor(PALETTE["muted"]),
            ),
            "MetaMr": ParagraphStyle(
                "MetaMr",
                fontName=norm_font,
                fontSize=8.5,
                leading=12.5,
                textColor=HexColor(PALETTE["muted"]),
            ),
            "PointersEn": ParagraphStyle(
                "PointersEn",
                fontName="Helvetica",
                fontSize=8.5,
                leading=12,
                textColor=HexColor(PALETTE["primary"]),
            ),
            "PointersMr": ParagraphStyle(
                "PointersMr",
                fontName=norm_font,
                fontSize=8.5,
                leading=12.5,
                textColor=HexColor(PALETTE["primary"]),
            ),
            "BodyEn": ParagraphStyle(
                "BodyEn",
                fontName="Helvetica",
                fontSize=9.5,
                leading=14.5,
                textColor=HexColor(PALETTE["text"]),
                alignment=TA_JUSTIFY,
                spaceAfter=7,
            ),
            "BodyMr": ParagraphStyle(
                "BodyMr",
                fontName=norm_font,
                fontSize=9.5,
                leading=15.5,
                textColor=HexColor(PALETTE["text"]),
                alignment=TA_JUSTIFY,
                spaceAfter=7,
            ),
            "QuizQuestion": ParagraphStyle(
                "QuizQuestion",
                fontName="Helvetica-Bold",
                fontSize=9.5,
                leading=13.5,
                textColor=HexColor(PALETTE["primary"]),
            ),
            "QuizOption": ParagraphStyle(
                "QuizOption",
                fontName="Helvetica",
                fontSize=8.5,
                leading=12,
                textColor=HexColor(PALETTE["text"]),
                leftIndent=10,
            ),
            "Answer": ParagraphStyle(
                "Answer",
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=12,
                textColor=HexColor(PALETTE["success"]),
            ),
            "QuizMeta": ParagraphStyle(
                "QuizMeta",
                fontName="Helvetica",
                fontSize=8,
                leading=11,
                textColor=HexColor(PALETTE["muted"]),
            ),
        }

    def export(self, digest: DailyDigest, hide_answers: bool = False) -> str:
        filename = f"UPSC_MPSC_Daily_Digest_{digest.date}.pdf"
        filepath = os.path.join(self.output_dir, filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            leftMargin=16 * mm,
            rightMargin=16 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
        )

        story = []
        self._build_cover_page(story, digest)
        story.append(PageBreak())

        self._build_articles_section(story, digest)
        
        if digest.quizzes:
            story.append(PageBreak())
            self._build_quizzes_section(story, digest, hide_answers)

        doc.build(story, canvasmaker=NumberedCanvas)
        logger.info(f"Generated PDF Compendium: {filepath}")
        return filepath

    def _build_cover_page(self, story: list, digest: DailyDigest):
        story.append(Spacer(1, 35 * mm))
        story.append(Paragraph("CIVIL SERVICES DAILY REVIEW", self.styles["CoverTitle"]))
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("UPSC & MPSC Comprehensive Editorial Compendium", self.styles["CoverSubtitle"]))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(f"<b>Edition Date:</b> {digest.date}", self.styles["CoverSubtitle"]))
        story.append(Spacer(1, 15 * mm))

        # Sources badge table
        src_counts = {}
        for a in digest.articles:
            src_counts[a.source] = src_counts.get(a.source, 0) + 1

        norm_font = DEVANAGARI_FONT if FONT_REGISTERED else "Helvetica"
        summary_data = [
            ["Source / Publisher", "Coverage & Type", "Articles"],
            ["The Hindu", "Editorials & Op-Ed (GS-2, GS-3)", str(src_counts.get("The Hindu", 0))],
            ["LiveMint", "Opinion & Economy (GS-3)", str(src_counts.get("LiveMint", 0))],
            ["Lokmat (लोकमत)", "अग्रलेख व विशेष लेख (MPSC)", str(src_counts.get("Lokmat", 0))],
            ["Mahasamvad (DGIPR)", "शासकीय निर्णय व धोरणे (MPSC)", str(src_counts.get("Mahasamvad (DGIPR)", 0))],
            ["GKToday", "Current Affairs & Quiz Bank", f"{src_counts.get('GKToday', 0)} CA + {len(digest.quizzes)} MCQs"],
        ]
        if src_counts.get("Indian Express", 0) > 0:
            summary_data.insert(2, ["Indian Express", "Explained & Ideas", str(src_counts.get("Indian Express", 0))])
        if src_counts.get("Loksatta", 0) > 0:
            summary_data.insert(3, ["Loksatta (लोकसत्ता)", "संपादकीय व विश्लेषक", str(src_counts.get("Loksatta", 0))])

        t = Table(summary_data, colWidths=[62 * mm, 72 * mm, 44 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor(PALETTE["primary"])),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), norm_font),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor(PALETTE["border"])),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 20 * mm))

    def _build_articles_section(self, story: list, digest: DailyDigest):
        # Group articles by GS paper
        grouped = {}
        for a in digest.articles:
            grouped.setdefault(a.gs_paper, []).append(a)

        paper_titles = {
            "GS-2": "UPSC GS-2 Focus: Governance, Constitution, Polity & International Relations",
            "GS-3": "UPSC GS-3 Focus: Economy, Agriculture, Science & Technology, Environment",
            "GS-1": "UPSC GS-1 Focus: Indian Heritage, History, Geography & Society",
            "GS-4": "UPSC GS-4 Focus: Ethics, Integrity & Aptitude",
            "MPSC-State": "MPSC राज्यसेवा विशेष: महाराष्ट्र शासन निर्णय, प्रशासन व अग्रलेख",
        }
        order = ["GS-2", "GS-3", "GS-1", "GS-4", "MPSC-State"]
        
        for paper in order:
            if paper not in grouped:
                continue
            arts = grouped[paper]
            section_title = paper_titles.get(paper, f"UPSC {paper} Focus")
            
            story.append(Paragraph(html.escape(section_title), self.styles["SectionHeader"]))
            story.append(HRFlowable(width="100%", thickness=1.5, color=HexColor(PALETTE["secondary"]), spaceAfter=12))

            for art in arts:
                is_mr = art.language == "mr" or has_devanagari(art.title) or has_devanagari(art.full_text[:300] if art.full_text else "")
                
                title_style = self.styles["ArticleTitleMr"] if is_mr else self.styles["ArticleTitleEn"]
                meta_style = self.styles["MetaMr"] if is_mr else self.styles["MetaEn"]
                body_style = self.styles["BodyMr"] if is_mr else self.styles["BodyEn"]
                pointers_style = self.styles["PointersMr"] if is_mr else self.styles["PointersEn"]

                # 1. Header Banner Card
                header_elements = []
                escaped_title = html.escape(art.title)
                header_elements.append(Paragraph(f"<b>{escaped_title}</b>", title_style))

                escaped_src = html.escape(art.source)
                escaped_author = html.escape(art.author or "Editorial Staff")
                escaped_date = html.escape(art.published_date or digest.date)
                escaped_stage = html.escape(art.exam_stage or "Prelims & Mains")
                escaped_paper = html.escape(art.gs_paper)

                meta_text = (
                    f"<b>{escaped_src}</b> | {escaped_author} | <i>{escaped_date}</i> | "
                    f"Exam: <b>{escaped_paper}</b> ({escaped_stage})"
                )
                header_elements.append(Paragraph(meta_text, meta_style))

                if art.syllabus_topics:
                    clean_topics = html.escape(" • ".join(art.syllabus_topics[:4]))
                    header_elements.append(Paragraph(f"<b>Syllabus Topics:</b> {clean_topics}", meta_style))

                if art.prelims_pointers:
                    clean_pointers = html.escape(" | ".join(art.prelims_pointers[:3]))
                    header_elements.append(Paragraph(f"<b>📌 Prelims Pointers:</b> {clean_pointers}", pointers_style))

                bg_color = HexColor(PALETTE["bg_marathi"]) if is_mr else HexColor(PALETTE["bg_banner_en"])
                border_color = HexColor(PALETTE["border_marathi"]) if is_mr else HexColor(PALETTE["border_banner_en"])

                card_table = Table([[elem] for elem in header_elements], colWidths=[178 * mm])
                card_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), bg_color),
                    ("BOX", (0, 0), (-1, -1), 0.8, border_color),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]))

                # Keep header banner together
                story.append(KeepTogether(card_table))
                story.append(Spacer(1, 3 * mm))

                # 2. Render Full Unabridged Article Text
                raw_text = (art.full_text or "").strip()
                if not raw_text and art.summary_bullets:
                    raw_text = "\n\n".join(art.summary_bullets)

                paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
                if not paragraphs and raw_text:
                    paragraphs = [p.strip() for p in raw_text.split("\n") if p.strip()]

                for para in paragraphs:
                    escaped_p = html.escape(para)
                    # Convert single inner newlines to break tags
                    escaped_p = escaped_p.replace("\n", "<br/>")
                    story.append(Paragraph(escaped_p, body_style))

                # 3. Clean divider after article
                story.append(HRFlowable(width="100%", thickness=0.6, color=HexColor(PALETTE["border"]), spaceBefore=6, spaceAfter=12))

    def _build_quizzes_section(self, story: list, digest: DailyDigest, hide_answers: bool):
        story.append(Paragraph("Daily Practice MCQs (Quiz Bank)", self.styles["SectionHeader"]))
        mode_str = "Test Mode (Answers Hidden)" if hide_answers else "Study Mode (With Explanations)"
        story.append(Paragraph(f"<b>Mode:</b> {mode_str} | Total Questions: {len(digest.quizzes)}", self.styles["MetaEn"]))
        story.append(HRFlowable(width="100%", thickness=1.5, color=HexColor(PALETTE["accent"]), spaceAfter=10))

        for q in digest.quizzes:
            q_flowables = []
            esc_q = html.escape(f"Q{q.question_num}. {q.question_text}")
            q_flowables.append(Paragraph(f"<b>{esc_q}</b>", self.styles["QuizQuestion"]))
            
            for opt_key in ["A", "B", "C", "D"]:
                if opt_key in q.options:
                    esc_opt = html.escape(f"[{opt_key}] {q.options[opt_key]}")
                    q_flowables.append(Paragraph(esc_opt, self.styles["QuizOption"]))

            if not hide_answers:
                if q.correct_option:
                    esc_ans = html.escape(f"Correct Answer: [{q.correct_option}]")
                    q_flowables.append(Paragraph(f"<b>{esc_ans}</b>", self.styles["Answer"]))
                if q.explanation:
                    esc_exp = html.escape(q.explanation)
                    q_flowables.append(Paragraph(f"<i>Notes:</i> {esc_exp}", self.styles["QuizMeta"]))

            card = Table([[item] for item in q_flowables], colWidths=[178 * mm])
            card.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), HexColor(PALETTE["bg_quiz"])),
                ("BOX", (0, 0), (-1, -1), 0.6, HexColor(PALETTE["border_quiz"])),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))

            story.append(KeepTogether(card))
            story.append(Spacer(1, 6 * mm))


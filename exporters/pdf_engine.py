"""
Magazine-grade PDF Compendium Exporter using ReportLab.
Includes NumberedCanvas (Page X of Y), embedded outline bookmarks,
and native Devanagari font support for Marathi (Loksatta) articles.
"""
import os
import re
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
    "border": "#e2e8f0",        # Light Border
    "bg_cover": "#f8fafc",      # Crisp Slate White
    "bg_card": "#ffffff",
    "bg_marathi": "#fefce8",    # Warm Cream tint for Marathi
    "border_marathi": "#fef08a",
    "bg_quiz": "#fdf4ff",       # Soft Purple Tint
    "border_quiz": "#f5d0fe",
}

# Register Devanagari Font
FONT_REGISTERED = False
DEVANAGARI_FONT = "Helvetica"

for candidate in [
    os.path.join(os.path.dirname(__file__), "..", "fonts", "NotoSansDevanagari-Regular.ttf"),
    "fonts/NotoSansDevanagari-Regular.ttf",
    "C:/Windows/Fonts/Nirmala.ttf",
    "C:/Windows/Fonts/mangal.ttf",
]:
    if os.path.exists(candidate):
        try:
            pdfmetrics.registerFont(TTFont("Devanagari", candidate))
            FONT_REGISTERED = True
            DEVANAGARI_FONT = "Devanagari"
            logger.info(f"Registered Devanagari font from {candidate}")
            break
        except Exception as e:
            logger.warning(f"Could not load font {candidate}: {e}")


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
        self.drawString(16 * mm, 9 * mm, "The Hindu • Indian Express • Loksatta • GKToday")

        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(HexColor(PALETTE["primary"]))
        self.drawRightString(A4[0] - 16 * mm, 9 * mm, page_str)
        self.restoreState()


class PDFExporter:
    """Compiles DailyDigest into high-yield magazine-quality PDFs."""

    def __init__(self, output_dir: str = "output/pdf"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.styles = self._init_styles()

    def _init_styles(self):
        base = getSampleStyleSheet()
        norm_font = DEVANAGARI_FONT if FONT_REGISTERED else "Helvetica"
        bold_font = DEVANAGARI_FONT if FONT_REGISTERED else "Helvetica-Bold"

        return {
            "CoverTitle": ParagraphStyle(
                "CoverTitle",
                fontName=bold_font,
                fontSize=26,
                leading=32,
                textColor=HexColor(PALETTE["primary"]),
                alignment=TA_CENTER,
            ),
            "CoverSubtitle": ParagraphStyle(
                "CoverSubtitle",
                fontName=norm_font,
                fontSize=13,
                leading=18,
                textColor=HexColor(PALETTE["secondary"]),
                alignment=TA_CENTER,
            ),
            "SectionHeader": ParagraphStyle(
                "SectionHeader",
                fontName=bold_font,
                fontSize=16,
                leading=22,
                textColor=HexColor(PALETTE["primary"]),
                spaceAfter=6,
            ),
            "ArticleTitle": ParagraphStyle(
                "ArticleTitle",
                fontName=bold_font,
                fontSize=13,
                leading=17,
                textColor=HexColor(PALETTE["primary"]),
                spaceAfter=4,
            ),
            "Meta": ParagraphStyle(
                "Meta",
                fontName=norm_font,
                fontSize=8,
                leading=11,
                textColor=HexColor(PALETTE["muted"]),
            ),
            "Body": ParagraphStyle(
                "Body",
                fontName=norm_font,
                fontSize=9.5,
                leading=14,
                textColor=HexColor(PALETTE["text"]),
                alignment=TA_JUSTIFY,
            ),
            "Bullet": ParagraphStyle(
                "Bullet",
                fontName=norm_font,
                fontSize=9,
                leading=13,
                textColor=HexColor(PALETTE["text"]),
                leftIndent=10,
            ),
            "QuizQuestion": ParagraphStyle(
                "QuizQuestion",
                fontName=norm_font,
                fontSize=9.5,
                leading=13.5,
                textColor=HexColor(PALETTE["primary"]),
            ),
            "QuizOption": ParagraphStyle(
                "QuizOption",
                fontName=norm_font,
                fontSize=8.5,
                leading=12,
                textColor=HexColor(PALETTE["text"]),
                leftIndent=10,
            ),
            "Answer": ParagraphStyle(
                "Answer",
                fontName=bold_font,
                fontSize=8.5,
                leading=12,
                textColor=HexColor(PALETTE["success"]),
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
        story.append(Spacer(1, 40 * mm))
        story.append(Paragraph("CIVIL SERVICES DAILY REVIEW", self.styles["CoverTitle"]))
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(f"UPSC & MPSC Comprehensive Editorial Compendium", self.styles["CoverSubtitle"]))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(f"<b>Edition Date:</b> {digest.date}", self.styles["CoverSubtitle"]))
        story.append(Spacer(1, 15 * mm))

        # Sources badge table
        src_counts = {}
        for a in digest.articles:
            src_counts[a.source] = src_counts.get(a.source, 0) + 1

        summary_data = [
            ["Source / Publisher", "Type", "Articles"],
            ["The Hindu", "Editorials & Op-Ed", str(src_counts.get("The Hindu", 0))],
            ["Indian Express", "Explained & Ideas", str(src_counts.get("Indian Express", 0))],
            ["Loksatta (लोकसत्ता)", "संपादकीय व विश्लेषक", str(src_counts.get("Loksatta", 0))],
            ["GKToday", "Current Affairs & MCQs", f"{src_counts.get('GKToday', 0)} CA + {len(digest.quizzes)} MCQs"],
        ]
        t = Table(summary_data, colWidths=[65 * mm, 65 * mm, 40 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor(PALETTE["primary"])),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), DEVANAGARI_FONT if FONT_REGISTERED else "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor(PALETTE["border"])),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 25 * mm))

    def _build_articles_section(self, story: list, digest: DailyDigest):
        # Group articles
        grouped = {}
        for a in digest.articles:
            grouped.setdefault(a.gs_paper, []).append(a)

        order = ["GS-2", "GS-3", "GS-1", "GS-4", "MPSC-State"]
        
        for paper in order:
            if paper not in grouped:
                continue
            arts = grouped[paper]
            display_name = "MPSC विशेष (लोकसत्ता संपादकीय)" if paper == "MPSC-State" else f"UPSC {paper} Focus"
            
            story.append(Paragraph(display_name, self.styles["SectionHeader"]))
            story.append(HRFlowable(width="100%", thickness=1.5, color=HexColor(PALETTE["secondary"]), spaceAfter=10))

            for art in arts:
                card_data = []
                # Header row
                title_p = Paragraph(f"<b>{art.title}</b>", self.styles["ArticleTitle"])
                meta_p = Paragraph(f"<b>{art.source}</b> | {art.author or 'Staff'} | <i>{art.published_date}</i> | Focus: {art.exam_stage} ({art.gs_paper})", self.styles["Meta"])
                card_data.append([title_p])
                card_data.append([meta_p])

                # Bullets
                if art.summary_bullets:
                    b_texts = "<br/>".join([f"• {b}" for b in art.summary_bullets[:3]])
                    card_data.append([Paragraph(f"<b>Core Takeaways:</b><br/>{b_texts}", self.styles["Bullet"])])

                # Prelims facts
                if art.prelims_pointers:
                    p_texts = " | ".join(art.prelims_pointers[:3])
                    card_data.append([Paragraph(f"<b>📌 Prelims Pointers:</b> {p_texts}", self.styles["Meta"])])

                bg_color = HexColor(PALETTE["bg_marathi"]) if art.language == "mr" else HexColor("#f8fafc")
                border_color = HexColor(PALETTE["border_marathi"]) if art.language == "mr" else HexColor(PALETTE["border"])

                card_table = Table(card_data, colWidths=[178 * mm])
                card_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), bg_color),
                    ("BOX", (0, 0), (-1, -1), 0.8, border_color),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]))

                story.append(card_table)
                story.append(Spacer(1, 8 * mm))

    def _build_quizzes_section(self, story: list, digest: DailyDigest, hide_answers: bool):
        story.append(Paragraph("Daily Practice MCQs (Quiz Bank)", self.styles["SectionHeader"]))
        mode_str = "Test Mode (Answers Hidden)" if hide_answers else "Study Mode (With Explanations)"
        story.append(Paragraph(f"<b>Mode:</b> {mode_str} | Total Questions: {len(digest.quizzes)}", self.styles["Meta"]))
        story.append(HRFlowable(width="100%", thickness=1.5, color=HexColor(PALETTE["accent"]), spaceAfter=10))

        for q in digest.quizzes:
            q_flowables = []
            q_flowables.append(Paragraph(f"<b>Q{q.question_num}. {q.question_text}</b>", self.styles["QuizQuestion"]))
            
            for opt_key in ["A", "B", "C", "D"]:
                if opt_key in q.options:
                    q_flowables.append(Paragraph(f"[{opt_key}] {q.options[opt_key]}", self.styles["QuizOption"]))

            if not hide_answers:
                if q.correct_option:
                    q_flowables.append(Paragraph(f"<b>Correct: [{q.correct_option}]</b>", self.styles["Answer"]))
                if q.explanation:
                    q_flowables.append(Paragraph(f"<i>Notes:</i> {q.explanation}", self.styles["Meta"]))

            card = Table([[item] for item in q_flowables], colWidths=[178 * mm])
            card.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), HexColor(PALETTE["bg_quiz"])),
                ("BOX", (0, 0), (-1, -1), 0.6, HexColor(PALETTE["border_quiz"])),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))

            story.append(KeepTogether(card))
            story.append(Spacer(1, 6 * mm))

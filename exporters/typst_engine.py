"""
Strict Black-and-White Publication-Grade Typst PDF Exporter.
Conforms to publication standards: Times New Roman / Mukta Devanagari typography,
10pt body, 0.72em leading, clean organic rule dividers, and zero decorative tint clutter.
"""
import os
import re
import logging
import subprocess
from datetime import datetime
from typing import Optional

from core.models import DailyDigest, Article, QuizQuestion

logger = logging.getLogger("typst_engine")


def escape_typst(text: Optional[str]) -> str:
    """Escapes special characters in text destined for Typst markup."""
    if not text:
        return ""
    s = text.replace("\\", "\\\\")
    for ch in ["#", "$", "@", "_", "*", "`", "<", ">"]:
        s = s.replace(ch, f"\\{ch}")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2018", "'").replace("\u2019", "'")
    return s.strip()


class TypstPDFEngine:
    """Compiles publication-grade A4 compendiums via the Typst compiler."""

    def __init__(self, output_dir: str = "output/pdf", fonts_dir: str = "fonts"):
        self.output_dir = output_dir
        self.fonts_dir = fonts_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_digest_pdf(self, digest: DailyDigest, filename: Optional[str] = None) -> str:
        """Generates a publication-grade compendium PDF from DailyDigest."""
        date_str = digest.date or datetime.now().strftime("%Y-%m-%d")
        if not filename:
            filename = f"UPSC_MPSC_Daily_Compendium_{date_str}.pdf"

        typ_file = os.path.join(self.output_dir, f"compendium_{date_str}.typ")
        pdf_file = os.path.join(self.output_dir, filename)

        typst_source = self._build_typst_markup(digest)
        with open(typ_file, "w", encoding="utf-8") as f:
            f.write(typst_source)

        logger.info(f"Wrote Typst markup to {typ_file}. Compiling to PDF...")

        compiled = False
        try:
            import typst
            typst.compile(typ_file, output=pdf_file, font_paths=[self.fonts_dir])
            compiled = True
            logger.info(f"Successfully compiled PDF using Python typst package: {pdf_file}")
        except Exception as e:
            logger.warning(f"Python typst library compilation failed ({e}), falling back to CLI...")

        if not compiled:
            cmd = ["typst", "compile", "--font-path", self.fonts_dir, typ_file, pdf_file]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                compiled = True
                logger.info(f"Successfully compiled PDF using Typst CLI: {pdf_file}")
            else:
                logger.error(f"Typst CLI failed with return code {res.returncode}: {res.stderr}")
                raise RuntimeError(f"Typst compilation error: {res.stderr}")

        return pdf_file

    def _build_typst_markup(self, digest: DailyDigest) -> str:
        date_str = digest.date
        tot_articles = len(digest.articles)
        tot_quizzes = len(digest.quizzes)

        # Build Typst document preamble using modern Typst 0.11+ / 0.15 context
        lines = [
            '// Publication-Grade Strict Black-and-White Compendium',
            '#set page(',
            '  paper: "a4",',
            '  margin: (top: 2.2cm, bottom: 2.2cm, left: 2.2cm, right: 2.2cm),',
            '  header: context {',
            '    if here().page() > 1 [',
            '      #set text(font: ("Times New Roman", "Mukta", "Noto Sans Devanagari"), size: 8.5pt, fill: luma(60))',
            f'      #grid(columns: (1fr, 1fr), align: (left, right), [UPSC & MPSC Daily Compendium - {escape_typst(date_str)}], [Exam Intelligence])',
            '      #line(length: 100%, stroke: 0.5pt + luma(120))',
            '    ]',
            '  },',
            '  footer: context {',
            '    [',
            '      #set text(font: ("Times New Roman", "Mukta"), size: 8.5pt, fill: luma(80))',
            '      #line(length: 100%, stroke: 0.5pt + luma(140))',
            '      #align(center)[#here().page()]',
            '    ]',
            '  }',
            ')',
            '',
            '#set text(',
            '  font: ("Times New Roman", "Mukta", "Noto Sans Devanagari"),',
            '  size: 10pt,',
            '  lang: "en"',
            ')',
            '#set par(justify: true, leading: 0.72em)',
            '',
            '// Title Block',
            '#align(center)[',
            '  #v(0.5cm)',
            '  #text(size: 19pt, weight: "bold")[CIVIL SERVICES DAILY COMPENDIUM]',
            '  #v(0.15cm)',
            f'  #text(size: 11pt, style: "italic")[Comprehensive Editorial Analysis & High-Yield MCQs | {escape_typst(date_str)}]',
            '  #v(0.1cm)',
            f'  #text(size: 9pt, fill: luma(60))[Curated Sources: The Hindu, Indian Express, Loksatta, GKToday, PIB | Total Articles: {tot_articles} | MCQs: {tot_quizzes}]',
            '  #v(0.4cm)',
            '  #line(length: 100%, stroke: 1.2pt + black)',
            ']',
            '',
        ]

        # 1. High-Yield MCQs Section
        if digest.quizzes:
            lines.extend([
                '#v(0.6cm)',
                '= PART I: HIGH-YIELD PRELIMS PRACTICE MCQS',
                '#line(length: 100%, stroke: 0.75pt + black)',
                '#v(0.2cm)',
            ])
            for q in digest.quizzes:
                lines.append(f'*Q{q.question_num}.* {escape_typst(q.question_text)}')
                lines.append('')
                if q.options:
                    for opt_key in sorted(q.options.keys()):
                        opt_val = q.options[opt_key]
                        lines.append(f'- *[{opt_key}]* {escape_typst(opt_val)}')
                    lines.append('')
                if q.correct_option or q.explanation:
                    corr = f"*[Answer: {escape_typst(q.correct_option)}]* " if q.correct_option else ""
                    expl = escape_typst(q.explanation)
                    lines.append(f'#rect(width: 100%, stroke: 0.5pt + luma(120), inset: 6pt)[{corr}{expl}]')
                    lines.append('')
                lines.append('#v(0.25cm)')

        # 2. Editorial & Current Affairs Section
        if digest.articles:
            lines.extend([
                '#v(0.8cm)',
                '= PART II: EDITORIAL PERSPECTIVES & POLICY ANALYSIS',
                '#line(length: 100%, stroke: 0.75pt + black)',
                '#v(0.3cm)',
            ])

            grouped = {}
            for art in digest.articles:
                paper = art.gs_paper or "General"
                grouped.setdefault(paper, []).append(art)

            order = ["GS-1", "GS-2", "GS-3", "GS-4", "MPSC-State", "General"]
            for paper in order:
                arts = grouped.get(paper, [])
                if not arts:
                    continue

                lines.extend([
                    f'== {paper}: Core Themes & Analyses',
                    '#v(0.15cm)',
                ])

                for art in arts:
                    title_esc = escape_typst(art.title)
                    source_esc = escape_typst(art.source)
                    cat_esc = escape_typst(art.category)
                    date_esc = escape_typst(art.published_date)

                    lines.extend([
                        f'=== {title_esc}',
                        f'#text(size: 8.5pt, fill: luma(60))[*Source:* {source_esc} | *Category:* {cat_esc} | *Date:* {date_esc}]',
                        '#v(0.15cm)',
                    ])

                    if art.summary_bullets:
                        lines.append('*Key Issues & Context:*')
                        for b in art.summary_bullets:
                            lines.append(f'- {escape_typst(b)}')
                        lines.append('')

                    if art.prelims_pointers:
                        lines.append('*Prelims High-Yield Facts:*')
                        for p in art.prelims_pointers:
                            lines.append(f'- {escape_typst(p)}')
                        lines.append('')

                    if art.mains_arguments:
                        lines.append('*Mains Analytical Dimensions:*')
                        for dim, args in art.mains_arguments.items():
                            dim_name = escape_typst(dim.replace("_", " ").title())
                            lines.append(f'+ *{dim_name}:*')
                            for a in args:
                                lines.append(f'  - {escape_typst(a)}')
                        lines.append('')

                    if not art.summary_bullets and not art.prelims_pointers:
                        excerpt = art.full_text[:1200] + ("..." if len(art.full_text) > 1200 else "")
                        lines.append(escape_typst(excerpt))
                        lines.append('')

                    lines.append('#line(length: 100%, stroke: 0.35pt + luma(160))')
                    lines.append('#v(0.3cm)')

        return "\n".join(lines)

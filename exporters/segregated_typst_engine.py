"""
Publication-Grade Segregated UPSC & MPSC Compendium Engine.
Faithfully reproduces the layout, typography, and structure of the reference edition:
- Part 1: प्रमुख विश्लेषणात्मक घडामोडी (Tier-1 Atomic Major News Stories [CA-YYMM-XX])
- Part 2: विषयवार स्वतंत्र सूक्ष्म घडामोडी (Subject-Grouped Atomic Micro-News [MN-YYMM-XX])
- Part 3: संदर्भ-जोडणीकृत जलद उजळणी तक्ता (Cross-Referenced Quick Revision Grid Table)
- Part 4: सराव बहुपर्यायी प्रश्नसंच (Verified Practice MCQs)
- Part 5: सर्वोच्च प्राधान्य परीक्षाभिमुख संकलन (Highest-Yield Exam Synthesis)
Fonts: Liberation Serif / Times New Roman + Noto Serif Devanagari / Mukta.
"""
import os
import re
import logging
import subprocess
from datetime import datetime
from typing import Optional, List, Dict, Any

from core.models import DailyDigest, Article, QuizQuestion

logger = logging.getLogger("segregated_typst")


def escape_typst(text: Optional[str]) -> str:
    """Escapes Typst markup characters."""
    if not text:
        return ""
    s = text.replace("\\", "\\\\")
    for ch in ["#", "$", "@", "_", "*", "`", "<", ">"]:
        s = s.replace(ch, f"\\{ch}")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2018", "'").replace("\u2019", "'")
    return s.strip()


class SegregatedTypstEngine:
    """Generates atomic segregated daily current affairs compendiums."""

    def __init__(self, output_dir: str = "output/pdf", fonts_dir: str = "fonts"):
        self.output_dir = output_dir
        self.fonts_dir = fonts_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_digest_pdf(self, digest: DailyDigest, filename: Optional[str] = None) -> str:
        date_str = digest.date or datetime.now().strftime("%Y-%m-%d")
        if not filename:
            filename = f"Daily_Current_Affairs_{date_str}_Segregated.pdf"

        typ_file = os.path.join(self.output_dir, f"segregated_{date_str}.typ")
        pdf_file = os.path.join(self.output_dir, filename)

        typst_source = self._build_markup(digest)
        with open(typ_file, "w", encoding="utf-8") as f:
            f.write(typst_source)

        logger.info(f"Wrote Typst markup to {typ_file}. Compiling...")

        compiled = False
        try:
            import typst
            typst.compile(typ_file, output=pdf_file, font_paths=[self.fonts_dir])
            compiled = True
        except Exception as e:
            logger.warning(f"Python typst library failed ({e}), trying CLI...")

        if not compiled:
            cmd = ["typst", "compile", "--font-path", self.fonts_dir, typ_file, pdf_file]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                compiled = True
            else:
                logger.error(f"Typst compilation failed: {res.stderr}")
                raise RuntimeError(f"Typst compile error: {res.stderr}")

        return pdf_file

    def _build_markup(self, digest: DailyDigest) -> str:
        date_obj = datetime.strptime(digest.date, "%Y-%m-%d") if digest.date else datetime.now()
        marathi_months = {
            1: "जानेवारी", 2: "फेब्रुवारी", 3: "मार्च", 4: "एप्रिल",
            5: "मे", 6: "जून", 7: "जुलै", 8: "ऑगस्ट",
            9: "सप्टेंबर", 10: "ऑक्टोबर", 11: "नोव्हेंबर", 12: "डिसेंबर"
        }
        marathi_date = f"{date_obj.day} {marathi_months.get(date_obj.month, '')} {date_obj.year}"
        date_code = date_obj.strftime("%d%m")

        # Partition articles into Major (Tier-1) vs Micro (Tier-2)
        major_articles = [a for a in digest.articles if len(a.full_text) > 400 or a.source in ["The Hindu", "Indian Express", "Loksatta"]][:10]
        micro_articles = [a for a in digest.articles if a not in major_articles]
        if not micro_articles and len(major_articles) > 5:
            micro_articles = major_articles[5:]
            major_articles = major_articles[:5]

        lines = [
            '// Publication-Grade Segregated Current Affairs Edition',
            '#set page(',
            '  paper: "a4",',
            '  margin: (top: 2.0cm, bottom: 2.0cm, left: 2.2cm, right: 2.2cm),',
            '  header: context {',
            '    [',
            '      #set text(font: ("Noto Serif Devanagari", "Tiro Devanagari Marathi", "Liberation Serif", "Times New Roman"), size: 8.5pt, fill: luma(60))',
            f'      #grid(columns: (1fr, 1fr), align: (left, right), [दैनिक स्पर्धा परीक्षा चालू घडामोडी संकलन | {marathi_date}], [पृष्ठ #here().page()])',
            '      #v(-2pt)',
            '      #line(length: 100%, stroke: 0.5pt + luma(140))',
            '    ]',
            '  },',
            '  footer: context {',
            '    [',
            '      #set text(font: ("Noto Serif Devanagari", "Liberation Serif", "Times New Roman"), size: 8pt, fill: luma(80))',
            '      #line(length: 100%, stroke: 0.5pt + luma(160))',
            '      #align(center)[#here().page()]',
            '    ]',
            '  }',
            ')',
            '',
            '#set text(',
            '  font: ("Noto Serif Devanagari", "Tiro Devanagari Marathi", "Liberation Serif", "Times New Roman"),',
            '  size: 9.6pt,',
            '  lang: "mr"',
            ')',
            '#set par(justify: true, leading: 0.68em)',
            '',
            '// Document Header',
            '#align(center)[',
            '  #text(size: 15pt, weight: "bold")[दैनिक स्पर्धा परीक्षा चालू घडामोडी संकलन]',
            '  #v(0.12cm)',
            f'  #text(size: 10.5pt, weight: "medium")[{marathi_date} | अणू-वर्गीकृत संपादकीय आवृत्ती (Atomic Segregated Edition)]',
            '  #v(0.1cm)',
            '  #text(size: 8.5pt, fill: luma(50))[UPSC नागरी सेवा व MPSC राज्यसेवा / संयुक्त परीक्षा मानकांनुसार स्वतंत्र बातमी क्रमांक (News ID), मूळ स्रोत आणि अभ्यासक्रम दुव्यांसह]',
            '  #v(0.25cm)',
            '  #line(length: 100%, stroke: 0.75pt + black)',
            ']',
            '',
            '// PART 1: Major News Stories',
            '#rect(width: 100%, fill: rgb(240, 240, 240), stroke: (top: 0.75pt + black, bottom: 0.75pt + black), inset: (x: 8pt, y: 5.5pt))[',
            '  #text(size: 10.5pt, weight: "bold")[भाग १: प्रमुख विश्लेषणात्मक घडामोडी (Tier-1 Atomic Major News Stories)]',
            ']',
            '#v(0.2cm)',
        ]

        # Render Major Articles
        grid_items = []
        for idx, art in enumerate(major_articles, 1):
            ca_id = f"CA-{date_code}-{idx:02d}"
            title_esc = escape_typst(art.title)
            cat_esc = escape_typst(art.category or "राष्ट्रीय घडामोडी")
            source_esc = escape_typst(art.source)
            url_esc = escape_typst(art.url)

            # Metadata Strip
            lines.extend([
                f'#v(0.25cm)',
                f'#text(size: 10.5pt, weight: "bold")[[{ca_id}] {title_esc}]',
                f'#v(0.08cm)',
                f'#rect(width: 100%, fill: rgb(247, 247, 247), stroke: (left: 1.5pt + black), inset: (x: 6pt, y: 3.5pt))[',
                f'  #set text(size: 8.2pt)',
                f'  *दिनांक:* {marathi_date} #h(0.4cm) | #h(0.4cm) *प्राथमिक प्रवर्ग:* {cat_esc} #h(0.4cm) | #h(0.4cm) *दुय्यम टॅग:* {art.gs_paper}, {source_esc}',
                f']',
                f'#v(0.12cm)',
            ])

            # What happened
            summary_first = art.summary_bullets[0] if art.summary_bullets else art.full_text[:300]
            lines.append(f'*काय घडले? (What happened?):* {escape_typst(summary_first)}')
            lines.append('')

            # Key facts & institutions
            if len(art.summary_bullets) > 1 or art.prelims_pointers:
                lines.append('*मुख्य तथ्ये, आकडेवारी व संस्था (Key Facts & Institutions):*')
                for b in art.summary_bullets[1:4]:
                    lines.append(f'- {escape_typst(b)}')
                for p in art.prelims_pointers:
                    lines.append(f'- {escape_typst(p)}')
                lines.append('')

            # Background & Significance
            lines.append(f'*पायाभूत संकल्पना व पार्श्वभूमी (Essential Background):* {escape_typst(art.full_text[300:750] if len(art.full_text) > 750 else art.full_text[:350])}')
            lines.append('')

            # Syllabus Linkage
            lines.append(f'*UPSC / MPSC अभ्यासक्रम दुवा (Syllabus Linkage):* पूर्व परीक्षा: {escape_typst(art.category)}. मुख्य परीक्षा ({art.gs_paper}): {escape_typst(art.title[:80])}.')
            lines.append('')

            # Source & Link
            lines.append(f'#text(size: 7.8pt, fill: luma(60))[*प्राथमिक संदर्भ स्रोत:* {source_esc} | *लिंक:* #link("{url_esc}")[{url_esc}]]')
            lines.append('')
            lines.append('#line(length: 100%, stroke: 0.5pt + luma(180))')

            # Add to revision grid data
            fact_summary = art.summary_bullets[0][:90] if art.summary_bullets else art.title[:90]
            grid_items.append((ca_id, cat_esc, fact_summary, f"{art.gs_paper}: पूर्व व मुख्य परीक्षा"))

        # PART 2: Micro News
        lines.extend([
            '#v(0.5cm)',
            '#rect(width: 100%, fill: rgb(240, 240, 240), stroke: (top: 0.75pt + black, bottom: 0.75pt + black), inset: (x: 8pt, y: 5.5pt))[',
            '  #text(size: 10.5pt, weight: "bold")[भाग २: विषयवार स्वतंत्र सूक्ष्म घडामोडी (Subject-Grouped Atomic Micro-News)]',
            ']',
            '#v(0.2cm)',
        ])

        categories_micro = {
            "गट अ: संरक्षण व सुरक्षा (Defence & Security)": [],
            "गट ब: आंतरराष्ट्रीय संबंध व व्यापार (International Relations)": [],
            "गट क: अर्थव्यवस्था व बँकिंग (Economy & Banking)": [],
            "गट ड: शासन, सामाजिक न्याय व संस्कृती (Governance, Social Justice & Culture)": [],
            "गट इ: विज्ञान, तंत्रज्ञान, पर्यावरण व कृषी (Science, Environment & Agriculture)": [],
        }

        # Fallback distribution if specific categories not filled
        cat_keys = list(categories_micro.keys())
        for idx, m_art in enumerate(micro_articles, 1):
            c_idx = idx % len(cat_keys)
            categories_micro[cat_keys[c_idx]].append(m_art)

        micro_idx = 1
        for cat_heading, arts in categories_micro.items():
            if not arts:
                continue
            lines.append(f'*#text(size: 9.8pt)[{cat_heading}]*')
            lines.append('')
            for art in arts:
                mn_id = f"MN-{date_code}-{micro_idx:02d}"
                micro_idx += 1
                body_snip = art.summary_bullets[0] if art.summary_bullets else art.full_text[:280]
                lines.append(f'[{mn_id}] *{escape_typst(art.title)}:* {escape_typst(body_snip)} _(स्रोत: {escape_typst(art.source)}, {marathi_date})_')
                lines.append('')
                # Add to grid items
                grid_items.append((mn_id, escape_typst(art.category or "सामान्य घडामोडी"), escape_typst(art.title[:90]), f"{art.gs_paper}: पूर्व परीक्षा"))
            lines.append('#v(0.15cm)')

        # PART 3: Quick Revision Grid Table
        lines.extend([
            '#v(0.5cm)',
            '#rect(width: 100%, fill: rgb(240, 240, 240), stroke: (top: 0.75pt + black, bottom: 0.75pt + black), inset: (x: 8pt, y: 5.5pt))[',
            '  #text(size: 10.5pt, weight: "bold")[भाग ३: संदर्भ-जोडणीकृत जलद उजळणी तक्ता (Cross-Referenced Quick Revision Grid)]',
            ']',
            '#v(0.2cm)',
            '#table(',
            '  columns: (1.8cm, 2.8cm, 1fr, 3.2cm),',
            '  fill: (col, row) => if row == 0 { rgb(235, 235, 235) } else { none },',
            '  stroke: 0.5pt + luma(140),',
            '  inset: (x: 5pt, y: 5pt),',
            '  align: (center + horizon, left + horizon, left + horizon, left + horizon),',
            '  [*बातमी क्र. (ID)*], [*प्राथमिक प्रवर्ग*], [*मुख्य परीक्षाभिमुख तथ्य (Key Revision Fact)*], [*अभ्यासक्रम संदर्भ*],',
        ])
        for gid, gcat, gfact, gsyl in grid_items[:12]:
            lines.append(f'  [{escape_typst(gid)}], [{escape_typst(gcat)}], [{escape_typst(gfact)}], [{escape_typst(gsyl)}],')
        lines.append(')')
        lines.append('')

        # PART 4: Practice MCQs
        if digest.quizzes:
            lines.extend([
                '#v(0.5cm)',
                '#rect(width: 100%, fill: rgb(240, 240, 240), stroke: (top: 0.75pt + black, bottom: 0.75pt + black), inset: (x: 8pt, y: 5.5pt))[',
                '  #text(size: 10.5pt, weight: "bold")[भाग ४: सराव बहुपर्यायी प्रश्नसंच (Verified Practice MCQs)]',
                ']',
                '#v(0.25cm)',
            ])
            for q in digest.quizzes[:8]:
                q_text = escape_typst(q.question_text)
                lines.append(f'*प्र. {q.question_num}.* {q_text}')
                lines.append('')
                if q.options:
                    opt_line = " #h(0.5cm) ".join([f'*({k})* {escape_typst(v)}' for k, v in sorted(q.options.items())])
                    lines.append(opt_line)
                    lines.append('')
                if q.correct_option or q.explanation:
                    c_opt = f"*उत्तर: ({escape_typst(q.correct_option)})* " if q.correct_option else ""
                    expl = escape_typst(q.explanation)
                    lines.append(f'#rect(width: 100%, stroke: 0.5pt + luma(140), inset: 5pt)[{c_opt}{expl}]')
                    lines.append('')
                lines.append('#v(0.2cm)')

        # PART 5: Highest-Yield Exam Synthesis
        lines.extend([
            '#v(0.4cm)',
            '#text(size: 11pt, weight: "bold")[🎯 सर्वोच्च प्राधान्य परीक्षाभिमुख संकलन (Highest-Yield Exam Synthesis)]',
            '#line(length: 100%, stroke: 0.75pt + black)',
            '#v(0.15cm)',
        ])
        for idx, art in enumerate(major_articles[:4], 1):
            title_esc = escape_typst(art.title)
            ca_id = f"CA-{date_code}-{idx:02d}"
            takeaway = escape_typst(art.summary_bullets[0] if art.summary_bullets else art.full_text[:180])
            lines.append(f'{idx}. *{title_esc} [{ca_id}]:* {takeaway} — राज्यसेवा व नागरी सेवा पूर्व आणि मुख्य परीक्षेसाठी अतिसंभाव्य घटक.')
            lines.append('')

        return "\n".join(lines)

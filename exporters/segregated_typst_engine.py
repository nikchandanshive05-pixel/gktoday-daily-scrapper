"""
Publication-Grade Clean Segregated UPSC & MPSC Compendium Engine.
Features:
- Pure clean titles (ZERO artificial code prefixes like [CA-2410-01] or [ED-2410-01])
- Part 1: प्रमुख विश्लेषणात्मक घडामोडी (Major Analytical Stories)
- Part 2: अग्रगण्य संपादकीय दृष्टिक्षेप व विश्लेषक (In-Depth Editorial Analyses)
- Part 3: विषयवार संक्षिप्त घडामोडी व क्रीडा संकलन (Grouped Micro-News & Consolidated Sports Digest)
- Part 4: संदर्भ-जोडणीकृत जलद उजळणी तक्ता (Quick Revision Grid)
- Part 5: सराव बहुपर्यायी प्रश्नसंच (Consecutive MCQs: प्र. १ ते प्र. ८)
- Part 6: सर्वोच्च प्राधान्य परीक्षाभिमुख संकलन (Highest-Yield Exam Synthesis)
- Sentence boundary integrity (no cut-off fragments)
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


def clean_sentence_boundary(text: str, max_chars: int = 500) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    sub = text[:max_chars]
    matches = list(re.finditer(r"([.!?।])(?:\s+|$)", sub))
    if matches:
        return sub[:matches[-1].end()].strip()
    return sub.rsplit(" ", 1)[0] + "."


class SegregatedTypstEngine:
    """Generates clean publication-grade A4 compendiums."""

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

        # Classify items cleanly
        editorials: List[Article] = []
        major_ca: List[Article] = []
        sports_news: List[Article] = []
        micro_news: List[Article] = []

        for a in digest.articles:
            text_low = (a.title + " " + a.full_text).lower()
            if any(w in text_low for w in ["para games", "asian para", "medal", "sports", "cricket", "billiards", "badminton", "pankaj advani"]):
                sports_news.append(a)
                continue

            is_editorial = (
                a.source in ["The Hindu", "Indian Express"] or
                "संपादकीय" in a.category or "अग्रलेख" in a.title or
                a.source == "Loksatta" or "Explained" in a.title or "Editorial" in a.title
            )
            if is_editorial and len(editorials) < 7:
                editorials.append(a)
            elif len(major_ca) < 7 and (len(a.full_text) > 400 or a.source in ["PIB", "GKToday"]):
                major_ca.append(a)
            else:
                micro_news.append(a)

        lines = [
            '// Publication-Grade Clean Segregated Current Affairs & Editorial Edition',
            '#set page(',
            '  paper: "a4",',
            '  margin: (top: 2.0cm, bottom: 2.0cm, left: 2.2cm, right: 2.2cm),',
            '  header: context {',
            '    [',
            '      #set text(font: ("Noto Serif Devanagari", "Tiro Devanagari Marathi", "Liberation Serif", "Times New Roman"), size: 8.5pt, fill: luma(60))',
            f'      #grid(columns: (1fr, 1fr), align: (left, right), [दैनिक स्पर्धा परीक्षा चालू घडामोडी व संपादकीय संकलन | {marathi_date}], [पृष्ठ #here().page()])',
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
            '  #text(size: 15pt, weight: "bold")[दैनिक स्पर्धा परीक्षा चालू घडामोडी व संपादकीय संकलन]',
            '  #v(0.12cm)',
            f'  #text(size: 10.5pt, weight: "medium")[{marathi_date} | अणू-वर्गीकृत संपादकीय आवृत्ती (Atomic Segregated Edition)]',
            '  #v(0.1cm)',
            '  #text(size: 8.5pt, fill: luma(50))[UPSC नागरी सेवा व MPSC राज्यसेवा / संयुक्त परीक्षा मानकांनुसार अधिकृत स्रोत व अभ्यासक्रम दुव्यांसह]',
            '  #v(0.25cm)',
            '  #line(length: 100%, stroke: 0.75pt + black)',
            ']',
            '',
        ]

        grid_items = []

        # =========================================================
        # PART 1: Major News Stories (Tier-1 Major Articles)
        # =========================================================
        if major_ca:
            lines.extend([
                '#rect(width: 100%, fill: rgb(240, 240, 240), stroke: (top: 0.75pt + black, bottom: 0.75pt + black), inset: (x: 8pt, y: 5.5pt))[',
                '  #text(size: 10.5pt, weight: "bold")[भाग १: प्रमुख विश्लेषणात्मक घडामोडी (Tier-1 Major News Stories)]',
                ']',
                '#v(0.2cm)',
            ])

            for idx, art in enumerate(major_ca, 1):
                title_esc = escape_typst(art.title)
                cat_esc = escape_typst(art.category or "राष्ट्रीय घडामोडी")
                source_esc = escape_typst(art.source)
                url_esc = escape_typst(art.url)

                lines.extend([
                    f'#v(0.25cm)',
                    f'#text(size: 10.5pt, weight: "bold")[१.{idx} {title_esc}]',
                    f'#v(0.08cm)',
                    f'#rect(width: 100%, fill: rgb(247, 247, 247), stroke: (left: 1.5pt + black), inset: (x: 6pt, y: 3.5pt))[',
                    f'  #set text(size: 8.2pt)',
                    f'  *दिनांक:* {marathi_date} #h(0.4cm) | #h(0.4cm) *प्राथमिक प्रवर्ग:* {cat_esc} #h(0.4cm) | #h(0.4cm) *अभ्यासक्रम पेपर:* {art.gs_paper}',
                    f']',
                    f'#v(0.12cm)',
                ])

                summary_first = art.summary_bullets[0] if art.summary_bullets else clean_sentence_boundary(art.full_text, 300)
                lines.append(f'*काय घडले? (What happened?):* {escape_typst(summary_first)}')
                lines.append('')

                if len(art.summary_bullets) > 1 or art.prelims_pointers:
                    lines.append('*मुख्य तथ्ये, आकडेवारी व संस्था (Key Facts & Institutions):*')
                    for b in art.summary_bullets[1:4]:
                        lines.append(f'- {escape_typst(clean_sentence_boundary(b, 200))}')
                    for p in art.prelims_pointers:
                        lines.append(f'- {escape_typst(p)}')
                    lines.append('')

                bg_text = clean_sentence_boundary(art.full_text[300:850] if len(art.full_text) > 850 else art.full_text[:400], 450)
                lines.append(f'*पायाभूत संकल्पना व पार्श्वभूमी (Essential Background):* {escape_typst(bg_text)}')
                lines.append('')

                lines.append(f'*UPSC / MPSC अभ्यासक्रम दुवा (Syllabus Linkage):* पूर्व परीक्षा: {cat_esc}. मुख्य परीक्षा ({art.gs_paper}): {title_esc[:80]}.')
                lines.append('')

                lines.append(f'#text(size: 7.8pt, fill: luma(60))[*प्राथमिक संदर्भ स्रोत:* {source_esc} | *लिंक:* #link("{url_esc}")[{url_esc}]]')
                lines.append('')
                lines.append('#line(length: 100%, stroke: 0.5pt + luma(180))')

                grid_items.append((f"प्रमुख {idx}", cat_esc, clean_sentence_boundary(summary_first, 90), f"{art.gs_paper}: पूर्व व मुख्य परीक्षा"))

        # =========================================================
        # PART 2: DEDICATED EDITORIAL ANALYSES (Tier-1 Editorials)
        # =========================================================
        if editorials:
            lines.extend([
                '#v(0.5cm)',
                '#rect(width: 100%, fill: rgb(240, 240, 240), stroke: (top: 0.75pt + black, bottom: 0.75pt + black), inset: (x: 8pt, y: 5.5pt))[',
                '  #text(size: 10.5pt, weight: "bold")[भाग २: अग्रगण्य संपादकीय दृष्टिक्षेप व विश्लेषक (Tier-1 Editorial Analyses & Op-Eds)]',
                ']',
                '#v(0.2cm)',
            ])

            for idx, ed in enumerate(editorials, 1):
                title_esc = escape_typst(ed.title)
                source_esc = escape_typst(ed.source)
                paper_esc = escape_typst(ed.gs_paper)
                url_esc = escape_typst(ed.url)

                lines.extend([
                    f'#v(0.25cm)',
                    f'#text(size: 10.5pt, weight: "bold")[२.{idx} {title_esc}]',
                    f'#v(0.08cm)',
                    f'#rect(width: 100%, fill: rgb(247, 247, 247), stroke: (left: 1.5pt + black), inset: (x: 6pt, y: 3.5pt))[',
                    f'  #set text(size: 8.2pt)',
                    f'  *संपादकीय स्रोत:* {source_esc} #h(0.4cm) | #h(0.4cm) *अभ्यासक्रम पेपर:* {paper_esc} #h(0.4cm) | #h(0.4cm) *दिनांक:* {marathi_date}',
                    f']',
                    f'#v(0.12cm)',
                ])

                # Core context
                if ed.summary_bullets:
                    lines.append('*संपादकीय संदर्भ व मूळ विचार (Core Context & Arguments):*')
                    for b in ed.summary_bullets[:3]:
                        lines.append(f'- {escape_typst(clean_sentence_boundary(b, 220))}')
                    lines.append('')
                else:
                    lines.append(f'*संपादकीय सारांश:* {escape_typst(clean_sentence_boundary(ed.full_text, 350))}')
                    lines.append('')

                # Mains Dimensions (Constitutional, Judicial, Policy)
                if ed.mains_arguments:
                    lines.append('*मुख्य परीक्षा विश्लेषणात्मक आयाम (Mains Analytical Dimensions):*')
                    for dim, points in ed.mains_arguments.items():
                        dim_title = escape_typst(dim)
                        pt_str = " ; ".join([escape_typst(clean_sentence_boundary(p, 180)) for p in points[:2]])
                        lines.append(f'+ *{dim_title}:* {pt_str}')
                    lines.append('')

                # Analysis body
                body_excerpt = clean_sentence_boundary(ed.full_text[350:950] if len(ed.full_text) > 950 else ed.full_text[:450], 480)
                lines.append(f'*सविस्तर विश्लेषण व निष्कर्ष (In-Depth Editorial Analysis):* {escape_typst(body_excerpt)}')
                lines.append('')

                lines.append(f'#text(size: 7.8pt, fill: luma(60))[*मूळ संपादकीय वाचन दुवा:* #link("{url_esc}")[{url_esc}]]')
                lines.append('')
                lines.append('#line(length: 100%, stroke: 0.5pt + luma(180))')

                grid_items.append((f"संपादकीय {idx}", f"{source_esc}", clean_sentence_boundary(ed.title, 90), f"{paper_esc}: मुख्य परीक्षा"))

        # =========================================================
        # PART 3: Consolidated Sports Digest & Micro News
        # =========================================================
        lines.extend([
            '#v(0.5cm)',
            '#rect(width: 100%, fill: rgb(240, 240, 240), stroke: (top: 0.75pt + black, bottom: 0.75pt + black), inset: (x: 8pt, y: 5.5pt))[',
            '  #text(size: 10.5pt, weight: "bold")[भाग ३: विषयवार संक्षिप्त घडामोडी व क्रीडा संकलन (Grouped Micro-News & Sports Digest)]',
            ']',
            '#v(0.2cm)',
        ])

        # A. Consolidated Sports Digest Table
        if sports_news:
            lines.extend([
                '*#text(size: 10pt)[🏆 क्रीडा व पुरस्कार संक्षिप्त संकलन (Consolidated Sports & Honours Digest)]*',
                '#v(0.1cm)',
                '#table(',
                '  columns: (2.8cm, 3.2cm, 1fr),',
                '  fill: (col, row) => if row == 0 { rgb(235, 235, 235) } else { none },',
                '  stroke: 0.5pt + luma(140),',
                '  inset: (x: 5pt, y: 4.5pt),',
                '  align: (left + horizon, left + horizon, left + horizon),',
                '  [*खेळाडू / स्पर्धा*], [*क्रीडा प्रकार / पदक*], [*महत्त्वपूर्ण विक्रम व नोंद (High-Yield Facts)*],',
            ])
            for s in sports_news[:6]:
                s_title = escape_typst(s.title[:45])
                s_cat = escape_typst(s.category or "क्रीडा")
                s_note = escape_typst(clean_sentence_boundary(s.summary_bullets[0] if s.summary_bullets else s.full_text, 140))
                lines.append(f'  [{s_title}], [{s_cat}], [{s_note}],')
            lines.append(')')
            lines.append('#v(0.3cm)')

        # B. Subject Grouped Micro News
        categories_micro = {
            "संरक्षण व सुरक्षा (Defence & Internal Security)": [],
            "अर्थव्यवस्था व कृषी (Economy & Agriculture)": [],
            "विज्ञान, तंत्रज्ञान व पर्यावरण (Science, Tech & Environment)": [],
            "शासन, राज्यव्यवस्था व समाज (Governance & Society)": [],
        }

        cat_keys = list(categories_micro.keys())
        for idx, m_art in enumerate(micro_news[:12], 1):
            c_idx = idx % len(cat_keys)
            categories_micro[cat_keys[c_idx]].append(m_art)

        for cat_heading, arts in categories_micro.items():
            if not arts:
                continue
            lines.append(f'*#text(size: 9.8pt)[• {cat_heading}]*')
            lines.append('')
            for art in arts:
                body_snip = clean_sentence_boundary(art.summary_bullets[0] if art.summary_bullets else art.full_text, 220)
                lines.append(f'• *{escape_typst(art.title)}:* {escape_typst(body_snip)} _(स्रोत: {escape_typst(art.source)})_')
                lines.append('')
                grid_items.append((f"संक्षिप्त", escape_typst(art.category[:20]), escape_typst(art.title[:80]), f"{art.gs_paper}: पूर्व परीक्षा"))
            lines.append('#v(0.15cm)')

        # =========================================================
        # PART 4: Quick Revision Grid Table
        # =========================================================
        lines.extend([
            '#v(0.5cm)',
            '#rect(width: 100%, fill: rgb(240, 240, 240), stroke: (top: 0.75pt + black, bottom: 0.75pt + black), inset: (x: 8pt, y: 5.5pt))[',
            '  #text(size: 10.5pt, weight: "bold")[भाग ४: संदर्भ-जोडणीकृत जलद उजळणी तक्ता (Cross-Referenced Quick Revision Grid)]',
            ']',
            '#v(0.2cm)',
            '#table(',
            '  columns: (2.2cm, 3.2cm, 1fr, 3.2cm),',
            '  fill: (col, row) => if row == 0 { rgb(235, 235, 235) } else { none },',
            '  stroke: 0.5pt + luma(140),',
            '  inset: (x: 5pt, y: 5pt),',
            '  align: (center + horizon, left + horizon, left + horizon, left + horizon),',
            '  [*अनुक्रमांक*], [*प्राथमिक प्रवर्ग*], [*मुख्य परीक्षाभिमुख तथ्य (Key Revision Fact)*], [*अभ्यासक्रम संदर्भ*],',
        ])
        for gid, gcat, gfact, gsyl in grid_items[:14]:
            lines.append(f'  [{escape_typst(gid)}], [{escape_typst(gcat)}], [{escape_typst(gfact)}], [{escape_typst(gsyl)}],')
        lines.append(')')
        lines.append('')

        # =========================================================
        # PART 5: Consecutively Numbered Practice MCQs (Q1 to Q8)
        # =========================================================
        if digest.quizzes:
            lines.extend([
                '#v(0.5cm)',
                '#rect(width: 100%, fill: rgb(240, 240, 240), stroke: (top: 0.75pt + black, bottom: 0.75pt + black), inset: (x: 8pt, y: 5.5pt))[',
                '  #text(size: 10.5pt, weight: "bold")[भाग ५: सराव बहुपर्यायी प्रश्नसंच (Verified Practice MCQs)]',
                ']',
                '#v(0.25cm)',
            ])
            for q_idx, q in enumerate(digest.quizzes[:8], 1):
                q_text = escape_typst(q.question_text)
                lines.append(f'*प्र. {q_idx}.* {q_text}')
                lines.append('')
                if q.options:
                    opt_line = " #h(0.5cm) ".join([f'*({k})* {escape_typst(v)}' for k, v in sorted(q.options.items())])
                    lines.append(opt_line)
                    lines.append('')
                if q.correct_option or q.explanation:
                    c_opt = f"*उत्तर: ({escape_typst(q.correct_option)})* " if q.correct_option else ""
                    expl = escape_typst(clean_sentence_boundary(q.explanation, 250))
                    lines.append(f'#rect(width: 100%, stroke: 0.5pt + luma(140), inset: 5pt)[{c_opt}{expl}]')
                    lines.append('')
                lines.append('#v(0.2cm)')

        # =========================================================
        # PART 6: Highest-Yield Exam Synthesis
        # =========================================================
        lines.extend([
            '#v(0.4cm)',
            '#text(size: 11pt, weight: "bold")[🎯 सर्वोच्च प्राधान्य परीक्षाभिमुख संकलन (Highest-Yield Exam Synthesis)]',
            '#line(length: 100%, stroke: 0.75pt + black)',
            '#v(0.15cm)',
        ])
        top_picks = (major_ca[:2] + editorials[:2]) if editorials else major_ca[:4]
        for idx, art in enumerate(top_picks, 1):
            title_esc = escape_typst(art.title)
            takeaway = escape_typst(clean_sentence_boundary(art.summary_bullets[0] if art.summary_bullets else art.full_text, 180))
            lines.append(f'{idx}. *{title_esc}:* {takeaway} — राज्यसेवा व नागरी सेवा पूर्व आणि मुख्य परीक्षेसाठी अतिसंभाव्य घटक.')
            lines.append('')

        return "\n".join(lines)

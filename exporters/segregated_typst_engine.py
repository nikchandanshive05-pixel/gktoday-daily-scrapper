"""
Publication-Grade Editorial Segregated UPSC, MPSC & CWC Compendium Engine.
Implements Oxford/The Economist-grade subtle professional palette:
- c-navy: rgb(26, 54, 93)   [Oxford Deep Navy for titles, section banners, table headers]
- c-slate: rgb(34, 37, 42)  [Off-black charcoal ink for high-legibility body text]
- c-muted: rgb(90, 101, 120)[Slate grey for thin dividers and metadata]
- c-tint: rgb(244, 246, 249)[Soft cool tint for callout backgrounds]
- c-green: rgb(42, 106, 78) [Forest olive green for correct MCQ answers and Agri/CWC]
- c-amber: rgb(160, 94, 26) [Muted terracotta for Prelims high-yield highlights]

Structure:
- Part 1: प्रमुख विश्लेषणात्मक घडामोडी (Major Analytical Stories)
- Part 2: अग्रगण्य संपादकीय दृष्टिक्षेप व विश्लेषक (In-Depth Editorial Analyses)
- Part 3: क्रीडा संकलन व विषयवार संक्षिप्त घडामोडी (Consolidated Sports & Micro News)
- Part 4: संदर्भ-जोडणीकृत जलद उजळणी तक्ता (Quick Revision Grid Table with Navy Headers)
- Part 5: सराव बहुपर्यायी प्रश्नसंच (Consecutive MCQs with Forest Green Answer Badges)
- Part 6: सर्वोच्च प्राधान्य परीक्षाभिमुख संकलन (Highest-Yield Exam Synthesis)
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
    """Generates clean publication-grade A4 compendiums with subtle editorial color styling."""

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

        # Classify items cleanly without artificial caps (allowing exhaustive depth)
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
            if is_editorial:
                editorials.append(a)
            elif len(a.full_text) > 400 or a.source in ["PIB", "GKToday"]:
                major_ca.append(a)
            else:
                micro_news.append(a)

        lines = [
            '// Publication-Grade Editorial Segregated Edition (Oxford Editorial Palette)',
            '#let c-navy = rgb(26, 54, 93)',
            '#let c-slate = rgb(34, 37, 42)',
            '#let c-muted = rgb(90, 101, 120)',
            '#let c-tint = rgb(244, 246, 249)',
            '#let c-border = rgb(220, 226, 235)',
            '#let c-amber = rgb(160, 94, 26)',
            '#let c-green = rgb(42, 106, 78)',
            '',
            '#set page(',
            '  paper: "a4",',
            '  margin: (top: 2.0cm, bottom: 2.0cm, left: 2.2cm, right: 2.2cm),',
            '  header: context {',
            '    [',
            '      #set text(font: ("Noto Serif Devanagari", "Tiro Devanagari Marathi", "Liberation Serif", "Times New Roman"), size: 8.5pt, fill: c-muted)',
            f'      #grid(columns: (1fr, 1fr), align: (left, right), [दैनिक स्पर्धा परीक्षा चालू घडामोडी व संपादकीय संकलन | {marathi_date}], [पृष्ठ #here().page()])',
            '      #v(-2pt)',
            '      #line(length: 100%, stroke: 0.5pt + c-border)',
            '    ]',
            '  },',
            '  footer: context {',
            '    [',
            '      #set text(font: ("Noto Serif Devanagari", "Liberation Serif", "Times New Roman"), size: 8pt, fill: c-muted)',
            '      #line(length: 100%, stroke: 0.5pt + c-border)',
            '      #align(center)[#here().page()]',
            '    ]',
            '  }',
            ')',
            '',
            '#set text(',
            '  font: ("Noto Serif Devanagari", "Tiro Devanagari Marathi", "Liberation Serif", "Times New Roman"),',
            '  size: 9.6pt,',
            '  fill: c-slate,',
            '  lang: "mr"',
            ')',
            '#set par(justify: true, leading: 0.70em)',
            '',
            '// Document Header',
            '#align(center)[',
            '  #text(size: 16pt, weight: "bold", fill: c-navy)[दैनिक स्पर्धा परीक्षा चालू घडामोडी व संपादकीय संकलन]',
            '  #v(0.12cm)',
            f'  #text(size: 10.5pt, weight: "medium", fill: c-slate)[{marathi_date} | अणू-वर्गीकृत संपादकीय आवृत्ती (Atomic Segregated Edition)]',
            '  #v(0.1cm)',
            '  #text(size: 8.5pt, fill: c-muted)[UPSC नागरी सेवा, MPSC राज्यसेवा व CWC परीक्षा मानकांनुसार अधिकृत स्रोत, तांत्रिक पैलू व अभ्यासक्रम दुव्यांसह]',
            '  #v(0.25cm)',
            '  #line(length: 100%, stroke: 1.2pt + c-navy)',
            ']',
            '',
        ]

        grid_items = []

        # =========================================================
        # PART 1: Major News Stories (Tier-1 Major Articles)
        # =========================================================
        if major_ca:
            lines.extend([
                '#rect(',
                '  width: 100%,',
                '  fill: c-tint,',
                '  stroke: (left: 3.5pt + c-navy, top: 0.5pt + c-border, bottom: 0.5pt + c-border, right: 0.5pt + c-border),',
                '  inset: (x: 10pt, y: 7pt),',
                '  radius: (right: 3pt)',
                ')[',
                '  #text(size: 11pt, weight: "bold", fill: c-navy)[भाग १: प्रमुख विश्लेषणात्मक घडामोडी (Tier-1 Major News Stories)]',
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
                    f'#text(size: 10.5pt, weight: "bold", fill: c-navy)[१.{idx} {title_esc}]',
                    f'#v(0.08cm)',
                    f'#rect(',
                    f'  width: 100%,',
                    f'  fill: c-tint,',
                    f'  stroke: (left: 2pt + c-navy, top: 0.3pt + c-border, bottom: 0.3pt + c-border, right: 0.3pt + c-border),',
                    f'  inset: (x: 7pt, y: 4.5pt),',
                    f'  radius: (right: 2pt)',
                    f')[',
                    f'  #set text(size: 8.2pt, fill: c-slate)',
                    f'  *दिनांक:* {marathi_date} #h(0.4cm) • #h(0.4cm) *प्राथमिक प्रवर्ग:* {cat_esc} #h(0.4cm) • #h(0.4cm) #text(fill: c-navy, weight: "bold")[[{art.gs_paper}]]',
                    f']',
                    f'#v(0.12cm)',
                ])

                summary_first = art.summary_bullets[0] if art.summary_bullets else clean_sentence_boundary(art.full_text, 300)
                lines.append(f'*काय घडले? (What happened?):* {escape_typst(summary_first)}')
                lines.append('')

                if len(art.summary_bullets) > 1 or art.prelims_pointers:
                    lines.append(f'*#text(fill: c-navy)[मुख्य तथ्ये, आकडेवारी व संस्था (Key Facts & Institutions):]*')
                    for b in art.summary_bullets[1:4]:
                        lines.append(f'- {escape_typst(clean_sentence_boundary(b, 220))}')
                    for p in art.prelims_pointers:
                        lines.append(f'- #text(fill: c-amber, weight: "medium")[\u25b6 {escape_typst(p)}]')
                    lines.append('')

                bg_text = clean_sentence_boundary(art.full_text[300:850] if len(art.full_text) > 850 else art.full_text[:400], 480)
                lines.append(f'*पायाभूत संकल्पना व पार्श्वभूमी (Essential Background):* {escape_typst(bg_text)}')
                lines.append('')

                lines.append(f'*UPSC / MPSC / CWC अभ्यासक्रम दुवा (Syllabus Linkage):* पूर्व परीक्षा: {cat_esc}. मुख्य परीक्षा ({art.gs_paper}): {title_esc[:80]}.')
                lines.append('')

                lines.append(f'#text(size: 7.8pt, fill: c-muted)[*प्राथमिक संदर्भ स्रोत:* {source_esc} | *लिंक:* #link("{url_esc}")[{url_esc}]]')
                lines.append('')
                lines.append('#line(length: 100%, stroke: 0.5pt + c-border)')

                grid_items.append((f"१.{idx}", cat_esc, clean_sentence_boundary(summary_first, 90), f"{art.gs_paper}: पूर्व व मुख्य परीक्षा"))

        # =========================================================
        # PART 2: DEDICATED EDITORIAL ANALYSES (Tier-1 Editorials)
        # =========================================================
        if editorials:
            lines.extend([
                '#v(0.5cm)',
                '#rect(',
                '  width: 100%,',
                '  fill: c-tint,',
                '  stroke: (left: 3.5pt + c-navy, top: 0.5pt + c-border, bottom: 0.5pt + c-border, right: 0.5pt + c-border),',
                '  inset: (x: 10pt, y: 7pt),',
                '  radius: (right: 3pt)',
                ')[',
                '  #text(size: 11pt, weight: "bold", fill: c-navy)[भाग २: अग्रगण्य संपादकीय दृष्टिक्षेप व विश्लेषक (Tier-1 Editorial Analyses & Op-Eds)]',
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
                    f'#text(size: 10.5pt, weight: "bold", fill: c-navy)[२.{idx} {title_esc}]',
                    f'#v(0.08cm)',
                    f'#rect(',
                    f'  width: 100%,',
                    f'  fill: c-tint,',
                    f'  stroke: (left: 2pt + c-navy, top: 0.3pt + c-border, bottom: 0.3pt + c-border, right: 0.3pt + c-border),',
                    f'  inset: (x: 7pt, y: 4.5pt),',
                    f'  radius: (right: 2pt)',
                    f')[',
                    f'  #set text(size: 8.2pt, fill: c-slate)',
                    f'  *संपादकीय स्रोत:* {source_esc} #h(0.4cm) • #h(0.4cm) *अभ्यासक्रम पेपर:* #text(fill: c-navy, weight: "bold")[[{paper_esc}]] #h(0.4cm) • #h(0.4cm) *दिनांक:* {marathi_date}',
                    f']',
                    f'#v(0.12cm)',
                ])

                if ed.summary_bullets:
                    lines.append(f'*#text(fill: c-navy)[संपादकीय संदर्भ व मूळ विचार (Core Context & Arguments):]*')
                    for b in ed.summary_bullets[:3]:
                        lines.append(f'- {escape_typst(clean_sentence_boundary(b, 220))}')
                    lines.append('')
                else:
                    lines.append(f'*संपादकीय सारांश:* {escape_typst(clean_sentence_boundary(ed.full_text, 350))}')
                    lines.append('')

                # Mains Dimensions
                if ed.mains_arguments:
                    lines.append(f'*#text(fill: c-navy)[मुख्य परीक्षा विश्लेषणात्मक आयाम (Mains Analytical Dimensions):]*')
                    for dim, points in ed.mains_arguments.items():
                        dim_title = escape_typst(dim)
                        pt_str = " ; ".join([escape_typst(clean_sentence_boundary(p, 180)) for p in points[:2]])
                        lines.append(f'+ #text(weight: "bold", fill: c-slate)[{dim_title}:] {pt_str}')
                    lines.append('')

                body_excerpt = clean_sentence_boundary(ed.full_text[350:1000] if len(ed.full_text) > 1000 else ed.full_text[:500], 520)
                lines.append(f'*सविस्तर विश्लेषण व निष्कर्ष (In-Depth Editorial Analysis):* {escape_typst(body_excerpt)}')
                lines.append('')

                lines.append(f'#text(size: 7.8pt, fill: c-muted)[*मूळ संपादकीय वाचन दुवा:* #link("{url_esc}")[{url_esc}]]')
                lines.append('')
                lines.append('#line(length: 100%, stroke: 0.5pt + c-border)')

                grid_items.append((f"२.{idx}", f"{source_esc}", clean_sentence_boundary(ed.title, 90), f"{paper_esc}: मुख्य परीक्षा"))

        # =========================================================
        # PART 3: Consolidated Sports Digest & Micro News
        # =========================================================
        lines.extend([
            '#v(0.5cm)',
            '#rect(',
            '  width: 100%,',
            '  fill: c-tint,',
            '  stroke: (left: 3.5pt + c-navy, top: 0.5pt + c-border, bottom: 0.5pt + c-border, right: 0.5pt + c-border),',
            '  inset: (x: 10pt, y: 7pt),',
            '  radius: (right: 3pt)',
            ')[',
            '  #text(size: 11pt, weight: "bold", fill: c-navy)[भाग ३: क्रीडा संकलन व विषयवार संक्षिप्त घडामोडी (Sports & Micro-News)]',
            ']',
            '#v(0.2cm)',
        ])

        # A. Consolidated Sports Digest Table with Oxford Navy Header
        if sports_news:
            lines.extend([
                '*#text(size: 10pt, fill: c-navy)[🏆 क्रीडा व पुरस्कार संक्षिप्त संकलन (Consolidated Sports & Honours Digest)]*',
                '#v(0.1cm)',
                '#table(',
                '  columns: (3.0cm, 3.2cm, 1fr),',
                '  fill: (col, row) => if row == 0 { c-navy } else if calc.even(row) { rgb(248, 250, 252) } else { none },',
                '  stroke: 0.4pt + c-border,',
                '  inset: (x: 6pt, y: 5pt),',
                '  align: (left + horizon, left + horizon, left + horizon),',
                '  [*#text(fill: white)[खेळाडू / स्पर्धा]*], [*#text(fill: white)[क्रीडा प्रकार / पदक]*], [*#text(fill: white)[महत्त्वपूर्ण विक्रम व नोंद (High-Yield Facts)]*],',
            ])
            for s in sports_news[:8]:
                s_title = escape_typst(s.title[:45])
                s_cat = escape_typst(s.category or "क्रीडा")
                s_note = escape_typst(clean_sentence_boundary(s.summary_bullets[0] if s.summary_bullets else s.full_text, 140))
                lines.append(f'  [{s_title}], [{s_cat}], [{s_note}],')
            lines.append(')')
            lines.append('#v(0.3cm)')

        # B. Subject Grouped Micro News
        categories_micro = {
            "संरक्षण व सुरक्षा (Defence & Internal Security)": [],
            "अर्थव्यवस्था, कृषी व गोदाम व्यवस्थापन (Economy, Agri & CWC)": [],
            "विज्ञान, जैवतंत्रज्ञान व पर्यावरण (Science, Biotech & Environment)": [],
            "शासन, राज्यव्यवस्था व समाज (Governance & Society)": [],
        }

        cat_keys = list(categories_micro.keys())
        for idx, m_art in enumerate(micro_news, 1):
            c_idx = idx % len(cat_keys)
            categories_micro[cat_keys[c_idx]].append(m_art)

        for cat_heading, arts in categories_micro.items():
            if not arts:
                continue
            lines.append(f'*#text(size: 9.8pt, fill: c-navy)[• {cat_heading}]*')
            lines.append('')
            for art in arts:
                body_snip = clean_sentence_boundary(art.summary_bullets[0] if art.summary_bullets else art.full_text, 220)
                lines.append(f'• *{escape_typst(art.title)}:* {escape_typst(body_snip)} _(स्रोत: {escape_typst(art.source)})_')
                lines.append('')
                grid_items.append(("संक्षिप्त", escape_typst(art.category[:20]), escape_typst(art.title[:80]), f"{art.gs_paper}: पूर्व परीक्षा"))
            lines.append('#v(0.15cm)')

        # =========================================================
        # PART 4: Quick Revision Grid Table with Oxford Navy Header
        # =========================================================
        lines.extend([
            '#v(0.5cm)',
            '#rect(',
            '  width: 100%,',
            '  fill: c-tint,',
            '  stroke: (left: 3.5pt + c-navy, top: 0.5pt + c-border, bottom: 0.5pt + c-border, right: 0.5pt + c-border),',
            '  inset: (x: 10pt, y: 7pt),',
            '  radius: (right: 3pt)',
            ')[',
            '  #text(size: 11pt, weight: "bold", fill: c-navy)[भाग ४: संदर्भ-जोडणीकृत जलद उजळणी तक्ता (Cross-Referenced Quick Revision Grid)]',
            ']',
            '#v(0.2cm)',
            '#table(',
            '  columns: (2.0cm, 3.2cm, 1fr, 3.2cm),',
            '  fill: (col, row) => if row == 0 { c-navy } else if calc.even(row) { rgb(248, 250, 252) } else { none },',
            '  stroke: 0.4pt + c-border,',
            '  inset: (x: 6pt, y: 5pt),',
            '  align: (center + horizon, left + horizon, left + horizon, left + horizon),',
            '  [*#text(fill: white)[क्रमांक]*], [*#text(fill: white)[प्राथमिक प्रवर्ग]*], [*#text(fill: white)[मुख्य परीक्षाभिमुख तथ्य (Key Revision Fact)]*], [*#text(fill: white)[अभ्यासक्रम संदर्भ]*],',
        ])
        for gid, gcat, gfact, gsyl in grid_items:
            lines.append(f'  [{escape_typst(gid)}], [{escape_typst(gcat)}], [{escape_typst(gfact)}], [{escape_typst(gsyl)}],')
        lines.append(')')
        lines.append('')

        # =========================================================
        # PART 5: Consecutively Numbered Practice MCQs (Forest Green Answer Badges)
        # =========================================================
        if digest.quizzes:
            lines.extend([
                '#v(0.5cm)',
                '#rect(',
                '  width: 100%,',
                '  fill: c-tint,',
                '  stroke: (left: 3.5pt + c-navy, top: 0.5pt + c-border, bottom: 0.5pt + c-border, right: 0.5pt + c-border),',
                '  inset: (x: 10pt, y: 7pt),',
                '  radius: (right: 3pt)',
                ')[',
                '  #text(size: 11pt, weight: "bold", fill: c-navy)[भाग ५: सराव बहुपर्यायी प्रश्नसंच (Verified Practice MCQs)]',
                ']',
                '#v(0.25cm)',
            ])
            for q_idx, q in enumerate(digest.quizzes, 1):
                q_text = escape_typst(q.question_text)
                lines.append(f'*#text(fill: c-navy)[प्र. {q_idx}.]* {q_text}')
                lines.append('')
                if q.options:
                    opt_line = " #h(0.5cm) ".join([f'*({k})* {escape_typst(v)}' for k, v in sorted(q.options.items())])
                    lines.append(opt_line)
                    lines.append('')
                if q.correct_option or q.explanation:
                    c_opt = f'#text(fill: c-green, weight: "bold")[उत्तर: ({escape_typst(q.correct_option)})] ' if q.correct_option else ""
                    expl = escape_typst(clean_sentence_boundary(q.explanation, 250))
                    lines.append(f'#rect(width: 100%, fill: c-tint, stroke: (left: 2.5pt + c-green, top: 0.3pt + c-border, bottom: 0.3pt + c-border, right: 0.3pt + c-border), inset: (x: 8pt, y: 5.5pt), radius: (right: 2pt))[{c_opt}#h(0.2cm){expl}]')
                    lines.append('')
                lines.append('#v(0.2cm)')

        # =========================================================
        # PART 6: Highest-Yield Exam Synthesis
        # =========================================================
        lines.extend([
            '#v(0.4cm)',
            '#text(size: 11.5pt, weight: "bold", fill: c-navy)[🎯 सर्वोच्च प्राधान्य परीक्षाभिमुख संकलन (Highest-Yield Exam Synthesis)]',
            '#line(length: 100%, stroke: 1pt + c-navy)',
            '#v(0.15cm)',
        ])
        top_picks = (major_ca[:3] + editorials[:3]) if editorials else major_ca[:5]
        for idx, art in enumerate(top_picks, 1):
            title_esc = escape_typst(art.title)
            takeaway = escape_typst(clean_sentence_boundary(art.summary_bullets[0] if art.summary_bullets else art.full_text, 180))
            lines.append(f'{idx}. *#text(fill: c-navy)[{title_esc}:]* {takeaway} — राज्यसेवा, नागरी सेवा व CWC तांत्रिक परीक्षेसाठी अतिसंभाव्य घटक.')
            lines.append('')

        return "\n".join(lines)

"""
Obsidian and PKM-ready Markdown exporter with YAML frontmatter.
Generates structured markdown notes for individual articles and a master daily index.
"""
import os
import re
import logging
from typing import List
from core.models import DailyDigest, Article

logger = logging.getLogger("markdown_engine")


def slugify(text: str) -> str:
    """Generate a filesystem-safe slug from a title."""
    s = re.sub(r"[^\w\s-]", "", text.strip().lower())
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s[:60] if s else "untitled-note"


class MarkdownExporter:
    """Exports articles into Obsidian-compatible markdown notes."""

    def __init__(self, output_dir: str = "output/notes"):
        self.output_dir = output_dir

    def export(self, digest: DailyDigest) -> List[str]:
        day_dir = os.path.join(self.output_dir, digest.date)
        os.makedirs(day_dir, exist_ok=True)
        generated_files = []

        # 1. Export each individual article note
        for art in digest.articles:
            filename = f"{slugify(art.title)}.md"
            filepath = os.path.join(day_dir, filename)
            content = self._render_article_markdown(art)

            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                generated_files.append(filepath)
            except Exception as e:
                logger.error(f"Failed to write markdown note for {art.title}: {e}")

        # 2. Export Master Index note
        index_path = os.path.join(day_dir, "00_DAILY_INDEX.md")
        index_content = self._render_index_markdown(digest)
        try:
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(index_content)
            generated_files.append(index_path)
        except Exception as e:
            logger.error(f"Failed to write daily index note: {e}")

        logger.info(f"Markdown Exporter generated {len(generated_files)} notes in {day_dir}")
        return generated_files

    def _render_article_markdown(self, art: Article) -> str:
        topics_yaml = "\n".join([f'  - "{t}"' for t in art.syllabus_topics]) if art.syllabus_topics else '  - "Current Affairs"'
        
        clean_title = art.title.replace('"', '\\"')
        md = f"""---
title: "{clean_title}"
date: {art.published_date}
source: "{art.source}"
language: "{art.language}"
author: "{art.author or 'Editorial Staff'}"
paper: "{art.gs_paper}"
exam_focus: "{art.exam_stage}"
relevance_score: {art.relevance_score}
url: "{art.url}"
topics:
{topics_yaml}
---

# {art.title}

> **Source**: [{art.source}]({art.url}) | **Paper**: `{art.gs_paper}` | **Relevance**: `{art.relevance_score}/10`

---

## 🎯 Executive Summary
"""
        for b in art.summary_bullets:
            md += f"- {b}\n"

        if art.prelims_pointers:
            md += "\n## 📌 Prelims High-Yield Facts\n"
            for p in art.prelims_pointers:
                md += f"- {p}\n"

        if art.mains_arguments:
            md += "\n## ⚖️ Mains Dimensions\n"
            for heading, points in art.mains_arguments.items():
                md += f"### {heading}\n"
                for pt in points:
                    md += f"- {pt}\n"

        md += f"\n---\n\n## 📖 Full Article Text\n\n{art.full_text}\n"
        return md

    def _render_index_markdown(self, digest: DailyDigest) -> str:
        md = f"""---
title: "Civil Services Daily Review - {digest.date}"
date: {digest.date}
total_articles: {len(digest.articles)}
total_quizzes: {len(digest.quizzes)}
---

# 📚 Civil Services Daily Compendium ({digest.date})

Daily curated editorials, explainers, and test MCQs mapped across UPSC & MPSC syllabus.

## 📑 Articles & Editorials

"""
        # Group by GS Paper
        by_paper = {}
        for a in digest.articles:
            by_paper.setdefault(a.gs_paper, []).append(a)

        for paper, arts in sorted(by_paper.items()):
            md += f"### {paper}\n\n"
            for a in arts:
                slug = slugify(a.title)
                md += f"- [[{slug}|{a.title}]] — *{a.source}* ({a.exam_stage})\n"
            md += "\n"

        if digest.quizzes:
            md += "## 📝 Daily Practice MCQs\n\n"
            for q in digest.quizzes:
                md += f"**Q{q.question_num}. {q.question_text}**\n"
                for opt_key, opt_val in q.options.items():
                    md += f"- [{opt_key}] {opt_val}\n"
                if q.correct_option:
                    md += f"\n> **Correct Answer: [{q.correct_option}]**\n"
                if q.explanation:
                    md += f"> *Notes*: {q.explanation}\n"
                md += "\n"

        return md

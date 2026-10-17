#!/usr/bin/env python3
"""
Civil Services Daily Compendium & Multi-Source Editorial Pipeline
UPSC & MPSC Daily Review Suite
Sources: The Hindu, Indian Express, Loksatta (लोकसत्ता), and GKToday
"""
import os
import sys
import argparse
import logging
from datetime import datetime, timezone

# Ensure UTF-8 output across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from core.models import DailyDigest, Article, QuizQuestion
from core.dedup import DeduplicationManager
from core.enricher import SyllabusEnricher
from sources.the_hindu import HinduScraper
from sources.indian_express import IndianExpressScraper
from sources.loksatta import LoksattaScraper
from sources.gktoday import GKTodayScraper
from exporters.pdf_engine import PDFExporter
from exporters.markdown_engine import MarkdownExporter
from exporters.json_engine import JSONExporter
from notifiers.telegram import TelegramNotifier
from notifiers.discord import DiscordNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("compendium_pipeline")


def build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="UPSC & MPSC Multi-Source Editorial Digest & Compendium Engine",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--sources",
        type=str,
        default="all",
        help="Comma-separated sources to scrape: 'hindu,express,loksatta,gktoday' or 'all'",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of days back to scrape",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["all", "pdf-only", "markdown-only", "json-only", "no-pdf"],
        default="all",
        help="Export mode",
    )
    parser.add_argument(
        "--hide-answers",
        action="store_true",
        default=False,
        help="Hide answers in quiz bank (Test Mode)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Root output directory",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Ignore deduplication cache and re-process all items",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Run scraper and logging without saving files or sending alerts",
    )
    parser.add_argument(
        "--no-telegram",
        action="store_true",
        default=False,
        help="Skip Telegram delivery",
    )
    parser.add_argument(
        "--no-discord",
        action="store_true",
        default=False,
        help="Skip Discord delivery",
    )
    return parser


class CompendiumPipeline:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.dedup = DeduplicationManager(os.path.join(args.output_dir, "processed.json"))
        self.enricher = SyllabusEnricher()

    def run(self):
        logger.info(f"=== Starting UPSC/MPSC Compendium Pipeline for {self.today_str} ===")
        sources_to_run = self._resolve_sources()

        raw_articles: list[Article] = []
        raw_quizzes: list[QuizQuestion] = []

        # 1. Ingestion Phase
        for scraper in sources_to_run:
            logger.info(f"Running scraper: {scraper.name}...")
            try:
                arts = scraper.fetch_articles(days=self.args.days)
                raw_articles.extend(arts)
            except Exception as e:
                logger.error(f"Error executing scraper {scraper.name}: {e}")

            try:
                qs = scraper.fetch_quizzes(days=self.args.days)
                raw_quizzes.extend(qs)
            except Exception as e:
                logger.error(f"Error fetching quizzes from {scraper.name}: {e}")

        logger.info(f"Ingested total {len(raw_articles)} raw articles and {len(raw_quizzes)} MCQs.")

        # 2. Deduplication Filter
        filtered_articles = []
        for a in raw_articles:
            if not self.args.force and self.dedup.is_processed(a.url):
                continue
            filtered_articles.append(a)

        filtered_quizzes = []
        for q in raw_quizzes:
            key = f"{q.source_url}#q{q.question_num}" if q.source_url else f"q_{q.question_text[:30]}"
            if not self.args.force and self.dedup.is_processed(key):
                continue
            filtered_quizzes.append(q)

        logger.info(f"After deduplication: {len(filtered_articles)} new articles, {len(filtered_quizzes)} new MCQs.")

        if not filtered_articles and not filtered_quizzes:
            logger.info("No new content found. Pipeline complete.")
            return

        # 3. Exam Intelligence Enrichment
        logger.info("Enriching articles with syllabus classification and study pointers...")
        enriched_articles = []
        for i, a in enumerate(filtered_articles):
            logger.info(f"[{i+1}/{len(filtered_articles)}] Enriching: {a.title[:55]} ({a.source})")
            enriched = self.enricher.enrich(a)
            enriched_articles.append(enriched)

        digest = DailyDigest(
            date=self.today_str,
            articles=enriched_articles,
            quizzes=filtered_quizzes,
            metadata={"generated_at": datetime.now(timezone.utc).isoformat()}
        )

        if self.args.dry_run:
            logger.info("Dry-run requested. Skipping file export and notifications.")
            return

        # 4. Multi-Format Exporters
        pdf_path = None
        pdf_dir = os.path.join(self.args.output_dir, "pdf")
        md_dir = os.path.join(self.args.output_dir, "notes")
        json_dir = os.path.join(self.args.output_dir, "data")

        # JSON Export
        if self.args.mode in ["all", "json-only", "no-pdf"]:
            json_exp = JSONExporter(json_dir)
            json_path = json_exp.export(digest)
            logger.info(f"JSON saved to: {json_path}")

        # Markdown Export (Obsidian-ready)
        if self.args.mode in ["all", "markdown-only", "no-pdf"]:
            md_exp = MarkdownExporter(md_dir)
            md_files = md_exp.export(digest)
            logger.info(f"Generated {len(md_files)} Obsidian Markdown notes.")

        # Magazine PDF Export
        if self.args.mode in ["all", "pdf-only"]:
            pdf_exp = PDFExporter(pdf_dir)
            pdf_path = pdf_exp.export(digest, hide_answers=self.args.hide_answers)
            logger.info(f"Compendium PDF built at: {pdf_path}")

        # 5. Multi-Channel Notifications
        if not self.args.no_telegram:
            tg = TelegramNotifier()
            if tg.is_configured:
                tg.send_digest_summary(digest)
                if pdf_path:
                    tg.send_pdf(pdf_path, caption=f"📚 Civil Services Daily Compendium ({digest.date})")

        if not self.args.no_discord:
            dc = DiscordNotifier()
            if dc.is_configured:
                dc.send_digest(digest, pdf_path=pdf_path)

        # 6. Update Deduplication History
        for a in filtered_articles:
            self.dedup.mark_processed(a.url)
        for q in filtered_quizzes:
            key = f"{q.source_url}#q{q.question_num}" if q.source_url else f"q_{q.question_text[:30]}"
            self.dedup.mark_processed(key)
        self.dedup.save()

        logger.info("=== Pipeline Execution Complete Successfully! ===")

    def _resolve_sources(self) -> list:
        src_map = {
            "hindu": HinduScraper,
            "express": IndianExpressScraper,
            "loksatta": LoksattaScraper,
            "gktoday": GKTodayScraper,
        }

        requested = [s.strip().lower() for s in self.args.sources.split(",")]
        if "all" in requested:
            return [cls() for cls in src_map.values()]

        instances = []
        for key in requested:
            if key in src_map:
                instances.append(src_map[key]())
            else:
                logger.warning(f"Unknown source requested: '{key}'. Available: {list(src_map.keys())}")
        return instances


if __name__ == "__main__":
    parser = build_cli()
    args = parser.parse_args()
    pipeline = CompendiumPipeline(args)
    pipeline.run()

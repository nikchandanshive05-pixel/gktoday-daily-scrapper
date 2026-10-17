"""
Core package for Civil Services Multi-Source Editorial & Current Affairs Engine.
"""
from .models import Article, QuizQuestion, DailyDigest
from .base_scraper import BaseScraper
from .dedup import DeduplicationManager
from .enricher import SyllabusEnricher

__all__ = [
    "Article",
    "QuizQuestion",
    "DailyDigest",
    "BaseScraper",
    "DeduplicationManager",
    "SyllabusEnricher",
]

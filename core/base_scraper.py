"""
Abstract base class for all content scrapers and feed ingesters.
"""
from abc import ABC, abstractmethod
from typing import List, Tuple
from .models import Article, QuizQuestion


class BaseScraper(ABC):
    """Abstract interface that all newspaper and website scrapers implement."""

    def __init__(self, name: str, source_id: str = ""):
        self.name = name
        self.source_id = source_id or name.lower().replace(" ", "_")

    @abstractmethod
    def fetch_articles(self, days: int = 1) -> List[Article]:
        """Fetch and return standard Article objects published within `days`."""
        pass

    def fetch_quizzes(self, days: int = 1) -> List[QuizQuestion]:
        """Fetch quizzes if available from this source. Defaults to empty list."""
        return []

"""
Data models for articles, quizzes, and daily digests.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime


@dataclass
class QuizQuestion:
    """Represents an extracted MCQ quiz question."""
    question_num: int
    question_text: str
    options: Dict[str, str] = field(default_factory=dict)  # {"A": "...", "B": "..."}
    correct_option: Optional[str] = None                   # "A", "B", etc.
    explanation: Optional[str] = None
    source_url: Optional[str] = None
    date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_num": self.question_num,
            "question_text": self.question_text,
            "options": self.options,
            "correct_option": self.correct_option,
            "explanation": self.explanation,
            "source_url": self.source_url,
            "date": self.date,
        }


@dataclass
class Article:
    """Represents an extracted article or editorial."""
    title: str
    url: str
    source: str                    # "The Hindu", "Indian Express", "Loksatta", "GKToday"
    published_date: str            # YYYY-MM-DD
    full_text: str
    language: str = "en"           # "en" or "mr"
    author: Optional[str] = None
    category: str = "General"      # e.g., "Economy", "Polity", "Environment"
    
    # UPSC / MPSC Exam Enrichment
    gs_paper: str = "GS-2"         # "GS-1", "GS-2", "GS-3", "GS-4", or "MPSC-State"
    syllabus_topics: List[str] = field(default_factory=list)
    exam_stage: str = "Both"       # "Prelims", "Mains", "Both"
    summary_bullets: List[str] = field(default_factory=list)
    prelims_pointers: List[str] = field(default_factory=list)
    mains_arguments: Dict[str, List[str]] = field(default_factory=dict)
    relevance_score: int = 7       # 1 to 10 scale

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "language": self.language,
            "published_date": self.published_date,
            "author": self.author,
            "category": self.category,
            "gs_paper": self.gs_paper,
            "syllabus_topics": self.syllabus_topics,
            "exam_stage": self.exam_stage,
            "summary_bullets": self.summary_bullets,
            "prelims_pointers": self.prelims_pointers,
            "mains_arguments": self.mains_arguments,
            "relevance_score": self.relevance_score,
            "full_text": self.full_text,
        }


@dataclass
class DailyDigest:
    """Consolidated compendium containing multi-source articles and quizzes."""
    date: str
    articles: List[Article] = field(default_factory=list)
    quizzes: List[QuizQuestion] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "total_articles": len(self.articles),
            "total_quizzes": len(self.quizzes),
            "metadata": self.metadata,
            "articles": [a.to_dict() for a in self.articles],
            "quizzes": [q.to_dict() for q in self.quizzes],
        }

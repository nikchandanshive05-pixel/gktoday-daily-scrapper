"""
Sources package for editorial and current affairs scrapers.
"""
from .gktoday import GKTodayScraper
from .the_hindu import HinduScraper
from .indian_express import IndianExpressScraper
from .loksatta import LoksattaScraper

__all__ = [
    "GKTodayScraper",
    "HinduScraper",
    "IndianExpressScraper",
    "LoksattaScraper",
]

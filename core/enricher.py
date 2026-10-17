"""
Exam intelligence enricher: UPSC & MPSC syllabus classification,
Prelims facts extraction, and Mains arguments summarizer.
Supports Google Gemini API with seamless rule-based heuristic fallback.
"""
import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from .models import Article

logger = logging.getLogger("enricher")

GS_KEYWORDS = {
    "GS-1": [
        "history", "culture", "heritage", "monument", "art", "geography", "monsoon",
        "earthquake", "cyclone", "urbanisation", "society", "population", "demography",
        "women empowerment", "glacier", "volcano", "tsunami", "mineral resources"
    ],
    "GS-2": [
        "constitution", "polity", "judiciary", "supreme court", "high court", "governance",
        "federalism", "parliament", "lok sabha", "rajya sabha", "election", "fundamental rights",
        "bill", "amendment", "statutory", "tribunal", "bilateral", "foreign policy", "diplomacy",
        "treaty", "united nations", "wto", "who", "welfare schemes", "health policy", "education policy",
        "citizen charter", "collegium", "governor", "cbi", "ed", "eci"
    ],
    "GS-3": [
        "economy", "gdp", "inflation", "rbi", "fiscal", "budget", "tax", "banking", "agriculture",
        "msp", "irrigation", "science", "technology", "space", "isro", "drdo", "defence", "ai",
        "semiconductor", "biotechnology", "environment", "biodiversity", "climate change",
        "cop", "renewable energy", "carbon emission", "pollution", "disaster management",
        "internal security", "cybersecurity", "money laundering", "border management", "naxalism"
    ],
    "GS-4": [
        "ethics", "integrity", "probity", "moral", "corruption", "whistleblower", "transparency",
        "accountability", "conflict of interest", "values", "empathy", "code of conduct"
    ],
    "MPSC-State": [
        "maharashtra", "mumbai", "pune", "vidarbha", "marathwada", "konkan", "sahyadri",
        "mpsc", "zp", "gram panchayat", "bmc", "marathi", "maratha", "dhangar", "sugar industry",
        "cooperative", "godavari", "krishna river", "western ghats"
    ]
}


class SyllabusEnricher:
    """Enriches articles with syllabus mapping and summaries."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.has_ai = False
        self.client = None

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                self.has_ai = True
                logger.info("Gemini AI API initialized for syllabus enrichment.")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini AI client: {e}. Using heuristic engine.")

    def enrich(self, article: Article) -> Article:
        """Enrich a single article with syllabus classification and high-yield study points."""
        if self.has_ai:
            try:
                return self._enrich_with_ai(article)
            except Exception as e:
                logger.warning(f"AI enrichment failed for '{article.title}': {e}. Falling back to heuristics.")

        return self._enrich_with_heuristics(article)

    def _enrich_with_ai(self, article: Article) -> Article:
        """Use Gemini Flash to generate high-yield UPSC/MPSC structured analysis."""
        prompt = f"""
You are an expert UPSC Civil Services and MPSC mentor. Analyze the following article and output a strict JSON response.
Article Title: {article.title}
Source: {article.source} (Language: {article.language})
Full Text: {article.full_text[:4000]}

Return JSON with this EXACT structure:
{{
  "gs_paper": "GS-1" or "GS-2" or "GS-3" or "GS-4" or "MPSC-State",
  "syllabus_topics": ["Topic 1", "Topic 2"],
  "exam_stage": "Prelims" or "Mains" or "Both",
  "relevance_score": integer between 1 and 10,
  "summary_bullets": ["Key bullet 1", "Key bullet 2", "Key bullet 3"],
  "prelims_pointers": ["Specific fact / article / body 1", "Fact 2"],
  "mains_arguments": {{
    "Issues": ["Core problem or background"],
    "Arguments": ["Key supporting points or debates"],
    "Way Forward": ["Solution / policy recommendation"]
  }}
}}
If the article is in Marathi (Loksatta), ensure the summary and analysis points accurately reflect the regional context and can be understood by Marathi/English MPSC aspirants.
Do not include markdown fences in the response, only pure JSON.
"""
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = response.text.strip()
        # Clean potential markdown fences
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n?", "", text)
            text = re.sub(r"\n?```$", "", text)

        data = json.loads(text)
        article.gs_paper = data.get("gs_paper", article.gs_paper)
        article.syllabus_topics = data.get("syllabus_topics", [])
        article.exam_stage = data.get("exam_stage", "Both")
        article.relevance_score = int(data.get("relevance_score", 7))
        article.summary_bullets = data.get("summary_bullets", [])
        article.prelims_pointers = data.get("prelims_pointers", [])
        article.mains_arguments = data.get("mains_arguments", {})
        return article

    def _enrich_with_heuristics(self, article: Article) -> Article:
        """Deterministic heuristic analysis when AI is not configured."""
        text_lower = (article.title + " " + article.full_text).lower()

        # 1. Syllabus Paper Scoring
        scores = {}
        for paper, keywords in GS_KEYWORDS.items():
            count = sum(1 for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", text_lower))
            scores[paper] = count

        # Special priority for Marathi articles from Loksatta -> MPSC-State / GS-2
        if article.language == "mr" or article.source == "Loksatta":
            if scores.get("MPSC-State", 0) > 0 or "महाराष्ट्र" in text_lower or "शासन" in text_lower:
                best_paper = "MPSC-State"
            else:
                best_paper = "GS-2" if scores.get("GS-2", 0) >= scores.get("GS-3", 0) else "GS-3"
        else:
            best_paper = max(scores, key=scores.get) if any(scores.values()) else "GS-2"

        article.gs_paper = best_paper

        # 2. Extract leading clean sentences as summary bullets
        sentences = [s.strip() for s in re.split(r"(?<=[.!?।])\s+", article.full_text) if len(s.strip()) > 30]
        article.summary_bullets = sentences[:3] if sentences else [article.title]

        # 3. Detect Prelims vs Mains focus
        prelims_clues = ["commission", "treaty", "report", "index", "summit", "satellite", "species", "sanctuary", "amendment", "article"]
        found_prelims = [p.capitalize() for p in prelims_clues if p in text_lower]
        article.prelims_pointers = [f"Focus Area: {p}" for p in found_prelims[:3]]

        article.mains_arguments = {
            "Core Theme": [article.title],
            "Key Observation": sentences[1:3] if len(sentences) >= 3 else sentences[:1],
            "Context": [f"Scraped from {article.source} under syllabus category {best_paper}."]
        }
        article.relevance_score = min(10, max(5, 5 + len(found_prelims)))
        return article

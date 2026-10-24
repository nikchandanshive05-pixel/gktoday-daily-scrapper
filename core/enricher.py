"""
Exam intelligence enricher: UPSC & MPSC syllabus classification,
Prelims facts extraction, and Mains arguments summarizer.
Provides robust junk filtering, precise GS-1/GS-2/GS-3/MPSC categorization,
and rich constitutional/judicial analytical dimensions.
"""
import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from .models import Article

logger = logging.getLogger("enricher")

# Titles / Patterns to completely filter out from compendium
JUNK_PATTERNS = [
    r"privacy policy",
    r"terms (?:and|&) conditions",
    r"about us",
    r"disclaimer",
    r"download mobile app",
    r"subscribe to",
    r"gk questions \d+.*for ssc",
    r"course promo",
    r"advertisement",
    r"test series",
    r"click here",
]

# Fine-tuned classification keywords
TAXONOMY_KEYWORDS = {
    "GS-1 (Geography, Heritage & Culture)": [
        "caldera", "magma", "volcano", "earthquake", "cyclone", "monsoon",
        "geography", "mineral", "glacier", "heritage", "monument", "art",
        "culture", "temple", "khajuraho", "dance", "tarpa", "tribe", "adivasi",
        "ancient", "medieval", "freedom struggle", "history", "society", "population"
    ],
    "GS-2 (Polity, Governance, Social Justice & IR)": [
        "constitution", "article 19", "article 21", "article 41", "article 368",
        "fundamental rights", "dpsp", "supreme court", "high court", "judiciary",
        "election", "eci", "parliament", "lok sabha", "rajya sabha", "governance",
        "cbfc", "ministry", "welfare scheme", "rpwd", "social justice", "health policy",
        "bilateral", "foreign policy", "diplomacy", "treaty", "united nations",
        "unsc", "summit", "poland", "tusk", "cdri", "international relations"
    ],
    "GS-3 (Economy, Agriculture, Science, Biotech, DM & Security)": [
        "economy", "gdp", "inflation", "rbi", "repo rate", "banking", "fiscal",
        "tax", "budget", "pli", "trade deficit", "export", "import", "msme",
        "agriculture", "crop", "msp", "fish production", "aquaculture", "ethanol",
        "sugar", "maize", "science", "technology", "ai", "artificial intelligence",
        "isro", "satellite", "navic", "drdo", "semiconductor", "biotechnology",
        "vaccine", "mosqivac", "malaria", "cancer", "blood test", "environment",
        "biodiversity", "climate change", "agrivoltaics", "renewable energy",
        "disaster management", "be ready", "resilience", "defence", "internal security",
        "itbp", "army", "navy", "military", "simbex", "radar", "lllr", "cybersecurity",
        "dpdp", "cert-in", "data breach"
    ],
    "GS-4 (Ethics, Integrity & Aptitude)": [
        "ethics", "integrity", "probity", "moral", "corruption", "whistleblower",
        "transparency", "accountability", "conflict of interest", "values"
    ],
    "MPSC-State (Maharashtra Specific)": [
        "महाराष्ट्र", "शासन", "मुंबई", "पुणे", "विदर्भ", "मराठवाडा", "कोकण",
        "सह्याद्री", "महानगरपालिका", "जिल्हा परिषद", "मराठी", "मराठा", "वारली",
        "कोल्हापूर", "वळवडे", "ऊस", "गोदावरी", "कृष्णा"
    ]
}


def is_junk_article(title: str, text: str) -> bool:
    combined = (title + " " + text[:200]).lower()
    for pat in JUNK_PATTERNS:
        if re.search(pat, combined):
            return True
    return False


def clean_sentence_boundary(text: str, max_chars: int = 500) -> str:
    """Cuts text neatly at the nearest sentence boundary rather than mid-word/mid-sentence."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text

    # Search for sentence ending between max_chars*0.6 and max_chars
    sub = text[:max_chars]
    matches = list(re.finditer(r"([.!?।])(?:\s+|$)", sub))
    if matches:
        last_match = matches[-1]
        return sub[:last_match.end()].strip()
    
    # Fallback to word boundary
    return sub.rsplit(" ", 1)[0] + "..."


class SyllabusEnricher:
    """Enriches articles with clean syllabus mapping and analytical study dimensions."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = None
        self.has_ai = False

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                self.has_ai = True
            except Exception:
                try:
                    import google.generativeai as genai_legacy
                    genai_legacy.configure(api_key=self.api_key)
                    self.client = genai_legacy.GenerativeModel("gemini-1.5-flash")
                    self.has_ai = True
                except Exception:
                    pass

    def enrich(self, article: Article) -> Optional[Article]:
        """Enriches article and returns None if article is identified as junk."""
        if is_junk_article(article.title, article.full_text):
            logger.info(f"Filtered out junk/promotional content: '{article.title}'")
            return None

        # Clean text boundaries
        article.full_text = clean_sentence_boundary(article.full_text, max_chars=3500)

        # Classify GS paper with refined taxonomy
        self._classify_taxonomy(article)

        # Extract analytical dimensions
        self._extract_mains_dimensions(article)

        return article

    def _classify_taxonomy(self, article: Article):
        text_lower = (article.title + " " + article.full_text).lower()

        # Specific targeted re-mappings from editorial audit
        if any(w in text_lower for w in ["fish production", "aquaculture", "blue economy"]):
            article.gs_paper = "GS-3"
            article.category = "अर्थव्यवस्था व कृषी (Economy & Agriculture)"
            article.exam_stage = "Both"
            return
        if any(w in text_lower for w in ["caldera", "magma", "volcan", "kikai"]):
            article.gs_paper = "GS-1"
            article.category = "प्राकृतिक भूगोल (Physical Geography)"
            article.exam_stage = "Prelims"
            return
        if any(w in text_lower for w in ["military ai", "defence ai", "itbp", "army", "navy", "simbex"]):
            article.gs_paper = "GS-3"
            article.category = "संरक्षण व अंतर्गत सुरक्षा (Defence & Security)"
            article.exam_stage = "Both"
            return
        if any(w in text_lower for w in ["be ready", "disaster"]):
            article.gs_paper = "GS-3"
            article.category = "आपत्ती व्यवस्थापन (Disaster Management)"
            article.exam_stage = "Both"
            return
        if any(w in text_lower for w in ["mosqivac", "malaria vaccine", "vaccine", "biotech"]):
            article.gs_paper = "GS-3"
            article.category = "विज्ञान व जैवतंत्रज्ञान (Science & Biotechnology)"
            article.exam_stage = "Both"
            return
        if any(w in text_lower for w in ["olympic", "cricket", "pankaj advani", "billiards", "sports", "badminton", "medal"]):
            article.gs_paper = "Prelims"
            article.category = "क्रीडा व पुरस्कार (Sports & Awards)"
            article.exam_stage = "Prelims"
            return
        if any(w in text_lower for w in ["obituary", "ryu murakami", "passed away"]):
            article.gs_paper = "Prelims"
            article.category = "व्यक्ती विशेष (Persons in News)"
            article.exam_stage = "Prelims"
            return

        # General scoring
        scores = {}
        for category, keywords in TAXONOMY_KEYWORDS.items():
            count = sum(1 for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", text_lower))
            scores[category] = count

        if article.language == "mr" or article.source == "Loksatta":
            if scores.get("MPSC-State (Maharashtra Specific)", 0) > 0 or "महाराष्ट्र" in text_lower:
                article.gs_paper = "MPSC-State"
                article.category = "महाराष्ट्र राज्य घडामोडी (MPSC State)"
                return

        best = max(scores, key=scores.get) if any(scores.values()) else "GS-2 (Polity, Governance, Social Justice & IR)"
        if "GS-1" in best:
            article.gs_paper = "GS-1"
            article.category = "इतिहास, भूगोल व संस्कृती (Heritage & Geography)"
        elif "GS-2" in best:
            article.gs_paper = "GS-2"
            article.category = "शासन, राज्यव्यवस्था व आंतरराष्ट्रीय संबंध (Polity & IR)"
        elif "GS-3" in best:
            article.gs_paper = "GS-3"
            article.category = "अर्थव्यवस्था, विज्ञान, पर्यावरण व सुरक्षा (Economy & Tech)"
        else:
            article.gs_paper = "GS-2"
            article.category = "सामान्य घडामोडी"

    def _extract_mains_dimensions(self, article: Article):
        """Extracts high-yield constitutional, statutory, and policy dimensions."""
        text_lower = (article.title + " " + article.full_text).lower()

        # Build clean summary bullets
        sentences = [s.strip() for s in re.split(r"(?<=[.!?।])\s+", article.full_text) if len(s.strip()) > 35]
        article.summary_bullets = sentences[:3] if sentences else [article.title]

        # Contextual analytical dimensions
        dims = {}
        if any(w in text_lower for w in ["advisory", "tv channel", "broadcasting", "speech", "media"]):
            dims["घटनात्मक तरतूद (Constitutional Lens)"] = [
                "कलम १९(१)(क) (भाषण व अभिव्यक्ती स्वातंत्र्य) विरुद्ध कलम १९(२) (सार्वजनिक सुव्यवस्था व देशाचे सार्वभौमत्व यावरील वाजवी बंधने)."
            ]
            dims["संस्थात्मक यंत्रणा (Regulatory Framework)"] = [
                "माहिती व प्रसारण मंत्रालयाची मार्गदर्शक तत्त्वे आणि न्यूज ब्रॉडकास्टिंग अँड डिजिटल स्टँडर्ड्स ॲथॉरिटीचे (NBDSA) स्वनियमन."
            ]
        elif any(w in text_lower for w in ["data breach", "privacy", "bank", "sbi", "hdfc", "cyber"]):
            dims["न्यायालयीन दाखला (Judicial Precedent)"] = [
                "न्या. के. एस. पुट्टास्वामी (निवृत्त) वि. भारतीय संघराज्य (२०१७) — गोपनीयतेचा अधिकार हा कलम २१ चा अविभाज्य भाग आहे."
            ]
            dims["वैधानिक बंधने (Statutory Compliance)"] = [
                "डिजिटल व्यक्तिगत डेटा संरक्षण (DPDP) कायदा आणि CERT-In कडे ६ तासांच्या आत सायबर हल्ल्याची अनिवार्य नोंद करणे."
            ]
        elif any(w in text_lower for w in ["ethanol", "sugar", "maize", "सध्या", "मका", "ऊस"]):
            dims["धोरणात्मक द्वंद्व (Policy Dilemma)"] = [
                "'अन्न सुरक्षा विरुद्ध इंधन सुरक्षा' (Food Security vs. Fuel Security) — साखर कारखान्यांची आर्थिक व्यवहार्यता व देशांतर्गत बाजारातील दर स्थिरीकरण."
            ]
            dims["उपाययोजना (Way Forward)"] = [
                "तुटलेले अन्नधान्य आणि मका यांसारख्या पर्यायी घटकांचा जैवइंधन पुरवठ्यासाठी संतुलित व शाश्वत वापर करणे."
            ]
        elif any(w in text_lower for w in ["china", "trade deficit", "import", "निर्यात", "चीन"]):
            dims["रचनात्मक आव्हाने (Structural Deficit)"] = [
                "सक्रिय औषधी घटक (APIs), टेलिकॉम उपकरणे आणि सोलर पॅनेल्सवरील चीनवरील भारताचे महत्त्वपूर्ण अवलंबित्व."
            ]
            dims["रणनीतिक उपाय (Strategic Measures)"] = [
                "उत्पादन संलग्न प्रोत्साहन (PLI) योजनांची प्रभावी अंमलबजावणी, पुरवठा साखळी लवचिकता (China+1), आणि डम्पिंगविरोधी शुल्क."
            ]
        elif any(w in text_lower for w in ["poland", "cdri", "tusk"]):
            dims["सामरिक महत्त्व (Strategic Significance)"] = [
                "मध्य युरोपातील पोलंडशी संरक्षण व उच्च तंत्रज्ञान सहकार्य वाढल्याने युरोपीय महासंघासोबत (EU) भारताचे संबंध अधिक दृढ होतील."
            ]
            dims["ऐतिहासिक अनुबंध (Historical Ties)"] = [
                "दुसऱ्या महायुद्धात पोलिश निर्वासितांना आश्रय देणारे नवानगरचे जामसाहेब आणि कोल्हापूरचे वळवडे शिबिर."
            ]
        else:
            dims["मुख्य गाभा (Core Issue)"] = [sentences[0] if sentences else article.title]
            if len(sentences) > 1:
                dims["विश्लेषणात्मक संदर्भ (Analytical Context)"] = [sentences[1]]

        article.mains_arguments = dims

        # Prelims high-yield pointers (clean, without 'Key Anchor:' junk)
        prelims = []
        if "cdri" in text_lower:
            prelims.append("CDRI स्थापना: २०१९ (नवी दिल्ली मुख्यालय)")
        if "rpwd" in text_lower or "अपंग" in text_lower or "divyang" in text_lower:
            prelims.append("RPwD कायदा २०१६: किमान ४०% बेंचमार्क अपंगत्व")
            prelims.append("कलम ४१ (DPSP): सार्वजनिक साहाय्य मिळवण्याचा हक्क")
        if "simbex" in text_lower:
            prelims.append("SIMBEX: भारत-सिंगापूर द्विपक्षीय नौदल सराव (१९९४ पासून)")
        if "tarpa" in text_lower or "वारली" in text_lower:
            prelims.append("तारपा नृत्य: पालघर व ठाण्यातील वारली, कोकणा आदिवासी संस्कृती")

        article.prelims_pointers = prelims

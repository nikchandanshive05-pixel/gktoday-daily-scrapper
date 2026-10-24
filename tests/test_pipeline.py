"""
Comprehensive Unit Test Suite for UPSC & MPSC Scraper Pipeline.
Tests data models, deduplication, syllabus enricher, Typst compiler, and scraper parsers.
"""
import os
import shutil
import tempfile
import unittest
from core.models import Article, QuizQuestion, DailyDigest
from core.dedup import DeduplicationManager
from core.enricher import SyllabusEnricher
from exporters.typst_engine import TypstPDFEngine, escape_typst


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_models_serialization(self):
        art = Article(
            title="Test Article",
            url="https://example.com/test",
            source="The Hindu",
            published_date="2026-10-24",
            full_text="Test content about RBI monetary policy and inflation.",
            gs_paper="GS-3",
        )
        d = art.to_dict()
        self.assertEqual(d["title"], "Test Article")
        self.assertEqual(d["gs_paper"], "GS-3")

        quiz = QuizQuestion(
            question_num=1,
            question_text="Sample MCQ question?",
            options={"A": "Opt A", "B": "Opt B"},
            correct_option="A",
            explanation="Notes on option A",
        )
        qd = quiz.to_dict()
        self.assertEqual(qd["correct_option"], "A")
        self.assertEqual(qd["options"]["A"], "Opt A")

    def test_dedup_manager(self):
        cache_file = os.path.join(self.test_dir, "processed.json")
        dedup = DeduplicationManager(cache_file)

        self.assertFalse(dedup.is_processed("https://test.com/item1"))
        dedup.mark_processed("https://test.com/item1")
        dedup.save()

        # Re-instantiate
        dedup2 = DeduplicationManager(cache_file)
        self.assertTrue(dedup2.is_processed("https://test.com/item1"))
        self.assertFalse(dedup2.is_processed("https://test.com/item2"))

    def test_enricher_heuristics(self):
        enricher = SyllabusEnricher(api_key=None)

        art_economy = Article(
            title="RBI keeps repo rate unchanged to control inflation and GDP growth",
            url="https://example.com/rbi",
            source="Indian Express",
            published_date="2026-10-24",
            full_text="The Reserve Bank of India monetary policy committee assessed inflation targets and banking liquidity.",
        )
        enriched = enricher.enrich(art_economy)
        self.assertEqual(enriched.gs_paper, "GS-3")
        self.assertTrue(len(enriched.summary_bullets) > 0)

        art_marathi = Article(
            title="अग्रलेख: महाराष्ट्र शासन आणि साखर उद्योग धोरण",
            url="https://example.com/loksatta-marathi",
            source="Loksatta",
            published_date="2026-10-24",
            full_text="महाराष्ट्र शासन आणि ऊस दर नियंत्रण समितीची बैठक पार पडली. विदर्भ आणि मराठवाडा भागात शेतकरी आंदोलन.",
            language="mr",
        )
        enriched_marathi = enricher.enrich(art_marathi)
        self.assertEqual(enriched_marathi.gs_paper, "MPSC-State")

    def test_typst_escaping(self):
        text = "Budget $100 & Inflation #GS3 *High* @Author"
        esc = escape_typst(text)
        self.assertIn(r"\$", esc)
        self.assertIn(r"\#", esc)
        self.assertIn(r"\*", esc)
        self.assertIn(r"\@", esc)

    def test_typst_compilation(self):
        digest = DailyDigest(
            date="2026-10-24",
            articles=[
                Article(
                    title="Test Editorial On Constitutional Law",
                    url="https://thehindu.com/test",
                    source="The Hindu",
                    published_date="2026-10-24",
                    full_text="Detailed examination of basic structure doctrine and judicial review.",
                    gs_paper="GS-2",
                    summary_bullets=["Constitutional checks and balances.", "Judicial independence."],
                    prelims_pointers=["Article 368", "Kesavananda Bharati Case"],
                )
            ],
            quizzes=[
                QuizQuestion(
                    question_num=1,
                    question_text="Which article deals with constitutional amendments?",
                    options={"A": "Article 368", "B": "Article 356", "C": "Article 370", "D": "Article 352"},
                    correct_option="A",
                    explanation="Article 368 in Part XX of the Constitution deals with the powers of Parliament to amend the Constitution.",
                )
            ],
        )
        engine = TypstPDFEngine(output_dir=self.test_dir, fonts_dir="fonts")
        pdf_path = engine.generate_digest_pdf(digest, "test_output.pdf")
        self.assertTrue(os.path.exists(pdf_path))
        self.assertGreater(os.path.getsize(pdf_path), 5000)


if __name__ == "__main__":
    unittest.main()

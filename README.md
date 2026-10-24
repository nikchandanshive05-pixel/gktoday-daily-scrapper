# 📚 UPSC & MPSC Multi-Source Editorial & Current Affairs Compendium Engine

An automated, production-grade intelligence pipeline that crawls and curates high-yield editorials and current affairs from **The Hindu**, **Indian Express**, **Loksatta (लोकसत्ता)**, **GKToday**, and **PIB (Press Information Bureau)**.

It classifies civil services relevance, maps articles across **GS1–GS4** and **MPSC State** syllabi, compiles publication-grade strict black-and-white PDFs via **Typst**, generates **Obsidian / PKM-ready Markdown cards** with YAML frontmatter, exports structured JSON data, and broadcasts alerts to **Telegram** and **Discord**.

---

## ✨ Key Features

- **🌐 Multi-Source Ingestion**:
  - **The Hindu**: Lead editorials and Op-Ed perspectives.
  - **Indian Express**: *Explained* deep-dives and analytical opinion columns.
  - **Loksatta (लोकसत्ता)**: अग्रलेख, संपादकीय, and विश्लेषक preserved in authentic Marathi for MPSC aspirants.
  - **GKToday**: High-yield factual one-liners and daily practice MCQs.
  - **PIB (Press Information Bureau)**: Official government press releases, cabinet decisions, and policy briefs.
- **🧠 Exam Intelligence & Syllabus Mapping**:
  - **Hybrid AI & Heuristic Engine**: Powered by Google Gemini (`GEMINI_API_KEY`) for GS1–GS4 paper classification, Prelims pointers, and Mains analytical dimensions (Issues, Arguments, Way Forward).
  - Built-in zero-dependency **deterministic heuristic NLP fallback** when running offline.
- **📄 Publication-Grade Typst PDF Engine**:
  - Compiles clean, publication-grade strict black-and-white A4 compendiums adhering to academic standards (Times New Roman / Mukta Devanagari typography, 10pt text, 0.72em leading, clean organic dividers, zero decorative clutter).
  - Study Mode and Test Mode (answers masked for student self-testing).
  - Legacy ReportLab fallback supported.
- **🗂️ Obsidian & PKM Markdown Exporter**:
  - Structured notes per article with full YAML frontmatter (source, GS paper, tags, relevance score).
  - Master `00_DAILY_INDEX.md` organized by GS syllabus papers with wikilinks.
- **🚀 Multi-Channel Delivery**:
  - **Telegram Bot**: Formatted HTML editorial cards and direct PDF document attachments.
  - **Discord Webhook**: Rich embed summaries and PDF attachments.
- **⚡ Smart Deduplication & Cache**:
  - Tracks processed URLs in `output/processed.json` to prevent re-crawling duplicate articles.
- **☁️ GitHub Actions Scheduled Automation**:
  - Runs daily cron at `06:00 AM IST` (`00:30 UTC`) with 14-day artifact retention.

---

## 🏗️ Architecture Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Multi-Source Ingestion                          │
│   • The Hindu (Editorial & Op-Ed)    • Indian Express (Explained)      │
│   • Loksatta (संपादकीय व विश्लेषक)   • GKToday (One-Liners & Quizzes)  │
│   • PIB (Official Press Releases & Policy Briefs)                      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Core Processing Engine                          │
│   • Deduplication Filter (output/processed.json)                       │
│   • Trafilatura Clean Text & Reader Extractor                          │
│   • Pluggable Syllabus Enricher (Gemini Flash / Heuristic Engine)      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
      ┌─────────────────────────────┼─────────────────────────────┐
      ▼                             ▼                             ▼
┌──────────────┐             ┌──────────────┐              ┌──────────────┐
│  Typst PDF   │             │   Obsidian   │              │  Structured  │
│ Compendium   │             │Markdown Notes│              │  JSON Data   │
│ (output/pdf) │             │(output/notes)│              │(output/data) │
└──────┬───────┘             └──────┬───────┘              └──────────────┘
       │                            │
       └──────────────┬─────────────┘
                      ▼
         ┌─────────────────────────┐
         │ Telegram & Discord Bot  │
         └─────────────────────────┘
```

---

## 🚀 Quickstart

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/nikchandanshive05-pixel/gktoday-daily-scrapper.git
cd gktoday-daily-scrapper

pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)

```bash
cp .env.example .env
```

```env
# Optional: Telegram Alerts & PDF upload
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
TELEGRAM_CHAT_ID=-1001234567890

# Optional: Discord Webhook
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Optional: Google Gemini API for AI syllabus tagging & Mains arguments
GEMINI_API_KEY=AIzaSy...
```

### 3. Run Pipeline

```bash
# Default run: all sources, Typst publication PDF
python main.py

# Select specific sources:
python main.py --sources "hindu,express,loksatta,gktoday,pib"

# Run in Test Mode (hide MCQ answers in PDF):
python main.py --hide-answers

# Force re-crawl ignoring cache:
python main.py --force
```

### 4. Run Unit Tests

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

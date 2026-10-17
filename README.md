# 📚 UPSC & MPSC Multi-Source Editorial & Current Affairs Engine

An automated, production-grade intelligence pipeline that crawls and curates high-yield editorials and current affairs from **The Hindu**, **Indian Express**, **Loksatta (लोकसत्ता)**, and **GKToday**. 

It evaluates civil services relevance, maps articles across **GS1–GS4** and **MPSC State** syllabi, generates magazine-grade bilingual PDFs (with Devanagari typography), produces **Obsidian / PKM-ready Markdown cards** with YAML frontmatter, exports structured JSON, and broadcasts to **Telegram** and **Discord**.

---

## ✨ Key Features

- **🌐 Multi-Source Editorial Ingestion**:
  - **The Hindu**: Lead editorials and Op-Ed perspectives.
  - **Indian Express**: *Explained* deep-dives and *Ideas/Opinion* pieces.
  - **Loksatta (लोकसत्ता)**: अग्रलेख, संपादकीय, अन्वयार्थ, and विश्लेषक preserved in authentic Marathi for MPSC aspirants.
  - **GKToday**: High-yield factual one-liners and daily practice MCQs.
- **🧠 Exam Intelligence & Syllabus Mapping**:
  - Pluggable **Google Gemini 2.5 Flash** integration (`GEMINI_API_KEY`) for automated GS Paper tagging (GS1–GS4, MPSC-State), Prelims high-yield fact extraction, and Mains arguments (Issues, Debates, Way Forward).
  - Built-in zero-dependency **deterministic heuristic NLP fallback** when running completely offline.
- **📄 Magazine-Grade Bilingual PDF Engine**:
  - ReportLab-powered A4 compendium with cover page, category grouping, and running `Page X of Y` footers.
  - Native **Devanagari Unicode font registration** (`Noto Sans Devanagari` / `Nirmala UI`) ensuring crisp rendering of Marathi text without missing glyphs.
  - Study Mode (with answers & notes) and Test Mode (answers hidden for student self-testing).
- **🗂️ Obsidian & PKM Markdown Exporter**:
  - Exports structured notes per article with full YAML frontmatter (source, GS paper, tags, relevance score).
  - Auto-generates a master `00_DAILY_INDEX.md` with wikilinks (`[[slug|title]]`) organized by syllabus papers.
- **🚀 Multi-Channel Delivery**:
  - **Telegram Bot**: Formatted HTML editorial cards and direct PDF document attachments.
  - **Discord Webhook**: Rich embed summaries and PDF uploads.
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
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Core Processing Engine                          │
│   • Deduplication Filter (output/processed.json)                       │
│   • Trafilatura Clean Text & Reader Extractor                          │
│   • Pluggable Syllabus Enricher (Gemini 2.5 Flash / Heuristic Engine)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
      ┌─────────────────────────────┼─────────────────────────────┐
      ▼                             ▼                             ▼
┌──────────────┐             ┌──────────────┐              ┌──────────────┐
│  ReportLab   │             │   Obsidian   │              │  Structured  │
│ Magazine PDF │             │Markdown Notes│              │  JSON Data   │
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

### 2. Configure Environment (.env)

Copy `.env.example` to `.env`:

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

---

## 💻 Command-Line Usage (CLI)

```bash
# Run full multi-source compendium (The Hindu, Indian Express, Loksatta, GKToday)
python main.py

# Scrape specific sources only (e.g. The Hindu & Indian Express)
python main.py --sources hindu,express

# Scrape Marathi content from Loksatta only
python main.py --sources loksatta

# Scrape last 2 days and generate Obsidian Markdown notes only (no PDF)
python main.py --days 2 --mode markdown-only

# Generate Quiz in Test Mode (hidden answers for student self-testing)
python main.py --sources gktoday --hide-answers

# Dry-run mode (scrape and log without saving files or sending alerts)
python main.py --dry-run

# Force re-scraping (ignore deduplication cache)
python main.py --force
```

### CLI Arguments Reference

| Argument | Description | Default |
| :--- | :--- | :--- |
| `--sources` | Comma-separated sources: `hindu,express,loksatta,gktoday` or `all` | `all` |
| `--days <N>` | Number of days back to scrape | `1` |
| `--mode` | Export mode: `all`, `pdf-only`, `markdown-only`, `json-only`, `no-pdf` | `all` |
| `--hide-answers` | Hide answers in quiz bank (Student Test Mode) | `false` |
| `--output-dir` | Target folder for outputs (`pdf/`, `notes/`, `data/`) | `output` |
| `--force` | Ignore deduplication cache | `false` |
| `--dry-run` | Run without saving files or triggering notifications | `false` |
| `--no-telegram` | Skip Telegram broadcast | `false` |
| `--no-discord` | Skip Discord broadcast | `false` |

---

## 📂 Output Structure

```
output/
├── pdf/
│   └── UPSC_MPSC_Daily_Digest_YYYY-MM-DD.pdf   # Magazine-grade bilingual compendium
├── notes/
│   └── YYYY-MM-DD/
│       ├── 00_DAILY_INDEX.md                  # Master index with syllabus wikilinks
│       ├── article-slug-one.md                # Individual YAML frontmatter notes
│       └── loksatta-marathi-article.md
├── data/
│   └── compendium_YYYY-MM-DD.json             # Full structured JSON export
└── processed.json                             # Incremental deduplication cache
```

---

## ☁️ GitHub Actions Scheduled Automation

A pre-configured GitHub Actions workflow is located at [`.github/workflows/daily_digest.yml`](.github/workflows/daily_digest.yml).

To automate daily delivery:
1. Go to your repository settings -> **Secrets and variables** -> **Actions**.
2. Add your secrets:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `DISCORD_WEBHOOK_URL`
   - `GEMINI_API_KEY` (optional)
3. The workflow will automatically execute daily at **06:00 AM IST** and publish the artifacts to your channels.
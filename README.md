# 📚 GKToday Daily Scraper & Digest Suite

An automated, production-grade Python scraper and publication pipeline for **GKToday Current Affairs** and **Daily Quizzes**. It extracts high-yield news, evaluates UPSC relevance, generates magazine-quality PDF digests, exports structured JSON data, and broadcasts to Telegram and Discord.

---

## ✨ Features

- **📰 Intelligent Article Extraction**: Scrapes daily current affairs, cleans clutter/adverts, and categorizes articles into domains (*Economy*, *Science & Technology*, *Environment*, *Defence*, *National*, *International*, etc.).
- **🎯 UPSC High-Yield Scoring & Key Points**: Automatically scores relevance for competitive exams (UPSC Prelims/Mains, SSC, State PSCs) and isolates key takeaways.
- **📝 DOM-Based Quiz & MCQ Parser**: Extracts daily question sets, options `[A]-[D]`, answer keys, and detailed explanatory notes.
- **📄 Magazine-Grade PDF Engine**:
  - **Combined Deep Digest**: Cover page, dynamic table of contents, article cards with category tags, and daily quizzes.
  - **Quiz Bank (Study Mode)**: All MCQs with correct answers and explanations.
  - **Quiz Bank (Test Mode)**: Hidden answers for student self-assessment and mock tests.
  - **NumberedCanvas**: Generates `Page X of Y` footers and embedded PDF outline bookmarks.
- **🚀 Multi-Channel Delivery**:
  - **Telegram Bot**: Formatted HTML message notifications and direct PDF document uploads.
  - **Discord Webhook**: Rich embed summaries and PDF attachments.
- **📊 Structured JSON Export**: Saves clean datasets to `output/data/gktoday_YYYY-MM-DD.json` for external integrations (Obsidian, Anki, Web apps).
- **⚡ Incremental Deduplication**: Tracks processed URLs in `output/processed.json` to prevent duplicate processing.
- **☁️ GitHub Actions Ready**: Pre-configured daily cron workflow at `06:00 AM IST` (`00:30 UTC`) with 14-day artifact retention.

---

## 🏗️ Architecture Flow

```
┌──────────────────┐
│  GKToday Website │
└────────┬─────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│                   Scraper Engine                       │
│  • GKTodayScraper (Articles & Relevance Scoring)       │
│  • QuizScraper (DOM-based MCQs & Explanations)         │
│  • Unicode Sanitizer & Flexible Date Parser            │
└────────────────────────┬───────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌──────────────────┐            ┌──────────────────┐
│ Structured JSON  │            │ PDF Engine       │
│ (output/data/)   │            │ (ReportLab A4)   │
└──────────────────┘            └────────┬─────────┘
                                         │
                         ┌───────────────┴───────────────┐
                         ▼                               ▼
                ┌──────────────────┐            ┌──────────────────┐
                │  Telegram Bot    │            │  Discord Webhook │
                └──────────────────┘            └──────────────────┘
```

---

## 🚀 Quickstart

### 1. Clone & Install Dependencies

```bash
# Clone the repository
git clone https://github.com/nikchandanshive05-pixel/gktoday-daily-scrapper.git
cd gktoday-daily-scrapper

# Install Python requirements
pip install -r requirements.txt
```

### 2. Environment Configuration (Optional)

Copy `.env.example` to `.env` and fill in your notification credentials:

```bash
cp .env.example .env
```

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
TELEGRAM_CHAT_ID=-1001234567890
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
MAX_DAYS_OLD=2
QUIZ_MODE=both
HIDE_ANSWERS=false
```

---

## 💻 Command-Line Usage (CLI)

Run the scraper with customizable flags:

```bash
# Run with default settings (scrapes last 2 days, generates both PDFs)
python gktoday_scraper.py

# Scrape last 5 days and produce combined digest only
python gktoday_scraper.py --days 5 --mode combined

# Run in Quiz Test Mode (answers hidden for self-assessment)
python gktoday_scraper.py --mode separate --hide-answers

# Export JSON data only without building PDFs
python gktoday_scraper.py --mode json-only

# Force re-scraping (ignore processed.json history)
python gktoday_scraper.py --force

# Dry-run mode (scrape and log without writing files or sending alerts)
python gktoday_scraper.py --dry-run
```

### CLI Options Reference

| Argument | Description | Default |
| :--- | :--- | :--- |
| `--days <N>` | Number of days back to scrape | `2` |
| `--mode` | Generation mode: `combined`, `separate`, `both`, `json-only` | `both` |
| `--hide-answers` | Hide answers in quiz PDF (Test Mode) | `false` |
| `--output-dir` | Target folder for output files | `output` |
| `--no-telegram` | Skip Telegram delivery | `false` |
| `--no-discord` | Skip Discord delivery | `false` |
| `--force` | Ignore deduplication cache | `false` |
| `--dry-run` | Test run without saving files or sending alerts | `false` |

---

## 🤖 Notification Setup Guides

### 📱 Telegram Bot Setup

1. Open Telegram and message [@BotFather](https://t.me/botfather).
2. Send `/newbot`, name your bot, and copy the **API Token**.
3. To send digests to a channel or group:
   - Add your bot as an **Administrator** with permission to post messages.
   - Obtain your chat/channel ID (e.g. using [@userinfobot](https://t.me/userinfobot) or your channel username like `@YourChannelName` or `-100xxxxxxxxxx`).
4. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env` or GitHub Secrets.

### 🎮 Discord Webhook Setup

1. Open your Discord server settings -> **Integrations** -> **Webhooks**.
2. Click **New Webhook**, select the target channel, and click **Copy Webhook URL**.
3. Set `DISCORD_WEBHOOK_URL` in `.env` or GitHub Secrets.

---

## ☁️ GitHub Actions Scheduled Automation

This repository includes a scheduled GitHub Actions workflow in [`.github/workflows/gktoday_scraper.yml`](.github/workflows/gktoday_scraper.yml).

### Setup in GitHub:
1. Go to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions**.
2. Add the following repository secrets:
   - `TELEGRAM_BOT_TOKEN` (optional)
   - `TELEGRAM_CHAT_ID` (optional)
   - `DISCORD_WEBHOOK_URL` (optional)
3. The workflow will automatically run every day at **06:00 AM IST** (**00:30 UTC**).
4. You can also trigger it manually at any time via **Actions** -> **GKToday Daily Scraper & Digest** -> **Run workflow**.

---

## 🧪 Testing Suite

Run the automated test suite locally:

```bash
python -m unittest discover tests
```

Tests cover:
- Flexible date parser & hyphenated range handling.
- Unicode sanitization (Rupee symbol `₹`, quotes, dashes, XML escaping).
- End-to-end PDF generation (Combined, Quiz Study Mode, and Quiz Test Mode).

---

## 📂 Project Structure

```
gktoday-daily-scrapper/
├── .github/
│   └── workflows/
│       └── gktoday_scraper.yml    # Daily GitHub Actions workflow
├── tests/
│   ├── __init__.py
│   ├── test_date_parser.py        # Date format unit tests
│   ├── test_sanitization.py       # Unicode & entity sanitizer tests
│   └── test_pdf.py                # PDF engine integration tests
├── output/
│   ├── pdfs/                      # Generated PDF digests
│   ├── data/                      # Structured JSON datasets
│   └── processed.json             # Deduplication history
├── .env.example                   # Example environment variables
├── gktoday_scraper.py             # Primary entrypoint
├── gktoday_scraper_v10.py         # Scraper engine & pipeline
├── requirements.txt               # Dependencies
└── README.md                      # Documentation
```

---

## ⚖️ License & Disclaimer

Educational and personal study tool for competitive examination aspirants. Content sourced from [GKToday.in](https://www.gktoday.in). All rights belong to their respective content owners.
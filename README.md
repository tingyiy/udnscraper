# UDN Scraper

Scrapes UDN (聯合新聞網) articles from the **全球** and **運動** sections and builds a static, mobile-friendly reading site hosted on GitHub Pages.

**Live site:** https://tingyiy.github.io/udnscraper/

## How it works

```
UDN API → sync.py → SQLite (udn.db) → build.py → static site (site/)
                                                        ↓
                                                  GitHub Pages
```

1. `sync.py` fetches latest article listings from UDN's API, then scrapes full content for new articles into a local SQLite database. Already-scraped articles are skipped (dedup by article ID).
2. `build.py` reads from SQLite and generates static JSON files under `site/data/`.
3. `site/index.html` is a single-page app (vanilla HTML/CSS/JS) that reads those JSON files. No framework, no build step.

## Setup

```bash
# Requirements: Python 3.9+
pip install requests beautifulsoup4

# Clone
git clone https://github.com/tingyiy/udnscraper.git
cd udnscraper
```

## Usage

### Sync + build

```bash
python sync.py        # Fetch listings + scrape new articles → SQLite
python build.py       # Generate static site from DB
```

### Sync only (no article scraping)

```bash
python sync.py --list-only
```

### Scrape a single article

```bash
python udn_scraper.py https://udn.com/news/story/124061/9422974              # markdown
python udn_scraper.py https://udn.com/news/story/124061/9422974 --format json  # JSON
python udn_scraper.py https://udn.com/news/story/124061/9422974 --format text  # plain text
```

### Preview locally

```bash
cd site && python -m http.server 8080
# Open http://localhost:8080
```

## Deploy to GitHub Pages

1. Go to repo **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main`, folder: `/site`
4. Save — site will be live at `https://tingyiy.github.io/udnscraper/`

## Cron job (keep site updated)

Run this on any machine (local crontab, Oracle Cloud, etc.):

```bash
cd /path/to/udnscraper
python sync.py && python build.py
git add site/data/
git commit -m "update articles $(date +%Y-%m-%d)"
git push
```

Example crontab (every 30 minutes):

```
*/30 * * * * cd /path/to/udnscraper && python3 sync.py && python3 build.py && git add site/data/ && git commit -m "update $(date +\%Y-\%m-\%d\ \%H:\%M)" && git push
```

Or use **GitHub Actions** for a fully serverless cron — no machine needed.

## Project structure

```
udnscraper/
├── udn_scraper.py    # Scrape individual UDN articles
├── db.py             # SQLite storage with dedup
├── sync.py           # Fetch listings + scrape new articles
├── build.py          # Generate static site from DB
├── udn.db            # Local SQLite database (gitignored)
├── site/
│   ├── index.html    # Mobile-friendly SPA
│   └── data/
│       ├── listings.json          # Section listings
│       └── articles/{id}.json     # Individual article content
└── research/         # Experiment logs from development
```

## Sections

| Section | UDN cate_id | URL |
|---------|-------------|-----|
| 全球    | 7225        | https://udn.com/news/cate/2/7225 |
| 運動    | 7227        | https://udn.com/news/cate/2/7227 |

To add more sections, edit the `SECTIONS` dict in `sync.py`.

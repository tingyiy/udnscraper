# UDN Scraper

Scrapes UDN (聯合新聞網) articles from the **全球** and **運動** sections and builds a static, mobile-friendly reading site hosted on GitHub Pages.

**Live site:** https://tingyiy.github.io/udnscraper/

## How it works

```
UDN API → sync.py → static JSON files (docs/data/) → GitHub Pages
```

1. `sync.py` fetches latest article listings from UDN's API, scrapes full content for new articles, and writes everything as static JSON files. Already-scraped articles are skipped (dedup by checking if `{id}.json` exists). Orphaned article files no longer in any listing are auto-deleted.
2. `docs/index.html` is a single-page app (vanilla HTML/CSS/JS) that reads those JSON files. No framework, no build step, no database.
3. A GitHub Actions workflow runs `sync.py` every 2 hours and commits new data automatically.

## Setup

```bash
# Requirements: Python 3.9+
pip install requests beautifulsoup4

# Clone
git clone https://github.com/tingyiy/udnscraper.git
cd udnscraper
```

## Usage

### Sync

```bash
python sync.py              # Fetch listings + scrape new articles + cleanup orphans
python sync.py --list-only  # Only update listings, skip scraping
```

### Scrape a single article

```bash
python udn_scraper.py https://udn.com/news/story/124061/9422974              # markdown
python udn_scraper.py https://udn.com/news/story/124061/9422974 --format json  # JSON
python udn_scraper.py https://udn.com/news/story/124061/9422974 --format text  # plain text
```

### Preview locally

```bash
cd docs && python -m http.server 8080
# Open http://localhost:8080
```

## Deploy to GitHub Pages

1. Go to repo **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main`, folder: `/docs`
4. Save — site will be live at `https://tingyiy.github.io/udnscraper/`

## Auto-sync with GitHub Actions

A workflow in `.github/workflows/sync.yml` runs every 2 hours:

1. Checks out the repo
2. Runs `python sync.py` (fetches listings, scrapes new articles, cleans orphans)
3. Commits and pushes any changes to `docs/data/`

You can also trigger it manually: **Actions → Sync UDN Articles → Run workflow**.

The workflow keeps itself alive because each sync commits new article data (GitHub disables scheduled workflows after 60 days of repo inactivity).

## Project structure

```
udnscraper/
├── udn_scraper.py              # Scrape individual UDN articles
├── sync.py                     # Fetch listings, scrape new articles, cleanup orphans
├── .github/workflows/sync.yml  # GitHub Actions: auto-sync every 2 hours
├── docs/
│   ├── index.html              # Mobile-friendly SPA
│   └── data/
│       ├── listings.json       # Section listings (slider, tiles, subsections)
│       ├── meta.json           # Last-updated timestamp
│       └── articles/{id}.json  # Individual article content
```

## Sections

| Section | UDN cate_id | URL |
|---------|-------------|-----|
| 全球    | 7225        | https://udn.com/news/cate/2/7225 |
| 運動    | 7227        | https://udn.com/news/cate/2/7227 |

To add more sections, edit the `SECTIONS` dict in `sync.py`.

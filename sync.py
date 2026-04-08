#!/usr/bin/env python3
"""
Sync UDN article listings and content into static JSON files.

Scrapes the full section page structure: slider, sub-sections, and latest articles.
Scrapes new article content. Deletes orphaned article files.

Usage:
    python sync.py              # Full sync: listings + scrape + cleanup
    python sync.py --list-only  # Only update listings, skip scraping
"""
import requests
from bs4 import BeautifulSoup
import json
import os
import re
import sys
import time
import glob

from udn_scraper import scrape_udn_article

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

SECTIONS = {
    "全球": 7225,
    "運動": 7227,
}

SECTION_URLS = {
    "全球": "https://udn.com/news/cate/2/7225",
    "運動": "https://udn.com/news/cate/2/7227",
}

API_BASE = "https://udn.com/api/more"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.join(BASE_DIR, "docs")
DATA_DIR = os.path.join(SITE_DIR, "data")
ARTICLES_DIR = os.path.join(DATA_DIR, "articles")

SKIP_SECTIONS = {"我的頻道", "熱門新聞", "猜你喜歡"}


def extract_article_id(title_link):
    match = re.search(r"/(\d+)\?", title_link)
    if match:
        return match.group(1)
    match = re.search(r"/(\d+)$", title_link)
    if match:
        return match.group(1)
    return None


def parse_slider(soup):
    """Extract slider/carousel items from inline JS."""
    items = []
    for script in soup.find_all("script"):
        text = script.string or ""
        if "slider" not in text or "titleLink" not in text:
            continue
        matches = re.findall(
            r"url:\s*'([^']*)',\s*title:\s*'([^']*)',\s*titleLink:\s*'([^']*)'",
            text,
        )
        for url, title, link in matches:
            aid = extract_article_id(link)
            if aid:
                items.append({
                    "article_id": aid,
                    "title": title,
                    "thumbnail": url,
                })
        break
    return items



def parse_subsections(soup):
    """Extract sub-sections (專欄, 棒球, MLB, etc.) from server-rendered HTML."""
    subsections = []
    for box in soup.select(".context-box"):
        title_el = box.select_one(".context-box__title")
        if not title_el:
            continue
        name = title_el.get_text(strip=True)
        if name in SKIP_SECTIONS:
            continue

        articles = []
        for item in box.select(".story-list__news"):
            a = item.find("a", href=True)
            heading = item.find("h2") or item.find("h3")
            time_el = item.find("time")
            img = item.find("img")

            if not a or not heading:
                continue

            aid = extract_article_id(a["href"])
            if not aid:
                continue

            articles.append({
                "article_id": aid,
                "title": heading.get_text(strip=True),
                "date": time_el.get_text(strip=True) if time_el else "",
                "thumbnail": img.get("src", "") if img else "",
            })

        if articles:
            subsections.append({"name": name, "articles": articles})

    return subsections


def fetch_latest_api(cate_id):
    """Fetch latest articles via API (paginated)."""
    items = []
    page = 0
    while True:
        resp = requests.get(API_BASE, params={
            "page": page, "channelId": 2,
            "cate_id": cate_id, "type": "cate_latest_news", "totalRecNo": 20,
        }, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for entry in data.get("lists", []):
            aid = extract_article_id(entry.get("titleLink", ""))
            if aid:
                items.append({
                    "article_id": aid,
                    "title": entry.get("title", ""),
                    "summary": entry.get("paragraph", ""),
                    "thumbnail": entry.get("url", ""),
                    "date": entry.get("time", {}).get("date", ""),
                })

        if data.get("end", True):
            break
        page += 1
        time.sleep(0.5)

    return items


def sync_section(section_name, cate_id):
    """Sync one section: fetch page, extract slider + subsections + API latest."""
    print(f"Syncing: {section_name}")

    # Fetch section page
    resp = requests.get(SECTION_URLS[section_name], headers=HEADERS, timeout=30)
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    # 1. Slider
    slider = parse_slider(soup)
    print(f"  Slider: {len(slider)} items")

    # 2. Sub-sections from HTML
    subsections = parse_subsections(soup)
    for sub in subsections:
        print(f"  {sub['name']}: {len(sub['articles'])} items")

    # 3. Replace "最新文章" subsection with full API data
    latest_api = fetch_latest_api(cate_id)
    print(f"  最新文章 (API): {len(latest_api)} items")

    # Replace server-rendered 最新文章 (only 6 items) with full API version, keeping original position
    for i, s in enumerate(subsections):
        if s["name"] == "最新文章":
            subsections[i] = {"name": "最新文章", "articles": latest_api}
            break
    else:
        subsections.append({"name": "最新文章", "articles": latest_api})

    return {"slider": slider, "subsections": subsections}


def sync_all():
    """Sync all sections. Returns full data structure and set of all article IDs."""
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    categories = {}

    for section_name, cate_id in SECTIONS.items():
        categories[section_name] = sync_section(section_name, cate_id)
        time.sleep(0.5)

    with open(os.path.join(DATA_DIR, "listings.json"), "w", encoding="utf-8") as f:
        json.dump(categories, f, ensure_ascii=False)

    # Write last-updated timestamp in UTC ISO format
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    with open(os.path.join(DATA_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"updated_at": now}, f, ensure_ascii=False)

    return categories


def collect_all_ids(categories):
    """Gather all article IDs referenced in any listing."""
    ids = set()
    for section in categories.values():
        for item in section.get("slider", []):
            ids.add(item["article_id"])
        for sub in section.get("subsections", []):
            for item in sub["articles"]:
                ids.add(item["article_id"])
    return ids


def scrape_new_articles(all_ids):
    """Scrape articles that don't have a JSON file yet."""
    new_ids = [aid for aid in all_ids if not os.path.exists(os.path.join(ARTICLES_DIR, f"{aid}.json"))]
    print(f"\nNew articles to scrape: {len(new_ids)}")

    for i, aid in enumerate(new_ids):
        url = f"https://udn.com/news/story/0/{aid}"
        print(f"  [{i+1}/{len(new_ids)}] {aid}", end=" ", flush=True)
        try:
            article = scrape_udn_article(url)
            if not article["title"] and not article["body"]:
                print("SKIP (empty/paywall)")
                continue
            out = {
                "article_id": aid,
                "title": article["title"],
                "date": article["date"],
                "source": article["source"],
                "author": article["author"],
                "section": article["section"],
                "cover_image": article["cover_image"],
                "body": article["body"],
            }
            with open(os.path.join(ARTICLES_DIR, f"{aid}.json"), "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False)
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
        time.sleep(1)


def cleanup_orphans(all_ids):
    """Delete article JSON files not referenced in any listing."""
    existing = set()
    for path in glob.glob(os.path.join(ARTICLES_DIR, "*.json")):
        aid = os.path.basename(path).replace(".json", "")
        existing.add(aid)

    orphans = existing - all_ids
    if orphans:
        print(f"\nCleaning up {len(orphans)} orphaned articles")
        for aid in orphans:
            os.remove(os.path.join(ARTICLES_DIR, f"{aid}.json"))
            print(f"  Deleted {aid}.json")
    else:
        print("\nNo orphaned articles")


def main():
    list_only = "--list-only" in sys.argv

    categories = sync_all()
    all_ids = collect_all_ids(categories)

    if not list_only:
        scrape_new_articles(all_ids)

    cleanup_orphans(all_ids)

    total_files = len(glob.glob(os.path.join(ARTICLES_DIR, "*.json")))
    print(f"\nDone. Referenced: {len(all_ids)}, Article files: {total_files}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Sync UDN article listings and content into static JSON files.

Fetches latest listings from UDN API, scrapes new articles,
and deletes orphaned article files no longer in any listing.

Usage:
    python sync.py              # Full sync: listings + scrape + cleanup
    python sync.py --list-only  # Only update listings, skip scraping
"""
import requests
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

API_BASE = "https://udn.com/api/more"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.join(BASE_DIR, "docs")
DATA_DIR = os.path.join(SITE_DIR, "data")
ARTICLES_DIR = os.path.join(DATA_DIR, "articles")


def extract_article_id(title_link):
    match = re.search(r"/(\d+)\?", title_link)
    if match:
        return match.group(1)
    match = re.search(r"/(\d+)$", title_link)
    if match:
        return match.group(1)
    return None


def fetch_listing_page(cate_id, page=0):
    resp = requests.get(API_BASE, params={
        "page": page,
        "channelId": 2,
        "cate_id": cate_id,
        "type": "cate_latest_news",
        "totalRecNo": 20,
    }, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def sync_listings():
    """Fetch all listing pages for each section. Returns {category: [items]}."""
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    categories = {}

    for section_name, cate_id in SECTIONS.items():
        print(f"Fetching listings: {section_name}")
        items = []
        page = 0

        while True:
            data = fetch_listing_page(cate_id, page)
            for entry in data.get("lists", []):
                article_id = extract_article_id(entry.get("titleLink", ""))
                if not article_id:
                    continue
                items.append({
                    "article_id": article_id,
                    "title": entry.get("title", ""),
                    "summary": entry.get("paragraph", ""),
                    "thumbnail": entry.get("url", ""),
                    "date": entry.get("time", {}).get("date", ""),
                })

            if data.get("end", True):
                break
            page += 1
            time.sleep(0.5)

        categories[section_name] = items
        print(f"  {len(items)} articles")

    with open(os.path.join(DATA_DIR, "listings.json"), "w", encoding="utf-8") as f:
        json.dump(categories, f, ensure_ascii=False)

    return categories


def scrape_new_articles(categories):
    """Scrape articles that don't have a JSON file yet."""
    all_ids = set()
    for items in categories.values():
        for item in items:
            all_ids.add(item["article_id"])

    new_ids = [aid for aid in all_ids if not os.path.exists(os.path.join(ARTICLES_DIR, f"{aid}.json"))]
    print(f"\nNew articles to scrape: {len(new_ids)}")

    for i, aid in enumerate(new_ids):
        url = f"https://udn.com/news/story/0/{aid}"
        print(f"  [{i+1}/{len(new_ids)}] {aid}", end=" ", flush=True)

        try:
            article = scrape_udn_article(url)
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


def cleanup_orphans(categories):
    """Delete article JSON files not referenced in any listing."""
    referenced = set()
    for items in categories.values():
        for item in items:
            referenced.add(item["article_id"])

    existing = set()
    for path in glob.glob(os.path.join(ARTICLES_DIR, "*.json")):
        aid = os.path.basename(path).replace(".json", "")
        existing.add(aid)

    orphans = existing - referenced
    if orphans:
        print(f"\nCleaning up {len(orphans)} orphaned articles")
        for aid in orphans:
            path = os.path.join(ARTICLES_DIR, f"{aid}.json")
            os.remove(path)
            print(f"  Deleted {aid}.json")
    else:
        print("\nNo orphaned articles")


def main():
    list_only = "--list-only" in sys.argv

    categories = sync_listings()

    if not list_only:
        scrape_new_articles(categories)

    cleanup_orphans(categories)

    total_articles = len(glob.glob(os.path.join(ARTICLES_DIR, "*.json")))
    total_listed = sum(len(v) for v in categories.values())
    print(f"\nDone. Listed: {total_listed}, Article files: {total_articles}")


if __name__ == "__main__":
    main()

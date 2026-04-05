#!/usr/bin/env python3
"""
Sync UDN article listings and content into local SQLite.

Usage:
    python sync.py              # Sync listings + scrape new articles
    python sync.py --list-only  # Only sync listings, don't scrape articles
"""
import requests
import re
import sys
import time

from db import init_db, article_exists, upsert_article, upsert_listing, clear_listings
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


def extract_article_id(title_link):
    """Extract numeric article ID from a UDN path like /news/story/124061/9422974?..."""
    match = re.search(r"/(\d+)\?", title_link)
    if match:
        return match.group(1)
    match = re.search(r"/(\d+)$", title_link)
    if match:
        return match.group(1)
    return None


def fetch_listing_page(cate_id, page=0):
    """Fetch one page of listings from the UDN API."""
    resp = requests.get(API_BASE, params={
        "page": page,
        "channelId": 2,
        "cate_id": cate_id,
        "type": "cate_latest_news",
        "totalRecNo": 20,
    }, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def sync_listings(conn):
    """Fetch all listing pages for each section and store in DB."""
    for section_name, cate_id in SECTIONS.items():
        print(f"Syncing listings: {section_name} (cate_id={cate_id})")
        clear_listings(conn, section_name)

        order = 0
        page = 0
        while True:
            data = fetch_listing_page(cate_id, page)
            items = data.get("lists", [])
            if not items:
                break

            for item in items:
                article_id = extract_article_id(item.get("titleLink", ""))
                if not article_id:
                    continue

                upsert_listing(
                    conn,
                    article_id=article_id,
                    category=section_name,
                    title=item.get("title", ""),
                    summary=item.get("paragraph", ""),
                    thumbnail=item.get("url", ""),
                    date=item.get("time", {}).get("date", ""),
                    list_order=order,
                )
                order += 1

            conn.commit()

            if data.get("end", True):
                break
            page += 1
            time.sleep(0.5)

        print(f"  {order} articles listed")


def scrape_new_articles(conn):
    """Scrape full content for articles not yet in the DB."""
    rows = conn.execute("""
        SELECT DISTINCT l.article_id, l.title
        FROM listings l
        LEFT JOIN articles a ON l.article_id = a.article_id
        WHERE a.article_id IS NULL
    """).fetchall()

    total = len(rows)
    print(f"\nNew articles to scrape: {total}")

    for i, row in enumerate(rows):
        aid = row["article_id"]
        title = row["title"]
        print(f"  [{i+1}/{total}] {aid}: {title[:40]}...", end=" ", flush=True)

        # Find the full URL from the listing
        listing = conn.execute(
            "SELECT * FROM listings WHERE article_id = ? LIMIT 1", (aid,)
        ).fetchone()

        url = f"https://udn.com/news/story/0/{aid}"

        try:
            article = scrape_udn_article(url)
            article["thumbnail"] = listing["thumbnail"] if listing else ""
            article["summary"] = listing["summary"] if listing else ""
            upsert_article(conn, aid, article)
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")

        time.sleep(1)  # be polite


def main():
    list_only = "--list-only" in sys.argv

    conn = init_db()
    sync_listings(conn)

    if not list_only:
        scrape_new_articles(conn)

    # Summary
    total_listings = conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
    total_articles = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    print(f"\nDone. Listings: {total_listings}, Articles with content: {total_articles}")
    conn.close()


if __name__ == "__main__":
    main()

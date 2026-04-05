#!/usr/bin/env python3
"""
Build static site from SQLite database.
Generates site/data/listings.json and site/data/articles/{id}.json
"""
import json
import os
import shutil

from db import init_db, get_listings, get_article

SITE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")
DATA_DIR = os.path.join(SITE_DIR, "data")
ARTICLES_DIR = os.path.join(DATA_DIR, "articles")


def build():
    os.makedirs(ARTICLES_DIR, exist_ok=True)

    conn = init_db()

    # Build listings.json
    categories = {}
    for cat in ["全球", "運動"]:
        listings = get_listings(conn, cat)
        categories[cat] = listings
        print(f"{cat}: {len(listings)} articles")

    with open(os.path.join(DATA_DIR, "listings.json"), "w", encoding="utf-8") as f:
        json.dump(categories, f, ensure_ascii=False)

    # Build individual article JSON files
    article_ids = set()
    for cat_listings in categories.values():
        for item in cat_listings:
            article_ids.add(item["article_id"])

    built = 0
    for aid in article_ids:
        article = get_article(conn, aid)
        if article:
            # Remove sqlite Row artifacts
            out = {
                "article_id": article["article_id"],
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
            built += 1

    print(f"Built {built} article files")
    conn.close()


if __name__ == "__main__":
    build()

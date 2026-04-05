"""
SQLite storage for UDN articles with dedup.
"""
import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "udn.db")


def get_conn(db_path=None):
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path=None):
    conn = get_conn(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            article_id  TEXT PRIMARY KEY,
            url         TEXT NOT NULL,
            title       TEXT NOT NULL,
            date        TEXT,
            source      TEXT,
            author      TEXT,
            section     TEXT,
            cover_image TEXT,  -- JSON {src, alt, caption}
            body        TEXT,  -- JSON list of {type, content/src/alt/caption}
            thumbnail   TEXT,
            summary     TEXT,
            scraped_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS listings (
            article_id  TEXT NOT NULL,
            category    TEXT NOT NULL,  -- '全球' or '運動'
            title       TEXT NOT NULL,
            summary     TEXT,
            thumbnail   TEXT,
            date        TEXT,
            list_order  INTEGER,
            fetched_at  TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (article_id, category)
        );

        CREATE INDEX IF NOT EXISTS idx_listings_category
            ON listings(category, list_order);

        CREATE INDEX IF NOT EXISTS idx_articles_date
            ON articles(date DESC);
    """)
    conn.commit()
    return conn


def article_exists(conn, article_id):
    row = conn.execute(
        "SELECT 1 FROM articles WHERE article_id = ?", (article_id,)
    ).fetchone()
    return row is not None


def upsert_article(conn, article_id, article_data):
    cover_json = json.dumps(article_data.get("cover_image"), ensure_ascii=False) if article_data.get("cover_image") else None
    body_json = json.dumps(article_data.get("body", []), ensure_ascii=False)

    conn.execute("""
        INSERT INTO articles (article_id, url, title, date, source, author, section, cover_image, body, thumbnail, summary)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(article_id) DO UPDATE SET
            title=excluded.title, date=excluded.date, source=excluded.source,
            author=excluded.author, section=excluded.section,
            cover_image=excluded.cover_image, body=excluded.body,
            thumbnail=excluded.thumbnail, summary=excluded.summary,
            updated_at=datetime('now')
    """, (
        article_id, article_data.get("url", ""), article_data["title"],
        article_data.get("date", ""), article_data.get("source", ""),
        article_data.get("author", ""), article_data.get("section", ""),
        cover_json, body_json,
        article_data.get("thumbnail", ""), article_data.get("summary", ""),
    ))
    conn.commit()


def upsert_listing(conn, article_id, category, title, summary, thumbnail, date, list_order):
    conn.execute("""
        INSERT INTO listings (article_id, category, title, summary, thumbnail, date, list_order)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(article_id, category) DO UPDATE SET
            title=excluded.title, summary=excluded.summary,
            thumbnail=excluded.thumbnail, date=excluded.date,
            list_order=excluded.list_order, fetched_at=datetime('now')
    """, (article_id, category, title, summary, thumbnail, date, list_order))


def clear_listings(conn, category):
    conn.execute("DELETE FROM listings WHERE category = ?", (category,))


def get_listings(conn, category):
    rows = conn.execute("""
        SELECT l.article_id, l.title, l.summary, l.thumbnail, l.date,
               (a.article_id IS NOT NULL) as has_content
        FROM listings l
        LEFT JOIN articles a ON l.article_id = a.article_id
        WHERE l.category = ?
        ORDER BY l.list_order
    """, (category,)).fetchall()
    return [dict(r) for r in rows]


def get_article(conn, article_id):
    row = conn.execute(
        "SELECT * FROM articles WHERE article_id = ?", (article_id,)
    ).fetchone()
    if row:
        d = dict(row)
        d["cover_image"] = json.loads(d["cover_image"]) if d["cover_image"] else None
        d["body"] = json.loads(d["body"]) if d["body"] else []
        return d
    return None


def get_categories(conn):
    rows = conn.execute(
        "SELECT DISTINCT category FROM listings ORDER BY category"
    ).fetchall()
    return [r["category"] for r in rows]

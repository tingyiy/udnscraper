#!/usr/bin/env python3
"""
UDN.com News Article Scraper

Extracts structured content from UDN news articles:
- Title, date, source, author, section
- Cover image (with caption)
- Body text and inline images

Usage:
    from udn_scraper import scrape_udn_article, to_markdown
    article = scrape_udn_article("https://udn.com/news/story/124061/9422974")
    print(to_markdown(article))

CLI:
    python udn_scraper.py <url> [--format md|json|text]
"""
import requests
from bs4 import BeautifulSoup
import json
import re
import sys


def scrape_udn_article(url):
    """
    Scrape a UDN news article and return structured data.

    Args:
        url: Full URL to a UDN news article

    Returns:
        dict with keys:
          - title: str
          - date: str (e.g. "2026-04-05 07:45")
          - source: str (e.g. "聯合報")
          - author: str (e.g. "盧思綸")
          - section: str (e.g. "即時報導")
          - cover_image: {src, alt, caption} or None
          - body: list of {type: "text", content: str} or {type: "image", src, alt, caption}
          - url: str
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    }

    resp = requests.get(url, headers=headers, timeout=30)
    resp.encoding = "utf-8"
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    result = {"url": url}

    # 1. Title
    h1 = soup.find("h1")
    result["title"] = h1.get_text(strip=True) if h1 else ""

    # 2. Date (in .article-content__time or section.authors > time)
    result["date"] = ""
    time_el = soup.select_one(".article-content__time")
    if time_el:
        result["date"] = time_el.get_text(strip=True)
    else:
        authors_section = soup.select_one("section.authors")
        if authors_section:
            t = authors_section.find("time")
            if t:
                result["date"] = t.get_text(strip=True)

    # 3. Source, author, section (in .article-content__author)
    result["source"] = ""
    result["author"] = ""
    result["section"] = ""

    author_el = soup.select_one(".article-content__author")
    if author_el:
        full_text = author_el.get_text(" ", strip=True)
        # Pattern: "聯合報／ 編譯 盧思綸 ／即時報導"
        parts = re.split(r'[／/]', full_text)
        parts = [p.strip() for p in parts if p.strip()]

        if len(parts) >= 1:
            result["source"] = parts[0]
        if len(parts) >= 2:
            mid = parts[1].strip()
            role_prefixes = ["編譯", "記者", "特派記者", "特約記者"]
            for prefix in role_prefixes:
                if mid.startswith(prefix):
                    result["author"] = mid[len(prefix):].strip()
                    break
            else:
                result["author"] = mid
        if len(parts) >= 3:
            result["section"] = parts[2]

    # 4. Cover image
    result["cover_image"] = None
    cover = soup.select_one(".article-content__cover")
    if cover:
        img = cover.find("img")
        cap = cover.find("figcaption")
        if img:
            result["cover_image"] = {
                "src": img.get("src", ""),
                "alt": img.get("alt", ""),
                "caption": cap.get_text(strip=True) if cap else "",
            }

    # 5. Body content
    result["body"] = []
    editor = soup.select_one(".article-content__editor")
    if editor:
        for child in editor.children:
            if not hasattr(child, "name") or not child.name:
                continue
            if child.name in ("style", "script"):
                continue
            classes = child.get("class", [])
            class_str = " ".join(classes) if classes else ""
            if "inline-ads" in class_str or "udn-ads" in class_str:
                continue

            # Inline images (figures)
            for fig in child.find_all("figure"):
                fig_img = fig.find("img")
                fig_cap = fig.find("figcaption")
                if fig_img:
                    result["body"].append({
                        "type": "image",
                        "src": fig_img.get("src", ""),
                        "alt": fig_img.get("alt", ""),
                        "caption": fig_cap.get_text(strip=True) if fig_cap else "",
                    })

            # Text paragraphs
            if child.name == "p":
                text = child.get_text(strip=True)
                if text:
                    result["body"].append({"type": "text", "content": text})

    return result


def to_markdown(article):
    """Convert structured article data to markdown string."""
    lines = []
    lines.append(f"# {article['title']}")
    lines.append("")

    meta_parts = []
    if article["date"]:
        meta_parts.append(article["date"])
    if article["source"]:
        meta_parts.append(article["source"])
    if article["author"]:
        meta_parts.append(article["author"])
    if article["section"]:
        meta_parts.append(article["section"])
    if meta_parts:
        lines.append(f"*{' | '.join(meta_parts)}*")
        lines.append("")

    if article["cover_image"]:
        ci = article["cover_image"]
        lines.append(f"![{ci['caption'] or ci['alt']}]({ci['src']})")
        if ci["caption"]:
            lines.append(f"*{ci['caption']}*")
        lines.append("")

    for part in article["body"]:
        if part["type"] == "text":
            lines.append(part["content"])
            lines.append("")
        elif part["type"] == "image":
            lines.append(f"![{part.get('caption') or part.get('alt', '')}]({part['src']})")
            if part.get("caption"):
                lines.append(f"*{part['caption']}*")
            lines.append("")

    return "\n".join(lines)


def to_json(article):
    """Convert structured article data to JSON string."""
    return json.dumps(article, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python udn_scraper.py <url> [--format md|json|text]")
        sys.exit(1)

    url = sys.argv[1]
    fmt = "md"
    if "--format" in sys.argv:
        idx = sys.argv.index("--format")
        if idx + 1 < len(sys.argv):
            fmt = sys.argv[idx + 1]

    article = scrape_udn_article(url)

    if fmt == "json":
        print(to_json(article))
    elif fmt == "text":
        print(article["title"])
        meta = f"{article['date']} {article['source']} {article['author']} {article['section']}".strip()
        if meta:
            print(meta)
        if article["cover_image"] and article["cover_image"]["caption"]:
            print(article["cover_image"]["caption"])
        for part in article["body"]:
            if part["type"] == "text":
                print(part["content"])
    else:
        print(to_markdown(article))

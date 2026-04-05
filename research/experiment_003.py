#!/usr/bin/env python3
"""
Experiment 003: Clean reusable scraper as a module
Hypothesis: Package the winning approach (exp 002) into a clean function
that returns structured data. Fix author/date parsing, handle edge cases.
Also test on the same URL to confirm no regression.
"""
import requests
from bs4 import BeautifulSoup
import json
import os
import re

def scrape_udn_article(url):
    """
    Scrape a UDN news article and return structured data.

    Returns dict with:
      - title: str
      - date: str (e.g. "2026-04-05 07:45")
      - source: str (e.g. "聯合報")
      - author: str (e.g. "盧思綸")
      - section: str (e.g. "即時報導")
      - cover_image: {src, alt, caption} or None
      - body: list of {type: "text"|"image", content: str|{src,alt,caption}}
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

    # 2. Date, source, author, section
    result["date"] = ""
    result["source"] = ""
    result["author"] = ""
    result["section"] = ""

    # Date is in .article-content__time or section.authors > time
    time_el = soup.select_one(".article-content__time")
    if time_el:
        result["date"] = time_el.get_text(strip=True)
    else:
        authors_section = soup.select_one("section.authors")
        if authors_section:
            t = authors_section.find("time")
            if t:
                result["date"] = t.get_text(strip=True)

    author_el = soup.select_one(".article-content__author")
    if author_el:

        # Get the full text, parse source/author/section
        full_text = author_el.get_text(" ", strip=True)

        # Pattern: "聯合報／ 編譯 盧思綸 ／即時報導"
        # or: "聯合報／ 記者XXX ／即時報導"
        parts = re.split(r'[／/]', full_text)
        parts = [p.strip() for p in parts if p.strip()]

        if len(parts) >= 1:
            result["source"] = parts[0]  # e.g. "聯合報"
        if len(parts) >= 2:
            # Middle part might be "編譯 盧思綸" or "記者 XXX"
            mid = parts[1].strip()
            # Extract author name (last word after role prefix)
            role_prefixes = ["編譯", "記者", "特派記者", "特約記者"]
            for prefix in role_prefixes:
                if mid.startswith(prefix):
                    result["author"] = mid[len(prefix):].strip()
                    break
            else:
                result["author"] = mid
        if len(parts) >= 3:
            result["section"] = parts[2]  # e.g. "即時報導"

    # 3. Cover image
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

    # 4. Body content
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
    """Convert structured article to markdown."""
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


def to_plain_text(article):
    """Convert structured article to plain text (for judge comparison)."""
    lines = []
    lines.append(article["title"])

    meta = ""
    if article["date"]:
        meta += article["date"] + " "
    if article["source"]:
        meta += article["source"]
    if article["author"]:
        meta += " " + article["author"]
    if article["section"]:
        meta += " " + article["section"]
    if meta:
        lines.append(meta.strip())

    if article["cover_image"] and article["cover_image"]["caption"]:
        lines.append(article["cover_image"]["caption"])

    for part in article["body"]:
        if part["type"] == "text":
            lines.append(part["content"])
        elif part["type"] == "image" and part.get("caption"):
            lines.append(part["caption"])

    return "\n".join(lines)


if __name__ == "__main__":
    url = "https://udn.com/news/story/124061/9422974"
    article = scrape_udn_article(url)

    # Print structured data
    print(f"Title: {article['title'][:60]}")
    print(f"Date: {article['date']}")
    print(f"Source: {article['source']}")
    print(f"Author: {article['author']}")
    print(f"Section: {article['section']}")
    print(f"Cover image: {bool(article['cover_image'])}")
    print(f"Body parts: {len(article['body'])}")

    # Save outputs
    base = os.path.dirname(__file__)

    with open(os.path.join(base, "results", "experiment_003.json"), "w", encoding="utf-8") as f:
        json.dump(article, f, ensure_ascii=False, indent=2)

    with open(os.path.join(base, "results", "experiment_003.md"), "w", encoding="utf-8") as f:
        f.write(to_markdown(article))

    with open(os.path.join(base, "results", "experiment_003.txt"), "w", encoding="utf-8") as f:
        f.write(to_plain_text(article))

    print(f"\nPlain text output:")
    print(to_plain_text(article))

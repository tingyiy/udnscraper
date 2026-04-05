#!/usr/bin/env python3
"""
Experiment 002: Targeted extraction with proper selectors
Hypothesis: Using specific CSS selectors for each content area will give
high recall and eliminate junk. Output markdown with inline images.
"""
import requests
from bs4 import BeautifulSoup
import os
import json

URL = "https://udn.com/news/story/124061/9422974"
OUTPUT = os.path.join(os.path.dirname(__file__), "results", "experiment_002.txt")
OUTPUT_MD = os.path.join(os.path.dirname(__file__), "results", "experiment_002.md")

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

resp = requests.get(URL, headers=headers, timeout=30)
resp.encoding = "utf-8"

soup = BeautifulSoup(resp.text, "html.parser")

# === Extract structured data ===

# 1. Title
title = ""
h1 = soup.find("h1")
if h1:
    title = h1.get_text(strip=True)

# 2. Date & Author
date_author = ""
author_el = soup.select_one(".article-content__author")
if author_el:
    # The author block contains time + source + author name + section
    time_el = author_el.find("time")
    date_str = time_el.get_text(strip=True) if time_el else ""

    # Get all text parts
    author_texts = []
    for span in author_el.find_all("span"):
        t = span.get_text(strip=True)
        if t and t != date_str:
            author_texts.append(t)

    # Fallback: get full text
    if not author_texts:
        full = author_el.get_text(" ", strip=True)
        date_author = full
    else:
        date_author = date_str + " " + " ".join(author_texts)

# 3. Cover image
cover_img_src = ""
cover_img_caption = ""
cover = soup.select_one(".article-content__cover")
if cover:
    img = cover.find("img")
    cap = cover.find("figcaption")
    if img:
        cover_img_src = img.get("src", "")
    if cap:
        cover_img_caption = cap.get_text(strip=True)

# 4. Body paragraphs (from .article-content__editor)
body_parts = []  # list of (type, content) tuples
editor = soup.select_one(".article-content__editor")
if editor:
    for child in editor.children:
        if not hasattr(child, "name") or not child.name:
            continue
        # Skip ads, styles, scripts
        if child.name in ("style", "script"):
            continue
        classes = child.get("class", [])
        class_str = " ".join(classes) if classes else ""
        if "inline-ads" in class_str or "udn-ads" in class_str:
            continue

        # Check for figures (inline images)
        for fig in child.find_all("figure"):
            fig_img = fig.find("img")
            fig_cap = fig.find("figcaption")
            if fig_img:
                body_parts.append(("image", {
                    "src": fig_img.get("src", ""),
                    "alt": fig_img.get("alt", ""),
                    "caption": fig_cap.get_text(strip=True) if fig_cap else "",
                }))

        # Paragraphs
        if child.name == "p":
            text = child.get_text(strip=True)
            if text:
                body_parts.append(("text", text))
        elif child.name == "div":
            # Skip related articles sections
            text = child.get_text(strip=True)
            if text and not text.startswith("【") and len(text) < 500:
                body_parts.append(("text", text))

# === Output plain text (for judge comparison) ===
plain_lines = []
plain_lines.append(title)
if date_author:
    plain_lines.append(date_author)
if cover_img_caption:
    plain_lines.append(cover_img_caption)
for part_type, content in body_parts:
    if part_type == "text":
        plain_lines.append(content)
    elif part_type == "image":
        if content.get("caption"):
            plain_lines.append(content["caption"])

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(plain_lines))

# === Output markdown (richer format with images) ===
md_lines = []
md_lines.append(f"# {title}")
md_lines.append("")
if date_author:
    md_lines.append(f"*{date_author}*")
    md_lines.append("")
if cover_img_src:
    md_lines.append(f"![{cover_img_caption}]({cover_img_src})")
    if cover_img_caption:
        md_lines.append(f"*{cover_img_caption}*")
    md_lines.append("")
for part_type, content in body_parts:
    if part_type == "text":
        md_lines.append(content)
        md_lines.append("")
    elif part_type == "image":
        md_lines.append(f"![{content.get('alt', '')}]({content['src']})")
        if content.get("caption"):
            md_lines.append(f"*{content['caption']}*")
        md_lines.append("")

with open(OUTPUT_MD, "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines))

# === Report ===
print(f"Title: {title[:60]}")
print(f"Date/Author: {date_author}")
print(f"Cover image: {bool(cover_img_src)}")
print(f"Body parts: {len(body_parts)}")
print(f"Plain text lines: {len(plain_lines)}")
print(f"Output: {OUTPUT}")
print(f"Markdown: {OUTPUT_MD}")

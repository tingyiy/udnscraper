#!/usr/bin/env python3
"""
Experiment 001: Baseline — requests + BeautifulSoup
Hypothesis: Simple HTTP GET with requests may return the article HTML.
UDN might server-side render content, making this sufficient.
"""
import requests
from bs4 import BeautifulSoup
import os

URL = "https://udn.com/news/story/124061/9422974"
OUTPUT = os.path.join(os.path.dirname(__file__), "results", "experiment_001.txt")

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

resp = requests.get(URL, headers=headers, timeout=30)
resp.encoding = "utf-8"
print(f"Status: {resp.status_code}")
print(f"Content length: {len(resp.text)}")

soup = BeautifulSoup(resp.text, "html.parser")

# Try to extract article content
lines = []

# Title
title = soup.find("h1")
if title:
    lines.append(title.get_text(strip=True))
    print(f"Title: {title.get_text(strip=True)[:60]}")

# Look for article body - try common selectors
for selector in [
    "article",
    ".article-content",
    ".article-body",
    ".story-body",
    "#story_body",
    ".article-content__paragraph",
    "[data-component='story-body']",
]:
    el = soup.select_one(selector)
    if el:
        print(f"Found content via: {selector}")
        for p in el.find_all(["p", "div"], recursive=True):
            text = p.get_text(strip=True)
            if text and len(text) > 5:
                lines.append(text)
        break

# If nothing found via selectors, dump page structure for analysis
if len(lines) <= 1:
    print("\nNo article content found via selectors. Page structure:")
    for tag in soup.find_all(True, limit=100):
        if tag.get("class"):
            print(f"  <{tag.name} class=\"{' '.join(tag['class'])}\">")
        elif tag.get("id"):
            print(f"  <{tag.name} id=\"{tag['id']}\">")

# Also save raw HTML for debugging
raw_path = os.path.join(os.path.dirname(__file__), "results", "experiment_001_raw.html")
with open(raw_path, "w", encoding="utf-8") as f:
    f.write(resp.text)
print(f"\nRaw HTML saved to {raw_path}")

# Write output
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"\nExtracted {len(lines)} lines")
print(f"Output saved to {OUTPUT}")

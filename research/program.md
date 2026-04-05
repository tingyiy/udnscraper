# UDN.com Article Scraper — Research Program

## Goal
Build a reliable scraper for udn.com news articles that extracts clean text content:
- **Title** (headline)
- **Date** and **source/author**
- **Body** (article paragraphs, in order)

The output should match a manually-extracted reference (clean text, no HTML, no ads, no navigation).

## Scope
- The agent may modify scraping approach, libraries, headers, parsing logic
- The agent may install new Python packages if needed
- Target: `https://udn.com/news/story/{category_id}/{article_id}` URL pattern

## Constraints
- Output must be plain text, matching the reference format
- Must handle Chinese (UTF-8) correctly
- Prefer lightweight solutions (requests > browser automation) if possible
- Must work without login/authentication

## Evaluation
- **Type B (Metric Judge)**: Compare extracted text against reference using line-level matching
- Primary metric: percentage of expected lines present in output
- Secondary metric: no extra junk lines (ads, nav, scripts)

## Test Cases
Starting with one article, expandable:
- `9422974` — https://udn.com/news/story/124061/9422974

## Available Tools
- Python 3.9.6 with requests, beautifulsoup4, lxml
- Node.js v22.16.0
- Can install: httpx, playwright, selenium, etc.

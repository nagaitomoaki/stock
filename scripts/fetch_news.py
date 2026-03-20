#!/usr/bin/env python3
"""
Fetch stock market news from RSS feeds.
"""
from __future__ import annotations

import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

# ── RSSフィード定義 ────────────────────────────────────────────────────────────
FEEDS_JP = [
    ("Yahoo Finance 日本 - 日経225",  "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EN225&region=JP&lang=ja-JP"),
    ("Yahoo Finance Japan - Market", "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EJPX&region=JP&lang=ja-JP"),
]

FEEDS_US = [
    ("Yahoo Finance - US Markets",   "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC,%5EDJI,%5EIXIC&region=US&lang=en-US"),
    ("Reuters - Business News",      "https://feeds.reuters.com/reuters/businessNews"),
]


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _fetch_rss(url: str, max_items: int = 10) -> list[dict]:
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; stock-wiki-bot/1.0)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
    except Exception as e:
        print(f"WARNING: Failed to fetch {url}: {e}", file=sys.stderr)
        return []

    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        print(f"WARNING: Failed to parse RSS {url}: {e}", file=sys.stderr)
        return []

    items = []
    for item in root.findall(".//item")[:max_items]:
        title       = _strip_html(item.findtext("title") or "")
        link        = (item.findtext("link") or "").strip()
        pub_date    = (item.findtext("pubDate") or "").strip()
        description = _strip_html(item.findtext("description") or "")[:300]
        if title:
            items.append({
                "title":       title,
                "link":        link,
                "pubDate":     pub_date,
                "description": description,
            })
    return items


def get_news_data(market: str) -> dict:
    """
    market: "jp" | "us"
    Returns {"market": str, "feeds": [{"name": str, "items": [...]}, ...]}
    """
    feeds_def = FEEDS_JP if market == "jp" else FEEDS_US
    feeds = []
    for name, url in feeds_def:
        items = _fetch_rss(url, max_items=8)
        feeds.append({"name": name, "items": items})
    return {"market": market, "feeds": feeds}


if __name__ == "__main__":
    import json, argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=["jp", "us", "both"], default="both")
    args = parser.parse_args()

    markets = ["jp", "us"] if args.market == "both" else [args.market]
    for m in markets:
        print(json.dumps(get_news_data(m), ensure_ascii=False, indent=2))

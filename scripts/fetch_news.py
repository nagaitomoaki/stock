#!/usr/bin/env python3
"""
Fetch stock market and geopolitical news from RSS feeds.
"""
from __future__ import annotations

import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

# ── 日本市場ニュース ────────────────────────────────────────────────────────────
FEEDS_JP = [
    ("Yahoo Finance 日本 - 日経225",  "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EN225&region=JP&lang=ja-JP"),
    ("Yahoo Finance Japan - Market", "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EJPX&region=JP&lang=ja-JP"),
]

# ── 米国市場ニュース ────────────────────────────────────────────────────────────
FEEDS_US = [
    ("Yahoo Finance - US Markets",   "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC,%5EDJI,%5EIXIC&region=US&lang=en-US"),
    ("MarketWatch - Top Stories",    "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("CNBC - World Markets",         "https://www.cnbc.com/id/15839069/device/rss/rss.html"),
]

# ── 地政学・世界情勢ニュース（株価への間接影響分析用） ────────────────────────
FEEDS_GEO = [
    ("AP - World News",              "https://feeds.apnews.com/rss/apf-worldnews"),
    ("AP - Business News",           "https://feeds.apnews.com/rss/apf-business"),
    ("AP - Technology",              "https://feeds.apnews.com/rss/apf-technology"),
    ("NHK World - Business",         "https://www3.nhk.or.jp/rss/news/cat6.xml"),
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


def get_geopolitical_news() -> list[dict]:
    """
    地政学・世界情勢ニュースを取得。
    株価への間接影響（供給チェーン・資源・制裁など）分析に使用。
    Returns flat list of news items with "source" key added.
    """
    all_items: list[dict] = []
    for name, url in FEEDS_GEO:
        items = _fetch_rss(url, max_items=8)
        for item in items:
            item["source"] = name
        all_items.extend(items)
    return all_items


if __name__ == "__main__":
    import json, argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=["jp", "us", "both", "geo"], default="both")
    args = parser.parse_args()

    if args.market == "geo":
        print(json.dumps(get_geopolitical_news(), ensure_ascii=False, indent=2))
    else:
        markets = ["jp", "us"] if args.market == "both" else [args.market]
        for m in markets:
            print(json.dumps(get_news_data(m), ensure_ascii=False, indent=2))

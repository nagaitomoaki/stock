#!/usr/bin/env python3
"""
Fetch stock market news and generate wiki markdown.
Usage:
  python fetch_news.py --market us   -> US market news
  python fetch_news.py --market jp   -> Japan market news
"""

import argparse
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
ET_NY = timezone(timedelta(hours=-5))  # EST (approximate; no DST handling needed for display)


def fetch_rss(url: str, max_items: int = 10) -> list[dict]:
    """Fetch and parse RSS feed, return list of {title, link, pubDate, description}."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; stock-wiki-bot/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
    except Exception as e:
        print(f"WARNING: Failed to fetch {url}: {e}", file=sys.stderr)
        return []

    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        print(f"WARNING: Failed to parse RSS from {url}: {e}", file=sys.stderr)
        return []

    items = []
    for item in root.findall(".//item")[:max_items]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        description = (item.findtext("description") or "").strip()
        # Remove HTML tags from description (simple approach)
        import re
        description = re.sub(r"<[^>]+>", "", description).strip()
        if title:
            items.append({"title": title, "link": link, "pubDate": pub_date, "description": description})
    return items


US_FEEDS = [
    ("Yahoo Finance - Market News", "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC,%5EDJI,%5EIXIC&region=US&lang=en-US"),
    ("Reuters - Business", "https://feeds.reuters.com/reuters/businessNews"),
]

JP_FEEDS = [
    ("Yahoo Finance Japan - 日経平均", "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EN225&region=JP&lang=ja-JP"),
    ("Yahoo Finance Japan - Market", "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EJPX&region=JP&lang=ja-JP"),
]


def build_us_page(now_utc: datetime) -> str:
    now_et = now_utc.astimezone(ET_NY)
    now_jst = now_utc.astimezone(JST)
    lines = [
        "# 米国株式市場ニュース (US Market News)",
        "",
        f"> 最終更新 / Last updated: {now_jst.strftime('%Y-%m-%d %H:%M')} JST  |  {now_et.strftime('%Y-%m-%d %H:%M')} ET",
        "",
        "---",
        "",
    ]

    for feed_name, url in US_FEEDS:
        items = fetch_rss(url, max_items=8)
        lines.append(f"## {feed_name}")
        lines.append("")
        if not items:
            lines.append("_ニュースを取得できませんでした。_")
            lines.append("")
            continue
        for item in items:
            title = item["title"]
            link = item["link"]
            pub = item["pubDate"]
            desc = item["description"]
            if link:
                lines.append(f"- **[{title}]({link})**")
            else:
                lines.append(f"- **{title}**")
            if pub:
                lines.append(f"  - {pub}")
            if desc and len(desc) < 200:
                lines.append(f"  - {desc}")
        lines.append("")

    lines += [
        "---",
        "",
        "_このページは GitHub Actions により自動更新されます。_",
        "_This page is automatically updated by GitHub Actions._",
    ]
    return "\n".join(lines) + "\n"


def build_jp_page(now_utc: datetime) -> str:
    now_jst = now_utc.astimezone(JST)
    lines = [
        "# 日本株式市場ニュース (Japan Market News)",
        "",
        f"> 最終更新: {now_jst.strftime('%Y-%m-%d %H:%M')} JST",
        "",
        "---",
        "",
    ]

    for feed_name, url in JP_FEEDS:
        items = fetch_rss(url, max_items=8)
        lines.append(f"## {feed_name}")
        lines.append("")
        if not items:
            lines.append("_ニュースを取得できませんでした。_")
            lines.append("")
            continue
        for item in items:
            title = item["title"]
            link = item["link"]
            pub = item["pubDate"]
            desc = item["description"]
            if link:
                lines.append(f"- **[{title}]({link})**")
            else:
                lines.append(f"- **{title}**")
            if pub:
                lines.append(f"  - {pub}")
            if desc and len(desc) < 200:
                lines.append(f"  - {desc}")
        lines.append("")

    lines += [
        "---",
        "",
        "_このページは GitHub Actions により自動更新されます。_",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=["us", "jp"], required=True)
    parser.add_argument("--output", default=None, help="Output file path (default: stdout)")
    args = parser.parse_args()

    now_utc = datetime.now(timezone.utc)

    if args.market == "us":
        content = build_us_page(now_utc)
        filename = "US-Market-News.md"
    else:
        content = build_jp_page(now_utc)
        filename = "Japan-Market-News.md"

    out_path = args.output or filename
    Path(out_path).write_text(content, encoding="utf-8")
    print(f"Written to {out_path}")


if __name__ == "__main__":
    main()

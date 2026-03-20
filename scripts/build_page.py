#!/usr/bin/env python3
"""
Build the GitHub Pages HTML from all data sources.
Usage: python scripts/build_page.py --output docs/index.html
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── パス設定 ─────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_news   import get_news_data
from fetch_prices import get_price_data
from translate    import translate_and_summarise


def build(output: Path) -> None:
    JST = timezone(timedelta(hours=9))
    now_jst = datetime.now(JST)
    updated_at = now_jst.strftime("%Y年%m月%d日 %H:%M JST")

    print("📡 ニュースを取得中...")
    jp_news = get_news_data("jp")
    us_news = get_news_data("us")

    print("💹 価格データを取得中...")
    prices = get_price_data()

    # 全ニュースアイテムを翻訳
    print("🤖 Claude で翻訳・要約中...")
    all_items: list[dict] = []
    for feed in jp_news["feeds"] + us_news["feeds"]:
        all_items.extend(feed["items"])

    all_items = translate_and_summarise(all_items)

    # テンプレート用にフラットなリストを用意
    jp_items = [item for feed in jp_news["feeds"] for item in feed["items"]]
    us_items = [item for feed in us_news["feeds"] for item in feed["items"]]

    print("🎨 HTML を生成中...")
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape  # type: ignore
    except ImportError:
        print("ERROR: jinja2 not installed. Run: pip install jinja2", file=sys.stderr)
        sys.exit(1)

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("index.html.jinja")

    html = template.render(
        updated_at=updated_at,
        jp_items=jp_items,
        us_items=us_items,
        prices=prices,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    print(f"✅ 出力完了: {output}  ({len(html):,} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="docs/index.html")
    args = parser.parse_args()
    build(Path(args.output))


if __name__ == "__main__":
    main()

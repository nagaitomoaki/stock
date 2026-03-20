#!/usr/bin/env python3
"""
Translate & summarise news items using the Anthropic API (claude-haiku).
Falls back to returning the original text if the API key is not set.
"""
from __future__ import annotations

import json
import os
import sys
import unicodedata


def _has_japanese(text: str) -> bool:
    for ch in text:
        name = unicodedata.name(ch, "")
        if "CJK" in name or "HIRAGANA" in name or "KATAKANA" in name:
            return True
    return False


def translate_and_summarise(items: list[dict]) -> list[dict]:
    """
    Each item: {"title": str, "description": str, "link": str, "pubDate": str}
    Returns same list with added keys: "title_ja", "summary_ja"
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("INFO: ANTHROPIC_API_KEY not set. Skipping translation.", file=sys.stderr)
        for item in items:
            item["title_ja"]   = item.get("title", "")
            item["summary_ja"] = item.get("description", "")
        return items

    # Filter items that need translation
    to_translate = [
        i for i, item in enumerate(items)
        if not _has_japanese(item.get("title", ""))
    ]

    if not to_translate:
        for item in items:
            item.setdefault("title_ja",   item.get("title", ""))
            item.setdefault("summary_ja", item.get("description", ""))
        return items

    try:
        import anthropic  # type: ignore
    except ImportError:
        print("WARNING: anthropic package not installed.", file=sys.stderr)
        for item in items:
            item["title_ja"]   = item.get("title", "")
            item["summary_ja"] = item.get("description", "")
        return items

    client = anthropic.Anthropic(api_key=api_key)

    # Build batch payload
    news_list = []
    for idx in to_translate:
        item = items[idx]
        news_list.append({
            "id":          idx,
            "title":       item.get("title", ""),
            "description": item.get("description", "")[:300],
        })

    prompt = f"""以下の株式市場ニュース記事を日本語に翻訳し、各記事に対して日本語の要約（50〜80文字）も作成してください。
固有名詞・企業名・指数名はそのまま使用してください。

入力JSON:
{json.dumps(news_list, ensure_ascii=False)}

出力形式（JSONのみ、他のテキスト不要）:
[
  {{"id": 0, "title_ja": "日本語タイトル", "summary_ja": "50〜80文字の日本語要約"}},
  ...
]"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # Extract JSON array from response
        start = raw.find("[")
        end   = raw.rfind("]") + 1
        results: list[dict] = json.loads(raw[start:end])

        result_map = {r["id"]: r for r in results}
        for idx in to_translate:
            r = result_map.get(idx, {})
            items[idx]["title_ja"]   = r.get("title_ja",   items[idx].get("title", ""))
            items[idx]["summary_ja"] = r.get("summary_ja", items[idx].get("description", ""))

    except Exception as e:
        print(f"WARNING: Translation failed: {e}", file=sys.stderr)
        for idx in to_translate:
            items[idx]["title_ja"]   = items[idx].get("title", "")
            items[idx]["summary_ja"] = items[idx].get("description", "")

    # Ensure already-Japanese items also have the keys
    for item in items:
        item.setdefault("title_ja",   item.get("title", ""))
        item.setdefault("summary_ja", item.get("description", ""))

    return items


if __name__ == "__main__":
    sample = [
        {"title": "S&P 500 rises on tech rally", "description": "The S&P 500 gained 1.2% as technology stocks led the market higher.", "link": "", "pubDate": ""},
        {"title": "日経平均が続伸",               "description": "東京市場では買い優勢の展開となった。",                               "link": "", "pubDate": ""},
    ]
    result = translate_and_summarise(sample)
    for r in result:
        print(r["title_ja"], "|", r["summary_ja"])

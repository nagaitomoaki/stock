#!/usr/bin/env python3
"""
Generate market commentary and featured stock/industry picks using Claude AI.
"""
from __future__ import annotations

import json
import os
import sys


def _build_market_snapshot(prices: dict) -> str:
    """Price data をテキスト要約に変換してプロンプトに埋め込む。"""
    lines = []

    lines.append("【主要指数】")
    for idx in prices.get("indices", []):
        if idx["price"]:
            lines.append(f"  {idx['emoji']} {idx['name']}: {idx['price']:,.2f}  ({idx['arrow']}{idx['change_pct']:+.2f}%)")

    lines.append("【セクター別ETF（米国）】")
    for s in prices.get("sectors", []):
        if s["price"]:
            lines.append(f"  {s['emoji']} {s['name']}: {s['arrow']}{s['change_pct']:+.2f}%")

    lines.append("【コモディティ】")
    for m in prices.get("commodities", []):
        if m["price"]:
            lines.append(f"  {m['emoji']} {m['name']}: ${m['price']:,.3f}  ({m['arrow']}{m['change_pct']:+.2f}%)")

    lines.append("【仮想通貨】")
    for c in prices.get("crypto", []):
        if c["price"]:
            lines.append(f"  {c['emoji']} {c['name']}: ${c['price']:,.2f}  ({c['arrow']}{c['change_pct']:+.2f}%)")

    return "\n".join(lines)


def _build_news_summary(jp_items: list[dict], us_items: list[dict]) -> str:
    """翻訳済みニュース見出しを要約テキストに変換。"""
    lines = ["【本日の主なニュース見出し】"]
    for item in (jp_items + us_items)[:20]:
        title = item.get("title_ja") or item.get("title", "")
        if title:
            lines.append(f"  ・{title}")
    return "\n".join(lines)


def generate_analysis(
    prices: dict,
    jp_items: list[dict],
    us_items: list[dict],
) -> dict:
    """
    Returns:
      {
        "commentary": {
          "overview": str,        # 市場全体の概況（2〜3文）
          "drivers": str,         # 相場を動かした主な要因（2〜3文）
          "global_trends": str,   # コモディティ・仮想通貨を含むグローバル動向（2〜3文）
        },
        "featured": [
          {
            "name": str,          # 銘柄名 or 業界名
            "emoji": str,
            "type": "銘柄" | "業界" | "コモディティ" | "仮想通貨",
            "reason": str,        # 注目理由（2〜3文）
            "outlook": str,       # 今後の見通し（1〜2文）
            "risk": "高" | "中" | "低",
            "tag": str,           # 短いタグ例: "テック" "エネルギー" "BTC" など
          },
          ...  # 5件
        ]
      }
    Falls back to empty strings / empty list if API key not set.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("INFO: ANTHROPIC_API_KEY not set. Skipping analysis.", file=sys.stderr)
        return _empty_analysis()

    try:
        import anthropic  # type: ignore
    except ImportError:
        print("WARNING: anthropic not installed.", file=sys.stderr)
        return _empty_analysis()

    snapshot = _build_market_snapshot(prices)
    news_text = _build_news_summary(jp_items, us_items)

    prompt = f"""あなたは株式市場アナリストです。以下の本日の市場データとニュース見出しをもとに、
2つのセクションを日本語で作成してください。

{snapshot}

{news_text}

---

## 出力形式（JSONのみ、他のテキスト不要）

{{
  "commentary": {{
    "overview":       "市場全体の概況を2〜3文で。値動きの大きさや方向性を具体的な数値を交えて説明。",
    "drivers":        "相場を動かした主な要因を2〜3文で。ニュースや経済指標、地政学リスクなどを踏まえて。",
    "global_trends":  "コモディティ・仮想通貨・為替を含むグローバル動向を2〜3文で。"
  }},
  "featured": [
    {{
      "name":    "注目の銘柄名または業界名",
      "emoji":   "代表的な絵文字1文字",
      "type":    "銘柄 | 業界 | コモディティ | 仮想通貨",
      "reason":  "今日注目すべき理由を2〜3文で。具体的な数値や出来事を含めること。",
      "outlook": "今後1〜2週間の見通しを1〜2文で。",
      "risk":    "高 | 中 | 低",
      "tag":     "短いカテゴリタグ"
    }}
  ]
}}

注意:
- featured は必ず5件
- 数値は実際のデータから引用すること
- 投資勧誘にならないよう「注目」「注視」などの表現を使うこと
- JSONのみを返すこと（コードブロック不要）"""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        result = json.loads(raw[start:end])

        # 型ガード
        commentary = result.get("commentary", {})
        featured   = result.get("featured", [])[:5]
        return {"commentary": commentary, "featured": featured}

    except Exception as e:
        print(f"WARNING: Analysis generation failed: {e}", file=sys.stderr)
        return _empty_analysis()


def generate_watchlist_analysis(watchlist: list[dict], prices: dict, jp_items: list[dict], us_items: list[dict]) -> list[dict]:
    """
    ウォッチリスト銘柄（NEC・ソフトバンクG）の当日評価を生成。
    Returns list of dicts with keys: ticker, name, emoji, rating, reason, points, caution
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return []

    try:
        import anthropic  # type: ignore
    except ImportError:
        return []

    valid = [w for w in watchlist if w.get("price")]
    if not valid:
        return []

    snapshot = _build_market_snapshot(prices)
    news_text = _build_news_summary(jp_items, us_items)

    stocks_text = "\n".join([
        f"  {w['emoji']} {w['name']} ({w['ticker']}): {w['price']:,.1f}円  "
        f"前日比 {w['arrow']}{w['change_pct']:+.2f}%  セクター: {w.get('sector','')}"
        for w in valid
    ])

    prompt = f"""あなたは日本株のデイトレード専門アナリストです。
以下の銘柄について、本日のデイトレード観点での評価を行ってください。

【対象銘柄】
{stocks_text}

【市場環境】
{snapshot}

{news_text}

---

## 出力形式（JSONのみ、コードブロック不要）

[
  {{
    "ticker":  "6701.T",
    "name":    "NEC",
    "emoji":   "🔵",
    "rating":  "強気 | やや強気 | 中立 | やや弱気 | 弱気",
    "score":   7,
    "reason":  "本日の注目ポイントを3〜4文で。市場環境・セクター動向・個別材料を踏まえて。",
    "points":  ["デイトレで注目すべきポイント1", "ポイント2", "ポイント3"],
    "caution": "注意すべきリスクを1〜2文で。",
    "entry_hint": "デイトレ観点でのエントリー・エグジットのヒントを1文で。"
  }}
]

注意:
- 対象銘柄すべてを含めること
- score は1〜10の整数（10が最強気）
- 投資助言にならないよう「注目」「観察」「ヒント」等の表現を使うこと
- JSONのみを返すこと"""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        start = raw.find("[")
        end   = raw.rfind("]") + 1
        result = json.loads(raw[start:end])

        # watchlist の price/change_pct を補完
        price_map = {w["ticker"]: w for w in valid}
        for item in result:
            base = price_map.get(item.get("ticker"), {})
            item["price"]      = base.get("price")
            item["change_pct"] = base.get("change_pct")
            item["direction"]  = base.get("direction", "flat")
            item["arrow"]      = base.get("arrow", "")
        return result

    except Exception as e:
        print(f"WARNING: Watchlist analysis failed: {e}", file=sys.stderr)
        return []


def generate_future_outlook(
    prices: dict,
    jp_items: list[dict],
    us_items: list[dict],
) -> dict:
    """
    中長期の相場見通しと本日のアクションプランを生成。
    Returns:
      {
        "macro_themes": [
          {
            "theme": str,             # テーマ名
            "emoji": str,
            "description": str,       # 現状説明（2文）
            "historical_parallel": str, # 過去の類似例
            "timeline": str,          # いつまでに何が起こりそうか
            "sectors_to_watch": [str] # 注目セクター
          }, ...  # 3件
        ],
        "sector_rotation": {
          "current_leaders": [str],   # 現在強いセクター
          "emerging": [str],          # 台頭しつつあるセクター
          "lagging": [str],           # 出遅れセクター
          "rotation_hint": str        # ローテーションの解説（2文）
        },
        "recovery_scenarios": [
          {
            "asset": str,             # 資産名（SaaS株など）
            "emoji": str,
            "current_situation": str, # 現状（1文）
            "historical_case": str,   # 過去の類似例（ITバブルなど）
            "recovery_timeline": str, # 回復の目安期間
            "conditions": str         # 回復に必要な条件（1〜2文）
          }, ...  # 2〜3件
        ],
        "today_actions": [
          {
            "priority": int,          # 1=最優先
            "action": str,            # アクション名
            "emoji": str,
            "reason": str,            # 理由（1〜2文）
            "timing": str             # タイミングヒント
          }, ...  # 4〜5件
        ]
      }
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {}

    try:
        import anthropic  # type: ignore
    except ImportError:
        return {}

    snapshot = _build_market_snapshot(prices)
    news_text = _build_news_summary(jp_items, us_items)

    prompt = f"""あなたは株式市場の上級アナリストです。以下の市場データとニュースをもとに、
中長期の相場見通しと本日のデイトレーダー向けアクションプランを日本語で作成してください。

{snapshot}

{news_text}

---

## 出力形式（JSONのみ、コードブロック不要）

{{
  "macro_themes": [
    {{
      "theme":               "マクロテーマ名（例: 地政学リスクとエネルギー高騰）",
      "emoji":               "🌐",
      "description":         "現状を2文で。具体的な数値や最新動向を含める。",
      "historical_parallel": "過去の類似局面の具体例（例: 2022年ロシア侵攻時、1970年代オイルショック）",
      "timeline":            "今後3〜12ヶ月の展望を1〜2文で。",
      "sectors_to_watch":    ["セクター1", "セクター2"]
    }}
  ],
  "sector_rotation": {{
    "current_leaders":  ["エネルギー", "防衛"],
    "emerging":         ["素材", "インフラ"],
    "lagging":          ["SaaS", "ハイグロース"],
    "rotation_hint":    "セクターローテーションの現状と今後の方向性を2文で解説。"
  }},
  "recovery_scenarios": [
    {{
      "asset":              "SaaS/グロース株",
      "emoji":              "💻",
      "current_situation":  "現状を1文で。",
      "historical_case":    "2000年ITバブル崩壊後の回復パターンなど、具体的な過去事例。",
      "recovery_timeline":  "回復の目安（例: 金利ピークアウトから6〜18ヶ月）",
      "conditions":         "回復に必要な条件を1〜2文で。"
    }}
  ],
  "today_actions": [
    {{
      "priority": 1,
      "action":   "アクション名（簡潔に）",
      "emoji":    "🎯",
      "reason":   "このアクションが優先される理由を1〜2文で。",
      "timing":   "寄り付き直後 / 前場中盤 / 後場 / 今日は見送り など"
    }}
  ]
}}

注意:
- macro_themes は3件、recovery_scenarios は2〜3件、today_actions は4〜5件（優先度順）
- today_actions はデイトレーダー（日本株）向けの具体的な行動を優先度順に並べる
- 歴史的事例は必ず実際の出来事（年・相場名）を引用すること
- 投資助言にならないよう「注目」「観察」「参考まで」等の表現を使うこと
- JSONのみを返すこと"""

    try:
        import anthropic  # type: ignore
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=6000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        return json.loads(raw[start:end])

    except Exception as e:
        print(f"WARNING: Future outlook generation failed: {e}", file=sys.stderr)
        return {}


def _empty_analysis() -> dict:
    return {
        "commentary": {
            "overview":      "",
            "drivers":       "",
            "global_trends": "",
        },
        "featured": [],
    }


if __name__ == "__main__":
    # 簡易テスト（価格データなしで空の場合の確認）
    result = generate_analysis(
        prices={"indices": [], "sectors": [], "commodities": [], "crypto": []},
        jp_items=[],
        us_items=[],
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

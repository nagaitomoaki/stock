#!/usr/bin/env python3
"""
Generate market commentary, featured picks, watchlist evaluations,
and future outlook using Claude AI.

Geopolitical events and supply chain impacts are explicitly analyzed.
"""
from __future__ import annotations

import json
import os
import sys


# ──────────────────────────────────────────────────────────────────────────────
# 内部ヘルパー
# ──────────────────────────────────────────────────────────────────────────────

def _build_market_snapshot(prices: dict) -> str:
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


def _build_news_summary(
    jp_items: list[dict],
    us_items: list[dict],
    geo_items: list[dict] | None = None,
) -> str:
    lines = ["【本日の主なニュース見出し】"]

    if jp_items or us_items:
        lines.append("─ 市場ニュース ─")
        for item in (jp_items + us_items)[:15]:
            title = item.get("title_ja") or item.get("title", "")
            if title:
                lines.append(f"  ・{title}")

    if geo_items:
        lines.append("─ 地政学・世界情勢ニュース ─")
        for item in geo_items[:20]:
            title = item.get("title", "")
            source = item.get("source", "")
            if title:
                lines.append(f"  ・[{source}] {title}")
        lines.append("  ※上記は英語原文のニュース見出しです。株価への影響を分析してください。")

    return "\n".join(lines)


def _call_claude(prompt: str, max_tokens: int = 3000) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    import anthropic  # type: ignore
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def _extract_json_object(raw: str) -> dict:
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    return json.loads(raw[start:end])


def _extract_json_array(raw: str) -> list:
    start = raw.find("[")
    end   = raw.rfind("]") + 1
    return json.loads(raw[start:end])


# ──────────────────────────────────────────────────────────────────────────────
# 1. 本日の市場解説 & 注目銘柄
# ──────────────────────────────────────────────────────────────────────────────

def generate_analysis(
    prices: dict,
    jp_items: list[dict],
    us_items: list[dict],
    geo_items: list[dict] | None = None,
) -> dict:
    """
    本日の市場解説と注目銘柄を生成。
    地政学ニュース(geo_items)があれば供給チェーン影響も分析。
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("INFO: ANTHROPIC_API_KEY not set. Skipping analysis.", file=sys.stderr)
        return _empty_analysis()

    try:
        import anthropic  # noqa
    except ImportError:
        print("WARNING: anthropic not installed.", file=sys.stderr)
        return _empty_analysis()

    snapshot  = _build_market_snapshot(prices)
    news_text = _build_news_summary(jp_items, us_items, geo_items)

    prompt = f"""あなたは株式市場の上級アナリストです。以下の市場データと各種ニュースをもとに、
本日の市場解説と注目銘柄リストを日本語で作成してください。

{snapshot}

{news_text}

【分析の重点事項】
- 地政学リスク（戦争・制裁・外交摩擦）が特定セクターや資源に与える直接・間接影響
- 供給チェーンの分断リスク（例: 希少資源の産出国紛争 → 半導体・電池・エネルギー産業への波及）
- エネルギー・コモディティ価格の動きと株価の連動関係
- 為替（USD/JPY）の動きと輸出入企業への影響
- 各ニュースが複数のセクターをまたいで波及する「横断的リスク」を明示すること

---

## 出力形式（JSONのみ、コードブロック不要）

{{
  "commentary": {{
    "overview":       "市場全体の概況を2〜3文で。値動きの大きさ・方向性を具体的な数値を交えて説明。",
    "drivers":        "相場を動かした主な要因を2〜3文で。地政学リスク・供給チェーン・経済指標・金融政策など複合的な視点で。",
    "geo_impact":     "地政学・世界情勢ニュースが株式市場に与えている影響を2〜3文で。資源・産業・地域別に具体的に分析。",
    "global_trends":  "コモディティ・仮想通貨・為替を含むグローバル動向を2〜3文で。"
  }},
  "featured": [
    {{
      "name":    "注目の銘柄名または業界名",
      "emoji":   "代表的な絵文字1文字",
      "type":    "銘柄 | 業界 | コモディティ | 仮想通貨",
      "reason":  "今日注目すべき理由を2〜3文で。地政学・供給チェーン・市場データとの関連を含めること。",
      "outlook": "今後1〜2週間の見通しを1〜2文で。",
      "risk":    "高 | 中 | 低",
      "tag":     "短いカテゴリタグ"
    }}
  ]
}}

注意:
- featured は必ず5件
- geo_impact フィールドは必須。地政学ニュースがなければ「本日は大きな地政学リスクは確認されていません」と記入
- 数値は実際のデータから引用すること
- 投資勧誘にならないよう「注目」「注視」などの表現を使うこと
- JSONのみを返すこと（コードブロック不要）"""

    try:
        raw = _call_claude(prompt, max_tokens=3000)
        result = _extract_json_object(raw)
        commentary = result.get("commentary", {})
        featured   = result.get("featured", [])[:5]
        return {"commentary": commentary, "featured": featured}
    except Exception as e:
        print(f"WARNING: Analysis generation failed: {e}", file=sys.stderr)
        return _empty_analysis()


# ──────────────────────────────────────────────────────────────────────────────
# 2. ウォッチリスト個別評価（NEC・ソフトバンクG）
# ──────────────────────────────────────────────────────────────────────────────

def generate_watchlist_analysis(
    watchlist: list[dict],
    prices: dict,
    jp_items: list[dict],
    us_items: list[dict],
    geo_items: list[dict] | None = None,
) -> list[dict]:
    """
    ウォッチリスト銘柄の当日デイトレード評価を生成。
    地政学ニュースによる個別銘柄への影響も分析。
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return []

    try:
        import anthropic  # noqa
    except ImportError:
        return []

    valid = [w for w in watchlist if w.get("price")]
    if not valid:
        return []

    snapshot  = _build_market_snapshot(prices)
    news_text = _build_news_summary(jp_items, us_items, geo_items)

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

【分析の重点事項】
- 地政学リスクや世界情勢が各銘柄のビジネス・サプライチェーンに与える影響を具体的に分析
  （例: エネルギー価格高騰 → データセンターコスト増 → クラウド・AI関連株への影響）
  （例: 半導体材料の供給不安 → 国内半導体関連株・電子部品メーカーへの影響）
- 為替の動きが各銘柄の収益性に与える影響（輸出比率・海外収益の割合）
- 本日の市場センチメントとセクターローテーションの観点

---

## 出力形式（JSONのみ、コードブロック不要）

[
  {{
    "ticker":      "6701.T",
    "name":        "NEC",
    "emoji":       "🔵",
    "rating":      "強気 | やや強気 | 中立 | やや弱気 | 弱気",
    "score":       7,
    "reason":      "本日の注目ポイントを3〜4文で。市場環境・地政学影響・セクター動向・個別材料を踏まえて。",
    "geo_note":    "地政学・世界情勢が当該銘柄に与える影響を1〜2文で。プラス・マイナス両面から。",
    "points":      ["デイトレで注目すべきポイント1", "ポイント2", "ポイント3"],
    "caution":     "注意すべきリスクを1〜2文で。",
    "entry_hint":  "デイトレ観点でのエントリー・エグジットのヒントを1文で。"
  }}
]

注意:
- 対象銘柄すべてを含めること
- geo_note フィールドは必須（影響がなければ「直接的な影響は限定的ですが、〜」と記入）
- score は1〜10の整数（10が最強気）
- 投資助言にならないよう「注目」「観察」「ヒント」等の表現を使うこと
- JSONのみを返すこと"""

    try:
        raw = _call_claude(prompt, max_tokens=2500)
        result = _extract_json_array(raw)
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


# ──────────────────────────────────────────────────────────────────────────────
# 3. 中長期の相場見通し & 本日のアクションプラン
# ──────────────────────────────────────────────────────────────────────────────

def generate_future_outlook(
    prices: dict,
    jp_items: list[dict],
    us_items: list[dict],
    geo_items: list[dict] | None = None,
) -> dict:
    """
    中長期の相場見通し、歴史的パターンに基づく回復シナリオ、
    地政学リスクの波及分析、本日のアクションプランを生成。
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {}

    try:
        import anthropic  # noqa
    except ImportError:
        return {}

    snapshot  = _build_market_snapshot(prices)
    news_text = _build_news_summary(jp_items, us_items, geo_items)

    prompt = f"""あなたは株式市場の上級アナリストです。以下の市場データとニュースをもとに、
中長期の相場見通しと本日のデイトレーダー向けアクションプランを日本語で作成してください。

{snapshot}

{news_text}

【分析の重点事項】
1. 地政学リスクの波及分析（必須）:
   - 紛争・制裁・外交摩擦が資源・エネルギー・半導体・食料などの供給チェーンに与える影響
   - 希少資源（ヘリウム・レアアース・パラジウム等）の産出国リスクと代替調達の可能性
   - 制裁・輸出規制が技術移転・産業構造に与える長期的影響

2. 歴史的パターンの引用（必須）:
   - 現在の状況に類似した過去の出来事（年・出来事名・その後の相場推移）を必ず引用
   - 例: ITバブル崩壊(2000-2002)・リーマンショック(2008)・コロナショック(2020)・
         オイルショック(1973/1979)・アジア通貨危機(1997)・ロシア侵攻(2022)など

3. セクターローテーションの見通し:
   - 現在強いセクターはいつまで続くか、次に台頭するセクターはどこか

4. 下落資産の回復シナリオ:
   - SaaS・グロース株・仮想通貨など下落中の資産について、過去の類似局面からの回復期間と条件を分析

---

## 出力形式（JSONのみ、コードブロック不要）

{{
  "macro_themes": [
    {{
      "theme":               "マクロテーマ名（例: 中東紛争とエネルギー・資源サプライチェーン危機）",
      "emoji":               "🌐",
      "description":         "現状を2文で。具体的な国名・資源名・数値を含めること。",
      "geo_analysis":        "地政学リスクが供給チェーン・産業・企業収益に波及するメカニズムを2文で説明。",
      "historical_parallel": "過去の類似局面の具体例（年・出来事名・その後の相場の動き）",
      "timeline":            "今後3〜12ヶ月の展望を1〜2文で。",
      "sectors_to_watch":    ["影響を受けるセクター1", "セクター2", "セクター3"]
    }}
  ],
  "sector_rotation": {{
    "current_leaders":  ["現在強いセクター名"],
    "emerging":         ["台頭しつつあるセクター名"],
    "lagging":          ["出遅れセクター名"],
    "rotation_hint":    "なぜこのローテーションが起きているか、歴史的事例を踏まえて2文で解説。"
  }},
  "recovery_scenarios": [
    {{
      "asset":              "SaaS/グロース株",
      "emoji":              "💻",
      "current_situation":  "現状と下落要因を1文で。",
      "historical_case":    "類似した過去の事例（例: 2000年ITバブル崩壊後は底打ちまで約2年半、NASDAQ回復まで約15年）",
      "recovery_timeline":  "回復の目安期間と根拠（例: 金利ピークアウトから6〜18ヶ月が歴史的パターン）",
      "conditions":         "回復に必要な条件を1〜2文で（金利・規制・需要回復など）。"
    }}
  ],
  "today_actions": [
    {{
      "priority": 1,
      "action":   "アクション名（簡潔に）",
      "emoji":    "🎯",
      "reason":   "このアクションが優先される理由を1〜2文で。地政学・市場データの根拠を含めること。",
      "timing":   "寄り付き直後 | 前場中盤 | 後場 | 引け前 | 今日は見送り"
    }}
  ]
}}

注意:
- macro_themes は3件（地政学テーマを必ず1件以上含める）
- recovery_scenarios は2〜3件
- today_actions は4〜5件（優先度順）
- 歴史的事例は必ず実際の出来事（年・相場名）を引用すること
- geo_analysis フィールドは必須。「A→B→C」の形で波及メカニズムを明確に示すこと
- 投資助言にならないよう「注目」「観察」「参考まで」等の表現を使うこと
- JSONのみを返すこと"""

    try:
        raw = _call_claude(prompt, max_tokens=6000)
        return _extract_json_object(raw)
    except Exception as e:
        print(f"WARNING: Future outlook generation failed: {e}", file=sys.stderr)
        return {}


# ──────────────────────────────────────────────────────────────────────────────
# フォールバック
# ──────────────────────────────────────────────────────────────────────────────

def _empty_analysis() -> dict:
    return {
        "commentary": {
            "overview":      "",
            "drivers":       "",
            "geo_impact":    "",
            "global_trends": "",
        },
        "featured": [],
    }


if __name__ == "__main__":
    result = generate_analysis(
        prices={"indices": [], "sectors": [], "commodities": [], "crypto": []},
        jp_items=[],
        us_items=[],
        geo_items=[],
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

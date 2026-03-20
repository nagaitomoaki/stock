#!/usr/bin/env python3
"""
Fetch price data for sectors, commodities, crypto, premarket, watchlist, and Nikkei movers.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

try:
    import yfinance as yf
except ImportError:
    yf = None  # type: ignore

# ── 寄り付き前チェック ────────────────────────────────────────────────────────
PREMARKET = [
    {"ticker": "JPY=X",  "name": "USD/JPY",       "emoji": "💱", "unit": "円"},
    {"ticker": "^VIX",   "name": "VIX（恐怖指数）", "emoji": "😨", "unit": ""},
    {"ticker": "NKD=F",  "name": "日経先物(CME)",  "emoji": "📈", "unit": ""},
]

# ── 主要株価指数 ──────────────────────────────────────────────────────────────
INDICES = [
    {"ticker": "^N225", "name": "日経225",    "emoji": "🗾"},
    {"ticker": "^GSPC", "name": "S&P 500",    "emoji": "🇺🇸"},
    {"ticker": "^DJI",  "name": "NYダウ",     "emoji": "📈"},
    {"ticker": "^IXIC", "name": "NASDAQ",     "emoji": "💡"},
    {"ticker": "^HSI",  "name": "香港ハンセン","emoji": "🇭🇰"},
]

# ── セクターETF ────────────────────────────────────────────────────────────────
SECTORS = [
    {"ticker": "XLK",  "name": "テクノロジー",   "emoji": "💻"},
    {"ticker": "XLF",  "name": "金融",           "emoji": "🏦"},
    {"ticker": "XLE",  "name": "エネルギー",     "emoji": "⚡"},
    {"ticker": "XLV",  "name": "ヘルスケア",     "emoji": "🏥"},
    {"ticker": "XLI",  "name": "資本財",         "emoji": "🏭"},
    {"ticker": "XLY",  "name": "一般消費財",     "emoji": "🛍️"},
    {"ticker": "XLP",  "name": "生活必需品",     "emoji": "🛒"},
    {"ticker": "XLB",  "name": "素材",           "emoji": "🔩"},
    {"ticker": "XLU",  "name": "公益事業",       "emoji": "💡"},
    {"ticker": "XLRE", "name": "不動産",         "emoji": "🏠"},
]

# ── コモディティ ──────────────────────────────────────────────────────────────
COMMODITIES = [
    {"ticker": "GC=F", "name": "金",       "emoji": "🥇", "unit": "USD/oz"},
    {"ticker": "SI=F", "name": "銀",       "emoji": "🥈", "unit": "USD/oz"},
    {"ticker": "PL=F", "name": "プラチナ", "emoji": "✨", "unit": "USD/oz"},
    {"ticker": "CL=F", "name": "原油(WTI)","emoji": "🛢️", "unit": "USD/bbl"},
    {"ticker": "NG=F", "name": "天然ガス", "emoji": "🔥", "unit": "USD/MMBtu"},
]

# ── 仮想通貨（BTC・ETHのみ）──────────────────────────────────────────────────
CRYPTO = [
    {"ticker": "BTC-USD", "name": "Bitcoin",  "emoji": "₿"},
    {"ticker": "ETH-USD", "name": "Ethereum", "emoji": "Ξ"},
]

# ── 個人ウォッチリスト ────────────────────────────────────────────────────────
WATCHLIST = [
    {"ticker": "6701.T", "name": "NEC",           "emoji": "🔵", "sector": "テクノロジー・防衛"},
    {"ticker": "9984.T", "name": "ソフトバンクG", "emoji": "🟠", "sector": "通信・テック投資"},
]

# ── 日経主要銘柄（値上がり・値下がりランキング用）────────────────────────────
NIKKEI_STOCKS = [
    {"ticker": "7203.T", "name": "トヨタ"},
    {"ticker": "6758.T", "name": "ソニーG"},
    {"ticker": "9984.T", "name": "ソフトバンクG"},
    {"ticker": "7974.T", "name": "任天堂"},
    {"ticker": "6861.T", "name": "キーエンス"},
    {"ticker": "9433.T", "name": "KDDI"},
    {"ticker": "8306.T", "name": "三菱UFJ"},
    {"ticker": "9983.T", "name": "ファストリ"},
    {"ticker": "6098.T", "name": "リクルート"},
    {"ticker": "4063.T", "name": "信越化"},
    {"ticker": "6954.T", "name": "ファナック"},
    {"ticker": "6367.T", "name": "ダイキン"},
    {"ticker": "7267.T", "name": "ホンダ"},
    {"ticker": "6501.T", "name": "日立"},
    {"ticker": "6702.T", "name": "富士通"},
    {"ticker": "9432.T", "name": "NTT"},
    {"ticker": "8591.T", "name": "ORIX"},
    {"ticker": "8604.T", "name": "野村HD"},
    {"ticker": "8316.T", "name": "三井住友FG"},
    {"ticker": "4502.T", "name": "武田薬品"},
    {"ticker": "6981.T", "name": "村田製作"},
    {"ticker": "6701.T", "name": "NEC"},
    {"ticker": "6752.T", "name": "パナソニック"},
    {"ticker": "7751.T", "name": "キヤノン"},
    {"ticker": "4519.T", "name": "中外製薬"},
]


def _fetch_quote(ticker: str) -> tuple[float | None, float | None]:
    if yf is None:
        return None, None
    try:
        info = yf.Ticker(ticker).fast_info
        price = float(info.last_price)
        prev  = float(info.previous_close)
        pct   = (price - prev) / prev * 100 if prev else 0.0
        return round(price, 4), round(pct, 2)
    except Exception as e:
        print(f"WARNING: {ticker} fetch failed: {e}", file=sys.stderr)
        return None, None


def _make_item(meta: dict) -> dict:
    price, pct = _fetch_quote(meta["ticker"])
    direction = "up" if (pct or 0) >= 0 else "down"
    return {
        **meta,
        "price":      price,
        "change_pct": pct,
        "direction":  direction,
        "arrow":      "▲" if direction == "up" else "▼",
    }


def get_price_data() -> dict:
    now = datetime.now(timezone.utc)

    # 日経銘柄を一括取得してランキング化
    nikkei_items = [_make_item(m) for m in NIKKEI_STOCKS]
    valid = [x for x in nikkei_items if x["price"] is not None]
    gainers = sorted(valid, key=lambda x: x["change_pct"], reverse=True)[:5]
    losers  = sorted(valid, key=lambda x: x["change_pct"])[:5]

    return {
        "premarket":   [_make_item(m) for m in PREMARKET],
        "indices":     [_make_item(m) for m in INDICES],
        "sectors":     [_make_item(m) for m in SECTORS],
        "commodities": [_make_item(m) for m in COMMODITIES],
        "crypto":      [_make_item(m) for m in CRYPTO],
        "watchlist":   [_make_item(m) for m in WATCHLIST],
        "gainers":     gainers,
        "losers":      losers,
        "fetched_at_utc": now.strftime("%Y-%m-%d %H:%M UTC"),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_price_data(), ensure_ascii=False, indent=2))

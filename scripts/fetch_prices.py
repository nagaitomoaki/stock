#!/usr/bin/env python3
"""
Fetch price data for sectors, commodities, and crypto via yfinance.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

try:
    import yfinance as yf
except ImportError:
    yf = None  # type: ignore

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

# ── 仮想通貨 ──────────────────────────────────────────────────────────────────
CRYPTO = [
    {"ticker": "BTC-USD", "name": "Bitcoin",  "emoji": "₿"},
    {"ticker": "ETH-USD", "name": "Ethereum", "emoji": "Ξ"},
    {"ticker": "SOL-USD", "name": "Solana",   "emoji": "◎"},
    {"ticker": "XRP-USD", "name": "XRP",      "emoji": "💫"},
    {"ticker": "BNB-USD", "name": "BNB",      "emoji": "🔶"},
]

# ── 主要株価指数 ──────────────────────────────────────────────────────────────
INDICES = [
    {"ticker": "^N225", "name": "日経225",    "emoji": "🗾"},
    {"ticker": "^GSPC", "name": "S&P 500",    "emoji": "🇺🇸"},
    {"ticker": "^DJI",  "name": "NYダウ",     "emoji": "📈"},
    {"ticker": "^IXIC", "name": "NASDAQ",     "emoji": "💡"},
    {"ticker": "^HSI",  "name": "香港ハンセン","emoji": "🇭🇰"},
]


def _fetch_quote(ticker: str) -> tuple[float, float] | tuple[None, None]:
    """Return (price, change_pct). Returns (None, None) on failure."""
    if yf is None:
        return None, None
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
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
    """Return all price data as a dict (safe to call even if yfinance is missing)."""
    now = datetime.now(timezone.utc)
    return {
        "indices":    [_make_item(m) for m in INDICES],
        "sectors":    [_make_item(m) for m in SECTORS],
        "commodities":[_make_item(m) for m in COMMODITIES],
        "crypto":     [_make_item(m) for m in CRYPTO],
        "fetched_at_utc": now.strftime("%Y-%m-%d %H:%M UTC"),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_price_data(), ensure_ascii=False, indent=2))

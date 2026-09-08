"""Public Bybit market-data adapter.

This module intentionally contains no authenticated client and no order endpoint.
It exists only to collect public candles for research/backtesting.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import PriceBar

TESTNET_BASE = "https://api-testnet.bybit.com"
MAINNET_BASE = "https://api.bybit.com"


def parse_kline_payload(payload: dict[str, Any]) -> list[PriceBar]:
    if payload.get("retCode") != 0:
        raise ValueError(f"Bybit returned error: {payload.get('retMsg', 'unknown error')}")
    raw_rows = payload.get("result", {}).get("list", [])
    bars: list[PriceBar] = []
    for row in raw_rows:
        if len(row) < 6:
            raise ValueError("unexpected Bybit kline row")
        timestamp_ms, open_, high, low, close, volume = row[:6]
        stamp = datetime.fromtimestamp(int(timestamp_ms) / 1000.0, tz=timezone.utc).isoformat()
        bars.append(
            PriceBar(
                timestamp=stamp,
                open=float(open_),
                high=float(high),
                low=float(low),
                close=float(close),
                volume=float(volume),
            )
        )
    # Bybit returns newest first; research code uses chronological order.
    bars.reverse()
    return bars


def fetch_bybit_klines(
    symbol: str,
    *,
    interval: str = "60",
    limit: int = 200,
    category: str = "linear",
    testnet: bool = True,
    timeout: float = 10.0,
) -> list[PriceBar]:
    """Fetch public candles without API credentials."""

    if not symbol or not symbol.strip():
        raise ValueError("symbol is required")
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    if category not in {"linear", "spot", "inverse"}:
        raise ValueError("category must be linear, spot, or inverse")

    base = TESTNET_BASE if testnet else MAINNET_BASE
    query = urlencode(
        {
            "category": category,
            "symbol": symbol.strip().upper(),
            "interval": interval,
            "limit": limit,
        }
    )
    request = Request(
        f"{base}/v5/market/kline?{query}",
        headers={"User-Agent": "CryptoQuantBot-research/0.2"},
    )
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    bars = parse_kline_payload(payload)
    if not bars:
        raise ValueError("Bybit returned no candles")
    return bars

"""
mcp_server/resources/historical.py

Responsible for providing cached historical price data for the last 30 days.
This module backs the MCP resource named `historical_prices`. A resource
in MCP is read-only data that the agent can request without triggering
a tool call — it is served at a URI and cached between requests.

The cache lives in memory for the lifetime of the MCP server process.
On first access the data is fetched from Robinhood; subsequent accesses
within the cache TTL return the in-memory copy.
"""

import robin_stocks.robinhood as rh
from typing import Any
from datetime import datetime, timedelta, timezone


# In-memory cache: maps symbol -> {"data": [...], "fetched_at": datetime}
_cache: dict[str, dict[str, Any]] = {}

# How long cached data is considered fresh before re-fetching
CACHE_TTL_SECONDS: int = 3600  # 1 hour


def get_historical_prices(symbols: list[str]) -> dict[str, Any]:
    """
    Return 30-day historical daily OHLCV data for each given symbol.

    This function is called by the MCP server when the agent reads the
    `historical_prices` resource. It checks the in-memory cache first
    and only calls Robinhood if the data is stale or missing.

    Receives:
        symbols (list[str]): List of uppercase stock ticker symbols
                             whose history should be returned.

    Returns:
        dict keyed by symbol, each mapping to a list of daily candle dicts:
          Each candle dict contains:
            - "date": str — ISO date string (YYYY-MM-DD)
            - "open": float
            - "high": float
            - "low": float
            - "close": float
            - "volume": int
        Also includes a top-level "as_of": str — ISO timestamp of data retrieval
    """

    now = datetime.now(timezone.utc)
    result: dict[str, Any] = {}

    for symbol in symbols:
        cached = _cache.get(symbol)
        if cached and (now - cached["fetched_at"]).total_seconds() < CACHE_TTL_SECONDS:
            result[symbol] = cached["data"]
            continue

        raw = rh.stocks.get_stock_historicals(symbol, interval="day", span="month") or []
        candles = []
        for bar in raw:
            try:
                date_str = bar["begins_at"][:10]
                candles.append({
                    "date": date_str,
                    "open": float(bar["open_price"]),
                    "high": float(bar["high_price"]),
                    "low": float(bar["low_price"]),
                    "close": float(bar["close_price"]),
                    "volume": int(bar.get("volume", 0) or 0),
                })
            except (KeyError, TypeError, ValueError):
                continue

        _cache[symbol] = {"data": candles, "fetched_at": now}
        result[symbol] = candles

    result["as_of"] = now.isoformat()
    return result

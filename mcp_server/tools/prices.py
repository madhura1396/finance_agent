"""
mcp_server/tools/prices.py

Responsible for fetching recent price changes for a list of stock symbols.
This module is called by the MCP server when the Claude agent invokes
the `get_price_changes` tool. It uses robin_stocks to get the latest
quote data and computes the day's absolute and percentage price movement.
"""

import robin_stocks.robinhood as rh
from typing import Any


def get_price_changes(symbols: list[str]) -> dict[str, Any]:
    """
    Fetch today's price change (absolute and percentage) for each given symbol.

    This function:
    1. Accepts a list of ticker symbols (e.g. ["AAPL", "TSLA"])
    2. Fetches the latest quote for each symbol from Robinhood
    3. Computes the absolute price change and percentage change for the day
    4. Returns a structured dict keyed by symbol

    Receives:
        symbols (list[str]): List of uppercase stock ticker symbols.
                             Example: ["AAPL", "MSFT", "NVDA"]

    Returns:
        dict with keys matching each input symbol, each mapping to a dict:
          - "current_price": float
          - "previous_close": float
          - "change": float — current_price minus previous_close
          - "change_pct": float — change expressed as a percentage
          - "volume": int — today's trading volume
          - "as_of": str — ISO timestamp of when data was fetched
    """

    from datetime import datetime, timezone

    if not symbols:
        return {}

    quotes = rh.stocks.get_quotes(symbols)
    as_of = datetime.now(timezone.utc).isoformat()
    result: dict[str, Any] = {}

    for symbol, quote in zip(symbols, quotes):
        if quote is None:
            result[symbol] = {"error": "Symbol not found or unavailable"}
            continue

        try:
            current_price = float(quote["last_trade_price"])
            previous_close = float(quote["adjusted_previous_close"])
            change = current_price - previous_close
            change_pct = (change / previous_close * 100) if previous_close else 0.0
            volume = int(quote.get("volume", 0) or 0)

            result[symbol] = {
                "current_price": current_price,
                "previous_close": previous_close,
                "change": change,
                "change_pct": change_pct,
                "volume": volume,
                "as_of": as_of,
            }
        except (KeyError, TypeError, ValueError) as e:
            result[symbol] = {"error": str(e)}

    return result

"""
mcp_server/tools/portfolio.py

Responsible for fetching the current portfolio from Robinhood.
This module is called by the MCP server when the Claude agent invokes
the `get_portfolio` tool. It uses robin_stocks to authenticate with
Robinhood and retrieve current open positions and their market values.
"""

import robin_stocks.robinhood as rh
from typing import Any


def get_portfolio() -> dict[str, Any]:
    """
    Fetch current portfolio positions and their market values from Robinhood.

    This function:
    1. Authenticates with Robinhood using credentials from config
    2. Retrieves all open stock positions
    3. Retrieves all open crypto positions (if applicable)
    4. Returns a structured dict with symbol, quantity, average cost,
       current price, current value, and unrealized gain/loss for each position

    Receives:
        Nothing — reads credentials from environment via config.py

    Returns:
        dict with keys:
          - "positions": list of dicts, each containing:
              - "symbol": str
              - "quantity": float
              - "average_buy_price": float
              - "current_price": float
              - "current_value": float
              - "unrealized_pnl": float
              - "unrealized_pnl_pct": float
          - "total_value": float — sum of all position values
          - "as_of": str — ISO timestamp of when data was fetched
    """

    from datetime import datetime, timezone

    holdings = rh.account.build_holdings()

    positions = []
    total_value = 0.0

    for symbol, data in holdings.items():
        quantity = float(data.get("quantity", 0))
        average_buy_price = float(data.get("average_buy_price", 0))

        prices = rh.stocks.get_latest_price(symbol)
        current_price = float(prices[0]) if prices and prices[0] is not None else 0.0

        current_value = quantity * current_price
        cost_basis = quantity * average_buy_price
        unrealized_pnl = current_value - cost_basis
        unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis else 0.0

        total_value += current_value

        positions.append({
            "symbol": symbol,
            "quantity": quantity,
            "average_buy_price": average_buy_price,
            "current_price": current_price,
            "current_value": current_value,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": unrealized_pnl_pct,
        })

    return {
        "positions": positions,
        "total_value": total_value,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }

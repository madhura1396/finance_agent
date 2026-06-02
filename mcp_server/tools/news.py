"""
mcp_server/tools/news.py

Responsible for fetching recent news articles relevant to a list of stock symbols.
This module is called by the MCP server when the Claude agent invokes
the `get_relevant_news` tool. It uses robin_stocks to pull news items
associated with each symbol from Robinhood's news endpoint.
"""

import robin_stocks.robinhood as rh
from typing import Any


def get_relevant_news(symbols: list[str]) -> dict[str, Any]:
    """
    Fetch recent news articles related to each given stock symbol.

    This function:
    1. Accepts a list of ticker symbols
    2. Queries Robinhood's news endpoint for each symbol
    3. Deduplicates articles that appear across multiple symbols
    4. Returns a structured dict of news items keyed by symbol

    Receives:
        symbols (list[str]): List of uppercase stock ticker symbols.
                             Example: ["AAPL", "MSFT"]

    Returns:
        dict with keys matching each input symbol, each mapping to a list of dicts:
          Each news item dict contains:
            - "title": str — headline of the article
            - "summary": str — short description or lede
            - "url": str — link to full article
            - "source": str — publisher name
            - "published_at": str — ISO timestamp of publication
          Also includes a top-level "deduplicated_feed": list of the same
          article dicts, sorted by published_at descending, with duplicates removed
    """

    if not symbols:
        return {"deduplicated_feed": []}

    result: dict[str, Any] = {}
    seen_urls: set[str] = set()
    all_articles: list[dict[str, Any]] = []

    for symbol in symbols:
        raw_articles = rh.stocks.get_news(symbol) or []
        parsed: list[dict[str, Any]] = []

        for article in raw_articles:
            url = article.get("url", "")
            item = {
                "title": article.get("title", ""),
                "summary": article.get("summary", ""),
                "url": url,
                "source": article.get("source", article.get("api_source", "")),
                "published_at": article.get("published_at", ""),
            }
            parsed.append(item)
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_articles.append(item)

        result[symbol] = parsed

    all_articles.sort(key=lambda a: a.get("published_at", ""), reverse=True)
    result["deduplicated_feed"] = all_articles

    return result

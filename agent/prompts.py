"""
agent/prompts.py

Defines the two instruction templates that the MCP server serves as prompts
and the agent client injects as the opening user message of each Claude session.

MORNING_BRIEFING_TEMPLATE — used by the 9am scheduled job.
EVENING_SUMMARY_TEMPLATE  — used by the 4pm scheduled job.

These are plain Python format strings. The single supported variable is {date}.
The MCP server's get_prompt() handler calls .format(date=date_str) on them.

Prompt design notes:
  - Each template explicitly tells Claude which tools it should call and in
    what order, so Claude does not have to infer a plan on its own.
  - The final instruction asks Claude to write the response in a style that
    reads well as a Telegram message (short paragraphs, emoji optional).
"""


MORNING_BRIEFING_TEMPLATE: str = """\
Today is {date}. You are a personal finance assistant monitoring a Robinhood portfolio.

Your job for this morning briefing:

1. Call get_portfolio() to retrieve all current open positions.
2. Extract the list of symbols from the portfolio.
3. Call get_price_changes(symbols) for those symbols to see how they opened.
4. Call get_relevant_news(symbols) to scan for any overnight or pre-market news.
5. You may also read the historical_prices resource if trend context is useful.

After gathering all data, write a concise morning briefing that includes:
  - A one-line summary of total portfolio value and overnight change.
  - For each significant position (>5% of portfolio), note the opening price move.
  - Highlight any news items that could materially affect positions today.
  - One sentence of forward-looking context or caution if warranted.

Keep the response under 300 words. Format it for easy reading in a Telegram message.
"""


EVENING_SUMMARY_TEMPLATE: str = """\
Today is {date}. You are a personal finance assistant monitoring a Robinhood portfolio.

The trading day has ended. Your job for this evening summary:

1. Call get_portfolio() to retrieve the current end-of-day state of all positions.
2. Extract the list of symbols from the portfolio.
3. Call get_price_changes(symbols) to get the full day's price movement.
4. Call get_relevant_news(symbols) to collect any news from during the trading day.
5. Read the historical_prices resource to compare today's close against the 30-day trend.

After gathering all data, write a concise evening summary that includes:
  - Total portfolio value, the day's dollar change, and the day's percentage change.
  - Top gainer and top loser for the day with their percentage moves.
  - One or two news items that most influenced today's moves.
  - A one-sentence reflection on whether today's moves fit the 30-day trend.

Keep the response under 300 words. Format it for easy reading in a Telegram message.
"""

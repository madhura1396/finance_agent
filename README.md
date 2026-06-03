# Finance Portfolio Notification Agent

A personal finance assistant that monitors your Robinhood portfolio and delivers AI-generated briefings to Telegram — built by creating a custom MCP (Model Context Protocol) server that exposes live financial data as tools and resources for Claude to reason over.

## What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io) is an open standard developed by Anthropic that defines how AI models connect to external data sources and tools. Instead of hardcoding API calls inside a prompt, you build an **MCP server** that exposes capabilities — tools, resources, and prompt templates — over a standard protocol. Any MCP-compatible client (like Claude) can then discover and call those capabilities dynamically.

This project builds a **custom MCP server from scratch** using the official Python SDK (`mcp` package) that gives Claude live access to a Robinhood portfolio.

## What the custom MCP server exposes

**Tools** — actions Claude can invoke:

| Tool | Description |
|---|---|
| `get_portfolio` | Fetches all open positions with quantity, cost basis, current price, and unrealized P&L |
| `get_price_changes` | Returns today's absolute and percentage price move for a list of symbols |
| `get_relevant_news` | Fetches and deduplicates recent news articles per symbol from Robinhood |

**Resources** — read-only data Claude can request:

| Resource | Description |
|---|---|
| `historical_prices` | 30-day daily OHLCV data for all portfolio symbols, cached in memory for 1 hour |

**Prompts** — reusable instruction templates:

| Prompt | Description |
|---|---|
| `morning_briefing` | Instructs Claude to summarize overnight moves, news, and day-ahead context |
| `evening_summary` | Instructs Claude to summarize the day's P&L, top movers, and 30-day trend |

## How it works

```
main.py
├── scheduler/jobs.py        APScheduler cron jobs (9am, 4pm weekdays)
├── tg/bot.py                Telegram bot (inbound messages + outbound delivery)
└── agent/client.py          MCP client + Claude tool-calling loop
        │
        └── MCP subprocess (stdio transport)
                mcp_server/server.py       Custom MCP server
                ├── tools/portfolio.py     get_portfolio
                ├── tools/prices.py        get_price_changes
                ├── tools/news.py          get_relevant_news
                └── resources/historical.py  historical_prices
```

When a scheduled job or Telegram message triggers the agent:

1. `agent/client.py` spawns `mcp_server/server.py` as a subprocess over **stdio transport**
2. The client calls `session.list_tools()` to discover what the MCP server exposes
3. Those tool definitions are forwarded to Claude via the Anthropic API
4. Claude reasons over the prompt and calls tools as needed — the client routes each call back to the MCP server
5. The loop continues until Claude produces a final text response
6. The response is delivered to Telegram

## What it does

- **9am weekdays** — morning briefing: portfolio value, overnight price moves, relevant news
- **4pm weekdays** — evening summary: day's P&L, top gainer/loser, 30-day trend context
- **On demand** — message the Telegram bot any time to ask ad-hoc questions about your portfolio

## Setup

### 1. Prerequisites

- Python 3.11+
- A [Robinhood](https://robinhood.com) account with holdings
- An [Anthropic API key](https://console.anthropic.com)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

### 2. Install dependencies

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `ROBINHOOD_USERNAME` | Robinhood account email |
| `ROBINHOOD_PASSWORD` | Robinhood account password |
| `ROBINHOOD_MFA_CODE` | TOTP secret if 2FA is enabled (leave blank otherwise) |
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your chat ID (message @userinfobot to find it) |
| `WATCHLIST_SYMBOLS` | Comma-separated fallback symbols e.g. `AAPL,TSLA,NVDA` |
| `TIMEZONE` | IANA timezone string e.g. `America/New_York` |
| `CLAUDE_MODEL` | Claude model ID (default: `claude-sonnet-4-6`) |

### 4. Authenticate with Robinhood (first time only)

```bash
source .venv/bin/activate
python -c "
import robin_stocks.robinhood as rh
from dotenv import load_dotenv; load_dotenv()
import os
rh.login(
    username=os.environ['ROBINHOOD_USERNAME'],
    password=os.environ['ROBINHOOD_PASSWORD'],
    store_session=True,
)
print('Login successful')
"
```

If Robinhood sends a device approval push notification, open the Robinhood mobile app and tap **Approve**. The session token is saved to disk — subsequent runs reuse it automatically.

### 5. Run

```bash
source .venv/bin/activate
python main.py
```

The scheduler and Telegram bot start together. Send any message to your bot to test it. Stop with **Ctrl+C**.

## MFA / 2FA

| Setup | What to put in `ROBINHOOD_MFA_CODE` |
|---|---|
| No 2FA | Leave blank |
| Authenticator app (TOTP) | The base32 secret key shown during setup |
| Robinhood push approval | Leave blank — approve on the app once, then `store_session=True` handles the rest |

## Project structure

```
finance_agent/
├── agent/
│   ├── client.py       MCP client + Claude tool-calling loop
│   └── prompts.py      Morning and evening prompt templates
├── mcp_server/
│   ├── server.py       Custom MCP server entry point
│   ├── tools/
│   │   ├── portfolio.py
│   │   ├── prices.py
│   │   └── news.py
│   └── resources/
│       └── historical.py
├── scheduler/
│   └── jobs.py         APScheduler cron job definitions
├── tg/
│   └── bot.py          Telegram bot send + receive
├── config.py           Environment variable loading + Robinhood login
├── main.py             Entry point
├── requirements.txt
└── .env.example
```

# Finance Portfolio Notification Agent

A personal finance assistant that monitors your Robinhood portfolio and delivers AI-generated briefings to Telegram. Powered by Claude AI and the Model Context Protocol (MCP).

## What it does

- **9am weekdays** — sends a morning briefing: portfolio value, overnight price moves, and relevant news
- **4pm weekdays** — sends an evening summary: day's P&L, top gainer/loser, and 30-day trend context
- **On demand** — message the Telegram bot any time to ask ad-hoc questions about your portfolio

## Architecture

```
main.py
├── scheduler/jobs.py        APScheduler cron jobs (9am, 4pm)
├── telegram/bot.py          Telegram bot (inbound + outbound)
└── agent/client.py          Claude tool-calling loop
        │
        └── MCP subprocess
                mcp_server/server.py
                ├── tools/portfolio.py      get_portfolio
                ├── tools/prices.py         get_price_changes
                ├── tools/news.py           get_relevant_news
                └── resources/historical.py historical_prices (30-day OHLCV)
```

The agent client spawns the MCP server as a subprocess over stdio. Claude calls tools via the MCP protocol; the server fetches live data from Robinhood and returns it as JSON.

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
│   ├── server.py       MCP server (tools, resources, prompts)
│   ├── tools/
│   │   ├── portfolio.py
│   │   ├── prices.py
│   │   └── news.py
│   └── resources/
│       └── historical.py
├── scheduler/
│   └── jobs.py         APScheduler cron job definitions
├── telegram/
│   └── bot.py          Telegram bot send + receive
├── config.py           Environment variable loading + Robinhood login
├── main.py             Entry point
├── requirements.txt
└── .env.example
```

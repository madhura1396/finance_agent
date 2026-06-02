"""
config.py

Central configuration module for the Finance Portfolio Notification Agent.

All environment variables are read here and exposed as typed Python constants.
Every other module imports from this file — no module should call os.environ
directly. This makes it easy to see all required configuration in one place
and to swap values for testing.

Required environment variables (copy .env.example to .env and fill in values):
  ANTHROPIC_API_KEY       — Anthropic API key for Claude
  ROBINHOOD_USERNAME      — Robinhood account email
  ROBINHOOD_PASSWORD      — Robinhood account password
  ROBINHOOD_MFA_CODE      — TOTP secret or static MFA code for Robinhood 2FA
  TELEGRAM_BOT_TOKEN      — Token from @BotFather on Telegram
  TELEGRAM_CHAT_ID        — Numeric chat ID to send messages to
  WATCHLIST_SYMBOLS       — Comma-separated symbols, e.g. "AAPL,TSLA,NVDA"
  TIMEZONE                — IANA timezone string, e.g. "America/New_York"
  CLAUDE_MODEL            — Claude model ID, e.g. "claude-opus-4-7"
  MAX_TOKENS              — Max tokens for Claude responses, e.g. "1024"
  MCP_SERVER_COMMAND      — Shell command to launch the MCP server,
                            e.g. "python -m mcp_server.server"
"""

import os
from dotenv import load_dotenv

# Load variables from a .env file in the project root (if present).
# In production, set environment variables directly instead.
load_dotenv()


# ---------------------------------------------------------------------------
# Anthropic / Claude
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
"""Anthropic API key. Required. Raises KeyError on startup if missing."""

CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-opus-4-7")
"""Claude model ID to use for all agent calls. Defaults to claude-opus-4-7."""

MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1024"))
"""Maximum tokens allowed in a single Claude response."""


# ---------------------------------------------------------------------------
# Robinhood
# ---------------------------------------------------------------------------

ROBINHOOD_USERNAME: str = os.environ["ROBINHOOD_USERNAME"]
"""Robinhood account email address."""

ROBINHOOD_PASSWORD: str = os.environ["ROBINHOOD_PASSWORD"]
"""Robinhood account password."""

ROBINHOOD_MFA_CODE: str = os.getenv("ROBINHOOD_MFA_CODE", "")
"""
Robinhood MFA code. Can be either:
  - A static numeric code (if you disabled TOTP)
  - A TOTP secret for generating time-based codes (requires pyotp)
Leave empty if Robinhood does not require MFA for this account.
"""


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
"""Telegram bot token from @BotFather."""

TELEGRAM_CHAT_ID: str = os.environ["TELEGRAM_CHAT_ID"]
"""
Numeric Telegram chat ID to send scheduled messages to.
To find your chat ID: message @userinfobot on Telegram.
"""


# ---------------------------------------------------------------------------
# Agent / MCP
# ---------------------------------------------------------------------------

MCP_SERVER_COMMAND: list[str] = os.getenv(
    "MCP_SERVER_COMMAND", "python -m mcp_server.server"
).split()
"""
Shell command split into a list for use with StdioServerParameters.
Example: ["python", "-m", "mcp_server.server"]
"""

WATCHLIST_SYMBOLS: list[str] = [
    s.strip().upper()
    for s in os.getenv("WATCHLIST_SYMBOLS", "").split(",")
    if s.strip()
]
"""
List of stock symbols to include in historical price data and as a fallback
when the portfolio cannot be fetched. Populated from WATCHLIST_SYMBOLS env var.
"""


# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------

TIMEZONE: str = os.getenv("TIMEZONE", "America/New_York")
"""
IANA timezone string for APScheduler cron triggers.
Defaults to Eastern time (US market hours).
"""


# ---------------------------------------------------------------------------
# Robinhood login helper
# ---------------------------------------------------------------------------

def robinhood_login() -> None:
    """
    Authenticate with Robinhood using the credentials in this module.

    Called once at MCP server startup so all subsequent tool calls share
    the same authenticated session. robin_stocks stores the session token
    in memory for the lifetime of the process.

    Receives:
        Nothing — reads ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD,
                  and ROBINHOOD_MFA_CODE from this module's constants.

    Returns:
        Nothing — raises an exception if authentication fails.
    """

    import logging
    import sys
    import robin_stocks.robinhood as rh

    logger = logging.getLogger(__name__)

    mfa_code = ROBINHOOD_MFA_CODE
    if len(mfa_code) > 6:
        import pyotp
        mfa_code = pyotp.TOTP(mfa_code).now()

    # robin_stocks prints progress messages to stdout, which corrupts the MCP
    # stdio JSON-RPC stream. Redirect stdout to stderr during login only.
    _real_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        rh.login(
            username=ROBINHOOD_USERNAME,
            password=ROBINHOOD_PASSWORD,
            mfa_code=mfa_code or None,
            store_session=True,
        )
    finally:
        sys.stdout = _real_stdout

    logger.info("Robinhood authentication successful for %s", ROBINHOOD_USERNAME)

"""
mcp_server/server.py

The MCP server for the Finance Portfolio Notification Agent.

This file is the single source of truth for everything the MCP protocol
exposes to the agent client. It uses the official Anthropic MCP Python SDK
(the `mcp` package) to register:

  Tools (actions Claude can ask the server to execute):
    - get_portfolio          → mcp_server/tools/portfolio.py
    - get_price_changes      → mcp_server/tools/prices.py
    - get_relevant_news      → mcp_server/tools/news.py

  Resources (read-only data Claude can request at any time):
    - historical_prices      → mcp_server/resources/historical.py

  Prompts (reusable instruction templates Claude receives at job start):
    - morning_briefing       → defined inline below (content from agent/prompts.py)
    - evening_summary        → defined inline below (content from agent/prompts.py)

The server communicates with the agent client over stdio transport, meaning
the client spawns this process and speaks the MCP JSON-RPC protocol over
stdin/stdout. No HTTP server or port is involved.
"""

import json
from typing import Any

# Official Anthropic MCP Python SDK imports
# `mcp` is the top-level package installed via: pip install mcp
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# Internal tool implementations
from mcp_server.tools.portfolio import get_portfolio
from mcp_server.tools.prices import get_price_changes
from mcp_server.tools.news import get_relevant_news

# Internal resource implementation
from mcp_server.resources.historical import get_historical_prices

# Prompt templates
from agent.prompts import MORNING_BRIEFING_TEMPLATE, EVENING_SUMMARY_TEMPLATE

# Config — used for Robinhood login before serving requests
import config


# ---------------------------------------------------------------------------
# Server instantiation
# ---------------------------------------------------------------------------

# The Server object is the core MCP SDK primitive.
# Its name is sent to the client during the MCP handshake (initialize request).
app = Server("finance-portfolio-agent")


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """
    Called by the MCP SDK when the client sends a tools/list request.
    Returns metadata about every tool this server exposes so the client
    can forward those definitions to Claude as available tools.

    Receives:
        Nothing (called by the SDK framework automatically)

    Returns:
        list[types.Tool]: Each Tool carries a name, description, and
        inputSchema (a JSON Schema dict describing the tool's parameters).
    """

    return [
        types.Tool(
            name="get_portfolio",
            description=(
                "Fetches the user's current Robinhood portfolio. "
                "Returns all open positions with symbol, quantity, average buy price, "
                "current price, current value, and unrealized P&L."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="get_price_changes",
            description=(
                "Fetches today's price change (absolute and percentage) "
                "for a given list of stock ticker symbols."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of uppercase stock ticker symbols, e.g. ['AAPL', 'TSLA']",
                    }
                },
                "required": ["symbols"],
            },
        ),
        types.Tool(
            name="get_relevant_news",
            description=(
                "Fetches recent news articles from Robinhood relevant to "
                "a given list of stock ticker symbols."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of uppercase stock ticker symbols, e.g. ['AAPL', 'MSFT']",
                    }
                },
                "required": ["symbols"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """
    Called by the MCP SDK when Claude asks the server to execute a tool.
    Dispatches the call to the correct implementation module and returns
    the result serialized as JSON inside a TextContent block.

    Receives:
        name (str):               The tool name Claude requested (must match a
                                  name returned by list_tools above).
        arguments (dict[str, Any]): The arguments Claude passed, validated
                                    against the tool's inputSchema.

    Returns:
        list[types.TextContent]: A single-element list whose TextContent
        wraps the JSON-serialized result string. MCP requires a list here.
    """

    if name == "get_portfolio":
        # TODO: Call get_portfolio() (no arguments)
        # Wrap result with json.dumps and return as TextContent
        result = get_portfolio()

    elif name == "get_price_changes":
        # TODO: Extract "symbols" from arguments dict
        # Call get_price_changes(symbols=arguments["symbols"])
        # Wrap result with json.dumps and return as TextContent
        symbols: list[str] = arguments["symbols"]
        result = get_price_changes(symbols=symbols)

    elif name == "get_relevant_news":
        # TODO: Extract "symbols" from arguments dict
        # Call get_relevant_news(symbols=arguments["symbols"])
        # Wrap result with json.dumps and return as TextContent
        symbols: list[str] = arguments["symbols"]
        result = get_relevant_news(symbols=symbols)

    else:
        # TODO: Raise a clear error for unknown tool names so the SDK
        # can return a proper MCP error response to the client
        raise ValueError(f"Unknown tool: {name!r}")

    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]


# ---------------------------------------------------------------------------
# Resource registration
# ---------------------------------------------------------------------------

@app.list_resources()
async def list_resources() -> list[types.Resource]:
    """
    Called by the MCP SDK when the client sends a resources/list request.
    Advertises the historical_prices resource so the agent client can read it.

    Receives:
        Nothing (called by the SDK framework automatically)

    Returns:
        list[types.Resource]: Each Resource carries a uri, name, description,
        and mimeType. The URI is the stable identifier the client uses when
        calling read_resource.
    """

    return [
        types.Resource(
            uri="finance://historical_prices",
            name="historical_prices",
            description=(
                "Cached historical daily OHLCV price data for the last 30 days "
                "for all symbols currently in the user's portfolio."
            ),
            mimeType="application/json",
        )
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    """
    Called by the MCP SDK when the agent client requests a resource by URI.
    Fetches or returns cached historical price data and serializes it as JSON.

    Receives:
        uri (str): The URI the client requested. Must match a URI from list_resources.

    Returns:
        str: JSON-serialized resource content. The MCP SDK wraps this in the
             appropriate protocol response automatically.
    """

    if uri == "finance://historical_prices":
        portfolio = get_portfolio()
        symbols = [p["symbol"] for p in portfolio.get("positions", [])]
        if not symbols:
            symbols = config.WATCHLIST_SYMBOLS
        result = get_historical_prices(symbols=symbols)
        return json.dumps(result, indent=2)

    else:
        raise ValueError(f"Unknown resource URI: {uri!r}")


# ---------------------------------------------------------------------------
# Prompt registration
# ---------------------------------------------------------------------------

@app.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    """
    Called by the MCP SDK when the client sends a prompts/list request.
    Advertises the two scheduled-job instruction templates.

    Receives:
        Nothing (called by the SDK framework automatically)

    Returns:
        list[types.Prompt]: Each Prompt carries a name and description.
        Arguments let callers customize the rendered template at call time.
    """

    return [
        types.Prompt(
            name="morning_briefing",
            description=(
                "Instruction template for the 9am morning briefing job. "
                "Instructs Claude to retrieve the portfolio, check price changes, "
                "scan relevant news, and produce a concise morning summary."
            ),
            arguments=[
                types.PromptArgument(
                    name="date",
                    description="Today's date in YYYY-MM-DD format",
                    required=False,
                )
            ],
        ),
        types.Prompt(
            name="evening_summary",
            description=(
                "Instruction template for the 4pm evening summary job. "
                "Instructs Claude to compare the day's performance against "
                "opening positions and summarize the day's P&L and key news."
            ),
            arguments=[
                types.PromptArgument(
                    name="date",
                    description="Today's date in YYYY-MM-DD format",
                    required=False,
                )
            ],
        ),
    ]


@app.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
    """
    Called by the MCP SDK when the client requests a specific prompt by name.
    Renders the prompt template with any provided arguments and returns it
    as a sequence of MCP messages for Claude to use as its initial context.

    Receives:
        name (str):                       The prompt name requested.
        arguments (dict[str, str] | None): Optional template variables
                                           (e.g. {"date": "2025-05-27"}).

    Returns:
        types.GetPromptResult: Contains a description and a list of
        PromptMessage objects. Each message has a role ("user" or "assistant")
        and a TextContent payload.
    """

    date_str: str = (arguments or {}).get("date", "today")

    if name == "morning_briefing":
        # TODO: Render MORNING_BRIEFING_TEMPLATE with date_str substituted
        # Return a GetPromptResult with role="user" and the rendered text
        rendered = MORNING_BRIEFING_TEMPLATE.format(date=date_str)

    elif name == "evening_summary":
        # TODO: Render EVENING_SUMMARY_TEMPLATE with date_str substituted
        # Return a GetPromptResult with role="user" and the rendered text
        rendered = EVENING_SUMMARY_TEMPLATE.format(date=date_str)

    else:
        raise ValueError(f"Unknown prompt: {name!r}")

    return types.GetPromptResult(
        description=f"Finance agent prompt: {name}",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text=rendered),
            )
        ],
    )


# ---------------------------------------------------------------------------
# Server entry point
# ---------------------------------------------------------------------------

async def run() -> None:
    """
    Start the MCP server and begin listening for client messages over stdio.

    This coroutine:
    1. Authenticates with Robinhood once so all tool calls share a session
    2. Wraps the `app` Server instance with the stdio_server context manager
    3. Hands control to the MCP SDK event loop which routes incoming JSON-RPC
       messages to the registered handlers above

    Receives:
        Nothing

    Returns:
        Nothing — runs until the client process closes stdin
    """

    config.robinhood_login()

    # stdio_server is the MCP SDK utility that wires the Server to stdin/stdout.
    # It yields (read_stream, write_stream) which app.run() consumes.
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )

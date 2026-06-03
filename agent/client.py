"""
agent/client.py

The agent client that:
  1. Spawns the MCP server as a subprocess and connects to it via stdio transport
  2. Asks the MCP server for its available tools on startup
  3. Converts MCP tool definitions into the format Anthropic's Claude API expects
  4. Runs a tool-calling loop: sends a prompt to Claude, executes any tool calls
     Claude requests via the MCP server, feeds results back, repeats until Claude
     returns a plain text response with no further tool calls
  5. Delivers the final text response to Telegram

This is the orchestration hub of the agent. It does not contain business logic —
it wires together the MCP server, the Claude API, and the Telegram sender.
"""

import asyncio
import json
from typing import Any

import anthropic

# Official MCP SDK client primitives
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from mcp import types as mcp_types

import config
from telegram.bot import send_message


# ---------------------------------------------------------------------------
# MCP ↔ Claude tool format conversion
# ---------------------------------------------------------------------------

def mcp_tool_to_claude_tool(mcp_tool: mcp_types.Tool) -> dict[str, Any]:
    """
    Convert one MCP Tool definition into the dict format that the
    Anthropic Claude API accepts in its `tools` parameter.

    MCP tools carry: name, description, inputSchema (JSON Schema dict)
    Claude tools expect: {"name": str, "description": str, "input_schema": dict}

    Receives:
        mcp_tool (mcp_types.Tool): A tool definition as returned by
                                   the MCP server's tools/list response.

    Returns:
        dict[str, Any]: A Claude-compatible tool definition dict with keys
                        "name", "description", and "input_schema".
    """

    return {
        "name": mcp_tool.name,
        "description": mcp_tool.description,
        "input_schema": mcp_tool.inputSchema,
    }


# ---------------------------------------------------------------------------
# Core agent loop
# ---------------------------------------------------------------------------

async def run_agent(prompt: str) -> str:
    """
    Execute one full agent session: connect to the MCP server, run the
    Claude tool-calling loop, and return the final text answer.

    The tool-calling loop works as follows:
      - Send the prompt to Claude with all available tools listed.
      - If Claude's response contains tool_use blocks, execute each tool
        via the MCP server, collect results, and send them back to Claude
        as tool_result messages.
      - Repeat until Claude returns a response whose stop_reason is "end_turn"
        (meaning Claude produced a final answer with no further tool calls).

    Receives:
        prompt (str): The full instruction text to send as the opening
                      user message. This comes from the morning_briefing or
                      evening_summary prompt template, or from a Telegram user.

    Returns:
        str: The final plain-text answer produced by Claude after all
             tool calls have been resolved.
    """

    import os
    from pathlib import Path
    from mcp.client.stdio import StdioServerParameters

    _project_dir = str(Path(__file__).parent.parent)

    server_params = StdioServerParameters(
        command=config.MCP_SERVER_COMMAND[0],
        args=config.MCP_SERVER_COMMAND[1:],
        env=os.environ.copy(),
        cwd=_project_dir,
    )

    _errlog = open("/tmp/mcp_server_stderr.log", "a")

    async with stdio_client(server_params, errlog=_errlog) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_response = await session.list_tools()
            mcp_tools = tools_response.tools
            claude_tools = [mcp_tool_to_claude_tool(t) for t in mcp_tools]

            client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]

            while True:
                response = client.messages.create(
                    model=config.CLAUDE_MODEL,
                    max_tokens=config.MAX_TOKENS,
                    tools=claude_tools,
                    messages=messages,
                )

                if response.stop_reason == "end_turn":
                    for block in response.content:
                        if hasattr(block, "text"):
                            return block.text
                    return ""

                if response.stop_reason == "tool_use":
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            tool_response = await session.call_tool(
                                name=block.name,
                                arguments=block.input,
                            )
                            result_text = ""
                            for content_block in tool_response.content:
                                if hasattr(content_block, "text"):
                                    result_text += content_block.text
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result_text,
                            })

                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": tool_results})


# ---------------------------------------------------------------------------
# Convenience wrapper
# ---------------------------------------------------------------------------

def run_agent_sync(prompt: str) -> str:
    """
    Synchronous wrapper around run_agent() for use by APScheduler jobs and
    the Telegram bot handler, both of which operate in non-async contexts.

    Receives:
        prompt (str): The instruction prompt to pass to run_agent().

    Returns:
        str: The final answer string from Claude.
    """

    return asyncio.run(run_agent(prompt))

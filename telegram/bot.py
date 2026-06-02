"""
telegram/bot.py

Implements the Telegram bot that serves two roles:

  1. Delivery channel: send_message() is called by scheduled jobs and the
     agent client to push text to a specific Telegram chat.

  2. On-demand interface: the bot listens for incoming messages from the user,
     passes them to run_agent_sync(), and replies with Claude's response.
     This lets the user ask ad-hoc questions like "Should I sell NVDA today?"
     at any time without waiting for a scheduled job.

Uses the python-telegram-bot library's Application class with the
ApplicationBuilder pattern and a plain MessageHandler for text messages.

Important: the bot's polling loop is blocking. main.py starts it last,
after the scheduler is already running in its background thread.
"""

import asyncio
import logging
from telegram import Bot, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Outbound: send a message to the configured chat
# ---------------------------------------------------------------------------

async def send_message_async(text: str) -> None:
    """
    Send a text message to the Telegram chat configured in config.TELEGRAM_CHAT_ID.

    This async version is used when already inside an async context (e.g. from
    within the bot's own message handler). For use from synchronous scheduler
    jobs, use the sync wrapper send_message() below.

    Receives:
        text (str): The message body to send. Telegram supports up to 4096
                    characters per message; longer texts must be split.

    Returns:
        Nothing — the message is delivered as a side effect.
    """

    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    chunk_size = 4096
    for i in range(0, max(len(text), 1), chunk_size):
        await bot.send_message(chat_id=config.TELEGRAM_CHAT_ID, text=text[i:i + chunk_size])


def send_message(text: str) -> None:
    """
    Synchronous wrapper around send_message_async() for use by APScheduler jobs,
    which run in a plain thread without an event loop.

    Receives:
        text (str): The message body to send.

    Returns:
        Nothing
    """

    asyncio.run(send_message_async(text))


# ---------------------------------------------------------------------------
# Inbound: handle messages from the user
# ---------------------------------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Telegram MessageHandler callback. Called whenever the user sends the bot
    a text message. Passes the message to the agent and replies with the result.

    Receives:
        update  (Update):                   The incoming Telegram update object.
                                            update.message.text contains the user's text.
        context (ContextTypes.DEFAULT_TYPE): The handler context (unused here).

    Returns:
        Nothing — replies are sent via update.message.reply_text() as a side effect.
    """

    user_text = update.message.text if update.message else None
    if not user_text:
        return

    await update.message.reply_text("Thinking…")

    try:
        from agent.client import run_agent_sync
        response = run_agent_sync(prompt=user_text)
        await update.message.reply_text(response)
    except Exception:
        logger.exception("handle_message failed")
        await update.message.reply_text("Sorry, something went wrong. Please try again.")


# ---------------------------------------------------------------------------
# Bot factory
# ---------------------------------------------------------------------------

def create_bot() -> Application:
    """
    Build and return a configured python-telegram-bot Application instance
    with the message handler registered but the polling loop not yet started.

    Receives:
        Nothing — reads config.TELEGRAM_BOT_TOKEN from the environment via config.py

    Returns:
        Application: A ready-to-run bot application. The caller starts polling
                     by calling application.run_polling() in main.py.
    """

    application = (
        ApplicationBuilder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .build()
    )

    # Register a handler for all plain text messages (excluding commands)
    # filters.TEXT & ~filters.COMMAND means: text messages that are not /commands
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # TODO: Optionally add a /start command handler that sends a welcome message
    # explaining what the bot does and what commands are available

    # TODO: Optionally add a /run_morning and /run_evening command handler
    # so the user can manually trigger the agent jobs on demand

    return application

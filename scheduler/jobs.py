"""
scheduler/jobs.py

Defines the two scheduled jobs that drive the agent automatically:
  - morning_briefing_job: runs at 9:00 AM local time, Monday–Friday
  - evening_summary_job:  runs at 4:00 PM local time, Monday–Friday

Uses APScheduler's BackgroundScheduler with a cron trigger so both jobs
run inside the same process as the Telegram bot, without needing a separate
worker process.

Each job:
  1. Fetches the appropriate prompt from the MCP server (or uses the
     locally defined template directly — see implementation note below)
  2. Passes the prompt to run_agent_sync() to get Claude's response
  3. Calls send_message() to push the response to Telegram

Implementation note on prompt sourcing:
  The MCP server exposes prompts as a protocol feature. In the scheduled
  job context we can either:
    Option A: Call run_agent_sync() with the raw template from agent/prompts.py
              (simpler — skips the MCP prompts/get step)
    Option B: Inside run_agent(), first call session.get_prompt() to retrieve
              the rendered template from the MCP server, then use it as the
              opening user message (fully MCP-native)
  The placeholder below uses Option A. Swap to Option B when implementing.
"""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)
from apscheduler.triggers.cron import CronTrigger

from agent.client import run_agent_sync
from agent.prompts import MORNING_BRIEFING_TEMPLATE, EVENING_SUMMARY_TEMPLATE
from telegram.bot import send_message
import config


def morning_briefing_job() -> None:
    """
    Execute the morning briefing agent session and deliver the result to Telegram.

    This function is called by APScheduler at 9:00 AM on weekdays.
    It renders the morning briefing prompt with today's date, passes it to
    the agent, and sends the response to the configured Telegram chat.

    Receives:
        Nothing — APScheduler calls this with no arguments

    Returns:
        Nothing — side effect is a Telegram message sent to config.TELEGRAM_CHAT_ID
    """

    try:
        today_str = datetime.today().strftime("%Y-%m-%d")
        prompt = MORNING_BRIEFING_TEMPLATE.format(date=today_str)
        response = run_agent_sync(prompt=prompt)
        send_message(text=response)
        logger.info("Morning briefing sent for %s", today_str)
    except Exception:
        logger.exception("Morning briefing job failed")


def evening_summary_job() -> None:
    """
    Execute the evening summary agent session and deliver the result to Telegram.

    This function is called by APScheduler at 4:00 PM on weekdays.
    It renders the evening summary prompt with today's date, passes it to
    the agent, and sends the response to the configured Telegram chat.

    Receives:
        Nothing — APScheduler calls this with no arguments

    Returns:
        Nothing — side effect is a Telegram message sent to config.TELEGRAM_CHAT_ID
    """

    try:
        today_str = datetime.today().strftime("%Y-%m-%d")
        prompt = EVENING_SUMMARY_TEMPLATE.format(date=today_str)
        response = run_agent_sync(prompt=prompt)
        send_message(text=response)
        logger.info("Evening summary sent for %s", today_str)
    except Exception:
        logger.exception("Evening summary job failed")


def create_scheduler() -> BackgroundScheduler:
    """
    Build and return a configured APScheduler BackgroundScheduler with both
    jobs registered but not yet started.

    The scheduler runs in a background thread so the Telegram bot's event
    loop can run concurrently in the main thread.

    Receives:
        Nothing

    Returns:
        BackgroundScheduler: A configured scheduler instance with both cron
        jobs registered. The caller must call scheduler.start() to activate it.
    """

    scheduler = BackgroundScheduler(timezone=config.TIMEZONE)

    # Register the 9am morning briefing job
    # CronTrigger fields: hour=9, minute=0, day_of_week="mon-fri"
    scheduler.add_job(
        func=morning_briefing_job,
        trigger=CronTrigger(
            hour=9,
            minute=0,
            day_of_week="mon-fri",
            timezone=config.TIMEZONE,
        ),
        id="morning_briefing",
        name="Morning Briefing — 9am weekdays",
        replace_existing=True,
    )

    # Register the 4pm evening summary job
    # CronTrigger fields: hour=16, minute=0, day_of_week="mon-fri"
    scheduler.add_job(
        func=evening_summary_job,
        trigger=CronTrigger(
            hour=16,
            minute=0,
            day_of_week="mon-fri",
            timezone=config.TIMEZONE,
        ),
        id="evening_summary",
        name="Evening Summary — 4pm weekdays",
        replace_existing=True,
    )

    return scheduler

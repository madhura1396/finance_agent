"""
main.py

Entry point for the Finance Portfolio Notification Agent.

Startup sequence:
  1. Load and validate configuration (config.py raises on missing env vars)
  2. Create the APScheduler background scheduler and register the 9am and 4pm jobs
  3. Start the scheduler in its background thread
  4. Create the Telegram bot application
  5. Start the Telegram bot's polling loop (blocking — runs until Ctrl+C)

On shutdown (KeyboardInterrupt or SIGTERM):
  - Shut down the scheduler cleanly
  - The Telegram library handles its own cleanup on exit

Note: The MCP server is NOT started here. It is spawned as a subprocess
by agent/client.py each time an agent session begins. stdio_client() in
the MCP SDK handles spawning and teardown automatically.
"""

import logging
import signal
import sys

from scheduler.jobs import create_scheduler
from tg.bot import create_bot

# Configure root logger so all modules' log messages appear in the console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def main() -> None:
    """
    Wire together the scheduler and Telegram bot, then run until interrupted.

    Receives:
        Nothing — reads all configuration from environment variables via config.py

    Returns:
        Nothing — runs indefinitely until the process receives a signal or
                  the user presses Ctrl+C
    """

    logger.info("Starting Finance Portfolio Notification Agent")

    # --- Step 1: Create and start the scheduler ----------------------------

    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started: morning_briefing (9am) and evening_summary (4pm) registered")

    # --- Step 2: Register a clean shutdown hook ----------------------------

    def shutdown() -> None:
        logger.info("Shutting down scheduler")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, lambda sig, frame: shutdown())

    # --- Step 3: Create and run the Telegram bot ---------------------------

    application = create_bot()

    try:
        application.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()

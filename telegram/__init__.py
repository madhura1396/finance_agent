"""
telegram/__init__.py

Makes telegram/ a Python package so its submodule can be imported with:
    from telegram.bot import send_message, create_bot

Note: `telegram` is also the top-level name of the python-telegram-bot package.
Python resolves local package names before site-packages, so this __init__.py
must NOT shadow that package. Keep this file empty of imports.
"""

"""
telegram/__init__.py

Makes telegram/ a Python package so its submodule can be imported with:
    from telegram.bot import send_message, create_bot

Because our package shares the name `telegram` with python-telegram-bot,
we proxy the real library here so that:
    from telegram import Bot, Update
    from telegram.ext import Application, ...
both resolve to the installed library rather than this local package.
"""

import sys as _sys
import importlib as _importlib
import os as _os

_project_dir = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))

# Temporarily remove the project root from sys.path so importlib finds
# the real python-telegram-bot in site-packages instead of this folder.
_removed = []
for _i in range(len(_sys.path) - 1, -1, -1):
    if _os.path.abspath(_sys.path[_i]) == _project_dir:
        _removed.append((_i, _sys.path.pop(_i)))

# Pop ourselves and import the real library.
_self = _sys.modules.pop("telegram", None)
_real_tg = _importlib.import_module("telegram")
_real_ext = _importlib.import_module("telegram.ext")

# Restore sys.path and our module in sys.modules.
for _i, _p in sorted(_removed):
    _sys.path.insert(_i, _p)
if _self is not None:
    _sys.modules["telegram"] = _self

# Re-export all public names from the real library into this namespace
# so `from telegram import Bot` works when telegram refers to this package.
globals().update({k: v for k, v in vars(_real_tg).items() if not k.startswith("__")})

# Register the real telegram.ext so `from telegram.ext import ...` resolves correctly.
ext = _real_ext
_sys.modules["telegram.ext"] = _real_ext

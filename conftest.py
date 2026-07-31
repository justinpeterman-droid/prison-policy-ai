"""Pytest bootstrap: put the repo root on sys.path so `backend.*` absolute
imports resolve when tests run (mirrors the PYTHONPATH=. convention used
everywhere else in this project)."""
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

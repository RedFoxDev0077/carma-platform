"""Deterministic demo data so the pipeline runs end-to-end without live portals.

Live automation is filled into each portal's `_scrape` where marked `LIVE:`.
When `settings.env == "production"` and live selectors are implemented, the demo
branch is skipped. Demo data is derived from the plate so results are stable
across a run (needed for reproducible tests / CI).
"""
from __future__ import annotations

import hashlib


def seed(plate: str) -> int:
    return int(hashlib.sha256(plate.encode()).hexdigest(), 16)


def pick(plate: str, options: list):
    return options[seed(plate) % len(options)]


def flag(plate: str, salt: str, pct: int) -> bool:
    """Return True ~pct% of the time, deterministically per plate+salt."""
    return (seed(plate + salt) % 100) < pct

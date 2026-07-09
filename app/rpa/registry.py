"""Portal registry — scrapers self-register with @register."""
from __future__ import annotations

from app.rpa.base import BaseScraper

_REGISTRY: dict[str, type[BaseScraper]] = {}


def register(cls: type[BaseScraper]) -> type[BaseScraper]:
    _REGISTRY[cls.meta.key] = cls
    return cls


def all_portals() -> dict[str, type[BaseScraper]]:
    # ensure modules are imported so decorators run
    from app.rpa import portals  # noqa: F401
    return dict(_REGISTRY)


def base_portals() -> dict[str, type[BaseScraper]]:
    return {k: v for k, v in all_portals().items() if v.meta.tier == "base"}


def paid_portals() -> dict[str, type[BaseScraper]]:
    return {k: v for k, v in all_portals().items() if v.meta.tier == "paid"}

"""Base scraper contract every portal integration implements.

Design notes
------------
* Each portal is a self-contained class registered in `registry.py`.
* Portals declare whether they are FREE or PAID and whether they need a captcha.
* The `fetch()` method returns a normalized `PortalResult` and MUST NOT raise —
  it captures its own errors so one failing portal never aborts the batch.
* Actual DOM automation lives in each subclass. Selectors depend on live sites
  and are filled in per portal; the framework here is site-agnostic.

Compliance
----------
Portals that return personal data of natural persons must place it under the
`personal` key of the result payload. The orchestrator routes anything under
`personal` to in-memory handling only (never persisted) per Ley N° 29733.
"""
from __future__ import annotations

import abc
import time
from dataclasses import dataclass
from typing import Any

from app.schemas.report import PortalResult


@dataclass(frozen=True)
class PortalMeta:
    key: str
    name: str
    free: bool
    has_captcha: bool
    # "base" portals are the free state sources we try FIRST (Fase 1 & 3);
    # "paid" portals cost money and only run after the cost gate approves.
    tier: str  # "base" | "paid"


class BaseScraper(abc.ABC):
    meta: PortalMeta

    def __init__(self, browser: Any, captcha_solver=None) -> None:
        self.browser = browser
        self.captcha = captcha_solver

    async def fetch(self, plate: str) -> PortalResult:
        """Run the scrape, timing it and never raising."""
        start = time.perf_counter()
        try:
            payload = await self._scrape(plate)
            return PortalResult(
                portal=self.meta.key,
                ok=True,
                free=self.meta.free,
                latency_ms=int((time.perf_counter() - start) * 1000),
                data=payload,
            )
        except Exception as exc:  # noqa: BLE001 — deliberately swallow per portal
            return PortalResult(
                portal=self.meta.key,
                ok=False,
                free=self.meta.free,
                latency_ms=int((time.perf_counter() - start) * 1000),
                error=f"{type(exc).__name__}: {exc}"[:250],
            )

    @abc.abstractmethod
    async def _scrape(self, plate: str) -> dict:
        """Portal-specific automation. Return a dict; put personal data under 'personal'."""
        raise NotImplementedError

    async def _new_page(self):
        ctx = await self.browser.new_context(
            locale="es-PE",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
            ),
        )
        return await ctx.new_page()

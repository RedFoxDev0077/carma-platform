"""SBS — FREE, has captcha. Total-loss insurance history + heavy accident alerts."""
from __future__ import annotations

from app.config import settings
from app.rpa.base import BaseScraper, PortalMeta
from app.rpa.portals import _demo
from app.rpa.registry import register


@register
class SbsScraper(BaseScraper):
    meta = PortalMeta(key="sbs", name="SBS", free=True, has_captcha=True, tier="base")

    async def _scrape(self, plate: str) -> dict:
        if settings.env == "production":
            return await self._scrape_live(plate)
        return {
            "total_loss_history": _demo.flag(plate, "loss", 7),
            "heavy_accident_alert": _demo.flag(plate, "accident", 10),
        }

    async def _scrape_live(self, plate: str) -> dict:
        raise NotImplementedError("SBS live automation pending")

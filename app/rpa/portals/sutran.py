"""SUTRAN — FREE, has captcha. National highway fines + retention orders."""
from __future__ import annotations

from app.config import settings
from app.rpa.base import BaseScraper, PortalMeta
from app.rpa.portals import _demo
from app.rpa.registry import register


@register
class SutranScraper(BaseScraper):
    meta = PortalMeta(key="sutran", name="SUTRAN", free=True, has_captcha=True, tier="base")

    async def _scrape(self, plate: str) -> dict:
        if settings.env == "production":
            return await self._scrape_live(plate)
        return {
            "highway_fines_soles": (_demo.seed(plate + "sutran") % 4) * 230.0,
            "retention_order": _demo.flag(plate, "retain", 5),
        }

    async def _scrape_live(self, plate: str) -> dict:
        raise NotImplementedError("SUTRAN live automation pending")

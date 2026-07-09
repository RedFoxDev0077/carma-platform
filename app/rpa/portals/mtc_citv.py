"""MTC / CITV — FREE, has captcha. Technical inspection status + mileage history."""
from __future__ import annotations

from app.config import settings
from app.rpa.base import BaseScraper, PortalMeta
from app.rpa.portals import _demo
from app.rpa.registry import register


@register
class MtcCitvScraper(BaseScraper):
    meta = PortalMeta(key="mtc_citv", name="MTC CITV", free=True, has_captcha=True, tier="base")

    async def _scrape(self, plate: str) -> dict:
        if settings.env == "production":
            return await self._scrape_live(plate)
        return {
            "citv_valid": _demo.flag(plate, "citv", 78),
            "mileage_km": 40000 + (_demo.seed(plate + "km") % 160000),
        }

    async def _scrape_live(self, plate: str) -> dict:
        raise NotImplementedError("MTC CITV live automation pending")

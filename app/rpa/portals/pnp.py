"""PNP — FREE, has captcha. Active theft reports + police warrants."""
from __future__ import annotations

from app.config import settings
from app.rpa.base import BaseScraper, PortalMeta
from app.rpa.portals import _demo
from app.rpa.registry import register


@register
class PnpScraper(BaseScraper):
    meta = PortalMeta(key="pnp", name="PNP", free=True, has_captcha=True, tier="base")

    async def _scrape(self, plate: str) -> dict:
        if settings.env == "production":
            return await self._scrape_live(plate)
        return {
            "has_theft_report": _demo.flag(plate, "theft", 4),
            "warrant": _demo.flag(plate, "warrant", 3),
        }

    async def _scrape_live(self, plate: str) -> dict:
        raise NotImplementedError("PNP live automation pending")

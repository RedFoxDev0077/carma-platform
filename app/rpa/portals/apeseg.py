"""APESEG — FREE, has captcha. SOAT status, policy type, expiration."""
from __future__ import annotations

from app.config import settings
from app.rpa.base import BaseScraper, PortalMeta
from app.rpa.portals import _demo
from app.rpa.registry import register


@register
class ApesegScraper(BaseScraper):
    meta = PortalMeta(key="apeseg", name="APESEG", free=True, has_captcha=True, tier="base")

    async def _scrape(self, plate: str) -> dict:
        if settings.env == "production":
            return await self._scrape_live(plate)
        return {
            "soat_valid": _demo.flag(plate, "soat", 82),
            "soat_company": _demo.pick(plate, ["Rimac", "Pacifico", "La Positiva", "Mapfre"]),
        }

    async def _scrape_live(self, plate: str) -> dict:
        raise NotImplementedError("APESEG live automation pending")

"""SAT Lima — FREE, has captcha. Traffic fines, capture orders, vehicle tax debt."""
from __future__ import annotations

from app.config import settings
from app.rpa.base import BaseScraper, PortalMeta
from app.rpa.portals import _demo
from app.rpa.registry import register


@register
class SatLimaScraper(BaseScraper):
    meta = PortalMeta(key="sat", name="SAT Lima", free=True, has_captcha=True, tier="base")

    async def _scrape(self, plate: str) -> dict:
        if settings.env == "production":
            return await self._scrape_live(plate)
        fines = (_demo.seed(plate + "sat") % 9) * 184.0  # UIT-based papeletas
        return {
            "fines_total_soles": fines,
            "tax_debt_soles": (_demo.seed(plate + "tax") % 5) * 120.0,
            "has_capture_order": _demo.flag(plate, "capture", 6),
        }

    async def _scrape_live(self, plate: str) -> dict:
        # LIVE: SAT consulta vehicular + reCAPTCHA solve.
        raise NotImplementedError("SAT Lima live automation pending")

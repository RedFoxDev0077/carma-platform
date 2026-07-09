"""SUNARP — PAID, has captcha. Vehicle specs, ownership, liens, prior price.

Personal data (owner/spouse names, DNI) returned under 'personal' — memory-only.
"""
from __future__ import annotations

from app.config import settings
from app.rpa.base import BaseScraper, PortalMeta
from app.rpa.portals import _demo
from app.rpa.registry import register


@register
class SunarpScraper(BaseScraper):
    meta = PortalMeta(
        key="sunarp", name="SUNARP", free=False, has_captcha=True, tier="paid"
    )

    async def _scrape(self, plate: str) -> dict:
        if settings.env == "production":
            return await self._scrape_live(plate)
        # --- demo branch ---
        brand = _demo.pick(plate, ["Toyota", "Kia", "Hyundai", "Nissan", "Suzuki"])
        model = _demo.pick(plate, ["Yaris", "Rio", "Accent", "Versa", "Swift"])
        year = 2012 + (_demo.seed(plate) % 12)
        return {
            "brand": brand,
            "model": model,
            "year": year,
            "body_style": _demo.pick(plate, ["Sedan", "Hatchback", "SUV"]),
            "fuel": _demo.pick(plate, ["gasolina", "GNV", "GLP"]),
            "has_liens": _demo.flag(plate, "lien", 15),
            "prior_purchase_price_soles": 18000 + (_demo.seed(plate) % 40000),
            "ownership_transfers_90d": 1 if _demo.flag(plate, "flip", 8) else 0,
            "personal": {  # <-- routed to memory-only handling
                "owner_name": "TITULAR REGISTRAL",
                "owner_doc": "********",
                "spouse_name": "",
            },
        }

    async def _scrape_live(self, plate: str) -> dict:
        # LIVE: authenticated SPRL session + captcha solve + deed parsing.
        raise NotImplementedError("SUNARP live automation pending authorized SPRL access")

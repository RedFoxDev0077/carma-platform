"""Parallel RPA orchestrator with cost control and Ley 29733 data routing.

Flow (implements client precisión #3):
  1. Run the FREE base portals (Fase 1 & 3) in parallel.
  2. COST GATE: if the essential base state portals are down, STOP before
     spending the S/ 6.10 paid SUNARP lookup and signal a "wait" to the user.
  3. Only if the gate passes, run the PAID portal(s).
  4. Normalize everything into ReportData. Personal data stays in the returned
     object in memory; the caller persists ONLY report.strip_personal().
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.config import settings
from app.rpa.captcha import CaptchaSolver
from app.rpa.registry import base_portals, paid_portals
from app.schemas.report import PersonalData, PortalResult, ReportData, VehicleTechnical

# Base portals whose failure means we should not spend money yet.
ESSENTIAL_BASE = {"sat", "sutran", "mtc_citv"}


@dataclass
class RpaOutcome:
    ok: bool
    report: ReportData | None
    rpa_cost_soles: float
    wait_reason: str = ""          # set when the cost gate blocks the run
    results: list[PortalResult] = None


class Orchestrator:
    def __init__(self) -> None:
        self.captcha = CaptchaSolver()

    async def run(self, plate: str) -> RpaOutcome:
        # Demo mode needs no real browser (scrapers return synthetic data), so we
        # skip launching Chromium — keeps local runs and CI lightweight.
        if settings.env != "production":
            return await self._run_all(None, plate)

        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                return await self._run_all(browser, plate)
            finally:
                await browser.close()

    async def _run_all(self, browser, plate: str) -> RpaOutcome:
        base = await self._run_group(browser, base_portals(), plate)

        # ---- COST GATE ----
        essential_ok = any(r.ok for r in base if r.portal in ESSENTIAL_BASE)
        if not essential_ok:
            return RpaOutcome(
                ok=False, report=None, rpa_cost_soles=0.0,
                wait_reason="state_portals_down", results=base,
            )

        # ---- PAID tier (only after gate passes) ----
        paid = await self._run_group(browser, paid_portals(), plate)
        cost = sum(settings.rpa_paid_cost_soles for r in paid if r.ok)

        report = self._normalize(plate, base + paid)
        return RpaOutcome(ok=True, report=report, rpa_cost_soles=cost, results=base + paid)

    async def _run_group(self, browser, portals: dict, plate: str) -> list[PortalResult]:
        sem = asyncio.Semaphore(settings.rpa_max_concurrency)

        async def _one(cls):
            async with sem:
                scraper = cls(browser, self.captcha)
                try:
                    return await asyncio.wait_for(
                        scraper.fetch(plate), timeout=settings.rpa_timeout_seconds
                    )
                except TimeoutError:
                    return PortalResult(
                        portal=cls.meta.key, ok=False, free=cls.meta.free,
                        error="timeout",
                    )

        return list(await asyncio.gather(*[_one(c) for c in portals.values()]))

    def _normalize(self, plate: str, results: list[PortalResult]) -> ReportData:
        """Merge portal payloads into JSON 1. Personal data isolated in memory."""
        tech = VehicleTechnical()
        personal = PersonalData()
        fines = 0.0

        by_key = {r.portal: r for r in results}

        def d(key: str) -> dict:
            r = by_key.get(key)
            return r.data if (r and r.ok) else {}

        s = d("sunarp")
        tech.brand = s.get("brand", "")
        tech.model = s.get("model", "")
        tech.year = s.get("year")
        tech.body_style = s.get("body_style", "")
        tech.fuel = s.get("fuel", "")
        tech.has_liens = s.get("has_liens", False)
        tech.prior_purchase_price_soles = s.get("prior_purchase_price_soles")
        tech.ownership_transfers_90d = s.get("ownership_transfers_90d", 0)
        if p := s.get("personal"):
            personal = PersonalData(**{k: v for k, v in p.items() if k in PersonalData.model_fields})

        fines += d("sat").get("fines_total_soles", 0.0)
        tech.tax_debt_soles = d("sat").get("tax_debt_soles", 0.0)
        tech.has_capture_order = d("sat").get("has_capture_order", False)
        fines += d("sutran").get("highway_fines_soles", 0.0)

        tech.citv_valid = d("mtc_citv").get("citv_valid", False)
        tech.mileage_km = d("mtc_citv").get("mileage_km")
        tech.soat_valid = d("apeseg").get("soat_valid", False)
        tech.has_theft_report = d("pnp").get("has_theft_report", False)
        tech.total_loss_history = d("sbs").get("total_loss_history", False)
        tech.fines_total_soles = round(fines, 2)

        # red-flag synthesis: (condition, label)
        signals = [
            (tech.has_liens, "Gravamen/embargo vigente"),
            (tech.has_capture_order, "Orden de captura vehicular"),
            (tech.has_theft_report, "Reporte de robo activo"),
            (tech.total_loss_history, "Historial de pérdida total"),
            (not tech.soat_valid, "SOAT no vigente"),
            (not tech.citv_valid, "Revisión técnica no vigente"),
            (bool(tech.ownership_transfers_90d), "Transferencia reciente (<90 días)"),
            (tech.fines_total_soles > 1000, "Papeletas elevadas"),
        ]
        tech.red_flags = [label for cond, label in signals if cond]

        return ReportData(
            plate=plate,
            technical=tech,
            personal=personal,
            portals=results,
        )

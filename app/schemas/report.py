"""JSON 1 — the scraped report + valuation."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PortalResult(BaseModel):
    """Normalized result of scraping a single portal."""
    portal: str
    ok: bool = False
    free: bool = True
    latency_ms: int = 0
    error: str = ""
    data: dict = Field(default_factory=dict)


class VehicleTechnical(BaseModel):
    """Non-personal technical data — safe to persist forever."""
    brand: str = ""
    model: str = ""
    year: int | None = None
    body_style: str = ""
    fuel: str = ""
    mileage_km: int | None = None

    fines_total_soles: float = 0.0
    tax_debt_soles: float = 0.0
    has_liens: bool = False
    has_capture_order: bool = False
    has_theft_report: bool = False
    soat_valid: bool = False
    citv_valid: bool = False
    total_loss_history: bool = False
    ownership_transfers_90d: int = 0
    red_flags: list[str] = Field(default_factory=list)
    prior_purchase_price_soles: float | None = None


class PersonalData(BaseModel):
    """Personal data of natural persons — Ley 29733 governed.

    Held in memory ONLY while the PDF is assembled, then discarded.
    Never persisted to the database. See ReportData.strip_personal().
    """
    owner_name: str = ""
    owner_doc: str = ""          # DNI / RUC
    spouse_name: str = ""
    extra: dict = Field(default_factory=dict)


class ReportData(BaseModel):
    """JSON 1 — full payload assembled by the RPA orchestrator."""
    plate: str
    technical: VehicleTechnical = Field(default_factory=VehicleTechnical)
    personal: PersonalData | None = None
    valuation_soles: float | None = None
    score: float | None = None                 # 1-10, filled by PDF compiler
    portals: list[PortalResult] = Field(default_factory=list)

    def strip_personal(self) -> ReportData:
        """Return a copy with all personal data removed (for persistence/analytics)."""
        return self.model_copy(update={"personal": None})

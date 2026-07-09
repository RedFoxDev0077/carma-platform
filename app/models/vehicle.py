"""Persisted technical/market vehicle data.

IMPORTANT (Ley N° 29733): only *non-personal* technical and historical data is
stored here — forever, for dashboard analytics. Personal data of natural persons
(names, DNI, spouses) is NEVER written to this table; it lives only in memory
during PDF assembly and is discarded. See app/rpa/orchestrator.py.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VehicleRecord(Base):
    __tablename__ = "vehicle_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    plate: Mapped[str] = mapped_column(String(16), index=True)

    brand: Mapped[str] = mapped_column(String(64), default="", index=True)
    model: Mapped[str] = mapped_column(String(64), default="", index=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    body_style: Mapped[str] = mapped_column(String(48), default="")
    fuel: Mapped[str] = mapped_column(String(24), default="")        # gasolina/GNV/GLP/diesel
    mileage_km: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # aggregated financial/legal signals (soles) — NOT tied to a person
    fines_total_soles: Mapped[float] = mapped_column(Float, default=0.0)
    tax_debt_soles: Mapped[float] = mapped_column(Float, default=0.0)
    has_liens: Mapped[bool] = mapped_column(Boolean, default=False)
    has_capture_order: Mapped[bool] = mapped_column(Boolean, default=False)
    has_theft_report: Mapped[bool] = mapped_column(Boolean, default=False)
    soat_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    citv_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    total_loss_history: Mapped[bool] = mapped_column(Boolean, default=False)

    ownership_transfers_90d: Mapped[int] = mapped_column(Integer, default=0)  # flipping signal
    red_flags: Mapped[list] = mapped_column(JSON, default=list)

    # full non-personal payload from the scrape run (for re-mapping / audit)
    raw_technical: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_vehicle_brand_model_year", "brand", "model", "year"),
    )

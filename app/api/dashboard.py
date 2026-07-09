"""Internal dashboard API — exactly 3 tabs (client precisión #4).

  /dashboard/finanzas     — net margins in real time
  /dashboard/control      — plate list + report link + portal semáforo
  /dashboard/inteligencia — market intelligence charts

Plus a CRUD dictionary for the 150-car knowledge base.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Order, OrderStatus, VehicleRecord, CarKnowledge, PortalHealthEvent, FeedbackVote,
)
from app.rpa.registry import all_portals

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ---------------- TAB 1: FINANZAS ----------------
@router.get("/finanzas")
def finanzas(db: Session = Depends(get_db)) -> dict:
    paid_states = (OrderStatus.REPORT_SENT, OrderStatus.CHAT_OPEN, OrderStatus.CHAT_CLOSED)
    revenue = db.scalar(select(func.coalesce(func.sum(Order.price_soles), 0.0))
                        .where(Order.status.in_(paid_states))) or 0.0
    rpa_cost = db.scalar(select(func.coalesce(func.sum(Order.rpa_cost_soles), 0.0))
                         .where(Order.status.in_(paid_states))) or 0.0
    count = db.scalar(select(func.count(Order.id)).where(Order.status.in_(paid_states))) or 0
    return {
        "reports_sold": count,
        "gross_revenue_soles": round(revenue, 2),
        "rpa_cost_soles": round(rpa_cost, 2),
        "net_margin_soles": round(revenue - rpa_cost, 2),
        "avg_margin_soles": round((revenue - rpa_cost) / count, 2) if count else 0.0,
    }


# ---------------- TAB 2: CONTROL ----------------
@router.get("/control")
def control(db: Session = Depends(get_db), limit: int = 50) -> dict:
    orders = db.scalars(select(Order).order_by(desc(Order.id)).limit(limit)).all()
    plates = [{
        "order_id": o.id, "plate": o.plate, "status": o.status.value,
        "score": o.score, "margin_soles": o.net_margin_soles,
        "report_url": f"/reports/{o.plate}.pdf" if o.pdf_path else None,
        "created_at": o.created_at.isoformat() if o.created_at else None,
    } for o in orders]

    # semáforo: portal health over last hour
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    semaforo = []
    for key, cls in all_portals().items():
        rows = db.scalars(select(PortalHealthEvent).where(
            PortalHealthEvent.portal == key, PortalHealthEvent.created_at >= since
        )).all()
        total = len(rows)
        ok = sum(1 for r in rows if r.ok)
        ratio = (ok / total) if total else None
        light = "grey" if ratio is None else "green" if ratio >= 0.9 else "amber" if ratio >= 0.5 else "red"
        semaforo.append({
            "portal": key, "name": cls.meta.name, "free": cls.meta.free,
            "light": light, "success_rate": round(ratio, 2) if ratio is not None else None,
            "samples": total,
        })
    return {"plates": plates, "semaforo": semaforo}


# ---------------- TAB 3: INTELIGENCIA DE MERCADO ----------------
@router.get("/inteligencia")
def inteligencia(db: Session = Depends(get_db)) -> dict:
    def top(col, label):
        rows = db.execute(
            select(col, func.count().label("n"))
            .where(col != "").group_by(col).order_by(desc("n")).limit(10)
        ).all()
        return [{label: r[0], "count": r[1]} for r in rows]

    top_brands = top(VehicleRecord.brand, "brand")
    top_models = top(VehicleRecord.model, "model")
    top_years = db.execute(
        select(VehicleRecord.year, func.count().label("n"))
        .where(VehicleRecord.year.is_not(None))
        .group_by(VehicleRecord.year).order_by(desc("n")).limit(10)
    ).all()

    avg_mileage = db.scalar(select(func.avg(VehicleRecord.mileage_km))) or 0
    gnv_glp = db.scalar(select(func.count()).where(VehicleRecord.fuel.in_(["GNV", "GLP"]))) or 0
    total = db.scalar(select(func.count(VehicleRecord.id))) or 0

    # top red flags across the fleet
    flag_counts: dict[str, int] = {}
    for (flags,) in db.execute(select(VehicleRecord.red_flags)).all():
        for f in (flags or []):
            flag_counts[f] = flag_counts.get(f, 0) + 1
    top_flags = sorted(
        ({"flag": k, "count": v} for k, v in flag_counts.items()),
        key=lambda x: x["count"], reverse=True,
    )[:10]

    return {
        "top_brands": top_brands,
        "top_models": top_models,
        "top_years": [{"year": y, "count": n} for y, n in top_years],
        "avg_mileage_km": int(avg_mileage),
        "gnv_glp_pct": round(gnv_glp / total * 100, 1) if total else 0.0,
        "top_red_flags": top_flags,
    }


# ---------------- CRUD dictionary (150-car base) ----------------
class KnowledgeIn(BaseModel):
    brand: str
    model: str
    year_from: int | None = None
    year_to: int | None = None
    safety_score: float | None = None
    reliability_score: float | None = None
    known_defects: list[str] = []
    recalls: list[str] = []
    market_notes: str = ""
    avg_price_soles: float | None = None
    structural_metrics: dict = {}


@router.get("/knowledge")
def list_knowledge(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(CarKnowledge).order_by(CarKnowledge.brand, CarKnowledge.model)).all()
    return [{"id": r.id, "brand": r.brand, "model": r.model,
             "safety_score": r.safety_score, "reliability_score": r.reliability_score,
             "known_defects": r.known_defects, "market_notes": r.market_notes} for r in rows]


@router.post("/knowledge")
def upsert_knowledge(item: KnowledgeIn, db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(CarKnowledge).where(
        CarKnowledge.brand.ilike(item.brand),
        CarKnowledge.model.ilike(item.model),
        CarKnowledge.year_from == item.year_from,
    ))
    if row is None:
        row = CarKnowledge(brand=item.brand, model=item.model, year_from=item.year_from)
        db.add(row)
    for k, v in item.model_dump().items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "saved": True}


@router.delete("/knowledge/{item_id}")
def delete_knowledge(item_id: int, db: Session = Depends(get_db)) -> dict:
    row = db.get(CarKnowledge, item_id)
    if not row:
        raise HTTPException(404, "not found")
    db.delete(row)
    db.commit()
    return {"deleted": True}

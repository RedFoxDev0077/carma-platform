"""End-to-end report lifecycle orchestration (the business core).

    plate -> order -> payment -> scrape (cost-gated) -> PDF -> WhatsApp -> chat

Personal data (Ley 29733): the ReportData returned by the orchestrator carries
personal data in memory only. We render the PDF from it, persist ONLY the
non-personal technical record, and let the object go out of scope. Nothing
personal ever touches the database.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import CarKnowledge, Order, OrderStatus, PortalHealthEvent, VehicleRecord
from app.pdf.compiler import render_pdf
from app.rpa.orchestrator import Orchestrator
from app.schemas.knowledge import KnowledgeEntry
from app.services.whatsapp_client import whatsapp


def create_order(db: Session, plate: str, wa_phone: str) -> Order:
    order = Order(
        plate=plate.upper().strip(),
        wa_phone=wa_phone,
        status=OrderStatus.AWAITING_PAYMENT,
        price_soles=settings.report_price_soles,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def _load_knowledge(db: Session, brand: str, model: str) -> KnowledgeEntry:
    row = db.scalar(
        select(CarKnowledge).where(
            CarKnowledge.brand.ilike(brand), CarKnowledge.model.ilike(model)
        )
    )
    if not row:
        return KnowledgeEntry.empty()
    return KnowledgeEntry(
        brand=row.brand, model=row.model, year_from=row.year_from, year_to=row.year_to,
        safety_score=row.safety_score, reliability_score=row.reliability_score,
        known_defects=row.known_defects or [], recalls=row.recalls or [],
        market_notes=row.market_notes, avg_price_soles=row.avg_price_soles,
        structural_metrics=row.structural_metrics or {},
    )


def _record_health(db: Session, results) -> None:
    for r in results or []:
        db.add(PortalHealthEvent(
            portal=r.portal, ok=r.ok, latency_ms=r.latency_ms, error=r.error or ""
        ))
    db.commit()


async def process_paid_order(db: Session, order: Order) -> None:
    """Run after payment confirmation. Scrapes, builds PDF, sends it, opens chat."""
    order.status = OrderStatus.SCRAPING
    db.commit()

    outcome = await Orchestrator().run(order.plate)
    _record_health(db, outcome.results)

    # ---- cost gate blocked: state portals down, no money spent ----
    if not outcome.ok:
        await whatsapp.send_text(
            order.wa_phone,
            "⏳ Los portales del Estado están temporalmente fuera de servicio. "
            "No te preocupes: aún no se ha realizado ningún cobro adicional y estamos "
            "reintentando. Te enviaremos tu reporte apenas se restablezcan. Gracias por tu paciencia.",
        )
        order.status = OrderStatus.PAID  # remains queued for retry
        db.commit()
        return

    report = outcome.report
    order.rpa_cost_soles = outcome.rpa_cost_soles

    knowledge = _load_knowledge(db, report.technical.brand, report.technical.model)

    # ---- render PDF from full (in-memory) report ----
    pdf_path = await render_pdf(report, knowledge)
    order.pdf_path = pdf_path
    order.score = report.score

    # ---- persist ONLY non-personal technical data (Ley 29733) ----
    _persist_vehicle(db, report.strip_personal())

    # ---- deliver via WhatsApp ----
    pdf_url = f"{settings.public_base_url}/reports/{order.plate}.pdf"
    await whatsapp.send_document(
        order.wa_phone, link=pdf_url, filename=f"CARMA_{order.plate}.pdf",
        caption=f"✅ Tu reporte CARMA para {order.plate} (Score {report.score}/10). "
                "Puedes hacerme hasta 15 preguntas sobre este auto. 🚗",
    )

    now = datetime.now(UTC)
    order.report_sent_at = now
    order.chat_expires_at = now + timedelta(minutes=settings.whatsapp_session_minutes)
    order.status = OrderStatus.CHAT_OPEN
    db.commit()
    # personal data (report.personal) is discarded as `report` goes out of scope here.


def _persist_vehicle(db: Session, report) -> None:
    t = report.technical
    db.add(VehicleRecord(
        plate=report.plate, brand=t.brand, model=t.model, year=t.year,
        body_style=t.body_style, fuel=t.fuel, mileage_km=t.mileage_km,
        fines_total_soles=t.fines_total_soles, tax_debt_soles=t.tax_debt_soles,
        has_liens=t.has_liens, has_capture_order=t.has_capture_order,
        has_theft_report=t.has_theft_report, soat_valid=t.soat_valid,
        citv_valid=t.citv_valid, total_loss_history=t.total_loss_history,
        ownership_transfers_90d=t.ownership_transfers_90d, red_flags=t.red_flags,
        raw_technical=t.model_dump(),
    ))
    db.commit()

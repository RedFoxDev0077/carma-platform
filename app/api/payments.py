"""Payment gateway webhook — confirms payment then kicks off the scrape job."""
from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order, OrderStatus
from app.services.payment import get_provider
from app.tasks.jobs import run_report

router = APIRouter(prefix="/webhook/payment", tags=["payments"])


@router.post("")
async def payment_webhook(request: Request, db: Session = Depends(get_db)):
    raw = await request.body()
    signature = request.headers.get("Stripe-Signature", "")

    result = get_provider().verify_webhook(raw, signature)
    if not result:
        return Response(status_code=400)

    order = db.get(Order, result["order_id"])
    if not order:
        return Response(status_code=404)

    if result["paid"] and order.status in (OrderStatus.AWAITING_PAYMENT, OrderStatus.NEW):
        from datetime import datetime
        order.status = OrderStatus.PAID
        order.paid_at = datetime.now(UTC)
        order.payment_ref = result["ref"]
        db.commit()
        # hand off to the worker so the webhook returns fast
        run_report.delay(order.id)

    return {"status": "ok"}

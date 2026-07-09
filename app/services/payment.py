"""Payment abstraction. Provider is swappable: Stripe today, Culqi/Izipay for Peru.

NOTE: Stripe does not onboard Peru-registered businesses. If CARMA bills from a
Peruvian entity, switch PAYMENT_PROVIDER=culqi and implement CulqiProvider.
The rest of the system depends only on this interface, not on the provider.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass

from app.config import settings


@dataclass
class PaymentLink:
    provider: str
    ref: str
    url: str


class PaymentProvider(abc.ABC):
    @abc.abstractmethod
    def create_checkout(self, order_id: int, amount_soles: float, plate: str) -> PaymentLink: ...

    @abc.abstractmethod
    def verify_webhook(self, payload: bytes, signature: str) -> dict | None:
        """Return {'order_id': int, 'paid': bool, 'ref': str} or None if invalid."""


class StripeProvider(PaymentProvider):
    def __init__(self) -> None:
        import stripe
        stripe.api_key = settings.stripe_secret_key
        self._stripe = stripe

    def create_checkout(self, order_id: int, amount_soles: float, plate: str) -> PaymentLink:
        session = self._stripe.checkout.Session.create(
            mode="payment",
            success_url=f"{settings.public_base_url}/pay/ok",
            cancel_url=f"{settings.public_base_url}/pay/cancel",
            line_items=[{
                "price_data": {
                    "currency": settings.currency.lower(),
                    "product_data": {"name": f"Reporte CARMA {plate}"},
                    "unit_amount": int(round(amount_soles * 100)),
                },
                "quantity": 1,
            }],
            metadata={"order_id": str(order_id), "plate": plate},
        )
        return PaymentLink(provider="stripe", ref=session.id, url=session.url)

    def verify_webhook(self, payload: bytes, signature: str) -> dict | None:
        try:
            event = self._stripe.Webhook.construct_event(
                payload, signature, settings.stripe_webhook_secret
            )
        except Exception:
            return None
        if event["type"] != "checkout.session.completed":
            return None
        obj = event["data"]["object"]
        return {
            "order_id": int(obj["metadata"]["order_id"]),
            "paid": obj.get("payment_status") == "paid",
            "ref": obj["id"],
        }


class MockProvider(PaymentProvider):
    """Used when no gateway is configured — keeps local/CI flows working."""
    def create_checkout(self, order_id: int, amount_soles: float, plate: str) -> PaymentLink:
        return PaymentLink(
            provider="mock", ref=f"mock_{order_id}",
            url=f"{settings.public_base_url}/pay/mock/{order_id}",
        )

    def verify_webhook(self, payload: bytes, signature: str) -> dict | None:
        import json
        try:
            data = json.loads(payload)
            return {"order_id": int(data["order_id"]), "paid": True, "ref": f"mock_{data['order_id']}"}
        except Exception:
            return None


def get_provider() -> PaymentProvider:
    if settings.payment_provider == "stripe" and settings.stripe_secret_key:
        return StripeProvider()
    # TODO: elif settings.payment_provider == "culqi": return CulqiProvider()
    return MockProvider()

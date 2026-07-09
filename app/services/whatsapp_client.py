"""Meta WhatsApp Cloud API client — text, documents (PDF), and templates."""
from __future__ import annotations

import httpx

from app.config import settings

GRAPH = "https://graph.facebook.com/v21.0"


class WhatsAppClient:
    def __init__(self) -> None:
        self.phone_id = settings.whatsapp_phone_number_id
        self.token = settings.whatsapp_token

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    async def send_text(self, to: str, body: str) -> dict:
        return await self._post({
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        })

    async def send_document(self, to: str, link: str, filename: str, caption: str = "") -> dict:
        return await self._post({
            "messaging_product": "whatsapp",
            "to": to,
            "type": "document",
            "document": {"link": link, "filename": filename, "caption": caption},
        })

    async def send_template(self, to: str, name: str, lang: str = "es", components: list | None = None) -> dict:
        tmpl = {"name": name, "language": {"code": lang}}
        if components:
            tmpl["components"] = components
        return await self._post({
            "messaging_product": "whatsapp", "to": to, "type": "template", "template": tmpl,
        })

    async def _post(self, payload: dict) -> dict:
        if not self.token or not self.phone_id:
            # not configured (e.g. local/CI) — no-op so flows stay testable
            return {"skipped": True, "reason": "whatsapp_not_configured", "payload": payload}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{GRAPH}/{self.phone_id}/messages", headers=self._headers, json=payload
            )
            r.raise_for_status()
            return r.json()


whatsapp = WhatsAppClient()

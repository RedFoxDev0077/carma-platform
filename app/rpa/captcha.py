"""Thin captcha-solver client (2captcha-style HTTP API).

Used only where a portal legitimately requires solving an image/reCAPTCHA to
complete an authorized lookup. Keyed by CAPTCHA_API_KEY.
"""
from __future__ import annotations

import asyncio

import httpx

from app.config import settings


class CaptchaSolver:
    def __init__(self, api_key: str | None = None, provider: str | None = None) -> None:
        self.api_key = api_key or settings.captcha_api_key
        self.provider = provider or settings.captcha_provider
        self._base = "https://2captcha.com"

    async def solve_recaptcha(self, site_key: str, url: str, timeout: int = 120) -> str:
        if not self.api_key:
            raise RuntimeError("CAPTCHA_API_KEY not configured")
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self._base}/in.php",
                data={
                    "key": self.api_key,
                    "method": "userrecaptcha",
                    "googlekey": site_key,
                    "pageurl": url,
                    "json": 1,
                },
            )
            req = r.json()
            if req.get("status") != 1:
                raise RuntimeError(f"captcha submit failed: {req.get('request')}")
            cid = req["request"]

            deadline = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < deadline:
                await asyncio.sleep(5)
                res = await client.get(
                    f"{self._base}/res.php",
                    params={"key": self.api_key, "action": "get", "id": cid, "json": 1},
                )
                data = res.json()
                if data.get("status") == 1:
                    return data["request"]
                if data.get("request") != "CAPCHA_NOT_READY":
                    raise RuntimeError(f"captcha error: {data.get('request')}")
        raise TimeoutError("captcha solve timed out")

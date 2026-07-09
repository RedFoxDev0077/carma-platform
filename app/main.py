"""CARMA API entrypoint."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from app import __version__
from app.api import dashboard, payments, whatsapp
from app.config import settings

app = FastAPI(
    title="CARMA API",
    version=__version__,
    docs_url="/docs" if settings.debug else None,
)

app.include_router(whatsapp.router)
app.include_router(payments.router)
app.include_router(dashboard.router)

REPORTS_DIR = Path("reports")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "env": settings.env}


@app.get("/reports/{plate}.pdf")
def serve_report(plate: str):
    """Serve a generated PDF (WhatsApp fetches this link to deliver the document)."""
    path = REPORTS_DIR / f"CARMA_{plate.upper()}.pdf"
    if not path.exists():
        return JSONResponse({"error": "not_found"}, status_code=404)
    return FileResponse(str(path), media_type="application/pdf", filename=path.name)

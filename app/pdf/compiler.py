"""Maps ReportData + knowledge into the PDF template and renders to PDF.

Rendering uses the already-installed headless Chromium (Playwright) so no extra
native PDF library is needed. The template is data-driven: every dynamic value —
score gauge, percentage indicators, radar chart, red-flag list, AI text blocks —
is injected via context keys, ready for your exact molde.
"""
from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.pdf.scoring import compute_score
from app.schemas.knowledge import KnowledgeEntry
from app.schemas.report import ReportData

TEMPLATE_DIR = Path(__file__).parent / "templates"
OUTPUT_DIR = Path("reports")

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)


def build_context(report: ReportData, knowledge: KnowledgeEntry, ai_summary: str = "") -> dict:
    """Assemble the exact data map injected into the template (client precisión #1)."""
    tech = report.technical
    breakdown = compute_score(tech, knowledge)
    report.score = breakdown.score

    # radar/axes chart inputs (0-100 scale)
    radar = {
        "Legal": 100 if not (tech.has_liens or tech.has_capture_order) else 30,
        "Seguridad": int((knowledge.safety_score or 3) / 5 * 100),
        "Mecánica": 90 if tech.citv_valid else 40,
        "Financiero": max(0, 100 - int(tech.fines_total_soles / 50)),
        "Documentos": 90 if tech.soat_valid else 45,
    }

    return {
        "plate": report.plate,
        "score": breakdown.score,
        "score_pct": int(breakdown.score * 10),
        "deductions": breakdown.deductions,
        "tech": tech.model_dump(),
        "personal": (report.personal.model_dump() if report.personal else {}),
        "knowledge": knowledge.model_dump(),
        "red_flags": tech.red_flags,
        "radar": radar,
        "radar_json": json.dumps(radar),
        "valuation": report.valuation_soles,
        "ai_summary": ai_summary,
    }


def render_html(report: ReportData, knowledge: KnowledgeEntry, ai_summary: str = "") -> str:
    ctx = build_context(report, knowledge, ai_summary)
    return _env.get_template("report.html").render(**ctx)


async def render_pdf(report: ReportData, knowledge: KnowledgeEntry, ai_summary: str = "") -> str:
    """Render the report to a PDF file and return its path."""
    from playwright.async_api import async_playwright

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    html = render_html(report, knowledge, ai_summary)
    out_path = OUTPUT_DIR / f"CARMA_{report.plate}.pdf"

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        await page.set_content(html, wait_until="networkidle")
        await page.pdf(path=str(out_path), format="A4", print_background=True)
        await browser.close()

    return str(out_path)

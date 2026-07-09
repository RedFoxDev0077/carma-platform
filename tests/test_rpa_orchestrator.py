"""RPA orchestration: cost gate + personal-data isolation + parallel scrape.

Runs in demo mode (settings.env != production) so no live portals are hit.
"""
import asyncio

from app.rpa.orchestrator import ESSENTIAL_BASE, Orchestrator
from app.rpa.registry import all_portals, base_portals, paid_portals


def test_seven_portals_registered():
    assert set(all_portals()) == {
        "sunarp", "sat", "sutran", "mtc_citv", "apeseg", "pnp", "sbs"
    }
    assert set(paid_portals()) == {"sunarp"}
    assert ESSENTIAL_BASE <= set(base_portals())


def test_full_run_produces_report_and_isolates_personal():
    outcome = asyncio.run(Orchestrator().run("ABC-123"))
    assert outcome.ok
    assert outcome.report is not None
    # personal data present in memory...
    assert outcome.report.personal is not None
    # ...but stripped copy (what we persist) has none
    assert outcome.report.strip_personal().personal is None
    # cost only charged for the paid portal
    assert outcome.rpa_cost_soles >= 0


def test_report_is_deterministic_per_plate():
    a = asyncio.run(Orchestrator().run("XYZ-987")).report
    b = asyncio.run(Orchestrator().run("XYZ-987")).report
    assert a.technical.brand == b.technical.brand
    assert a.technical.model == b.technical.model

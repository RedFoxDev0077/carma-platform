"""Scoring engine — deterministic, no external deps."""
from app.pdf.scoring import compute_score
from app.schemas.knowledge import KnowledgeEntry
from app.schemas.report import VehicleTechnical


def test_clean_vehicle_scores_high():
    tech = VehicleTechnical(soat_valid=True, citv_valid=True)
    result = compute_score(tech)
    assert result.score >= 9.5


def test_score_never_below_one():
    tech = VehicleTechnical(
        has_theft_report=True, has_capture_order=True, total_loss_history=True,
        has_liens=True, soat_valid=False, citv_valid=False,
        fines_total_soles=9000, tax_debt_soles=5000, ownership_transfers_90d=1,
    )
    result = compute_score(tech)
    assert result.score == 1.0
    assert result.deductions  # explains why


def test_theft_dominates():
    tech = VehicleTechnical(has_theft_report=True, soat_valid=True, citv_valid=True)
    assert compute_score(tech).score <= 4.0


def test_ncap_bonus_and_penalty():
    tech = VehicleTechnical(soat_valid=True, citv_valid=True)
    low = compute_score(tech, KnowledgeEntry(safety_score=2)).score
    high = compute_score(tech, KnowledgeEntry(safety_score=5)).score
    assert high > low

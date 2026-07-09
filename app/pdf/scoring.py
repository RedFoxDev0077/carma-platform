"""1-10 vehicle score.

Deterministic, explainable rule engine. Starts at 10 and deducts weighted
penalties for each risk signal, then nudges for knowledge-base safety/reliability.
The breakdown is returned so the PDF and AI can explain *why*.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.knowledge import KnowledgeEntry
from app.schemas.report import VehicleTechnical


@dataclass
class ScoreBreakdown:
    score: float
    deductions: list[tuple[str, float]] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "score": self.score,
            "deductions": [{"reason": r, "points": p} for r, p in self.deductions],
        }


# (attribute, predicate, penalty, label)
_RULES = [
    ("has_theft_report", True, 6.0, "Reporte de robo activo"),
    ("has_capture_order", True, 4.0, "Orden de captura"),
    ("total_loss_history", True, 4.0, "Pérdida total previa"),
    ("has_liens", True, 2.5, "Gravamen vigente"),
    ("soat_valid", False, 1.0, "SOAT no vigente"),
    ("citv_valid", False, 1.0, "Revisión técnica no vigente"),
]


def compute_score(tech: VehicleTechnical, knowledge: KnowledgeEntry | None = None) -> ScoreBreakdown:
    score = 10.0
    deductions: list[tuple[str, float]] = []

    for attr, trigger, penalty, label in _RULES:
        if getattr(tech, attr) == trigger:
            score -= penalty
            deductions.append((label, penalty))

    # fines: -0.5 per S/1000, capped at -2
    if tech.fines_total_soles > 0:
        pen = min(2.0, round(tech.fines_total_soles / 1000 * 0.5, 2))
        if pen:
            score -= pen
            deductions.append(("Papeletas / deudas", pen))

    # tax debt: -0.5 per S/1000, capped at -1.5
    if tech.tax_debt_soles > 0:
        pen = min(1.5, round(tech.tax_debt_soles / 1000 * 0.5, 2))
        if pen:
            score -= pen
            deductions.append(("Deuda tributaria", pen))

    # flipping signal
    if tech.ownership_transfers_90d:
        score -= 1.0
        deductions.append(("Transferencia reciente (<90 días)", 1.0))

    # knowledge base adjustment
    if knowledge and knowledge.safety_score is not None:
        if knowledge.safety_score < 3:
            score -= 1.0
            deductions.append(("Seguridad estructural baja (NCAP)", 1.0))
        elif knowledge.safety_score >= 4.5:
            score += 0.5
            deductions.append(("Bonus seguridad NCAP", -0.5))

    score = max(1.0, min(10.0, round(score, 1)))
    return ScoreBreakdown(score=score, deductions=deductions)

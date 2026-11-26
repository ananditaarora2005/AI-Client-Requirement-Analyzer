"""Requirement completeness scoring and readiness classification."""

from typing import Dict, List

from config.settings import DIMENSION_LABELS, SCORE_WEIGHTS
from models.schemas import (
    CompletenessDimensions,
    CompletenessSummary,
    MissingInformationItem,
    ReadinessStatus,
)


SEVERITY_PENALTIES: Dict[str, float] = {
    "High": 2.5,
    "Medium": 1.0,
    "Low": 0.5,
}
MAX_GAP_PENALTY = 20.0


def classify_readiness(score: float) -> ReadinessStatus:
    """Map numeric completeness score to a client-readiness status tier."""
    if score >= 78.0:
        return "Ready for Planning"
    if score >= 50.0:
        return "Needs Clarification"
    return "Incomplete"


def calculate_completeness_summary(
    dimensions: CompletenessDimensions,
    missing_information: List[MissingInformationItem],
) -> CompletenessSummary:
    """Compute weighted completeness score, gap penalty, and per-dimension breakdown."""
    dimension_dict = dimensions.model_dump()

    base_weighted = 0.0
    dimension_scores: Dict[str, int] = {}
    dimension_details: Dict[str, Dict[str, str | int]] = {}

    for key, weight in SCORE_WEIGHTS.items():
        dim_data = dimension_dict[key]
        raw_score = int(dim_data["score"])
        base_weighted += raw_score * (weight / 100.0)
        dimension_scores[key] = raw_score
        dimension_details[key] = {
            "label": DIMENSION_LABELS[key],
            "weight": weight,
            "score": raw_score,
            "evidence": str(dim_data.get("evidence", "")).strip(),
            "gap_note": str(dim_data.get("gap_note", "")).strip(),
        }

    raw_penalty = sum(
        SEVERITY_PENALTIES.get(item.severity, 1.0) for item in missing_information
    )
    gap_penalty = round(min(MAX_GAP_PENALTY, raw_penalty), 1)

    overall_score = round(max(0.0, min(100.0, base_weighted - gap_penalty)), 1)
    readiness = classify_readiness(overall_score)

    return CompletenessSummary(
        overall_score=overall_score,
        base_weighted_score=round(base_weighted, 1),
        gap_penalty=gap_penalty,
        readiness_status=readiness,
        dimension_scores=dimension_scores,
        dimension_details=dimension_details,
    )

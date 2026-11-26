"""Pydantic v2 schemas for structured AI outputs and database records."""

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


PriorityLevel = Literal["Must", "Should", "Could", "Won't"]
SeverityLevel = Literal["High", "Medium", "Low"]
ReadinessStatus = Literal["Ready for Planning", "Needs Clarification", "Incomplete"]


class DimensionScore(BaseModel):
    """Score and justification for one requirement completeness dimension."""

    score: int = Field(ge=0, le=100, description="Score from 0 to 100 for this dimension.")
    evidence: str = Field(default="", description="Evidence observed in client input.")
    gap_note: str = Field(default="", description="Brief note on what is missing, if any.")


class CompletenessDimensions(BaseModel):
    """Seven weighted dimensions evaluated for every requirement document."""

    business_goal: DimensionScore
    functional_scope: DimensionScore
    user_roles: DimensionScore
    non_functional: DimensionScore
    data_and_integrations: DimensionScore
    timeline_and_budget: DimensionScore
    success_criteria: DimensionScore


class FunctionalRequirement(BaseModel):
    """Single extracted functional requirement."""

    req_code: str = Field(min_length=2, max_length=20, examples=["FR-01"])
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=5)
    priority: PriorityLevel = "Should"
    category: str = Field(default="Core Feature", max_length=80)
    acceptance_criteria: str = Field(default="To be refined with client.")

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, value: str) -> str:
        """Normalize priority casing from LLM output."""
        mapping = {
            "must": "Must",
            "must have": "Must",
            "high": "Must",
            "should": "Should",
            "should have": "Should",
            "medium": "Should",
            "could": "Could",
            "could have": "Could",
            "low": "Could",
            "wont": "Won't",
            "won't": "Won't",
            "won't have": "Won't",
        }
        normalized = mapping.get(str(value).strip().lower(), "Should")
        return normalized


class NonFunctionalRequirement(BaseModel):
    """Single extracted non-functional requirement."""

    req_code: str = Field(min_length=2, max_length=20, examples=["NFR-01"])
    category: str = Field(min_length=2, max_length=80, examples=["Security"])
    requirement: str = Field(min_length=5)
    priority: SeverityLevel = "Medium"
    metric_target: str = Field(default="Define measurable SLA target.")

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_severity(cls, value: str) -> str:
        """Normalize NFR priority level."""
        mapping = {"high": "High", "critical": "High", "medium": "Medium", "low": "Low"}
        return mapping.get(str(value).strip().lower(), "Medium")


class TechStackRecommendation(BaseModel):
    """Recommended technology choice for a specific architectural layer."""

    layer: str = Field(min_length=2, max_length=80, examples=["Backend"])
    technology: str = Field(min_length=2, max_length=120, examples=["FastAPI (Python)"])
    rationale: str = Field(min_length=5)
    alternatives: List[str] = Field(default_factory=list)


class ProjectMilestone(BaseModel):
    """Phased delivery milestone for timeline and Gantt chart generation."""

    phase_number: int = Field(ge=1)
    phase_name: str = Field(min_length=2, max_length=120)
    duration_weeks: int = Field(ge=1, le=52)
    start_week: int = Field(ge=1)
    end_week: int = Field(ge=1)
    deliverables: List[str] = Field(default_factory=list)
    dependencies: str = Field(default="None")


class MissingInformationItem(BaseModel):
    """Detected ambiguity or missing specification with a client-facing question."""

    area: str = Field(min_length=2, max_length=80)
    severity: SeverityLevel = "Medium"
    missing_detail: str = Field(min_length=5)
    clarifying_question: str = Field(min_length=5)
    impact: str = Field(default="May impact scope estimation or architecture.")

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(cls, value: str) -> str:
        """Normalize severity level."""
        mapping = {"high": "High", "critical": "High", "medium": "Medium", "low": "Low"}
        return mapping.get(str(value).strip().lower(), "Medium")


class AIAnalysisPayload(BaseModel):
    """Structured output returned by the LLM analysis service."""

    executive_summary: str = Field(min_length=20)
    project_domain: str = Field(default="Software Application", max_length=100)
    target_users: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    functional_requirements: List[FunctionalRequirement] = Field(default_factory=list)
    non_functional_requirements: List[NonFunctionalRequirement] = Field(default_factory=list)
    tech_stack: List[TechStackRecommendation] = Field(default_factory=list)
    milestones: List[ProjectMilestone] = Field(default_factory=list)
    missing_information: List[MissingInformationItem] = Field(default_factory=list)
    completeness_dimensions: CompletenessDimensions


class CompletenessSummary(BaseModel):
    """Computed completeness score breakdown and readiness classification."""

    overall_score: float = Field(ge=0.0, le=100.0)
    base_weighted_score: float = Field(ge=0.0, le=100.0)
    gap_penalty: float = Field(ge=0.0, le=30.0)
    readiness_status: ReadinessStatus
    dimension_scores: Dict[str, int]
    dimension_details: Dict[str, Dict[str, str | int]]


class ProjectAnalysisRecord(BaseModel):
    """Complete persisted analysis record returned by the database layer."""

    id: Optional[int] = None
    project_title: str
    client_name: str
    engagement_type: str = "Web / SaaS Application"
    source_type: str = "raw_text"
    source_filename: Optional[str] = None
    raw_input_text: str
    executive_summary: str
    project_domain: str
    target_users: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    completeness_score: float
    readiness_status: str
    score_breakdown: CompletenessSummary
    model_used: str
    functional_requirements: List[FunctionalRequirement] = Field(default_factory=list)
    non_functional_requirements: List[NonFunctionalRequirement] = Field(default_factory=list)
    tech_stack: List[TechStackRecommendation] = Field(default_factory=list)
    milestones: List[ProjectMilestone] = Field(default_factory=list)
    missing_information: List[MissingInformationItem] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

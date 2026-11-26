"""Dataframe converters for structured requirement tables."""

from typing import List

import pandas as pd

from models.schemas import (
    FunctionalRequirement,
    MissingInformationItem,
    NonFunctionalRequirement,
    ProjectMilestone,
    TechStackRecommendation,
)


def functional_reqs_to_df(items: List[FunctionalRequirement]) -> pd.DataFrame:
    """Convert functional requirement objects into a clean Pandas DataFrame."""
    return pd.DataFrame(
        [
            {
                "ID": item.req_code,
                "Title": item.title,
                "Category": item.category,
                "Priority": item.priority,
                "Description": item.description,
                "Acceptance Criteria": item.acceptance_criteria,
            }
            for item in items
        ]
    )


def non_functional_reqs_to_df(items: List[NonFunctionalRequirement]) -> pd.DataFrame:
    """Convert non-functional requirement objects into a clean Pandas DataFrame."""
    return pd.DataFrame(
        [
            {
                "ID": item.req_code,
                "Category": item.category,
                "Priority": item.priority,
                "Requirement": item.requirement,
                "Target Metric": item.metric_target,
            }
            for item in items
        ]
    )


def tech_stack_to_df(items: List[TechStackRecommendation]) -> pd.DataFrame:
    """Convert tech stack recommendations into a Pandas DataFrame."""
    return pd.DataFrame(
        [
            {
                "Layer": item.layer,
                "Recommended Technology": item.technology,
                "Rationale": item.rationale,
                "Alternatives": ", ".join(item.alternatives) if item.alternatives else "-",
            }
            for item in items
        ]
    )


def milestones_to_df(items: List[ProjectMilestone]) -> pd.DataFrame:
    """Convert project milestones into a Pandas DataFrame."""
    return pd.DataFrame(
        [
            {
                "Phase": f"Phase {item.phase_number}",
                "Name": item.phase_name,
                "Schedule": f"Weeks {item.start_week}–{item.end_week}",
                "Duration (Wks)": item.duration_weeks,
                "Deliverables": "; ".join(item.deliverables) if item.deliverables else "-",
                "Dependencies": item.dependencies,
            }
            for item in items
        ]
    )


def missing_info_to_df(items: List[MissingInformationItem]) -> pd.DataFrame:
    """Convert missing information items into a Pandas DataFrame."""
    return pd.DataFrame(
        [
            {
                "Area": item.area,
                "Severity": item.severity,
                "Missing Detail": item.missing_detail,
                "Clarifying Question": item.clarifying_question,
                "Impact": item.impact,
            }
            for item in items
        ]
    )

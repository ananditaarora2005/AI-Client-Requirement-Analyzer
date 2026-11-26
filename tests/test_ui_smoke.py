"""Fast UI smoke tests for charts, table formatters, and Streamlit page imports."""

import pandas as pd

import app
from models.schemas import (
    FunctionalRequirement,
    MissingInformationItem,
    NonFunctionalRequirement,
    ProjectMilestone,
    TechStackRecommendation,
)
from ui.components.charts import (
    completeness_gauge_chart,
    dashboard_nfr_chart,
    dashboard_priority_chart,
    dashboard_readiness_chart,
    dimension_breakdown_chart,
    milestone_gantt_chart,
)
from ui.components.metric_cards import status_badge_html
from ui.components.tables import (
    functional_reqs_to_df,
    milestones_to_df,
    missing_info_to_df,
    non_functional_reqs_to_df,
    tech_stack_to_df,
)


def test_ui_charts_and_tables_render_cleanly() -> None:
    assert callable(app.main)

    gauge = completeness_gauge_chart(84.5, dark_mode=True)
    assert len(gauge.data) == 1

    dim_fig = dimension_breakdown_chart(
        {
            "business_goal": {"label": "Business Goal", "weight": 15, "score": 85},
            "functional_scope": {"label": "Functional Scope", "weight": 25, "score": 70},
        },
        dark_mode=True,
    )
    assert len(dim_fig.data) == 1

    milestones = [
        ProjectMilestone(
            phase_number=1,
            phase_name="Discovery",
            duration_weeks=2,
            start_week=1,
            end_week=2,
            deliverables=["Architecture Spec"],
            dependencies="None",
        )
    ]
    gantt = milestone_gantt_chart(milestones)
    assert len(gantt.data) == 1
    assert len(milestones_to_df(milestones)) == 1

    fr_df = functional_reqs_to_df(
        [
            FunctionalRequirement(
                req_code="FR-01",
                title="Login",
                description="Authenticate user via email/password.",
                priority="Must",
                category="Auth",
                acceptance_criteria="JWT issued on valid credentials.",
            )
        ]
    )
    assert len(fr_df) == 1

    nfr_df = non_functional_reqs_to_df(
        [
            NonFunctionalRequirement(
                req_code="NFR-01",
                category="Security",
                requirement="TLS 1.3 everywhere",
                priority="High",
                metric_target="100% HTTPS",
            )
        ]
    )
    assert len(nfr_df) == 1

    stack_df = tech_stack_to_df(
        [
            TechStackRecommendation(
                layer="Backend",
                technology="FastAPI",
                rationale="Typed REST API",
                alternatives=["Django"],
            )
        ]
    )
    assert len(stack_df) == 1

    gaps_df = missing_info_to_df(
        [
            MissingInformationItem(
                area="Budget",
                severity="High",
                missing_detail="No ceiling stated",
                clarifying_question="What is your target budget?",
            )
        ]
    )
    assert len(gaps_df) == 1

    assert "badge-success" in status_badge_html("Ready for Planning")
    assert len(dashboard_priority_chart(pd.DataFrame([{"priority": "Must", "count": 3}])).data) == 1
    assert len(dashboard_nfr_chart(pd.DataFrame([{"category": "Security", "count": 2}])).data) == 1
    assert len(dashboard_readiness_chart(pd.DataFrame([{"readiness_status": "Ready for Planning", "count": 1}])).data) == 1

"""Integration tests for SQLite persistence and ReportLab PDF generation."""

from pathlib import Path

from database.db_manager import DatabaseManager
from models.schemas import (
    CompletenessDimensions,
    DimensionScore,
    FunctionalRequirement,
    MissingInformationItem,
    NonFunctionalRequirement,
    ProjectAnalysisRecord,
    ProjectMilestone,
    TechStackRecommendation,
)
from services.report_generator import generate_pdf_report
from services.scoring_service import calculate_completeness_summary


def _build_sample_record() -> ProjectAnalysisRecord:
    dims = CompletenessDimensions(
        business_goal=DimensionScore(score=85, evidence="Clear goal", gap_note=""),
        functional_scope=DimensionScore(score=80, evidence="Features listed", gap_note=""),
        user_roles=DimensionScore(score=75, evidence="Roles listed", gap_note=""),
        non_functional=DimensionScore(score=70, evidence="SLA noted", gap_note=""),
        data_and_integrations=DimensionScore(score=65, evidence="CSV export", gap_note=""),
        timeline_and_budget=DimensionScore(score=60, evidence="12 weeks", gap_note="Budget unclear"),
        success_criteria=DimensionScore(score=70, evidence="3-day turnaround", gap_note=""),
    )
    gaps = [
        MissingInformationItem(
            area="Integrations",
            severity="Medium",
            missing_detail="Accounting API version not specified.",
            clarifying_question="Which QuickBooks Online plan/API tier are you using?",
            impact="Impacts connector authentication setup.",
        )
    ]
    summary = calculate_completeness_summary(dims, gaps)
    return ProjectAnalysisRecord(
        project_title="Expense Automation Portal",
        client_name="FinFlow Logistics",
        engagement_type="Web / SaaS Application",
        source_type="raw_text",
        raw_input_text="Sample client text describing expense automation requirements.",
        executive_summary="Automate receipt capture, policy validation, and reimbursement approvals.",
        project_domain="FinTech",
        target_users=["Employee", "Manager", "Finance Admin"],
        assumptions=["Cloud deployment on AWS"],
        completeness_score=summary.overall_score,
        readiness_status=summary.readiness_status,
        score_breakdown=summary,
        model_used="openai:gpt-4o-mini",
        functional_requirements=[
            FunctionalRequirement(
                req_code="FR-01",
                title="Receipt Upload & OCR",
                description="Employees upload receipts and auto-extract totals.",
                priority="Must",
                category="Claims",
                acceptance_criteria="PDF/JPG upload extracts vendor, date, and amount.",
            )
        ],
        non_functional_requirements=[
            NonFunctionalRequirement(
                req_code="NFR-01",
                category="Security",
                requirement="Encrypt stored receipts and audit logs.",
                priority="High",
                metric_target="AES-256 at rest, TLS 1.3 in transit",
            )
        ],
        tech_stack=[
            TechStackRecommendation(
                layer="Backend",
                technology="FastAPI + Python",
                rationale="Rapid API development and strong typing.",
                alternatives=["Django", "Node.js NestJS"],
            )
        ],
        milestones=[
            ProjectMilestone(
                phase_number=1,
                phase_name="Discovery & Architecture",
                duration_weeks=2,
                start_week=1,
                end_week=2,
                deliverables=["System Architecture", "DB Schema"],
                dependencies="None",
            ),
            ProjectMilestone(
                phase_number=2,
                phase_name="Core MVP Build",
                duration_weeks=4,
                start_week=3,
                end_week=6,
                deliverables=["Auth", "Expense Workflow"],
                dependencies="Phase 1",
            ),
        ],
        missing_information=gaps,
    )


def test_sqlite_crud_and_dashboard_metrics(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "test_analyzer.db")
    record = _build_sample_record()

    saved_id = db.save_analysis(record)
    assert saved_id > 0

    loaded = db.get_analysis(saved_id)
    assert loaded is not None
    assert loaded.project_title == "Expense Automation Portal"
    assert len(loaded.functional_requirements) == 1
    assert len(loaded.milestones) == 2

    df = db.list_analyses_df(search_query="FinFlow")
    assert len(df) == 1
    assert int(df.iloc[0]["fr_count"]) == 1

    metrics = db.get_dashboard_metrics()
    assert metrics["total_analyses"] == 1
    assert metrics["total_frs"] == 1
    assert metrics["avg_duration_weeks"] == 6.0

    assert db.delete_analysis(saved_id) is True
    assert db.get_analysis(saved_id) is None


def test_generate_pdf_report_produces_valid_pdf_bytes() -> None:
    record = _build_sample_record()
    pdf_bytes = generate_pdf_report(record)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1500

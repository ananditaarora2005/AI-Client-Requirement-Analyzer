"""Unit tests for completeness scoring and mocked AI analysis pipeline."""

import json
from pathlib import Path

import pytest

from config.settings import Settings
from models.schemas import (
    CompletenessDimensions,
    DimensionScore,
    MissingInformationItem,
)
from services.ai_analyzer import AIAnalysisError, _extract_json_text, analyze_requirements
from services.scoring_service import calculate_completeness_summary, classify_readiness


def _sample_dimensions(score_val: int) -> CompletenessDimensions:
    dim = DimensionScore(score=score_val, evidence="Observed", gap_note="")
    return CompletenessDimensions(
        business_goal=dim,
        functional_scope=dim,
        user_roles=dim,
        non_functional=dim,
        data_and_integrations=dim,
        timeline_and_budget=dim,
        success_criteria=dim,
    )


def test_classify_readiness_tiers() -> None:
    assert classify_readiness(82.0) == "Ready for Planning"
    assert classify_readiness(65.0) == "Needs Clarification"
    assert classify_readiness(40.0) == "Incomplete"


def test_completeness_summary_applies_bounded_penalty() -> None:
    dims = _sample_dimensions(90)
    gaps = [
        MissingInformationItem(
            area="Budget",
            severity="High",
            missing_detail="No budget cap provided.",
            clarifying_question="What is your target budget range?",
        ),
        MissingInformationItem(
            area="UX",
            severity="Low",
            missing_detail="Brand colors missing.",
            clarifying_question="Do you have brand guidelines?",
        ),
    ]
    summary = calculate_completeness_summary(dims, gaps)
    assert summary.base_weighted_score == 90.0
    assert summary.gap_penalty == 3.0
    assert summary.overall_score == 87.0
    assert summary.readiness_status == "Ready for Planning"


def test_extract_json_text_strips_markdown_fences() -> None:
    raw = '```json\n{"hello": "world"}\n```'
    assert _extract_json_text(raw) == '{"hello": "world"}'


def test_analyze_requirements_with_mocked_llm(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mock_payload = {
        "executive_summary": "Build a modern B2B analytics portal with role-based dashboards.",
        "project_domain": "SaaS Analytics",
        "target_users": ["Analyst", "Admin"],
        "assumptions": ["Cloud hosting on AWS"],
        "functional_requirements": [
            {
                "req_code": "FR-01",
                "title": "SSO Login",
                "description": "Users sign in using corporate SSO.",
                "priority": "Must",
                "category": "Auth",
                "acceptance_criteria": "Valid SAML login redirects to dashboard.",
            }
        ],
        "non_functional_requirements": [
            {
                "req_code": "NFR-01",
                "category": "Security",
                "requirement": "Encrypt data at rest and in transit.",
                "priority": "High",
                "metric_target": "AES-256 and TLS 1.3",
            }
        ],
        "tech_stack": [
            {
                "layer": "Backend",
                "technology": "FastAPI",
                "rationale": "Fast Python API with Pydantic validation.",
                "alternatives": ["Django REST"],
            }
        ],
        "milestones": [
            {
                "phase_number": 1,
                "phase_name": "Discovery & Architecture",
                "duration_weeks": 2,
                "start_week": 1,
                "end_week": 2,
                "deliverables": ["Architecture Spec"],
                "dependencies": "None",
            }
        ],
        "missing_information": [
            {
                "area": "Timeline",
                "severity": "Medium",
                "missing_detail": "Exact launch date missing.",
                "clarifying_question": "What is your target launch date?",
                "impact": "Affects sprint staffing.",
            }
        ],
        "completeness_dimensions": {
            "business_goal": {"score": 85, "evidence": "Clear objective", "gap_note": ""},
            "functional_scope": {"score": 80, "evidence": "Core features listed", "gap_note": ""},
            "user_roles": {"score": 75, "evidence": "2 roles mentioned", "gap_note": ""},
            "non_functional": {"score": 70, "evidence": "Security noted", "gap_note": ""},
            "data_and_integrations": {"score": 60, "evidence": "SSO noted", "gap_note": ""},
            "timeline_and_budget": {"score": 40, "evidence": "", "gap_note": "Budget missing"},
            "success_criteria": {"score": 65, "evidence": "KPIs implied", "gap_note": ""},
        },
    }

    monkeypatch.setattr(
        "services.ai_analyzer._call_openai_compatible",
        lambda settings, prompt: json.dumps(mock_payload),
    )

    test_settings = Settings(
        app_name="Test",
        base_dir=tmp_path,
        database_path=tmp_path / "test.db",
        exports_dir=tmp_path / "exports",
        samples_dir=tmp_path / "samples",
        llm_provider="openai",
        openai_api_key="mock-openai-key-for-unit-test",
        openai_model="gpt-4o-mini",
        openai_base_url="",
        gemini_api_key="",
        gemini_model="gemini-2.5-flash",
        max_upload_size_mb=10,
        min_input_chars=20,
        max_input_chars=50000,
        log_level="INFO",
    )

    record = analyze_requirements(
        project_title="Analytics Portal",
        client_name="Northwind",
        engagement_type="Web / SaaS Application",
        source_type="raw_text",
        raw_text="We need a B2B analytics portal with SSO login and role-based dashboards for analysts.",
        settings=test_settings,
    )

    assert record.project_title == "Analytics Portal"
    assert len(record.functional_requirements) == 1
    assert record.completeness_score > 0
    assert record.milestones[0].end_week == 2


def test_analyze_requirements_requires_api_key(tmp_path: Path) -> None:
    empty_settings = Settings(
        app_name="Test",
        base_dir=tmp_path,
        database_path=tmp_path / "test.db",
        exports_dir=tmp_path / "exports",
        samples_dir=tmp_path / "samples",
        llm_provider="openai",
        openai_api_key="",
        openai_model="gpt-4o-mini",
        openai_base_url="",
        gemini_api_key="",
        gemini_model="gemini-2.5-flash",
        max_upload_size_mb=10,
        min_input_chars=20,
        max_input_chars=50000,
        log_level="INFO",
    )
    with pytest.raises(AIAnalysisError):
        analyze_requirements(
            project_title="Portal",
            client_name="Client",
            engagement_type="Web / SaaS Application",
            source_type="raw_text",
            raw_text="Build a web portal for customer onboarding and reporting.",
            settings=empty_settings,
        )


def test_analyze_requirements_offline_demo_mode(tmp_path: Path) -> None:
    offline_settings = Settings(
        app_name="Test",
        base_dir=tmp_path,
        database_path=tmp_path / "test.db",
        exports_dir=tmp_path / "exports",
        samples_dir=tmp_path / "samples",
        llm_provider="offline_demo",
        openai_api_key="",
        openai_model="gpt-4o-mini",
        openai_base_url="",
        gemini_api_key="",
        gemini_model="gemini-2.5-flash",
        max_upload_size_mb=10,
        min_input_chars=20,
        max_input_chars=50000,
        log_level="INFO",
    )
    record = analyze_requirements(
        project_title="Clinic Appointment App",
        client_name="CareBridge Clinic",
        engagement_type="Web / SaaS Application",
        source_type="raw_text",
        raw_text=(
            "Patients need online appointment booking with doctors and SMS reminders.\n"
            "Front desk staff need a calendar view to reschedule visits and export billing."
        ),
        settings=offline_settings,
    )
    assert record.project_domain == "Healthcare"
    assert len(record.functional_requirements) >= 2
    assert len(record.milestones) >= 4
    assert record.completeness_score > 0


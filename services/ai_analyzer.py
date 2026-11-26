"""LLM integration and offline heuristic requirement analysis service."""

import json
import re
from typing import List, Optional

from google import genai
from google.genai import types as genai_types
from openai import OpenAI
from pydantic import ValidationError as PydanticValidationError

from config.settings import Settings, get_settings
from models.schemas import (
    AIAnalysisPayload,
    CompletenessDimensions,
    DimensionScore,
    FunctionalRequirement,
    MissingInformationItem,
    NonFunctionalRequirement,
    ProjectAnalysisRecord,
    ProjectMilestone,
    TechStackRecommendation,
)
from prompts.analysis_prompts import SYSTEM_PROMPT, build_analysis_user_prompt
from services.scoring_service import calculate_completeness_summary
from utils.logger import get_logger
from utils.validators import validate_project_metadata, validate_requirement_text


class AIAnalysisError(RuntimeError):
    """Raised when LLM execution or response parsing fails."""


def _extract_json_text(raw_response: str) -> str:
    """Strip markdown code fences if a model wraps JSON inside ```json ... ```."""
    cleaned = raw_response.strip()
    fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.DOTALL)
    if fenced_match:
        return fenced_match.group(1).strip()

    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return cleaned[first_brace : last_brace + 1]
    return cleaned


def _call_openai_compatible(settings: Settings, user_prompt: str) -> str:
    """Call OpenAI or an OpenAI-compatible API requesting a JSON object."""
    client_kwargs = {"api_key": settings.openai_api_key, "timeout": 90.0}
    if settings.openai_base_url:
        client_kwargs["base_url"] = settings.openai_base_url

    client = OpenAI(**client_kwargs)
    response = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = response.choices[0].message.content
    if not content:
        raise AIAnalysisError("LLM returned an empty response.")
    return content


def _call_gemini(settings: Settings, user_prompt: str) -> str:
    """Call Google Gemini API requesting JSON output."""
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=user_prompt,
        config=genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )
    text = getattr(response, "text", None)
    if not text:
        raise AIAnalysisError("Gemini returned an empty response.")
    return text


def _normalize_milestones(payload: AIAnalysisPayload) -> AIAnalysisPayload:
    """Ensure milestone phase numbers and week ranges remain internally consistent."""
    running_week = 1
    for idx, milestone in enumerate(payload.milestones, start=1):
        milestone.phase_number = idx
        if milestone.start_week < 1 or milestone.end_week < milestone.start_week:
            milestone.start_week = running_week
        milestone.end_week = milestone.start_week + milestone.duration_weeks - 1
        running_week = milestone.end_week + 1
    return payload


def _run_offline_demo_analysis(
    project_title: str,
    client_name: str,
    engagement_type: str,
    raw_text: str,
) -> AIAnalysisPayload:
    """Deterministic heuristic analyzer used when Offline Demo mode is selected."""
    lower = raw_text.lower()
    lines = [
        line.strip(" -*\t")
        for line in raw_text.splitlines()
        if len(line.strip(" -*\t")) >= 20
    ]

    # Infer domain from content keywords.
    domain = "Enterprise SaaS"
    if any(k in lower for k in ("patient", "clinic", "doctor", "medical", "hipaa", "ehr")):
        domain = "Healthcare"
    elif any(k in lower for k in ("expense", "reimbursement", "invoice", "payment", "receipt", "quickbooks")):
        domain = "FinTech"
    elif any(k in lower for k in ("cart", "checkout", "catalog", "order", "inventory")):
        domain = "E-Commerce"

    # Extract candidate feature statements from input lines.
    feature_candidates = [
        line for line in lines
        if not line.lower().startswith(("subject:", "from:", "best regards", "hi ", "action item"))
    ][:7]
    if not feature_candidates:
        feature_candidates = [
            f"Core workflow module for {project_title}",
            "Role-based user management and authentication",
            "Analytics reporting and export dashboard",
        ]

    functional_reqs: List[FunctionalRequirement] = []
    for idx, stmt in enumerate(feature_candidates, start=1):
        short_title = stmt.split(".")[0][:65].strip()
        if len(short_title) < 5:
            short_title = f"Requirement {idx}"
        priority = "Must" if idx <= 3 else ("Should" if idx <= 5 else "Could")
        functional_reqs.append(
            FunctionalRequirement(
                req_code=f"FR-{idx:02d}",
                title=short_title,
                description=stmt,
                priority=priority,
                category="Core Workflow" if idx <= 3 else "Operations & Reporting",
                acceptance_criteria=f"Verified end-to-end flow for '{short_title}' with audit logging.",
            )
        )

    nfrs: List[NonFunctionalRequirement] = [
        NonFunctionalRequirement(
            req_code="NFR-01",
            category="Security",
            requirement="Enforce role-based access control and TLS/AES encryption for sensitive records.",
            priority="High",
            metric_target="TLS 1.3 in transit, AES-256 at rest",
        ),
        NonFunctionalRequirement(
            req_code="NFR-02",
            category="Performance",
            requirement="Maintain fast API and dashboard response times under peak load.",
            priority="Medium",
            metric_target="P95 API latency < 1.5s",
        ),
        NonFunctionalRequirement(
            req_code="NFR-03",
            category="Availability",
            requirement="Ensure reliable uptime with automated health checks and backups.",
            priority="High" if "99.9" in lower else "Medium",
            metric_target="99.9% monthly uptime SLA",
        ),
        NonFunctionalRequirement(
            req_code="NFR-04",
            category="Usability",
            requirement="Responsive interface optimized for desktop and tablet workflows.",
            priority="Medium",
            metric_target="WCAG 2.1 AA baseline compliance",
        ),
    ]

    tech_stack = [
        TechStackRecommendation(
            layer="Frontend",
            technology="React + TypeScript (or Next.js)",
            rationale=f"Delivers a responsive, maintainable UI tailored to {engagement_type}.",
            alternatives=["Vue 3", "Streamlit (Rapid Internal MVP)"],
        ),
        TechStackRecommendation(
            layer="Backend",
            technology="FastAPI (Python 3.12)",
            rationale="High-performance typed REST APIs with rapid Pydantic validation and AI SDK support.",
            alternatives=["Django REST Framework", "NestJS"],
        ),
        TechStackRecommendation(
            layer="Database",
            technology="PostgreSQL",
            rationale="ACID-compliant relational storage with strong auditability and JSONB flexibility.",
            alternatives=["MySQL 8", "SQLite (Single-node MVP)"],
        ),
        TechStackRecommendation(
            layer="Authentication",
            technology="OAuth 2.0 / OIDC (Okta or Auth0)",
            rationale="Supports enterprise SSO and granular RBAC.",
            alternatives=["AWS Cognito", "Keycloak"],
        ),
        TechStackRecommendation(
            layer="Cloud / DevOps",
            technology="AWS ECS / RDS + GitHub Actions",
            rationale="Automated CI/CD pipelines, managed backups, and predictable scaling.",
            alternatives=["Google Cloud Run", "Azure App Service"],
        ),
    ]

    milestones = [
        ProjectMilestone(
            phase_number=1,
            phase_name="Discovery, UX Wireframes & Architecture",
            duration_weeks=2,
            start_week=1,
            end_week=2,
            deliverables=["Finalized SRS & Scope", "Database Schema", "Interactive Wireframes"],
            dependencies="None",
        ),
        ProjectMilestone(
            phase_number=2,
            phase_name="Core Backend, Auth & Data Layer",
            duration_weeks=3,
            start_week=3,
            end_week=5,
            deliverables=["RBAC & SSO Integration", "Core CRUD APIs", "Automated Unit Tests"],
            dependencies="Phase 1",
        ),
        ProjectMilestone(
            phase_number=3,
            phase_name="Frontend Workflows & Third-Party Integrations",
            duration_weeks=4,
            start_week=6,
            end_week=9,
            deliverables=["Primary User Workflows", "External Integrations", "Analytics Dashboard"],
            dependencies="Phase 2",
        ),
        ProjectMilestone(
            phase_number=4,
            phase_name="QA Hardening, UAT & Production Launch",
            duration_weeks=2,
            start_week=10,
            end_week=11,
            deliverables=["Security & Load Testing", "Client UAT Sign-off", "Production Deployment"],
            dependencies="Phase 3",
        ),
    ]

    has_budget = any(k in lower for k in ("$", "budget", "usd", "eur", "cost"))
    has_timeline = any(k in lower for k in ("week", "month", "q1", "q2", "q3", "q4", "launch", "deadline"))
    has_security = any(k in lower for k in ("soc 2", "hipaa", "gdpr", "encrypt", "sso", "rbac", "security"))
    has_metrics = any(k in lower for k in ("kpi", "sla", "99.", "under ", "turnaround", "target", "days"))
    has_roles = any(k in lower for k in ("admin", "manager", "employee", "patient", "doctor", "user", "staff"))
    has_integrations = any(k in lower for k in ("api", "slack", "quickbooks", "ehr", "whatsapp", "sms", "csv", "export"))

    missing_items: List[MissingInformationItem] = []
    if not has_budget:
        missing_items.append(
            MissingInformationItem(
                area="Budget",
                severity="High",
                missing_detail="No target budget range or commercial ceiling was stated.",
                clarifying_question="What is your approved budget range for Phase 1 MVP vs. future enhancements?",
                impact="Determines build vs. buy choices and phased staffing.",
            )
        )
    if not has_timeline:
        missing_items.append(
            MissingInformationItem(
                area="Timeline",
                severity="Medium",
                missing_detail="Target launch date or hard milestone deadlines are not specified.",
                clarifying_question="Are there fixed business events or compliance deadlines driving the launch date?",
                impact="Affects sprint velocity and MVP scope prioritization.",
            )
        )
    if not has_integrations or "forgot" in lower or "not sure" in lower:
        missing_items.append(
            MissingInformationItem(
                area="Integrations",
                severity="High",
                missing_detail="Third-party system APIs, vendors, or data formats require confirmation.",
                clarifying_question="Which exact external systems and API versions must be integrated in Phase 1?",
                impact="Integration complexity is a primary schedule risk.",
            )
        )
    if not has_security:
        missing_items.append(
            MissingInformationItem(
                area="Compliance",
                severity="High",
                missing_detail="Regulatory standards and data retention policies are not clearly defined.",
                clarifying_question="Which compliance frameworks (e.g., SOC 2, HIPAA, GDPR) apply to stored data?",
                impact="Impacts hosting architecture, encryption, and audit logging.",
            )
        )
    if not missing_items:
        missing_items.append(
            MissingInformationItem(
                area="Scope",
                severity="Low",
                missing_detail="Edge-case error handling and post-launch support SLAs need sign-off.",
                clarifying_question="What post-launch support hours and escalation SLAs do your teams expect?",
                impact="Helps finalize ongoing maintenance estimates.",
            )
        )

    dims = CompletenessDimensions(
        business_goal=DimensionScore(
            score=85 if len(raw_text) > 250 else 65,
            evidence="Problem context and primary objectives detected in client notes.",
            gap_note="" if len(raw_text) > 250 else "Expand on quantifiable business ROI.",
        ),
        functional_scope=DimensionScore(
            score=82 if len(functional_reqs) >= 5 else 60,
            evidence=f"Extracted {len(functional_reqs)} candidate functional workflows.",
            gap_note="Confirm Phase 1 MVP boundaries.",
        ),
        user_roles=DimensionScore(
            score=80 if has_roles else 45,
            evidence="User roles referenced in text." if has_roles else "Minimal role detail.",
            gap_note="" if has_roles else "Define explicit user personas and permissions.",
        ),
        non_functional=DimensionScore(
            score=78 if has_security else 40,
            evidence="Security/SLA indicators found." if has_security else "No explicit NFRs.",
            gap_note="" if has_security else "Specify uptime, latency, and compliance targets.",
        ),
        data_and_integrations=DimensionScore(
            score=72 if has_integrations else 40,
            evidence="Integration touchpoints mentioned." if has_integrations else "No integrations detailed.",
            gap_note="Verify external API documentation and data migration needs.",
        ),
        timeline_and_budget=DimensionScore(
            score=(45 if has_timeline else 20) + (40 if has_budget else 15),
            evidence="Timeline/budget cues evaluated from input.",
            gap_note="" if (has_budget and has_timeline) else "Clarify budget cap and target go-live date.",
        ),
        success_criteria=DimensionScore(
            score=75 if has_metrics else 40,
            evidence="Measurable operational targets identified." if has_metrics else "No KPIs stated.",
            gap_note="" if has_metrics else "Define measurable launch success metrics.",
        ),
    )

    return AIAnalysisPayload(
        executive_summary=(
            f"{client_name} requires {project_title}, a {engagement_type.lower()} in the {domain} domain. "
            f"This structured plan organizes the submitted requirements into {len(functional_reqs)} functional "
            f"capabilities, {len(nfrs)} non-functional standards, a recommended cloud stack, and an 11-week "
            "phased delivery roadmap (generated via Offline Smart Mode)."
        ),
        project_domain=domain,
        target_users=["End Users", "Operations Staff", "System Administrators"],
        assumptions=[
            "Generated using Offline Smart Mode (heuristic parser) because no live LLM API key was active.",
            "Phase 1 prioritizes core Must-Have workflows prior to secondary enhancements.",
        ],
        functional_requirements=functional_reqs,
        non_functional_requirements=nfrs,
        tech_stack=tech_stack,
        milestones=milestones,
        missing_information=missing_items,
        completeness_dimensions=dims,
    )


def analyze_requirements(
    project_title: str,
    client_name: str,
    engagement_type: str,
    source_type: str,
    raw_text: str,
    source_filename: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> ProjectAnalysisRecord:
    """Validate inputs, invoke the configured engine, score completeness, and build a record."""
    cfg = settings or get_settings()
    logger = get_logger(__name__, cfg.log_level)

    clean_title, clean_client = validate_project_metadata(project_title, client_name)
    clean_text = validate_requirement_text(
        raw_text,
        min_chars=cfg.min_input_chars,
        max_chars=cfg.max_input_chars,
    )

    if cfg.llm_provider == "offline_demo":
        logger.info("Running offline heuristic analysis (no external LLM call)")
        payload = _run_offline_demo_analysis(
            project_title=clean_title,
            client_name=clean_client,
            engagement_type=engagement_type,
            raw_text=clean_text,
        )
        payload = _normalize_milestones(payload)
    else:
        if not cfg.is_llm_configured():
            provider_hint = (
                "GEMINI_API_KEY" if cfg.llm_provider == "gemini" else "OPENAI_API_KEY"
            )
            raise AIAnalysisError(
                f"AI credentials are not configured for provider '{cfg.llm_provider}'. "
                f"Enter your {provider_hint} in the sidebar 'AI Engine Setup' panel and click "
                "'Save to .env & Apply', or select 'Offline Smart Mode (No Key)'."
            )

        user_prompt = build_analysis_user_prompt(
            project_title=clean_title,
            client_name=clean_client,
            engagement_type=engagement_type,
            raw_text=clean_text,
        )

        last_error: Optional[Exception] = None
        payload = None

        # Allow 1 automatic retry in case the LLM produces malformed JSON on the first pass.
        for attempt in range(1, 3):
            try:
                logger.info(
                    "Running requirement analysis (provider=%s, model=%s, attempt=%d)",
                    cfg.llm_provider,
                    cfg.active_model_name(),
                    attempt,
                )
                if cfg.llm_provider == "gemini":
                    raw_output = _call_gemini(cfg, user_prompt)
                else:
                    raw_output = _call_openai_compatible(cfg, user_prompt)

                json_str = _extract_json_text(raw_output)
                parsed_dict = json.loads(json_str)
                payload = AIAnalysisPayload.model_validate(parsed_dict)
                payload = _normalize_milestones(payload)
                break
            except (json.JSONDecodeError, PydanticValidationError) as exc:
                last_error = exc
                logger.warning("Structured output parse failed on attempt %d: %s", attempt, exc)
            except Exception as exc:
                logger.error("LLM API request failed: %s", exc)
                raise AIAnalysisError(
                    f"AI service request failed ({cfg.llm_provider}): {exc}"
                ) from exc

        if payload is None:
            raise AIAnalysisError(
                f"AI returned invalid structured data after retries: {last_error}"
            )

    completeness = calculate_completeness_summary(
        dimensions=payload.completeness_dimensions,
        missing_information=payload.missing_information,
    )

    return ProjectAnalysisRecord(
        project_title=clean_title,
        client_name=clean_client,
        engagement_type=engagement_type,
        source_type=source_type,
        source_filename=source_filename,
        raw_input_text=clean_text,
        executive_summary=payload.executive_summary,
        project_domain=payload.project_domain,
        target_users=payload.target_users,
        assumptions=payload.assumptions,
        completeness_score=completeness.overall_score,
        readiness_status=completeness.readiness_status,
        score_breakdown=completeness,
        model_used=f"{cfg.llm_provider}:{cfg.active_model_name()}",
        functional_requirements=payload.functional_requirements,
        non_functional_requirements=payload.non_functional_requirements,
        tech_stack=payload.tech_stack,
        milestones=payload.milestones,
        missing_information=payload.missing_information,
    )

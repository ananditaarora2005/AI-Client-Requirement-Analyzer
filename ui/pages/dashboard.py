"""Executive dashboard page displaying KPIs, analytics charts, and recent analyses."""

from typing import Callable, Optional

import streamlit as st

from database.db_manager import DatabaseManager
from ui.components.charts import (
    dashboard_nfr_chart,
    dashboard_priority_chart,
    dashboard_readiness_chart,
)
from ui.components.metric_cards import (
    KPICardData,
    render_kpi_row,
    render_page_header,
    render_section_heading,
)


def render_dashboard(
    db: DatabaseManager,
    navigate_to: Callable[[str, Optional[int]], None],
    dark_mode: bool = False,
) -> None:
    """Render the main SaaS overview dashboard."""
    header_col, action_col = st.columns([3.8, 1.2], vertical_alignment="center")
    with header_col:
        render_page_header(
            "Requirement Intelligence Dashboard",
            "Monitor requirement completeness, extracted specifications, and delivery readiness across client projects.",
        )
    with action_col:
        if st.button("⚡ New Analysis", type="primary", use_container_width=True):
            navigate_to("New Analysis", None)

    metrics = db.get_dashboard_metrics()
    total_reqs = metrics["total_frs"] + metrics["total_nfrs"]

    cards: list[KPICardData] = [
        {
            "label": "Total Analyses",
            "value": str(metrics["total_analyses"]),
            "subtitle": "Saved client project plans",
            "icon": "📁",
        },
        {
            "label": "Avg Completeness",
            "value": f"{metrics['avg_completeness']:.1f}%",
            "subtitle": f"{metrics['high_gaps']} high-severity gaps open",
            "icon": "🎯",
        },
        {
            "label": "Requirements",
            "value": str(total_reqs),
            "subtitle": f"{metrics['total_frs']} FRs  •  {metrics['total_nfrs']} NFRs",
            "icon": "📋",
        },
        {
            "label": "Avg Timeline",
            "value": f"{metrics['avg_duration_weeks']:.1f} wks",
            "subtitle": "Across phased delivery plans",
            "icon": "⏱️",
        },
    ]
    render_kpi_row(cards)
    st.markdown("<div style='height: 0.85rem;'></div>", unsafe_allow_html=True)

    if metrics["total_analyses"] == 0:
        st.markdown(
            """
            <div class="onboarding-banner">
                <div class="onboarding-title">Welcome to AI Client Requirement Analyzer</div>
                <p class="onboarding-desc">
                    Turn messy client emails, discovery call transcripts, PDFs, and Word specifications into
                    structured project plans with completeness scores, architecture stacks, milestones, and PDF reports.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        f1, f2, f3 = st.columns(3)
        with f1:
            st.markdown(
                """
                <div class="feature-card">
                    <div class="feature-card-title">1. Multi-Source Intake</div>
                    <div class="feature-card-body">Paste raw client emails or upload PDF, DOCX, and TXT requirement documents with automatic validation.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with f2:
            st.markdown(
                """
                <div class="feature-card">
                    <div class="feature-card-title">2. Architecture & Scoring</div>
                    <div class="feature-card-body">Extract FRs, NFRs, tech stacks, Gantt milestones, missing gaps, and a 7-dimension completeness score.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with f3:
            st.markdown(
                """
                <div class="feature-card">
                    <div class="feature-card-title">3. History & PDF Export</div>
                    <div class="feature-card-body">Store every project plan in SQLite, search across engagements, and download branded ReportLab PDFs.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height: 0.9rem;'></div>", unsafe_allow_html=True)
        col1, col2, _ = st.columns([1.4, 1.4, 2.2])
        with col1:
            if st.button("Start First Analysis", type="primary", use_container_width=True):
                navigate_to("New Analysis", None)
        with col2:
            if st.button("Open Analysis History", use_container_width=True):
                navigate_to("History", None)
        return

    chart_col1, chart_col2, chart_col3 = st.columns(3)
    with chart_col1:
        render_section_heading("Functional Priority Mix", "📊")
        fr_df = metrics["fr_priority_df"]
        if not fr_df.empty:
            st.plotly_chart(dashboard_priority_chart(fr_df, dark_mode=dark_mode), use_container_width=True)
        else:
            st.caption("No functional requirement data available.")

    with chart_col2:
        render_section_heading("Non-Functional Categories", "🛡️")
        nfr_df = metrics["nfr_category_df"]
        if not nfr_df.empty:
            st.plotly_chart(dashboard_nfr_chart(nfr_df, dark_mode=dark_mode), use_container_width=True)
        else:
            st.caption("No non-functional requirement data available.")

    with chart_col3:
        render_section_heading("Project Readiness", "🎯")
        readiness_df = metrics["readiness_df"]
        if not readiness_df.empty:
            st.plotly_chart(dashboard_readiness_chart(readiness_df, dark_mode=dark_mode), use_container_width=True)
        else:
            st.caption("No readiness data available.")

    st.divider()
    render_section_heading("Recent Requirement Analyses", "📑")
    recent_df = db.list_analyses_df()
    display_df = recent_df.head(8)[
        [
            "id",
            "project_title",
            "client_name",
            "project_domain",
            "completeness_score",
            "readiness_status",
            "fr_count",
            "nfr_count",
            "gap_count",
            "total_weeks",
        ]
    ].rename(
        columns={
            "id": "ID",
            "project_title": "Project Title",
            "client_name": "Client",
            "project_domain": "Domain",
            "completeness_score": "Score (%)",
            "readiness_status": "Readiness",
            "fr_count": "FRs",
            "nfr_count": "NFRs",
            "gap_count": "Gaps",
            "total_weeks": "Weeks",
        }
    )
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    options = {
        f"#{row['id']} — {row['project_title']} ({row['client_name']})": int(row["id"])
        for _, row in recent_df.head(15).iterrows()
    }
    jump_col1, jump_col2 = st.columns([3.8, 1.2], vertical_alignment="center")
    with jump_col1:
        selected_label = st.selectbox(
            "Quick-open project plan",
            options=list(options.keys()),
            label_visibility="collapsed",
        )
    with jump_col2:
        if st.button("Open Project Plan", type="primary", use_container_width=True):
            navigate_to("Analysis Details", options[selected_label])

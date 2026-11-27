"""Analysis History page with search, filtering, CSV export, PDF download, and deletion."""

from typing import Callable, Optional

import streamlit as st

from database.db_manager import DatabaseManager
from services.report_generator import generate_pdf_report
from ui.components.metric_cards import render_page_header, render_section_heading


def render_history(
    db: DatabaseManager,
    navigate_to: Callable[[str, Optional[int]], None],
) -> None:
    """Render searchable, filterable history of all saved requirement analyses."""
    render_page_header(
        "Analysis History",
        "Search, filter, compare, export, or manage previously analyzed client projects.",
    )

    f_col1, f_col2, f_col3 = st.columns([2.2, 1.3, 1.5])
    with f_col1:
        search_query = st.text_input(
            "Search by Project, Client, or Domain",
            placeholder="Type project title, client name, or domain...",
        )
    with f_col2:
        readiness_filter = st.selectbox(
            "Readiness Status",
            options=["All", "Ready for Planning", "Needs Clarification", "Incomplete"],
        )
    with f_col3:
        min_score = st.slider("Min Completeness (%)", min_value=0, max_value=100, value=0, step=5)

    df = db.list_analyses_df(
        search_query=search_query,
        min_score=float(min_score),
        readiness_filter=readiness_filter,
    )

    if df.empty:
        st.info("No analyses match the current filters.")
        if st.button("+ Start New Analysis", type="primary"):
            navigate_to("New Analysis", None)
        return

    display_df = df[
        [
            "id",
            "project_title",
            "client_name",
            "project_domain",
            "engagement_type",
            "completeness_score",
            "readiness_status",
            "fr_count",
            "nfr_count",
            "gap_count",
            "total_weeks",
            "created_at",
        ]
    ].rename(
        columns={
            "id": "ID",
            "project_title": "Project Title",
            "client_name": "Client",
            "project_domain": "Domain",
            "engagement_type": "Type",
            "completeness_score": "Score (%)",
            "readiness_status": "Readiness",
            "fr_count": "FRs",
            "nfr_count": "NFRs",
            "gap_count": "Gaps",
            "total_weeks": "Weeks",
            "created_at": "Created (UTC)",
        }
    )

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    csv_bytes = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Export Filtered History (CSV)",
        data=csv_bytes,
        file_name="requirement_analyses_history.csv",
        mime="text/csv",
    )

    st.divider()
    render_section_heading("Quick Actions on Saved Analysis", "⚡")
    options = {
        int(row["id"]): f"#{row['id']} — {row['project_title']} ({row['client_name']}) • {row['completeness_score']}%"
        for _, row in df.iterrows()
    }
    selected_id = st.selectbox(
        "Choose a saved analysis",
        options=list(options.keys()),
        format_func=lambda aid: options[aid],
    )

    a_col1, a_col2, a_col3 = st.columns([1.5, 1.5, 1.2], vertical_alignment="center")
    with a_col1:
        if st.button("📑 View Full Project Plan", type="primary", use_container_width=True):
            navigate_to("Analysis Details", selected_id)
    with a_col2:
        selected_record = db.get_analysis(selected_id)
        if selected_record:
            pdf_bytes = generate_pdf_report(selected_record)
            st.download_button(
                label="📥 Download PDF Report",
                data=pdf_bytes,
                file_name=f"analysis_{selected_id}_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
    with a_col3:
        if st.button("🗑️ Delete Selected", use_container_width=True):
            st.session_state["history_confirm_delete_id"] = selected_id

    if st.session_state.get("history_confirm_delete_id") == selected_id:
        st.warning(f"Are you sure you want to permanently delete analysis **#{selected_id}**?")
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if st.button("Yes, Delete", type="primary"):
                db.delete_analysis(selected_id)
                st.session_state.pop("history_confirm_delete_id", None)
                if st.session_state.get("selected_analysis_id") == selected_id:
                    st.session_state["selected_analysis_id"] = None
                st.success(f"Deleted analysis #{selected_id}.")
                st.rerun()
        with c2:
            if st.button("Cancel Delete"):
                st.session_state.pop("history_confirm_delete_id", None)
                st.rerun()

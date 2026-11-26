"""Detailed Project Plan & PDF Export view for a saved requirement analysis."""

from typing import Callable, Optional

import pandas as pd
import streamlit as st

from database.db_manager import DatabaseManager
from services.report_generator import generate_pdf_report
from ui.components.charts import (
    completeness_gauge_chart,
    dimension_breakdown_chart,
    milestone_gantt_chart,
)
from ui.components.metric_cards import (
    KPICardData,
    render_kpi_row,
    render_page_header,
    status_badge_html,
)
from ui.components.tables import (
    functional_reqs_to_df,
    milestones_to_df,
    missing_info_to_df,
    non_functional_reqs_to_df,
    tech_stack_to_df,
)


def render_analysis_details(
    db: DatabaseManager,
    selected_id: Optional[int],
    navigate_to: Callable[[str, Optional[int]], None],
    dark_mode: bool = False,
) -> None:
    """Render full structured project plan, visualizations, and PDF export controls."""
    analyses_df = db.list_analyses_df()
    if analyses_df.empty:
        render_page_header(
            "Analysis Details",
            "Inspect extracted requirements, tech stack recommendations, project milestones, and export PDFs.",
        )
        st.info("No analyses found in the database yet.")
        if st.button("+ Create First Analysis", type="primary"):
            navigate_to("New Analysis", None)
        return

    id_list = analyses_df["id"].astype(int).tolist()
    label_map = {
        int(row["id"]): f"#{row['id']} — {row['project_title']} ({row['client_name']})"
        for _, row in analyses_df.iterrows()
    }
    active_id = selected_id if selected_id in id_list else id_list[0]

    top_col1, top_col2, top_col3 = st.columns([3.2, 1.3, 0.9], vertical_alignment="bottom")
    with top_col1:
        chosen_id = st.selectbox(
            "Select Saved Project Analysis",
            options=id_list,
            index=id_list.index(active_id),
            format_func=lambda aid: label_map[aid],
        )
        st.session_state["selected_analysis_id"] = chosen_id

    record = db.get_analysis(chosen_id)
    if record is None:
        st.error(f"Analysis #{chosen_id} could not be loaded.")
        return

    with top_col2:
        pdf_bytes = generate_pdf_report(record)
        safe_slug = "".join(c if c.isalnum() else "_" for c in record.project_title).strip("_").lower()
        st.download_button(
            label="Download PDF Report",
            data=pdf_bytes,
            file_name=f"{safe_slug or 'project_plan'}_report.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )

    with top_col3:
        if st.button("Delete", use_container_width=True):
            st.session_state[f"confirm_delete_{chosen_id}"] = True

    if st.session_state.get(f"confirm_delete_{chosen_id}"):
        st.warning(f"Confirm permanent deletion of **#{chosen_id} — {record.project_title}**?")
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if st.button("Confirm Delete", type="primary"):
                db.delete_analysis(chosen_id)
                st.session_state.pop(f"confirm_delete_{chosen_id}", None)
                st.session_state["selected_analysis_id"] = None
                st.success("Analysis deleted.")
                st.rerun()
        with c2:
            if st.button("Cancel"):
                st.session_state.pop(f"confirm_delete_{chosen_id}", None)
                st.rerun()

    render_page_header(
        record.project_title,
        f"Client: {record.client_name}  •  Domain: {record.project_domain}  •  "
        f"Engagement: {record.engagement_type}  •  Model: {record.model_used}",
        eyebrow="Structured Project Plan",
    )
    st.markdown(
        f"**Readiness Status:** {status_badge_html(record.readiness_status)} &nbsp;&nbsp; "
        f"**Source:** `{record.source_type}`"
        + (f" (`{record.source_filename}`)" if record.source_filename else ""),
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

    total_weeks = max((m.end_week for m in record.milestones), default=0)
    kpi_cards: list[KPICardData] = [
        {
            "label": "Completeness Score",
            "value": f"{record.completeness_score:.1f}%",
            "subtitle": f"Base {record.score_breakdown.base_weighted_score:.1f}% − {record.score_breakdown.gap_penalty:.1f} gap penalty",
        },
        {
            "label": "Functional Specs",
            "value": str(len(record.functional_requirements)),
            "subtitle": f"{sum(1 for f in record.functional_requirements if f.priority == 'Must')} Must-Have items",
        },
        {
            "label": "Non-Functional Specs",
            "value": str(len(record.non_functional_requirements)),
            "subtitle": f"{sum(1 for n in record.non_functional_requirements if n.priority == 'High')} High-priority SLAs",
        },
        {
            "label": "Estimated Timeline",
            "value": f"{total_weeks} Weeks",
            "subtitle": f"{len(record.milestones)} delivery phases  •  {len(record.missing_information)} open gaps",
        },
    ]
    render_kpi_row(kpi_cards)
    st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

    tab_overview, tab_reqs, tab_stack, tab_gaps, tab_raw = st.tabs(
        [
            "Overview & Completeness",
            "Functional & Non-Functional",
            "Tech Stack & Timeline",
            "Missing Info & Clarifications",
            "Original Input",
        ]
    )

    with tab_overview:
        st.markdown("#### Executive Summary")
        st.write(record.executive_summary)

        meta_c1, meta_c2 = st.columns(2)
        with meta_c1:
            st.markdown("#### Target Users & Personas")
            if record.target_users:
                for user in record.target_users:
                    st.markdown(f"- {user}")
            else:
                st.caption("No explicit user personas extracted.")
        with meta_c2:
            st.markdown("#### Engineering Assumptions")
            if record.assumptions:
                for assumption in record.assumptions:
                    st.markdown(f"- {assumption}")
            else:
                st.caption("No assumptions recorded.")

        st.divider()
        st.markdown("#### Requirement Completeness Breakdown")
        g_col, b_col = st.columns([1.2, 2.2])
        with g_col:
            st.plotly_chart(
                completeness_gauge_chart(record.completeness_score, dark_mode=dark_mode),
                use_container_width=True,
            )
        with b_col:
            st.plotly_chart(
                dimension_breakdown_chart(record.score_breakdown.dimension_details, dark_mode=dark_mode),
                use_container_width=True,
            )

        dim_rows = [
            {
                "Dimension": str(d["label"]),
                "Weight (%)": int(d["weight"]),
                "Score (/100)": int(d["score"]),
                "Evidence Observed": str(d["evidence"]) or "-",
                "Gap Note": str(d["gap_note"]) or "-",
            }
            for d in record.score_breakdown.dimension_details.values()
        ]
        st.dataframe(pd.DataFrame(dim_rows), use_container_width=True, hide_index=True)

    with tab_reqs:
        st.markdown("#### Functional Requirements")
        fr_df = functional_reqs_to_df(record.functional_requirements)
        if not fr_df.empty:
            priority_filter = st.multiselect(
                "Filter Functional Requirements by Priority",
                options=["Must", "Should", "Could", "Won't"],
                default=["Must", "Should", "Could", "Won't"],
            )
            filtered_fr = fr_df[fr_df["Priority"].isin(priority_filter)]
            st.dataframe(filtered_fr, use_container_width=True, hide_index=True)
        else:
            st.caption("No functional requirements extracted.")

        st.divider()
        st.markdown("#### Non-Functional Requirements")
        nfr_df = non_functional_reqs_to_df(record.non_functional_requirements)
        if not nfr_df.empty:
            categories = sorted(nfr_df["Category"].unique().tolist())
            selected_cats = st.multiselect(
                "Filter Non-Functional Requirements by Category",
                options=categories,
                default=categories,
            )
            filtered_nfr = nfr_df[nfr_df["Category"].isin(selected_cats)]
            st.dataframe(filtered_nfr, use_container_width=True, hide_index=True)
        else:
            st.caption("No non-functional requirements extracted.")

    with tab_stack:
        st.markdown("#### Recommended Technology Stack")
        stack_df = tech_stack_to_df(record.tech_stack)
        if not stack_df.empty:
            st.dataframe(stack_df, use_container_width=True, hide_index=True)
        else:
            st.caption("No tech stack recommendations available.")

        st.divider()
        st.markdown("#### Project Timeline & Milestones")
        if record.milestones:
            st.plotly_chart(
                milestone_gantt_chart(record.milestones, dark_mode=dark_mode),
                use_container_width=True,
            )
            st.dataframe(milestones_to_df(record.milestones), use_container_width=True, hide_index=True)
        else:
            st.caption("No project milestones generated.")

    with tab_gaps:
        st.markdown("#### Missing Information & Ambiguities")
        gap_df = missing_info_to_df(record.missing_information)
        if not gap_df.empty:
            st.dataframe(gap_df, use_container_width=True, hide_index=True)

            st.markdown("#### Client Clarification Email Draft")
            st.code(
                f"Subject: Follow-up Questions – {record.project_title}\n\n"
                f"Hi {record.client_name} Team,\n\n"
                f"Thank you for sharing your requirements for {record.project_title}. "
                "To finalize the technical scope and timeline estimate, could you please clarify the items below?\n\n"
                + "\n".join(
                    f"{idx}. [{item.area}] {item.clarifying_question}"
                    for idx, item in enumerate(record.missing_information, start=1)
                )
                + "\n\nBest regards,\nSolution Architecture Team",
                language="text",
            )
            st.caption("Use the copy icon in the top-right corner of the block above to copy the email draft.")
        else:
            st.success("No major missing information gaps detected.")

    with tab_raw:
        st.markdown("#### Source Client Requirement Input")
        st.text_area(
            "Extracted / Submitted Raw Text",
            value=record.raw_input_text,
            height=360,
            disabled=True,
            label_visibility="collapsed",
        )

"""New Requirement Analysis page: raw text intake, PDF/DOCX upload, and AI execution."""

from pathlib import Path
from typing import Callable, Optional

import streamlit as st

from config.settings import Settings, save_provider_configuration
from database.db_manager import DatabaseError, DatabaseManager
from services.ai_analyzer import AIAnalysisError, analyze_requirements
from services.document_parser import DocumentParseError, ParsedDocument, parse_uploaded_document
from ui.components.metric_cards import render_page_header
from utils.validators import ValidationError


ENGAGEMENT_TYPES = [
    "Web / SaaS Application",
    "Mobile Application",
    "AI / Data Platform",
    "Enterprise Internal Tool",
    "API / Microservices",
    "E-Commerce Platform",
]


def _load_sample_text(samples_dir: Path, filename: str) -> str:
    """Read a sample requirement document from data/samples."""
    target = samples_dir / filename
    if target.exists():
        return target.read_text(encoding="utf-8")
    return ""


def render_new_analysis(
    db: DatabaseManager,
    settings: Settings,
    navigate_to: Callable[[str, Optional[int]], None],
) -> None:
    """Render the client requirement intake, document upload, and AI analysis view."""
    render_page_header(
        "New Requirement Analysis",
        "Paste client emails or meeting transcripts, or upload a PDF/DOCX specification to generate a structured project plan.",
    )

    if not settings.is_llm_configured():
        warn_col, btn_col = st.columns([3.2, 1.6], vertical_alignment="center")
        with warn_col:
            st.warning(
                f"No API key is active for **{settings.llm_provider.upper()}**. "
                "Add your key in the sidebar **AI Engine Setup** panel, or test immediately using **Offline Smart Mode**."
            )
        with btn_col:
            if st.button("Use Offline Smart Mode", use_container_width=True):
                save_provider_configuration(
                    provider="offline_demo",
                    model_name="heuristic-v1",
                    persist_to_env=True,
                )
                st.rerun()

    st.session_state.setdefault("input_project_title", "")
    st.session_state.setdefault("input_client_name", "")
    st.session_state.setdefault("input_raw_text", "")
    st.session_state.setdefault("input_source_type", "raw_text")
    st.session_state.setdefault("input_source_filename", None)

    meta_col1, meta_col2, meta_col3 = st.columns([2, 1.5, 1.5])
    with meta_col1:
        project_title = st.text_input(
            "Project Title *",
            key="input_project_title",
            placeholder="e.g., B2B Expense & Reimbursement Portal",
        )
    with meta_col2:
        client_name = st.text_input(
            "Client Name *",
            key="input_client_name",
            placeholder="e.g., FinFlow Logistics",
        )
    with meta_col3:
        engagement_type = st.selectbox("Engagement Type", options=ENGAGEMENT_TYPES)

    tab_paste, tab_upload = st.tabs(["Paste Text / Email / Transcript", "Upload Document (PDF / DOCX / TXT)"])

    with tab_paste:
        sample_col1, sample_col2, sample_col3 = st.columns([1.4, 1.4, 2.2])
        with sample_col1:
            if st.button("Load Sample 1 (FinTech Brief)", use_container_width=True):
                st.session_state["input_project_title"] = "FinFlow B2B Expense Portal"
                st.session_state["input_client_name"] = "FinFlow Logistics"
                st.session_state["input_raw_text"] = _load_sample_text(
                    settings.samples_dir, "01_fintech_expense_app.txt"
                )
                st.session_state["input_source_type"] = "raw_text"
                st.session_state["input_source_filename"] = None
                st.rerun()
        with sample_col2:
            if st.button("Load Sample 2 (Clinic Notes)", use_container_width=True):
                st.session_state["input_project_title"] = "CareBridge Patient Booking App"
                st.session_state["input_client_name"] = "CareBridge Clinic"
                st.session_state["input_raw_text"] = _load_sample_text(
                    settings.samples_dir, "02_healthcare_booking_chat.txt"
                )
                st.session_state["input_source_type"] = "raw_text"
                st.session_state["input_source_filename"] = None
                st.rerun()
        with sample_col3:
            if st.button("Clear Input Fields", use_container_width=True):
                st.session_state["input_project_title"] = ""
                st.session_state["input_client_name"] = ""
                st.session_state["input_raw_text"] = ""
                st.session_state["input_source_type"] = "raw_text"
                st.session_state["input_source_filename"] = None
                st.rerun()

        raw_text = st.text_area(
            "Client Requirement Text *",
            key="input_raw_text",
            height=290,
            placeholder=(
                "Paste unstructured client conversation notes, discovery call transcript, "
                "RFP excerpts, or requirement emails here..."
            ),
        )
        char_count = len(raw_text.strip())
        word_count = len(raw_text.strip().split()) if char_count else 0
        st.caption(
            f"Length: **{char_count:,} characters** ({word_count:,} words) • "
            f"Minimum required: {settings.min_input_chars} characters"
        )

    with tab_upload:
        uploaded_file = st.file_uploader(
            f"Upload PDF, DOCX, or TXT requirement document (Max {settings.max_upload_size_mb} MB)",
            type=["pdf", "docx", "txt"],
        )
        if uploaded_file is not None:
            file_bytes = uploaded_file.getvalue()
            try:
                parsed: ParsedDocument = parse_uploaded_document(
                    filename=uploaded_file.name,
                    file_bytes=file_bytes,
                    max_size_mb=settings.max_upload_size_mb,
                )
                st.success(
                    f"Extracted **{parsed.word_count:,} words** ({parsed.char_count:,} chars) "
                    f"from `{parsed.filename}` ({parsed.file_type}, ~{parsed.page_count} page(s))."
                )
                if st.button("Use Extracted Document Text", type="secondary"):
                    st.session_state["input_raw_text"] = parsed.text
                    st.session_state["input_source_type"] = parsed.file_type.lower()
                    st.session_state["input_source_filename"] = parsed.filename
                    if not st.session_state["input_project_title"]:
                        st.session_state["input_project_title"] = Path(parsed.filename).stem.replace("_", " ").title()
                    st.rerun()

                with st.expander("Preview Extracted Text", expanded=True):
                    st.text(parsed.text[:4000] + ("\n\n...[truncated preview]" if len(parsed.text) > 4000 else ""))
            except DocumentParseError as exc:
                st.error(f"Document processing error: {exc}")

    st.divider()
    run_col1, run_col2 = st.columns([2, 3], vertical_alignment="center")
    with run_col1:
        analyze_clicked = st.button(
            "Run AI Requirement Analysis",
            type="primary",
            use_container_width=True,
        )
    with run_col2:
        st.caption(
            f"Active Engine: `{settings.llm_provider}` • Model: `{settings.active_model_name()}` • "
            "Results are automatically saved to SQLite history."
        )

    if analyze_clicked:
        try:
            with st.spinner("Analyzing client requirements, scoring completeness, and building project plan..."):
                record = analyze_requirements(
                    project_title=project_title,
                    client_name=client_name,
                    engagement_type=engagement_type,
                    source_type=st.session_state.get("input_source_type", "raw_text"),
                    raw_text=st.session_state.get("input_raw_text", ""),
                    source_filename=st.session_state.get("input_source_filename"),
                    settings=settings,
                )
                new_id = db.save_analysis(record)

            st.success(f"Analysis saved (#{new_id})! Opening structured project plan...")
            navigate_to("Analysis Details", new_id)

        except (ValidationError, AIAnalysisError, DatabaseError) as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Unexpected error during analysis: {exc}")

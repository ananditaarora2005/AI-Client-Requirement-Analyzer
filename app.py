"""Main Streamlit entry point for AI Client Requirement Analyzer."""

from pathlib import Path
from typing import Optional

import streamlit as st

from config.settings import (
    SUPPORTED_PROVIDERS,
    Settings,
    get_settings,
    save_provider_configuration,
)
from database.db_manager import DatabaseManager
from ui.components.metric_cards import status_badge_html
from ui.pages.analysis_details import render_analysis_details
from ui.pages.dashboard import render_dashboard
from ui.pages.history import render_history
from ui.pages.new_analysis import render_new_analysis


PAGES = ["Dashboard", "New Analysis", "Analysis Details", "History"]

THEME_VARS = {
    "Light": """
    :root {
        --bg-canvas: #f8fafc;
        --bg-card: #ffffff;
        --bg-sidebar: #ffffff;
        --bg-elevated: #f1f5f9;
        --border-subtle: #e2e8f0;
        --text-primary: #0f172a;
        --text-secondary: #475569;
        --accent: #2563eb;
        --accent-soft: #eff6ff;
        --input-bg: #ffffff;
        --code-bg: #eef2ff;
        --code-fg: #1e3a8a;
        --shadow-card: 0 1px 3px rgba(15, 23, 42, 0.06);
        --badge-success-bg: #dcfce7;
        --badge-success-fg: #166534;
        --badge-success-border: #bbf7d0;
        --badge-warn-bg: #fef3c7;
        --badge-warn-fg: #92400e;
        --badge-warn-border: #fde68a;
        --badge-danger-bg: #fee2e2;
        --badge-danger-fg: #991b1b;
        --badge-danger-border: #fecaca;
    }
    """,
    "Night": """
    :root {
        --bg-canvas: #0b1120;
        --bg-card: #111827;
        --bg-sidebar: #0f172a;
        --bg-elevated: #1e293b;
        --border-subtle: #1f2937;
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --accent: #3b82f6;
        --accent-soft: rgba(59, 130, 246, 0.16);
        --input-bg: #1e293b;
        --code-bg: #1e293b;
        --code-fg: #93c5fd;
        --shadow-card: 0 4px 12px rgba(0, 0, 0, 0.28);
        --badge-success-bg: rgba(34, 197, 94, 0.16);
        --badge-success-fg: #86efac;
        --badge-success-border: rgba(34, 197, 94, 0.38);
        --badge-warn-bg: rgba(245, 158, 11, 0.16);
        --badge-warn-fg: #fcd34d;
        --badge-warn-border: rgba(245, 158, 11, 0.38);
        --badge-danger-bg: rgba(239, 68, 68, 0.16);
        --badge-danger-fg: #fca5a5;
        --badge-danger-border: rgba(239, 68, 68, 0.38);
    }
    """,
}


st.set_page_config(
    page_title="AI Client Requirement Analyzer",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _load_css(css_path: Path, theme_mode: str) -> None:
    """Inject dynamic Light/Night CSS variables and shared SaaS styling."""
    vars_css = THEME_VARS.get(theme_mode, THEME_VARS["Light"])
    base_css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
    st.markdown(f"<style>{vars_css}\n{base_css}</style>", unsafe_allow_html=True)


@st.cache_resource
def _get_db_manager(db_path_str: str) -> DatabaseManager:
    """Initialize and cache the SQLite database manager."""
    return DatabaseManager(Path(db_path_str))


def _navigate_to(page: str, analysis_id: Optional[int] = None) -> None:
    """Safely schedule navigation to another view and trigger rerun."""
    if page in PAGES:
        st.session_state["pending_nav_page"] = page
    if analysis_id is not None:
        st.session_state["selected_analysis_id"] = analysis_id
    st.rerun()


def _render_sidebar_ai_setup(settings: Settings) -> Settings:
    """Render sidebar AI engine setup allowing safe .env key configuration."""
    with st.expander("AI Engine Setup", expanded=not settings.is_llm_configured()):
        provider_idx = (
            SUPPORTED_PROVIDERS.index(settings.llm_provider)
            if settings.llm_provider in SUPPORTED_PROVIDERS
            else 0
        )
        provider = st.selectbox(
            "Provider",
            options=list(SUPPORTED_PROVIDERS),
            index=provider_idx,
            format_func=lambda p: {
                "openai": "OpenAI",
                "gemini": "Google Gemini",
                "openai_compatible": "OpenAI-Compatible",
                "offline_demo": "Offline Smart Mode (No Key)",
            }[p],
        )

        if provider == "offline_demo":
            st.caption("Uses deterministic heuristic parsing locally without external API calls.")
            if st.button("Activate Offline Mode", use_container_width=True):
                settings = save_provider_configuration(
                    provider="offline_demo",
                    model_name="heuristic-v1",
                    persist_to_env=True,
                )
                st.success("Offline Smart Mode active.")
                st.rerun()
        else:
            default_model = (
                settings.gemini_model if provider == "gemini" else settings.openai_model
            )
            model_name = st.text_input("Model", value=default_model)

            base_url = ""
            if provider == "openai_compatible":
                base_url = st.text_input(
                    "Base URL",
                    value=settings.openai_base_url,
                    placeholder="https://api.groq.com/openai/v1",
                )

            api_key_input = st.text_input(
                "API Key",
                value="",
                type="password",
                placeholder="Paste key and press Save",
                help="Stored locally in .env (never in source code). Leave blank to keep existing key.",
            )

            # If user pasted a key and pressed Enter, apply it to active session immediately.
            if api_key_input.strip():
                settings = save_provider_configuration(
                    provider=provider,
                    model_name=model_name,
                    api_key=api_key_input.strip(),
                    base_url=base_url,
                    persist_to_env=True,
                )

            if st.button("Save to .env & Apply", type="primary", use_container_width=True):
                existing_key = (
                    settings.gemini_api_key if provider == "gemini" else settings.openai_api_key
                )
                effective_key = api_key_input.strip() or existing_key
                if not effective_key:
                    st.error("Please enter a valid API key before saving.")
                elif provider == "openai_compatible" and not base_url.strip():
                    st.error("Please enter a Base URL for the OpenAI-compatible endpoint.")
                else:
                    settings = save_provider_configuration(
                        provider=provider,
                        model_name=model_name,
                        api_key=effective_key,
                        base_url=base_url,
                        persist_to_env=True,
                    )
                    st.success("Saved to .env and activated!")
                    st.rerun()

    return settings


def main() -> None:
    """Application shell, sidebar navigation, theme switcher, and page router."""
    settings: Settings = get_settings()
    db = _get_db_manager(str(settings.database_path))

    if "theme_mode" not in st.session_state:
        st.session_state["theme_mode"] = "Light"
    if "nav_page" not in st.session_state:
        st.session_state["nav_page"] = "Dashboard"
    if "pending_nav_page" in st.session_state:
        st.session_state["nav_page"] = st.session_state.pop("pending_nav_page")
    st.session_state.setdefault("selected_analysis_id", None)

    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <span class="sidebar-brand-pill">SaaS Workspace</span>
                <p class="sidebar-brand-title">AI Requirement Analyzer</p>
                <p class="sidebar-brand-sub">Client Discovery to Project Plan</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        selected_page = st.radio(
            "Navigation",
            options=PAGES,
            key="nav_page",
            label_visibility="collapsed",
        )

        st.markdown("<div style='height: 0.4rem;'></div>", unsafe_allow_html=True)
        st.caption("Appearance")
        theme_choice = st.radio(
            "Theme",
            options=["Light", "Night"],
            index=0 if st.session_state["theme_mode"] == "Light" else 1,
            horizontal=True,
            format_func=lambda t: "☀️ Day (Light)" if t == "Light" else "🌙 Night (Dark)",
            label_visibility="collapsed",
        )
        st.session_state["theme_mode"] = theme_choice

        st.divider()
        settings = _render_sidebar_ai_setup(settings)

        st.caption("Workspace Status")
        if settings.llm_provider == "offline_demo":
            key_badge = status_badge_html("Offline Demo")
        elif settings.is_llm_configured():
            key_badge = status_badge_html("Configured")
        else:
            key_badge = status_badge_html("Not Configured")

        st.markdown(
            f"""
            <div class="workspace-card">
                <div><strong>AI Engine:</strong> <code>{settings.llm_provider}</code></div>
                <div><strong>Model:</strong> <code>{settings.active_model_name()}</code></div>
                <div><strong>API Status:</strong> {key_badge}</div>
                <div><strong>Storage:</strong> <code>SQLite Ready</code></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    dark_mode = st.session_state["theme_mode"] == "Night"
    _load_css(settings.base_dir / "ui" / "styles" / "theme.css", st.session_state["theme_mode"])

    if selected_page == "Dashboard":
        render_dashboard(db=db, navigate_to=_navigate_to, dark_mode=dark_mode)
    elif selected_page == "New Analysis":
        render_new_analysis(db=db, settings=settings, navigate_to=_navigate_to)
    elif selected_page == "Analysis Details":
        render_analysis_details(
            db=db,
            selected_id=st.session_state.get("selected_analysis_id"),
            navigate_to=_navigate_to,
            dark_mode=dark_mode,
        )
    elif selected_page == "History":
        render_history(db=db, navigate_to=_navigate_to)


if __name__ == "__main__":
    main()

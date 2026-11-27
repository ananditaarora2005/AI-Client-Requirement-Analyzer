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

PAGE_ICONS = {
    "Dashboard": "📊  Dashboard",
    "New Analysis": "⚡  New Analysis",
    "Analysis Details": "📑  Analysis Details",
    "History": "🕒  History",
}

THEME_VARS = {
    "Light": """
    :root {
        --bg-canvas: #F8FAFC;
        --bg-card: #FFFFFF;
        --bg-sidebar: #FFFFFF;
        --bg-elevated: #F1F5F9;
        --border-subtle: #E2E8F0;
        --border-focus: #2563EB;
        --text-primary: #0F172A;
        --text-secondary: #475569;
        --text-muted: #64748B;
        --accent: #2563EB;
        --accent-hover: #1D4ED8;
        --accent-soft: #EFF6FF;
        --accent-glow: rgba(37, 99, 235, 0.16);
        --input-bg: #FFFFFF;
        --code-bg: #F1F5F9;
        --code-fg: #1E3A8A;
        --shadow-card: 0 1px 3px rgba(15, 23, 42, 0.08), 0 1px 2px rgba(15, 23, 42, 0.04);
        --shadow-hover: 0 10px 25px -5px rgba(37, 99, 235, 0.12), 0 8px 10px -6px rgba(15, 23, 42, 0.04);
        --sidebar-text: #0F172A;
        --sidebar-text-muted: #64748B;
        --sidebar-nav-active-bg: #EFF6FF;
        --sidebar-nav-active-border: #2563EB;
        --sidebar-nav-active-color: #2563EB;
        --card-top-border: #2563EB;
        --radio-border: #94A3B8;
        --radio-checked: #2563EB;
        --badge-success-bg: #DCFCE7;
        --badge-success-fg: #166534;
        --badge-success-border: #BBF7D0;
        --badge-warn-bg: #FEF3C7;
        --badge-warn-fg: #92400E;
        --badge-warn-border: #FDE68A;
        --badge-danger-bg: #FEE2E2;
        --badge-danger-fg: #991B1B;
        --badge-danger-border: #FECACA;
    }
    """,
    "Night": """
    :root {
        --bg-canvas: #0B1120;
        --bg-card: #151F32;
        --bg-sidebar: #111827;
        --bg-elevated: #1E293B;
        --border-subtle: #334155;
        --border-focus: #3B82F6;
        --text-primary: #F8FAFC;
        --text-secondary: #CBD5E1;
        --text-muted: #94A3B8;
        --accent: #3B82F6;
        --accent-hover: #60A5FA;
        --accent-soft: rgba(59, 130, 246, 0.14);
        --accent-glow: rgba(59, 130, 246, 0.28);
        --input-bg: #1E293B;
        --code-bg: #1E293B;
        --code-fg: #93C5FD;
        --shadow-card: 0 4px 16px rgba(0, 0, 0, 0.4), 0 1px 3px rgba(0, 0, 0, 0.25);
        --shadow-hover: 0 12px 30px -4px rgba(59, 130, 246, 0.25), 0 4px 12px rgba(0, 0, 0, 0.35);
        --sidebar-text: #F8FAFC;
        --sidebar-text-muted: #94A3B8;
        --sidebar-nav-active-bg: rgba(59, 130, 246, 0.18);
        --sidebar-nav-active-border: #3B82F6;
        --sidebar-nav-active-color: #60A5FA;
        --card-top-border: #3B82F6;
        --radio-border: #64748B;
        --radio-checked: #3B82F6;
        --badge-success-bg: rgba(34, 197, 94, 0.16);
        --badge-success-fg: #86EFAC;
        --badge-success-border: rgba(34, 197, 94, 0.35);
        --badge-warn-bg: rgba(245, 158, 11, 0.16);
        --badge-warn-fg: #FCD34D;
        --badge-warn-border: rgba(245, 158, 11, 0.35);
        --badge-danger-bg: rgba(239, 68, 68, 0.16);
        --badge-danger-fg: #FCA5A5;
        --badge-danger-border: rgba(239, 68, 68, 0.35);
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
                <span class="sidebar-brand-pill">AI ARCHITECT</span>
                <h2 class="sidebar-brand-title">Requirement Analyzer</h2>
                <p class="sidebar-brand-sub">Client Discovery to Project Plan</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption("Navigation")
        selected_page = st.radio(
            "Navigation",
            options=PAGES,
            format_func=lambda p: PAGE_ICONS.get(p, p),
            key="nav_page",
            label_visibility="collapsed",
        )

        st.markdown("<div style='height: 0.6rem;'></div>", unsafe_allow_html=True)
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
                <div class="ws-item"><span class="ws-label">AI Engine:</span> <code>{settings.llm_provider}</code></div>
                <div class="ws-item"><span class="ws-label">Model:</span> <code>{settings.active_model_name()}</code></div>
                <div class="ws-item"><span class="ws-label">API Status:</span> {key_badge}</div>
                <div class="ws-item"><span class="ws-label">Storage:</span> <code>SQLite Ready</code></div>
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

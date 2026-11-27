"""Reusable KPI metric cards, headers, and status badge components."""

from html import escape
from typing import List, Optional, TypedDict

import streamlit as st


class KPICardData(TypedDict, total=False):
    """Data contract for one KPI card."""

    label: str
    value: str
    subtitle: str
    icon: Optional[str]


def render_page_header(title: str, subtitle: str, eyebrow: str = "AI Project Architect") -> None:
    """Render a consistent SaaS page header."""
    st.markdown(
        f"""
        <div class="page-header">
            <div class="page-eyebrow">{escape(eyebrow)}</div>
            <h1 class="page-title">{escape(title)}</h1>
            <p class="page-subtitle">{escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_heading(title: str, icon: str = "") -> None:
    """Render a clean, standard section header with an optional icon."""
    icon_html = f'<span class="section-heading-icon">{escape(icon)}</span> ' if icon else ""
    st.markdown(
        f'<div class="section-heading">{icon_html}<span>{escape(title)}</span></div>',
        unsafe_allow_html=True,
    )


def _get_default_icon(label: str) -> str:
    """Derive an appropriate visual icon for a metric card."""
    lbl = label.lower()
    if "total" in lbl or "analyses" in lbl:
        return "📁"
    if "completeness" in lbl or "score" in lbl:
        return "🎯"
    if "requirement" in lbl or "spec" in lbl:
        return "📋"
    if "timeline" in lbl or "week" in lbl or "duration" in lbl:
        return "⏱️"
    return "📊"


def render_kpi_row(cards: List[KPICardData]) -> None:
    """Render a responsive row of equal-height KPI summary cards with icons."""
    if not cards:
        return
    columns = st.columns(len(cards))
    for col, card in zip(columns, cards):
        icon = card.get("icon") or _get_default_icon(card.get("label", ""))
        with col:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-top-row">
                        <span class="kpi-label">{escape(card['label'])}</span>
                        <span class="kpi-icon">{icon}</span>
                    </div>
                    <div class="kpi-value">{escape(card['value'])}</div>
                    <div class="kpi-sub">{escape(card['subtitle'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def status_badge_html(status: str) -> str:
    """Return an HTML badge styled according to readiness, engine status, or severity."""
    normalized = status.strip().lower()
    if normalized in {"ready for planning", "low", "configured", "ready", "offline demo"}:
        css_class = "badge-success"
    elif normalized in {"needs clarification", "medium"}:
        css_class = "badge-warning"
    elif normalized in {"incomplete", "high", "not configured"}:
        css_class = "badge-danger"
    else:
        css_class = "badge-info"
    return f'<span class="status-badge {css_class}">{escape(status)}</span>'

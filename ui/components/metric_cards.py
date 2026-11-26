"""Reusable KPI metric cards, headers, and status badge components."""

from html import escape
from typing import List, TypedDict

import streamlit as st


class KPICardData(TypedDict):
    """Data contract for one KPI card."""

    label: str
    value: str
    subtitle: str


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


def render_kpi_row(cards: List[KPICardData]) -> None:
    """Render a responsive row of equal-height KPI summary cards."""
    if not cards:
        return
    columns = st.columns(len(cards))
    for col, card in zip(columns, cards):
        with col:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-label">{escape(card['label'])}</div>
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

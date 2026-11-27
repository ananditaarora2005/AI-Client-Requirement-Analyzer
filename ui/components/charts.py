"""Plotly charts for dashboard analytics, completeness scoring, and project timelines."""

from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from models.schemas import ProjectMilestone


def _chart_theme(dark_mode: bool) -> Dict[str, str]:
    """Return consistent chart colors for Light or Dark mode."""
    if dark_mode:
        return {
            "text": "#F8FAFC",
            "muted": "#94A3B8",
            "grid": "#334155",
            "gauge_bg": "#151F32",
            "bar": "#3B82F6",
            "bar_border": "#60A5FA",
        }
    return {
        "text": "#0F172A",
        "muted": "#475569",
        "grid": "#E2E8F0",
        "gauge_bg": "#F1F5F9",
        "bar": "#2563EB",
        "bar_border": "#1E3A8A",
    }


def completeness_gauge_chart(score: float, dark_mode: bool = False) -> go.Figure:
    """Render a 0-100 requirement completeness gauge chart."""
    colors = _chart_theme(dark_mode)
    bar_color = "#22C55E" if score >= 78 else ("#F59E0B" if score >= 50 else "#EF4444")
    steps = (
        [
            {"range": [0, 50], "color": "rgba(239, 68, 68, 0.22)"},
            {"range": [50, 78], "color": "rgba(245, 158, 11, 0.22)"},
            {"range": [78, 100], "color": "rgba(34, 197, 94, 0.22)"},
        ]
        if dark_mode
        else [
            {"range": [0, 50], "color": "#FEE2E2"},
            {"range": [50, 78], "color": "#FEF3C7"},
            {"range": [78, 100], "color": "#DCFCE7"},
        ]
    )

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "%", "font": {"size": 34, "color": colors["text"]}},
            title={"text": "Completeness Score", "font": {"size": 14, "color": colors["muted"]}},
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickwidth": 1,
                    "tickcolor": colors["grid"],
                    "tickfont": {"color": colors["muted"]},
                },
                "bar": {"color": bar_color},
                "bgcolor": colors["gauge_bg"],
                "borderwidth": 0,
                "steps": steps,
            },
        )
    )
    fig.update_layout(
        height=240,
        margin=dict(l=20, r=20, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=colors["text"]),
    )
    return fig


def dimension_breakdown_chart(
    dimension_details: Dict[str, Dict[str, Any]],
    dark_mode: bool = False,
) -> go.Figure:
    """Render a horizontal bar chart of the 7 completeness dimensions."""
    colors = _chart_theme(dark_mode)
    rows = [
        {
            "Dimension": str(detail["label"]),
            "Score": int(detail["score"]),
            "Weight": f"{detail['weight']}%",
        }
        for detail in dimension_details.values()
    ]
    df = pd.DataFrame(rows).sort_values("Score", ascending=True)

    fig = px.bar(
        df,
        x="Score",
        y="Dimension",
        orientation="h",
        text="Score",
        hover_data=["Weight"],
        color="Score",
        color_continuous_scale=["#EF4444", "#F59E0B", "#22C55E"],
        range_color=[0, 100],
    )
    fig.update_traces(texttemplate="%{text}/100", textposition="outside", textfont=dict(color=colors["text"]))
    fig.update_layout(
        height=280,
        margin=dict(l=10, r=35, t=20, b=20),
        xaxis=dict(
            range=[0, 118],
            title="Score (0–100)",
            gridcolor=colors["grid"],
            tickfont=dict(color=colors["muted"]),
            title_font=dict(color=colors["muted"]),
        ),
        yaxis=dict(title="", tickfont=dict(color=colors["text"])),
        coloraxis_showscale=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=colors["text"]),
    )
    return fig


def milestone_gantt_chart(
    milestones: List[ProjectMilestone],
    dark_mode: bool = False,
) -> go.Figure:
    """Render a phased delivery Gantt timeline across project weeks."""
    colors = _chart_theme(dark_mode)
    ordered = sorted(milestones, key=lambda m: m.phase_number, reverse=True)
    labels = [f"P{m.phase_number}: {m.phase_name}" for m in ordered]
    starts = [m.start_week - 1 for m in ordered]
    durations = [m.duration_weeks for m in ordered]
    hover_texts = [
        f"Weeks {m.start_week}–{m.end_week} ({m.duration_weeks} wks)<br>"
        f"Dependencies: {m.dependencies}"
        for m in ordered
    ]

    fig = go.Figure(
        go.Bar(
            x=durations,
            y=labels,
            base=starts,
            orientation="h",
            marker=dict(color=colors["bar"], line=dict(color=colors["bar_border"], width=1)),
            text=[f"Wk {m.start_week}–{m.end_week}" for m in ordered],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color="#FFFFFF"),
            hovertext=hover_texts,
            hoverinfo="text",
        )
    )
    max_week = max((m.end_week for m in milestones), default=8)
    fig.update_layout(
        title=dict(text="Project Delivery Roadmap (Weeks)", font=dict(size=14, color=colors["text"])),
        height=max(240, 55 * len(milestones) + 80),
        margin=dict(l=10, r=20, t=45, b=30),
        xaxis=dict(
            title="Project Week",
            dtick=1,
            range=[0, max_week + 1],
            gridcolor=colors["grid"],
            tickfont=dict(color=colors["muted"]),
            title_font=dict(color=colors["muted"]),
        ),
        yaxis=dict(title="", tickfont=dict(color=colors["text"])),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=colors["text"]),
    )
    return fig


def dashboard_priority_chart(df: pd.DataFrame, dark_mode: bool = False) -> go.Figure:
    """Render a donut chart of Functional Requirements by MoSCoW priority."""
    colors = _chart_theme(dark_mode)
    fig = px.pie(
        df,
        names="priority",
        values="count",
        hole=0.55,
        color="priority",
        color_discrete_map={
            "Must": "#1D4ED8",
            "Should": "#3B82F6",
            "Could": "#0EA5E9",
            "Won't": "#64748B",
        },
    )
    fig.update_traces(textfont=dict(color="#FFFFFF"))
    fig.update_layout(
        height=270,
        margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(color=colors["text"]),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=colors["text"]),
    )
    return fig


def dashboard_nfr_chart(df: pd.DataFrame, dark_mode: bool = False) -> go.Figure:
    """Render a bar chart of Non-Functional Requirements by category."""
    colors = _chart_theme(dark_mode)
    sorted_df = df.sort_values("count", ascending=True)
    fig = px.bar(
        sorted_df,
        x="count",
        y="category",
        orientation="h",
        text="count",
        color_discrete_sequence=[colors["bar"]],
    )
    fig.update_traces(textposition="outside", textfont=dict(color=colors["text"]))
    fig.update_layout(
        height=270,
        margin=dict(l=10, r=25, t=20, b=20),
        xaxis=dict(
            title="Requirements Count",
            dtick=1,
            gridcolor=colors["grid"],
            tickfont=dict(color=colors["muted"]),
            title_font=dict(color=colors["muted"]),
        ),
        yaxis=dict(title="", tickfont=dict(color=colors["text"])),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=colors["text"]),
    )
    return fig


def dashboard_readiness_chart(df: pd.DataFrame, dark_mode: bool = False) -> go.Figure:
    """Render a bar chart of analyses grouped by readiness classification."""
    colors = _chart_theme(dark_mode)
    fig = px.bar(
        df,
        x="readiness_status",
        y="count",
        text="count",
        color="readiness_status",
        color_discrete_map={
            "Ready for Planning": "#22C55E",
            "Needs Clarification": "#F59E0B",
            "Incomplete": "#EF4444",
        },
    )
    fig.update_traces(textposition="outside", textfont=dict(color=colors["text"]))
    fig.update_layout(
        height=270,
        margin=dict(l=10, r=10, t=20, b=20),
        xaxis=dict(title="", tickfont=dict(color=colors["text"])),
        yaxis=dict(
            title="Projects",
            dtick=1,
            gridcolor=colors["grid"],
            tickfont=dict(color=colors["muted"]),
            title_font=dict(color=colors["muted"]),
        ),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=colors["text"]),
    )
    return fig

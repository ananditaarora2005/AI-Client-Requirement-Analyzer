"""Executive PDF report generator built with ReportLab."""

from datetime import datetime
import io
from typing import List
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from models.schemas import ProjectAnalysisRecord


BRAND_PRIMARY = colors.HexColor("#1E3A8A")
BRAND_ACCENT = colors.HexColor("#2563EB")
SLATE_DARK = colors.HexColor("#0F172A")
SLATE_MUTED = colors.HexColor("#475569")
SURFACE_ALT = colors.HexColor("#F8FAFC")
BORDER_LIGHT = colors.HexColor("#CBD5E1")


def _safe(text: str) -> str:
    """Escape XML-reserved characters for ReportLab Paragraph rendering."""
    return escape(str(text or "")).replace("\n", "<br/>")


def _draw_footer(canvas, doc) -> None:
    """Render subtle page footer with document title and page number."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(SLATE_MUTED)
    canvas.drawString(0.65 * inch, 0.45 * inch, "AI Client Requirement Analyzer — Project Plan Report")
    canvas.drawRightString(letter[0] - 0.65 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _styled_table(data: List[List], col_widths: List[float]) -> Table:
    """Build a consistently styled ReportLab table with alternating row shading."""
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
                ("TOPPADDING", (0, 0), (-1, 0), 7),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SURFACE_ALT]),
                ("GRID", (0, 0), (-1, -1), 0.4, BORDER_LIGHT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 1), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
            ]
        )
    )
    return table


def generate_pdf_report(record: ProjectAnalysisRecord) -> bytes:
    """Generate a multi-section executive PDF report and return its bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title=f"{record.project_title} - Project Plan",
    )

    base_styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=base_styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=SLATE_DARK,
        alignment=0,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=SLATE_MUTED,
        spaceAfter=10,
    )
    h2_style = ParagraphStyle(
        "SectionHeader",
        parent=base_styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=BRAND_PRIMARY,
        spaceBefore=14,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=SLATE_DARK,
    )
    cell_style = ParagraphStyle(
        "TableCell",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=8.2,
        leading=11,
        textColor=SLATE_DARK,
    )
    cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=cell_style,
        fontName="Helvetica-Bold",
    )
    header_cell = ParagraphStyle(
        "HeaderCell",
        parent=cell_style,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    story: List = []
    generated_at = (record.created_at or datetime.now()).strftime("%Y-%m-%d %H:%M")

    # 1. Title & Metadata Banner
    story.append(Paragraph(_safe(record.project_title), title_style))
    story.append(
        Paragraph(
            _safe(
                f"Client: {record.client_name}  |  Domain: {record.project_domain}  |  "
                f"Type: {record.engagement_type}  |  Generated: {generated_at}"
            ),
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_ACCENT, spaceAfter=10))

    meta_table = _styled_table(
        [
            [
                Paragraph("Completeness Score", header_cell),
                Paragraph("Readiness Status", header_cell),
                Paragraph("Functional Reqs", header_cell),
                Paragraph("Non-Functional Reqs", header_cell),
                Paragraph("Open Gaps", header_cell),
            ],
            [
                Paragraph(f"<b>{record.completeness_score:.1f}%</b>", cell_style),
                Paragraph(_safe(record.readiness_status), cell_style),
                Paragraph(str(len(record.functional_requirements)), cell_style),
                Paragraph(str(len(record.non_functional_requirements)), cell_style),
                Paragraph(str(len(record.missing_information)), cell_style),
            ],
        ],
        col_widths=[1.4 * inch, 1.8 * inch, 1.3 * inch, 1.4 * inch, 1.3 * inch],
    )
    story.append(meta_table)

    # 2. Executive Summary
    story.append(Paragraph("1. Executive Summary", h2_style))
    story.append(Paragraph(_safe(record.executive_summary), body_style))

    if record.target_users:
        story.append(Spacer(1, 6))
        users_text = ", ".join(record.target_users)
        story.append(Paragraph(f"<b>Target Users:</b> {_safe(users_text)}", body_style))

    if record.assumptions:
        story.append(Spacer(1, 6))
        story.append(Paragraph("<b>Key Assumptions:</b>", body_style))
        for item in record.assumptions:
            story.append(Paragraph(f"• {_safe(item)}", body_style))

    # 3. Completeness Breakdown
    story.append(Paragraph("2. Requirement Completeness Scorecard", h2_style))
    score_rows = [
        [
            Paragraph("Dimension", header_cell),
            Paragraph("Weight", header_cell),
            Paragraph("Score", header_cell),
            Paragraph("Gap / Observation", header_cell),
        ]
    ]
    for _, detail in record.score_breakdown.dimension_details.items():
        note = detail.get("gap_note") or detail.get("evidence") or "-"
        score_rows.append(
            [
                Paragraph(_safe(str(detail["label"])), cell_bold),
                Paragraph(f"{detail['weight']}%", cell_style),
                Paragraph(f"{detail['score']}/100", cell_style),
                Paragraph(_safe(str(note)), cell_style),
            ]
        )
    story.append(_styled_table(score_rows, [2.2 * inch, 0.7 * inch, 0.8 * inch, 3.5 * inch]))

    # 4. Functional Requirements
    story.append(Paragraph("3. Functional Requirements", h2_style))
    fr_rows = [
        [
            Paragraph("ID", header_cell),
            Paragraph("Title & Description", header_cell),
            Paragraph("Priority", header_cell),
            Paragraph("Acceptance Criteria", header_cell),
        ]
    ]
    for fr in record.functional_requirements:
        fr_rows.append(
            [
                Paragraph(_safe(fr.req_code), cell_bold),
                Paragraph(
                    f"<b>{_safe(fr.title)}</b><br/>{_safe(fr.description)}<br/>"
                    f"<i>Category: {_safe(fr.category)}</i>",
                    cell_style,
                ),
                Paragraph(_safe(fr.priority), cell_style),
                Paragraph(_safe(fr.acceptance_criteria), cell_style),
            ]
        )
    story.append(_styled_table(fr_rows, [0.7 * inch, 3.2 * inch, 0.8 * inch, 2.5 * inch]))

    # 5. Non-Functional Requirements
    story.append(Paragraph("4. Non-Functional Requirements", h2_style))
    nfr_rows = [
        [
            Paragraph("ID", header_cell),
            Paragraph("Category", header_cell),
            Paragraph("Requirement", header_cell),
            Paragraph("Priority", header_cell),
            Paragraph("Target Metric", header_cell),
        ]
    ]
    for nfr in record.non_functional_requirements:
        nfr_rows.append(
            [
                Paragraph(_safe(nfr.req_code), cell_bold),
                Paragraph(_safe(nfr.category), cell_style),
                Paragraph(_safe(nfr.requirement), cell_style),
                Paragraph(_safe(nfr.priority), cell_style),
                Paragraph(_safe(nfr.metric_target), cell_style),
            ]
        )
    story.append(
        _styled_table(nfr_rows, [0.7 * inch, 1.1 * inch, 2.7 * inch, 0.8 * inch, 1.9 * inch])
    )

    # 6. Recommended Technology Stack
    story.append(Paragraph("5. Recommended Technology Stack", h2_style))
    stack_rows = [
        [
            Paragraph("Layer", header_cell),
            Paragraph("Recommended Technology", header_cell),
            Paragraph("Rationale & Alternatives", header_cell),
        ]
    ]
    for tech in record.tech_stack:
        alts = f"<br/><i>Alternatives: {_safe(', '.join(tech.alternatives))}</i>" if tech.alternatives else ""
        stack_rows.append(
            [
                Paragraph(_safe(tech.layer), cell_bold),
                Paragraph(_safe(tech.technology), cell_bold),
                Paragraph(f"{_safe(tech.rationale)}{alts}", cell_style),
            ]
        )
    story.append(_styled_table(stack_rows, [1.3 * inch, 1.9 * inch, 4.0 * inch]))

    # 7. Project Timeline & Milestones
    story.append(Paragraph("6. Project Timeline & Milestones", h2_style))
    ms_rows = [
        [
            Paragraph("Phase", header_cell),
            Paragraph("Timeline", header_cell),
            Paragraph("Deliverables", header_cell),
            Paragraph("Dependencies", header_cell),
        ]
    ]
    for ms in record.milestones:
        deliverables_html = "<br/>".join(f"• {_safe(d)}" for d in ms.deliverables) or "-"
        ms_rows.append(
            [
                Paragraph(f"<b>Phase {ms.phase_number}:</b> {_safe(ms.phase_name)}", cell_style),
                Paragraph(f"Weeks {ms.start_week}–{ms.end_week}<br/>({ms.duration_weeks} wks)", cell_style),
                Paragraph(deliverables_html, cell_style),
                Paragraph(_safe(ms.dependencies), cell_style),
            ]
        )
    story.append(_styled_table(ms_rows, [1.8 * inch, 1.1 * inch, 2.8 * inch, 1.5 * inch]))

    # 8. Missing Information & Client Clarification Checklist
    story.append(Paragraph("7. Missing Information & Clarification Questions", h2_style))
    gap_rows = [
        [
            Paragraph("Area", header_cell),
            Paragraph("Severity", header_cell),
            Paragraph("Missing Detail & Impact", header_cell),
            Paragraph("Question for Client", header_cell),
        ]
    ]
    for gap in record.missing_information:
        gap_rows.append(
            [
                Paragraph(_safe(gap.area), cell_bold),
                Paragraph(_safe(gap.severity), cell_style),
                Paragraph(f"{_safe(gap.missing_detail)}<br/><i>Impact: {_safe(gap.impact)}</i>", cell_style),
                Paragraph(_safe(gap.clarifying_question), cell_style),
            ]
        )
    story.append(_styled_table(gap_rows, [1.0 * inch, 0.8 * inch, 2.7 * inch, 2.7 * inch]))

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return buffer.getvalue()

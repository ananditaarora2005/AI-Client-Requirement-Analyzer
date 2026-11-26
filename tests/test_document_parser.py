"""Unit tests for PDF, DOCX, and TXT document parsing."""

import io

from docx import Document
import pytest
from reportlab.pdfgen import canvas

from services.document_parser import DocumentParseError, parse_uploaded_document


def test_parse_txt_document() -> None:
    payload = b"Client needs an inventory tracking web app with RBAC and audit logs."
    parsed = parse_uploaded_document("notes.txt", payload)
    assert parsed.file_type == "TXT"
    assert "inventory tracking" in parsed.text
    assert parsed.word_count > 5


def test_parse_docx_including_tables() -> None:
    doc = Document()
    doc.add_paragraph("Project Overview: Build an internal ticketing portal.")
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "FR-01"
    table.cell(0, 1).text = "User Login via SSO"

    buf = io.BytesIO()
    doc.save(buf)

    parsed = parse_uploaded_document("requirements.docx", buf.getvalue())
    assert parsed.file_type == "DOCX"
    assert "internal ticketing portal" in parsed.text
    assert "FR-01 | User Login via SSO" in parsed.text


def test_parse_pdf_roundtrip() -> None:
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf)
    pdf.drawString(72, 720, "Client Requirement: Build a B2B invoicing dashboard.")
    pdf.save()

    parsed = parse_uploaded_document("client_brief.pdf", buf.getvalue())
    assert parsed.file_type == "PDF"
    assert parsed.page_count == 1
    assert "B2B invoicing dashboard" in parsed.text


def test_parse_rejects_invalid_extension() -> None:
    with pytest.raises(DocumentParseError):
        parse_uploaded_document("image.png", b"12345")

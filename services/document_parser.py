"""Document parsing service for PDF, DOCX, and plain text requirement files."""

from dataclasses import dataclass
import io
from typing import List

from docx import Document
from pypdf import PdfReader

from utils.validators import ValidationError, sanitize_text, validate_uploaded_file


class DocumentParseError(RuntimeError):
    """Raised when an uploaded document cannot be parsed cleanly."""


@dataclass(frozen=True)
class ParsedDocument:
    """Extracted document content and metadata."""

    filename: str
    file_type: str
    text: str
    page_count: int
    char_count: int
    word_count: int


def _extract_pdf_text(file_bytes: bytes) -> tuple[str, int]:
    """Extract text page-by-page from a PDF byte payload."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except Exception as exc:
        raise DocumentParseError(f"Invalid or corrupted PDF file: {exc}") from exc

    if reader.is_encrypted:
        raise DocumentParseError(
            "This PDF is password-protected/encrypted. Please upload an unlocked PDF."
        )

    pages: List[str] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            content = page.extract_text() or ""
        except Exception as exc:
            raise DocumentParseError(f"Failed to read page {index} of PDF: {exc}") from exc
        if content.strip():
            pages.append(content.strip())

    combined = "\n\n".join(pages)
    return combined, len(reader.pages)


def _extract_docx_text(file_bytes: bytes) -> tuple[str, int]:
    """Extract paragraphs and table contents from a DOCX byte payload."""
    try:
        doc = Document(io.BytesIO(file_bytes))
    except Exception as exc:
        raise DocumentParseError(f"Invalid or corrupted DOCX file: {exc}") from exc

    blocks: List[str] = []
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text:
            blocks.append(text)

    # Also capture table rows, which often hold requirement matrices in client specs.
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
            non_empty = [c for c in cells if c]
            if non_empty:
                blocks.append(" | ".join(non_empty))

    combined = "\n".join(blocks)
    # DOCX doesn't encode fixed print pages; estimate ~450 words per logical page.
    word_est = max(1, len(combined.split()) // 450) if combined.strip() else 0
    return combined, word_est


def _extract_txt_text(file_bytes: bytes) -> tuple[str, int]:
    """Decode a plain text requirement file with UTF-8 fallback to Latin-1."""
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1", errors="replace")
    lines = max(1, len(text.splitlines()))
    return text, max(1, lines // 45)


def parse_uploaded_document(
    filename: str,
    file_bytes: bytes,
    max_size_mb: int = 10,
) -> ParsedDocument:
    """Validate and extract clean text from an uploaded PDF, DOCX, or TXT file."""
    try:
        ext = validate_uploaded_file(filename, file_bytes, max_size_mb=max_size_mb)
    except ValidationError as exc:
        raise DocumentParseError(str(exc)) from exc

    if ext == ".pdf":
        raw_text, page_count = _extract_pdf_text(file_bytes)
    elif ext == ".docx":
        raw_text, page_count = _extract_docx_text(file_bytes)
    else:
        raw_text, page_count = _extract_txt_text(file_bytes)

    cleaned = sanitize_text(raw_text)
    if not cleaned:
        raise DocumentParseError(
            "No readable text was found in the uploaded file. "
            "If this is a scanned PDF, please run OCR or paste the text directly."
        )

    return ParsedDocument(
        filename=filename,
        file_type=ext.lstrip(".").upper(),
        text=cleaned,
        page_count=page_count,
        char_count=len(cleaned),
        word_count=len(cleaned.split()),
    )

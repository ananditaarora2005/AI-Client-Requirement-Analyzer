"""Unit tests for input validation and sanitization helpers."""

import pytest

from utils.validators import (
    ValidationError,
    sanitize_text,
    validate_project_metadata,
    validate_requirement_text,
    validate_uploaded_file,
)


def test_sanitize_text_normalizes_whitespace() -> None:
    raw = "Line 1\r\n\r\n\r\n\r\nLine 2\x00"
    assert sanitize_text(raw) == "Line 1\n\nLine 2"


def test_validate_project_metadata_valid() -> None:
    title, client = validate_project_metadata("  CRM Portal  ", "  Acme Corp ")
    assert title == "CRM Portal"
    assert client == "Acme Corp"


def test_validate_project_metadata_rejects_short_inputs() -> None:
    with pytest.raises(ValidationError):
        validate_project_metadata("AB", "Acme")
    with pytest.raises(ValidationError):
        validate_project_metadata("Valid Title", "A")


def test_validate_requirement_text_enforces_bounds() -> None:
    with pytest.raises(ValidationError):
        validate_requirement_text("Too short", min_chars=50)

    valid = "A" * 60
    assert validate_requirement_text(valid, min_chars=50) == valid


def test_validate_uploaded_file_checks_extension_and_size() -> None:
    assert validate_uploaded_file("spec.pdf", b"hello", max_size_mb=1) == ".pdf"

    with pytest.raises(ValidationError):
        validate_uploaded_file("malware.exe", b"data", max_size_mb=1)

    with pytest.raises(ValidationError):
        validate_uploaded_file("empty.docx", b"", max_size_mb=1)

    with pytest.raises(ValidationError):
        validate_uploaded_file("huge.pdf", b"x" * (2 * 1024 * 1024), max_size_mb=1)

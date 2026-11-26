"""Input validation and sanitization helpers."""

from pathlib import Path
import re
from typing import Tuple

from config.settings import ALLOWED_UPLOAD_EXTENSIONS


class ValidationError(ValueError):
    """Raised when user-supplied inputs fail validation checks."""


def sanitize_text(text: str) -> str:
    """Normalize line endings, strip control characters, and collapse excessive blank lines."""
    if not text:
        return ""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    # Remove non-printable control characters except newline and tab.
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)
    # Collapse 3+ consecutive newlines into 2 newlines for clean prompting.
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def validate_project_metadata(project_title: str, client_name: str) -> Tuple[str, str]:
    """Validate and clean project title and client name fields."""
    title = sanitize_text(project_title)
    client = sanitize_text(client_name)

    if len(title) < 3:
        raise ValidationError("Project Title must be at least 3 characters long.")
    if len(title) > 120:
        raise ValidationError("Project Title cannot exceed 120 characters.")

    if len(client) < 2:
        raise ValidationError("Client Name must be at least 2 characters long.")
    if len(client) > 100:
        raise ValidationError("Client Name cannot exceed 100 characters.")

    return title, client


def validate_requirement_text(
    text: str,
    min_chars: int = 50,
    max_chars: int = 60000,
) -> str:
    """Validate that raw requirement text is non-empty and within length bounds."""
    cleaned = sanitize_text(text)
    if not cleaned:
        raise ValidationError("Requirement text cannot be empty.")
    if len(cleaned) < min_chars:
        raise ValidationError(
            f"Requirement text is too short ({len(cleaned)} chars). "
            f"Please provide at least {min_chars} characters for meaningful AI analysis."
        )
    if len(cleaned) > max_chars:
        raise ValidationError(
            f"Requirement text exceeds the maximum limit of {max_chars:,} characters."
        )
    return cleaned


def validate_uploaded_file(
    filename: str,
    file_bytes: bytes,
    max_size_mb: int = 10,
) -> str:
    """Validate uploaded document extension, non-empty payload, and file size."""
    if not filename:
        raise ValidationError("Uploaded file is missing a filename.")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        allowed = ", ".join(ALLOWED_UPLOAD_EXTENSIONS)
        raise ValidationError(f"Unsupported file type '{ext}'. Allowed types: {allowed}.")

    if not file_bytes:
        raise ValidationError("The uploaded file is empty (0 bytes).")

    max_bytes = max_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        size_mb = len(file_bytes) / (1024 * 1024)
        raise ValidationError(
            f"File size ({size_mb:.2f} MB) exceeds the {max_size_mb} MB limit."
        )

    return ext

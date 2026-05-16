"""L1 — Input validation: extension, size, and basic integrity checks."""

from pathlib import Path

MAX_FILE_SIZE_MB = 5
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}


def validate_resume_file(file_path: str) -> dict:
    """
    Validate a resume file before parsing.

    Returns:
        {"valid": True, "error": None} or {"valid": False, "error": "reason"}
    """
    path = Path(file_path)

    if not path.exists():
        return {"valid": False, "error": f"File not found: {file_path}"}

    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return {
            "valid": False,
            "error": f"Unsupported file type '{path.suffix}'. Allowed: PDF, DOCX."
        }

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return {
            "valid": False,
            "error": f"File too large ({size_mb:.1f} MB). Maximum allowed: {MAX_FILE_SIZE_MB} MB."
        }

    return {"valid": True, "error": None}


def validate_jd_text(jd_text: str) -> dict:
    """
    Validate job description text input.
    """
    if not jd_text or not jd_text.strip():
        return {"valid": False, "error": "Job description cannot be empty."}

    if len(jd_text.strip()) < 50:
        return {"valid": False, "error": "Job description is too short (minimum 50 characters)."}

    if len(jd_text) > 50_000:
        return {"valid": False, "error": "Job description is too long (maximum 50,000 characters)."}

    return {"valid": True, "error": None}

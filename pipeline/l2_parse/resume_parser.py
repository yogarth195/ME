"""L2 — Resume parser: PDF/DOCX → structured dict with sections + metadata."""

import re
from pathlib import Path
from typing import Optional

import fitz          # PyMuPDF
import docx          # python-docx


# Section heading keywords — order matters (first match wins per line)
SECTION_KEYWORDS = {
    "experience":  ["work experience", "experience", "employment", "work history",
                    "professional experience", "internship", "internships"],
    "education":   ["education", "academic background", "qualifications",
                    "academic qualifications", "degrees"],
    "skills":      ["technical skills", "skills", "core competencies",
                    "technologies", "tools", "competencies", "expertise",
                    "programming languages", "technical expertise"],
    "projects":    ["projects", "personal projects", "academic projects",
                    "key projects", "notable projects", "portfolio"],
    "certifications": ["certifications", "certificates", "courses", "training"],
    "summary":     ["summary", "profile", "objective", "about me",
                    "professional summary", "career objective"],
}

EDUCATION_LEVELS = [
    ("phd",        ["ph.d", "phd", "doctor of philosophy", "doctorate"]),
    ("mtech",      ["m.tech", "mtech", "m.e.", "master of technology"]),
    ("mba",        ["mba", "master of business"]),
    ("msc",        ["m.sc", "msc", "master of science", "m.s."]),
    ("ma",         ["m.a.", "master of arts"]),
    ("masters",    ["master", "masters", "postgraduate", "pg"]),
    ("btech",      ["b.tech", "btech", "b.e.", "bachelor of technology",
                    "bachelor of engineering"]),
    ("bsc",        ["b.sc", "bsc", "bachelor of science", "b.s."]),
    ("bca",        ["bca", "bachelor of computer applications"]),
    ("ba",         ["b.a.", "bachelor of arts"]),
    ("bachelors",  ["bachelor", "bachelors", "undergraduate", "ug", "graduate"]),
    ("diploma",    ["diploma", "polytechnic"]),
    ("highschool", ["12th", "xii", "high school", "secondary"]),
]


def _extract_text_pdf(path: Path) -> str:
    text_parts = []
    with fitz.open(str(path)) as doc:
        for page in doc:
            text_parts.append(page.get_text("text"))
    return "\n".join(text_parts)


def _extract_text_docx(path: Path) -> str:
    doc = docx.Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def _extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _extract_text_pdf(path)
    if ext in (".docx", ".doc"):
        return _extract_text_docx(path)
    raise ValueError(f"Unsupported file type: {ext}")


def _is_section_heading(line: str) -> Optional[str]:
    """Return section key if line looks like a section heading, else None."""
    stripped = line.strip()
    if not stripped or len(stripped) > 60:
        return None

    # Normalise: lowercase, strip trailing colon/dash, collapse whitespace
    cleaned = re.sub(r"\s+", " ", stripped.lower().rstrip(":—-").strip())

    for section, keywords in SECTION_KEYWORDS.items():
        for kw in keywords:
            if cleaned == kw or cleaned.startswith(kw + " ") or cleaned.startswith(kw + ":"):
                return section

    # ALL CAPS headings: "EXPERIENCE", "TECHNICAL SKILLS", etc.
    if stripped == stripped.upper() and stripped.replace(" ", "").isalpha():
        cleaned_upper = re.sub(r"\s+", " ", stripped.lower().rstrip(":—-").strip())
        for section, keywords in SECTION_KEYWORDS.items():
            for kw in keywords:
                if cleaned_upper == kw or cleaned_upper.startswith(kw + " "):
                    return section

    return None


def _detect_sections(text: str) -> dict:
    lines = text.splitlines()
    sections = {k: [] for k in SECTION_KEYWORDS}
    current_section = "summary"

    for line in lines:
        heading = _is_section_heading(line)
        if heading:
            current_section = heading
        else:
            sections[current_section].append(line)

    return {k: "\n".join(v).strip() for k, v in sections.items()}


def _extract_years_of_experience(experience_text: str) -> int:
    """Best-effort: count distinct years mentioned or sum durations."""
    if not experience_text:
        return 0

    # Pattern: "2019 - 2022", "Jan 2020 – Dec 2021", "2021–present"
    year_ranges = re.findall(
        r"(20\d{2}|19\d{2})\s*[-–—to]+\s*(20\d{2}|19\d{2}|present|current|now)",
        experience_text.lower()
    )
    total = 0
    current_year = 2026
    for start, end in year_ranges:
        try:
            s = int(start)
            e = current_year if end in ("present", "current", "now") else int(end)
            total += max(0, e - s)
        except ValueError:
            pass

    if total > 0:
        return min(total, 40)

    # Fallback: look for "X years of experience"
    match = re.search(r"(\d+)\+?\s*years?\s+of\s+experience", experience_text.lower())
    if match:
        return int(match.group(1))

    return 0


def _detect_education_level(text: str) -> str:
    lower = text.lower()
    for level, keywords in EDUCATION_LEVELS:
        for kw in keywords:
            if kw in lower:
                return level
    return "unknown"


def parse_resume(file_path: str) -> dict:
    """
    Parse a resume PDF or DOCX.

    Returns:
        {
            "raw_text": str,
            "sections": {
                "experience": str,
                "education": str,
                "skills": str,
                "projects": str,
                "certifications": str,
                "summary": str,
            },
            "years_of_experience": int,
            "education_level": str,   # e.g. "btech", "mtech", "phd"
            "file_name": str,
        }
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Resume not found: {file_path}")

    raw_text = _extract_text(path)
    sections = _detect_sections(raw_text)
    years = _extract_years_of_experience(sections["experience"])
    edu_level = _detect_education_level(
        sections["education"] + " " + raw_text[:500]
    )

    return {
        "raw_text": raw_text,
        "sections": sections,
        "years_of_experience": years,
        "education_level": edu_level,
        "file_name": path.name,
    }

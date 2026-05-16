"""L2 — JD parser: plain text → structured dict with sections + metadata."""

import re
from typing import Optional


SECTION_KEYWORDS = {
    "required_skills": [
        "required skills", "must have", "must-have", "requirements",
        "required qualifications", "required experience", "you must have",
        "what you'll need", "what you need", "minimum qualifications",
        "mandatory skills", "key skills", "technical requirements",
    ],
    "preferred_skills": [
        "preferred skills", "nice to have", "nice-to-have", "good to have",
        "preferred qualifications", "bonus", "plus", "advantageous",
        "preferred experience", "would be a plus", "desirable",
    ],
    "responsibilities": [
        "responsibilities", "what you'll do", "what you will do",
        "job responsibilities", "key responsibilities", "your role",
        "duties", "role overview", "about the role", "the role",
    ],
    "about": [
        "about the company", "about us", "company overview",
        "who we are", "the company", "overview",
    ],
    "benefits": [
        "benefits", "perks", "what we offer", "compensation",
        "salary", "package",
    ],
}

EDUCATION_LEVELS = [
    ("phd",      ["ph.d", "phd", "doctorate", "doctor of philosophy"]),
    ("masters",  ["master", "masters", "m.tech", "mtech", "m.sc", "msc",
                  "m.s.", "postgraduate", "pg degree"]),
    ("bachelors",["bachelor", "bachelors", "b.tech", "btech", "b.e.",
                  "b.sc", "bsc", "undergraduate", "ug degree",
                  "four year degree", "4 year degree"]),
    ("diploma",  ["diploma", "polytechnic"]),
]


def _detect_section(line: str) -> Optional[str]:
    cleaned = line.strip().lower().rstrip(":").strip()
    if not cleaned or len(cleaned) > 80:
        return None
    for section, keywords in SECTION_KEYWORDS.items():
        for kw in keywords:
            if cleaned == kw or cleaned.startswith(kw):
                return section
    return None


def _extract_required_years(text: str) -> int:
    """Extract minimum years of experience required from JD text."""
    patterns = [
        r"(\d+)\+?\s*years?\s+of\s+(?:relevant\s+)?experience",
        r"(\d+)\+?\s*years?\s+(?:of\s+)?(?:work\s+)?experience",
        r"minimum\s+(?:of\s+)?(\d+)\s*\+?\s*years?",
        r"at\s+least\s+(\d+)\s*\+?\s*years?",
        r"(\d+)\s*[-–]\s*\d+\s*years?\s+(?:of\s+)?experience",
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return int(match.group(1))
    return 0


def _extract_education(text: str) -> str:
    lower = text.lower()
    for level, keywords in EDUCATION_LEVELS:
        for kw in keywords:
            if kw in lower:
                return level
    return "any"


def _split_into_sections(text: str) -> dict:
    sections = {k: [] for k in SECTION_KEYWORDS}
    current = "required_skills"  # default — most JDs start with requirements

    for line in text.splitlines():
        heading = _detect_section(line)
        if heading:
            current = heading
        else:
            sections[current].append(line)

    return {k: "\n".join(v).strip() for k, v in sections.items()}


def parse_jd(jd_text: str) -> dict:
    """
    Parse a raw job description string.

    Returns:
        {
            "raw_text": str,
            "sections": {
                "required_skills": str,
                "preferred_skills": str,
                "responsibilities": str,
                "about": str,
                "benefits": str,
            },
            "required_years": int,
            "required_education": str,   # "bachelors", "masters", "phd", "any"
            "job_title": str,            # first non-empty line, usually the title
        }
    """
    text = jd_text.strip()
    lines = [l for l in text.splitlines() if l.strip()]
    job_title = lines[0].strip() if lines else "Unknown"

    sections = _split_into_sections(text)
    required_years = _extract_required_years(text)
    required_education = _extract_education(text)

    return {
        "raw_text": text,
        "sections": sections,
        "required_years": required_years,
        "required_education": required_education,
        "job_title": job_title,
    }

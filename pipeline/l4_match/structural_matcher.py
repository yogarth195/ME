"""
L4c — Structural Matcher

Compares resume structural signals against JD requirements.
Does NOT look at skill content — that's L4a/L4b's job.
Looks at: years of experience, education level, section completeness.

Why this matters:
  A candidate with 8 years experience applying for a senior role should
  score higher than someone with 1 year, even if their skill lists are
  identical. The graph and semantic matchers are blind to this.

Output: structural_score (0.0 – 1.0) + per-dimension breakdown for SHAP.
"""

from dataclasses import dataclass, asdict

# Education level → numeric rank for comparison arithmetic
EDUCATION_RANK = {
    "highschool": 1,
    "diploma":    2,
    "bachelors":  3,
    "bca":        3,
    "ba":         3,
    "bsc":        3,
    "btech":      3,
    "mba":        4,
    "msc":        4,
    "ma":         4,
    "mtech":      4,
    "masters":    4,
    "phd":        5,
    "unknown":    2,   # penalise missing info slightly
    "any":        3,   # JD has no requirement — treat as bachelors equivalent
}

# Resume section names that indicate a well-structured resume
KEY_SECTIONS = ["experience", "education", "skills", "projects"]


@dataclass
class StructuralScore:
    structural_score: float       # final combined score 0.0 – 1.0

    # Per-dimension scores (fed individually to XGBoost as features)
    yoe_score:       float        # years of experience match
    edu_score:       float        # education level match
    section_score:   float        # resume completeness (has expected sections)

    # Raw signals (for SHAP interpretability)
    resume_yoe:      int          # years extracted from resume
    required_yoe:    int          # years required by JD (0 = not specified)
    resume_edu_rank: int          # numeric rank of resume education
    required_edu_rank: int        # numeric rank of JD required education
    sections_present: list        # which key sections were found in resume

    # Human-readable explanation strings
    yoe_reasoning:   str
    edu_reasoning:   str
    section_reasoning: str

    def to_dict(self) -> dict:
        return asdict(self)


def _score_yoe(resume_yoe: int, required_yoe: int) -> tuple[float, str]:
    """
    Score years-of-experience match.

    If JD has no requirement (required_yoe == 0): full score — no penalty.
    If resume meets or exceeds requirement: full score.
    If resume is within 1 year short: partial score (0.7).
    If resume is 2 years short: 0.4.
    If resume is 3+ years short: 0.1 (not 0 — candidate might still apply).
    """
    if required_yoe == 0:
        return 1.0, "No experience requirement specified — no penalty."

    if resume_yoe == 0:
        # Could not extract YOE from resume — neutral, not zero
        return 0.5, "Could not extract years of experience from resume."

    gap = required_yoe - resume_yoe
    if gap <= 0:
        score = 1.0
        reasoning = f"Meets experience requirement: {resume_yoe} years vs {required_yoe} required."
    elif gap == 1:
        score = 0.7
        reasoning = f"1 year short of requirement: {resume_yoe} years vs {required_yoe} required."
    elif gap == 2:
        score = 0.4
        reasoning = f"2 years short of requirement: {resume_yoe} years vs {required_yoe} required."
    else:
        score = 0.1
        reasoning = f"Significantly under-experienced: {resume_yoe} years vs {required_yoe} required ({gap} year gap)."

    return round(score, 4), reasoning


def _score_education(resume_edu: str, required_edu: str) -> tuple[float, str]:
    """
    Score education match.

    If JD requires no specific level (required_edu == 'any'): full score.
    If resume meets or exceeds requirement: full score.
    If resume is one level below (e.g. bachelors when masters wanted): 0.6.
    If resume is two levels below: 0.3.
    """
    resume_rank   = EDUCATION_RANK.get(resume_edu,   EDUCATION_RANK["unknown"])
    required_rank = EDUCATION_RANK.get(required_edu, EDUCATION_RANK["any"])

    if required_rank <= EDUCATION_RANK["any"]:
        return 1.0, "No specific education requirement — no penalty.", resume_rank, required_rank

    gap = required_rank - resume_rank
    if gap <= 0:
        score = 1.0
        reasoning = f"Meets education requirement: {resume_edu} vs {required_edu} required."
    elif gap == 1:
        score = 0.6
        reasoning = f"One level below requirement: {resume_edu} vs {required_edu} required."
    else:
        score = 0.2
        reasoning = (
            f"Significantly below education requirement: "
            f"{resume_edu} vs {required_edu} required."
        )

    return round(score, 4), reasoning, resume_rank, required_rank


def _score_sections(resume_sections: dict) -> tuple[float, list, str]:
    """
    Score resume completeness based on which key sections are present and non-empty.
    A resume missing experience and skills is likely incomplete or mis-parsed.
    """
    present = [s for s in KEY_SECTIONS if resume_sections.get(s, "").strip()]
    score = round(len(present) / len(KEY_SECTIONS), 4)

    missing = [s for s in KEY_SECTIONS if s not in present]
    if missing:
        reasoning = (
            f"Resume has {len(present)}/{len(KEY_SECTIONS)} key sections. "
            f"Missing: {', '.join(missing)}."
        )
    else:
        reasoning = "Resume has all key sections (experience, education, skills, projects)."

    return score, present, reasoning


def structural_match(
    resume_parsed: dict,
    jd_parsed: dict,
) -> dict:
    """
    Compare resume structural signals against JD requirements.

    Args:
        resume_parsed : output of resume_parser.parse_resume()
        jd_parsed     : output of jd_parser.parse_jd()

    Returns:
        StructuralScore.to_dict() — flat dict with all scores + reasoning strings.
    """
    resume_yoe   = resume_parsed.get("years_of_experience", 0)
    resume_edu   = resume_parsed.get("education_level", "unknown")
    resume_sects = resume_parsed.get("sections", {})

    required_yoe = jd_parsed.get("required_years", 0)
    required_edu = jd_parsed.get("required_education", "any")

    yoe_score, yoe_reasoning = _score_yoe(resume_yoe, required_yoe)
    edu_score, edu_reasoning, resume_edu_rank, required_edu_rank = _score_education(
        resume_edu, required_edu
    )
    section_score, sections_present, section_reasoning = _score_sections(resume_sects)

    # Weighted combination:
    #   YOE: 40% — most JDs gate on this first
    #   Education: 30% — strong requirement in most roles
    #   Section completeness: 30% — proxy for resume quality
    structural_score = round(
        0.40 * yoe_score + 0.30 * edu_score + 0.30 * section_score, 4
    )

    result = StructuralScore(
        structural_score   = structural_score,
        yoe_score          = yoe_score,
        edu_score          = edu_score,
        section_score      = section_score,
        resume_yoe         = resume_yoe,
        required_yoe       = required_yoe,
        resume_edu_rank    = resume_edu_rank,
        required_edu_rank  = required_edu_rank,
        sections_present   = sections_present,
        yoe_reasoning      = yoe_reasoning,
        edu_reasoning      = edu_reasoning,
        section_reasoning  = section_reasoning,
    )

    return result.to_dict()

"""Unit tests for L4c structural matcher."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.l4_match.structural_matcher import structural_match


def _resume(yoe=0, edu="btech", sections=None):
    return {
        "years_of_experience": yoe,
        "education_level": edu,
        "sections": sections or {
            "experience": "some content",
            "education":  "some content",
            "skills":     "some content",
            "projects":   "some content",
        },
    }


def _jd(yoe=0, edu="any"):
    return {"required_years": yoe, "required_education": edu}


def test_perfect_match():
    result = structural_match(_resume(yoe=5, edu="btech"), _jd(yoe=3, edu="bachelors"))
    assert result["structural_score"] == 1.0
    assert result["yoe_score"] == 1.0
    assert result["edu_score"] == 1.0
    assert result["section_score"] == 1.0
    print(f"PASS: perfect match -> {result['structural_score']}")


def test_yoe_gap():
    # 1 year short
    r1 = structural_match(_resume(yoe=2), _jd(yoe=3))
    assert r1["yoe_score"] == 0.7

    # 2 years short
    r2 = structural_match(_resume(yoe=1), _jd(yoe=3))
    assert r2["yoe_score"] == 0.4

    # 3+ years short
    r3 = structural_match(_resume(yoe=0, edu="btech"), _jd(yoe=5))
    assert r3["yoe_score"] == 0.5   # 0 yoe = unknown, gets 0.5 neutral

    print(f"PASS: yoe gap scoring")


def test_no_yoe_requirement():
    result = structural_match(_resume(yoe=0), _jd(yoe=0))
    assert result["yoe_score"] == 1.0
    print(f"PASS: no yoe requirement -> full score")


def test_education_gap():
    # Has bachelors, needs masters → one level below
    r = structural_match(_resume(edu="btech"), _jd(edu="masters"))
    assert r["edu_score"] == 0.6
    print(f"PASS: education one level below -> {r['edu_score']}")


def test_education_exceeds():
    # Has PhD, needs bachelors → full score
    r = structural_match(_resume(edu="phd"), _jd(edu="bachelors"))
    assert r["edu_score"] == 1.0
    print(f"PASS: education exceeds requirement -> {r['edu_score']}")


def test_missing_sections():
    resume = _resume(sections={"experience": "content", "education": "", "skills": "", "projects": ""})
    result = structural_match(resume, _jd())
    assert result["section_score"] == 0.25
    assert result["sections_present"] == ["experience"]
    print(f"PASS: missing sections -> section_score={result['section_score']}")


def test_reasoning_strings_present():
    result = structural_match(_resume(yoe=2, edu="btech"), _jd(yoe=5, edu="masters"))
    assert result["yoe_reasoning"]
    assert result["edu_reasoning"]
    assert result["section_reasoning"]
    print(f"PASS: reasoning strings present")
    print(f"      YOE: {result['yoe_reasoning']}")
    print(f"      Edu: {result['edu_reasoning']}")


def test_full_output_keys():
    result = structural_match(_resume(), _jd())
    expected = [
        "structural_score", "yoe_score", "edu_score", "section_score",
        "resume_yoe", "required_yoe", "resume_edu_rank", "required_edu_rank",
        "sections_present", "yoe_reasoning", "edu_reasoning", "section_reasoning",
    ]
    for key in expected:
        assert key in result, f"Missing key: {key}"
    print(f"PASS: all output keys present")


if __name__ == "__main__":
    test_perfect_match()
    test_yoe_gap()
    test_no_yoe_requirement()
    test_education_gap()
    test_education_exceeds()
    test_missing_sections()
    test_reasoning_strings_present()
    test_full_output_keys()
    print("\nAll structural matcher tests passed.")

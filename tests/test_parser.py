"""Tests for resume and JD parsers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.l2_parse.resume_parser import parse_resume, _detect_education_level, _extract_years_of_experience


def test_education_detection():
    assert _detect_education_level("B.Tech in Computer Science") == "btech"
    assert _detect_education_level("PhD from IIT Delhi") == "phd"
    assert _detect_education_level("Master of Technology") == "mtech"
    assert _detect_education_level("MBA from IIM") == "mba"
    print("PASS: education detection")


def test_years_extraction():
    text = "Software Engineer at Google 2019 - 2022\nIntern at Microsoft 2018 - 2019"
    assert _extract_years_of_experience(text) == 4
    print("PASS: years of experience extraction")


def test_parse_real_resume():
    resume_dir = Path(__file__).parent.parent / "data" / "raw" / "resumes"
    pdfs = list(resume_dir.glob("*.pdf"))
    if not pdfs:
        print("SKIP: no PDFs in data/raw/resumes/ yet — add one to test")
        return

    result = parse_resume(str(pdfs[0]))
    print(f"\nFile: {result['file_name']}")
    print(f"Education: {result['education_level']}")
    print(f"Years of experience: {result['years_of_experience']}")
    print(f"Sections found: {[k for k, v in result['sections'].items() if v]}")
    print(f"Raw text length: {len(result['raw_text'])} chars")
    print("PASS: real resume parsed")


from pipeline.l2_parse.jd_parser import parse_jd


def test_jd_parser():
    jd = """
    Senior Backend Developer

    Requirements:
    3+ years of experience with Python and Django.
    Experience with PostgreSQL and Redis.
    Familiarity with Docker and Kubernetes.
    Bachelor's degree in Computer Science or related field.

    Preferred Skills:
    Experience with AWS or GCP.
    Knowledge of GraphQL.
    """

    result = parse_jd(jd)
    assert result["required_years"] == 3, f"Expected 3, got {result['required_years']}"
    assert result["required_education"] == "bachelors"
    assert "python" in result["sections"]["required_skills"].lower()
    assert "aws" in result["sections"]["preferred_skills"].lower()
    print(f"Job title: {result['job_title']}")
    print(f"Required years: {result['required_years']}")
    print(f"Required education: {result['required_education']}")
    print("PASS: JD parser")


if __name__ == "__main__":
    test_education_detection()
    test_years_extraction()
    test_parse_real_resume()
    test_jd_parser()

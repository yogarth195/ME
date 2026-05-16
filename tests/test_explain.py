"""Tests for L6 evidence mapper + suggestion engine."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.l4_match.graph_matcher import graph_match
from pipeline.l6_explain.evidence_mapper import map_evidence
from pipeline.l6_explain.suggestion_engine import generate_suggestions


SAMPLE_RESUME_TEXT = """
Senior Backend Engineer

EXPERIENCE
Senior Software Engineer at Flipkart (2021-2024)
Built REST APIs using FastAPI and Python serving 10 million requests per day.
Designed microservices architecture using Docker and Kubernetes on AWS.
Optimized PostgreSQL queries reducing latency by 40 percent.
Set up CI/CD pipelines using GitHub Actions for automated deployment.

Software Engineer at Razorpay (2019-2021)
Developed Node.js Express backend for payment processing systems.
Worked with MongoDB and Redis for caching and session management.

SKILLS
Python, Node.js, FastAPI, Express, PostgreSQL, MongoDB, Redis,
Docker, Kubernetes, GitHub Actions, REST, Git, Linux, microservices

EDUCATION
B.Tech Computer Science, DTU 2019

PROJECTS
URL shortener with Redis caching and PostgreSQL persistence.
REST API rate limiter using token bucket algorithm in Python.
"""

JD_SKILLS = ["python", "docker", "postgresql", "rest", "nodejs", "cicd", "terraform"]


def test_evidence_found():
    result = graph_match(resume_skills=["python", "docker", "postgresql", "rest", "nodejs"],
                         jd_skills=JD_SKILLS)
    evidence = map_evidence(result["matched"], SAMPLE_RESUME_TEXT)

    print("\n=== Evidence Mapper Output ===")
    for r in evidence["evidence"]:
        status = "FOUND" if r["has_evidence"] else "MISSING"
        print(f"\n[{status}] {r['jd_skill']} ({r['match_type']})")
        if r["evidence"]:
            for sent in r["evidence"]:
                print(f"  -> \"{sent[:100]}\"")
        else:
            print(f"  -> {r['reasoning']}")

    print(f"\nCoverage with evidence: {evidence['coverage_with_evidence']:.0%}")
    assert evidence["coverage_with_evidence"] > 0
    print("PASS: evidence mapper")


def test_suggestions_and_counterfactual():
    result = graph_match(resume_skills=["python", "docker", "postgresql"],
                         jd_skills=JD_SKILLS)
    evidence = map_evidence(result["matched"], SAMPLE_RESUME_TEXT)
    partial  = [r for r in result["matched"] if r["match_type"] not in ("exact", "no_match")]

    output = generate_suggestions(
        missing_skills  = evidence["missing_skills"],
        partial_matches = partial,
        jd_skills       = JD_SKILLS,
        graph_score     = result["graph_score"],
        threshold       = 0.7,
    )

    print("\n=== Suggestions ===")
    for s in output["suggestions"]:
        print(f"  P{s['priority']} | {s['skill']:20} | gain={s['score_gain']} | {s['resource']['platform']}")
        print(f"       {s['reason']}")

    print(f"\n=== Counterfactual ===")
    cf = output["counterfactual"]
    print(f"  {cf['explanation']}")
    print(f"  Skills to add: {cf['skills_needed']}")

    assert len(output["suggestions"]) > 0
    assert "explanation" in output["counterfactual"]
    print("\nPASS: suggestion engine + counterfactual")


def test_predictor():
    from pipeline.l5_classify.predictor import predict
    features = {
        "graph_score": 0.85, "coverage": 0.85, "exact_matches": 5,
        "partial_matches": 1, "no_matches": 1, "sbert_score": 0.72,
        "structural_score": 0.9, "yoe_score": 1.0, "edu_score": 1.0,
        "section_score": 1.0, "resume_yoe": 5, "required_yoe": 3,
        "resume_edu_rank": 3, "required_edu_rank": 3,
    }
    result = predict(features)
    print(f"\n=== Predictor Output ===")
    print(f"  Label      : {result['label']} ({'match' if result['label'] else 'no match'})")
    print(f"  Probability: {result['probability']:.0%}")
    print(f"  Explanation: {result['explanation']}")
    print(f"  Top reasons:")
    for r in result["top_reasons"]:
        print(f"    {r['feature']:25} SHAP={r['shap']:+.4f}  {r['reasoning']}")
    assert result["label"] == 1
    print("PASS: predictor")


if __name__ == "__main__":
    test_evidence_found()
    test_suggestions_and_counterfactual()
    test_predictor()
    print("\nAll explanation tests passed.")

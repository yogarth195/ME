"""End-to-end pipeline test using a real PDF resume if available, else a DOCX stub."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.l7_present.pipeline_runner import run_pipeline

SAMPLE_JD = """
Senior Backend Engineer

We are looking for a Senior Backend Engineer with 3+ years of experience.

Requirements:
- 3+ years of backend development experience
- Strong Python or Node.js skills
- REST API design and development
- PostgreSQL or MongoDB experience
- Docker and Kubernetes
- CI/CD pipeline experience
- Bachelor's degree in Computer Science or related field

Nice to have:
- AWS experience
- Microservices architecture knowledge
- Redis caching experience
"""


def test_pipeline_validation():
    result = run_pipeline(resume_path="nonexistent.pdf", jd_text=SAMPLE_JD)
    assert result["status"] == "error"
    assert "not found" in result["error"].lower()
    print("PASS: validation catches missing file")

    result2 = run_pipeline(resume_path="fake.txt", jd_text=SAMPLE_JD)
    assert result2["status"] == "error"
    print("PASS: validation catches wrong file type")

    result3 = run_pipeline(resume_path="fake.pdf", jd_text="too short")
    assert result3["status"] == "error"
    print("PASS: validation catches short JD")


def test_pipeline_with_resume():
    search_dirs = [
        Path(__file__).parent.parent / "data" / "raw",
        Path(__file__).parent.parent / "data",
        Path(__file__).parent.parent,
    ]
    resume_path = None
    for d in search_dirs:
        files = list(d.glob("*.pdf")) + list(d.glob("*.docx"))
        if files:
            resume_path = str(files[0])
            break

    if not resume_path:
        print("\nNo resume file found — drop a PDF into data/raw/ to test end-to-end.")
        print("Skipping file-based test.")
        return

    print(f"\nTesting with: {resume_path}")
    result = run_pipeline(resume_path=resume_path, jd_text=SAMPLE_JD)
    _print_result(result)


def _print_result(result: dict):
    if result["status"] == "error":
        print(f"ERROR: {result['error']}")
        return

    print(f"\n{'='*60}")
    print(f"JD      : {result['jd_meta']['job_title']}")
    print(f"Resume  : {result['resume_meta']['file_name']}")
    print(f"{'='*60}")
    print(f"PREDICTION   : {'MATCH' if result['label'] == 1 else 'NO MATCH'} ({result['probability']:.0%} confidence)")
    print(f"Graph score  : {result['graph_score']:.0%}")
    print(f"SBERT score  : {result['sbert_score']:.0%}")
    print(f"Structural   : {result['structural_score']:.0%}")
    print(f"Coverage     : {result['coverage']:.0%}")
    print(f"\nExplanation  : {result['explanation']}")

    print(f"\nTop SHAP reasons:")
    for r in result["top_reasons"]:
        print(f"  {r['feature']:25} {r['reasoning']}")

    print(f"\nSkill evidence:")
    for m in result["matched"]:
        tag = "OK" if m["has_evidence"] else "--"
        print(f"  [{tag}] {m['jd_skill']:20} ({m['match_type']})")
        for sent in m["evidence"]:
            print(f"        -> \"{sent[:90]}\"")

    print(f"\nMissing : {result['missing_skills']}")
    print(f"\nCounterfactual:")
    print(f"  {result['counterfactual']['explanation']}")

    print(f"\nSuggestions (top 3):")
    for s in result["suggestions"][:3]:
        print(f"  P{s['priority']} | {s['skill']:20} | {s['resource']['platform']}")

    print(f"\nTiming  : {result['timing_ms']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    test_pipeline_validation()
    print()
    test_pipeline_with_resume()
    print("\nPipeline test complete.")

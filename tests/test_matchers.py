"""Unit tests for L4a graph matcher."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.l4_match.graph_matcher import graph_match, DISTANCE_WEIGHTS


def test_exact_match():
    result = graph_match(
        resume_skills=["python", "docker", "postgresql"],
        jd_skills=["python", "docker", "postgresql"],
    )
    assert result["graph_score"] == 1.0
    assert result["match_summary"]["exact"] == 3
    print(f"PASS: exact match → score {result['graph_score']}")


def test_alias_match():
    # k8s is alias of kubernetes
    result = graph_match(
        resume_skills=["kubernetes", "python"],
        jd_skills=["kubernetes", "python"],
    )
    assert result["graph_score"] == 1.0

    result2 = graph_match(
        resume_skills=["python"],
        jd_skills=["kubernetes", "python"],
    )
    assert result2["match_summary"]["no_match"] == 1
    print(f"PASS: alias match → score {result['graph_score']}")


def test_child_parent_match():
    # pytorch is child of deep_learning
    result = graph_match(
        resume_skills=["pytorch"],
        jd_skills=["deep_learning"],
    )
    assert result["matched"][0]["match_type"] == "child_parent"
    assert result["matched"][0]["weight"] == DISTANCE_WEIGHTS["child_parent"]
    assert result["graph_score"] == DISTANCE_WEIGHTS["child_parent"]
    print(f"PASS: child→parent match → score {result['graph_score']}")
    print(f"      Reasoning: {result['matched'][0]['reasoning']}")


def test_parent_child_match():
    # deep_learning is parent of pytorch — resume has concept, JD wants specific tool
    result = graph_match(
        resume_skills=["deep_learning"],
        jd_skills=["pytorch"],
    )
    assert result["matched"][0]["match_type"] == "parent_child"
    assert result["matched"][0]["weight"] == DISTANCE_WEIGHTS["parent_child"]
    print(f"PASS: parent→child match → score {result['graph_score']}")
    print(f"      Reasoning: {result['matched'][0]['reasoning']}")


def test_sibling_match():
    # pytorch and tensorflow are both children of deep_learning
    result = graph_match(
        resume_skills=["pytorch"],
        jd_skills=["tensorflow"],
    )
    assert result["matched"][0]["match_type"] == "sibling"
    assert result["matched"][0]["weight"] == DISTANCE_WEIGHTS["sibling"]
    print(f"PASS: sibling match → score {result['graph_score']}")
    print(f"      Reasoning: {result['matched'][0]['reasoning']}")


def test_no_match():
    result = graph_match(
        resume_skills=["python"],
        jd_skills=["kubernetes"],
    )
    assert result["matched"][0]["match_type"] == "no_match"
    assert result["graph_score"] == 0.0
    print(f"PASS: no match → score {result['graph_score']}")


def test_mixed_match():
    # kubernetes is a child of docker, so knowing kubernetes proves docker knowledge
    # docker should match via child_parent, not be unmatched
    result = graph_match(
        resume_skills=["kubernetes", "python"],
        jd_skills=["kubernetes", "docker", "python"],
    )
    assert result["graph_score"] > 0.6
    docker_match = next(r for r in result["matched"] if r["jd_skill"] == "docker")
    assert docker_match["match_type"] == "child_parent"

    # spark has no relation to python/kubernetes — should be unmatched
    result2 = graph_match(
        resume_skills=["kubernetes", "python"],
        jd_skills=["kubernetes", "python", "spark"],
    )
    assert "spark" in result2["unmatched_jd_skills"]
    print(f"PASS: mixed match → score {result['graph_score']}")
    print(f"      Matched: {[(r['jd_skill'], r['match_type']) for r in result['matched']]}")


def test_real_resume_vs_jd():
    # Simulate your actual resume vs a backend JD
    resume = ["javascript", "typescript", "react", "nodejs", "mongodb",
              "postgresql", "python", "docker", "git", "rest", "nextjs"]

    jd = ["nodejs", "python", "postgresql", "docker", "kubernetes",
          "rest", "mongodb", "cicd"]

    result = graph_match(resume_skills=resume, jd_skills=jd)
    print(f"\nPASS: real resume vs backend JD")
    print(f"      Score: {result['graph_score']}")
    print(f"      Coverage: {result['coverage']}")
    print(f"      Summary: {result['match_summary']}")
    print(f"      Unmatched: {result['unmatched_jd_skills']}")
    for r in result["matched"]:
        status = "✅" if r["match_type"] != "no_match" else "❌"
        print(f"      {status} {r['jd_skill']:20} → {r['match_type']:15} (w={r['weight']})")


def test_chef_applying_for_backend():
    # Chef has zero tech skills — should get low score + domain mismatch warning
    chef_skills = []  # chef has no ontology skills at all
    backend_jd  = ["python", "docker", "postgresql", "rest", "nodejs"]

    result = graph_match(resume_skills=chef_skills, jd_skills=backend_jd)
    assert result["graph_score"] == 0.0
    assert result["coverage"] == 0.0
    print(f"\nPASS: chef applying for backend role")
    print(f"      Score: {result['graph_score']} (correctly 0)")
    print(f"      All unmatched: {result['unmatched_jd_skills']}")

    # Now test someone with food/unrelated skills that happen to not be in ontology
    result2 = graph_match(
        resume_skills=["python"],   # knows python but nothing else
        jd_skills=["kubernetes", "docker", "cicd", "terraform", "ansible"],
    )
    print(f"\n      Partial mismatch (only python, needs devops):")
    print(f"      Score: {result2['graph_score']}")
    print(f"      Domain mismatch: {result2['domain_mismatch']['is_mismatch']}")
    if result2['domain_mismatch']['warning']:
        print(f"      Warning: {result2['domain_mismatch']['warning']}")


from pipeline.l4_match.semantic_matcher import semantic_match


def test_semantic_similar():
    resume = """
    Experienced backend developer with 3 years building REST APIs using Python,
    FastAPI, PostgreSQL and Docker. Deployed microservices on AWS. Strong knowledge
    of distributed systems and CI/CD pipelines.
    """
    jd = """
    We are looking for a Backend Engineer with experience in Python, REST APIs,
    PostgreSQL, Docker and AWS. Knowledge of microservices architecture required.
    """
    result = semantic_match(resume, jd)
    assert result["sbert_score"] > 0.5, f"Expected >0.5, got {result['sbert_score']}"
    print(f"PASS: similar texts → sbert_score={result['sbert_score']} — {result['interpretation']}")


def test_semantic_different():
    chef_resume = """
    Professional chef with 5 years experience in fine dining. Expert in French cuisine,
    menu planning, kitchen management, food safety, and team leadership.
    Trained at Le Cordon Bleu. Specialized in pastry and desserts.
    """
    backend_jd = """
    Senior Backend Developer needed with Python, Django, PostgreSQL, Docker,
    Kubernetes, Redis, AWS, CI/CD, microservices architecture experience.
    """
    result = semantic_match(chef_resume, backend_jd)
    assert result["sbert_score"] < 0.5, f"Expected <0.5, got {result['sbert_score']}"
    print(f"PASS: chef vs backend JD → sbert_score={result['sbert_score']} — {result['interpretation']}")


def test_semantic_empty():
    result = semantic_match("", "some jd text")
    assert result["sbert_score"] == 0.0
    print("PASS: empty input → score 0.0")


if __name__ == "__main__":
    test_exact_match()
    test_alias_match()
    test_child_parent_match()
    test_parent_child_match()
    test_sibling_match()
    test_no_match()
    test_mixed_match()
    test_real_resume_vs_jd()
    test_chef_applying_for_backend()
    print("\n--- Semantic Matcher ---")
    test_semantic_similar()
    test_semantic_different()
    test_semantic_empty()
    print("\nAll matcher tests passed.")

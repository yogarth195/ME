"""
L6 — Suggestion Engine + Counterfactual Explainer.

Two jobs:
  1. Suggestion engine: for each missing/weak skill, suggest how to learn it.
  2. Counterfactual: "if you add X skills, your match score crosses threshold Y."

Why counterfactuals matter for a research paper:
  Standard explainability (SHAP) tells you why you scored low.
  Counterfactuals tell you what to DO about it — actionable, not just diagnostic.
  This is the key novelty claim of ExplainHire.
"""

# Learning resource suggestions per skill node
# Format: (resource_type, description, url_hint)
SKILL_RESOURCES: dict[str, list[dict]] = {
    "python":           [{"type": "course",   "title": "Python for Everybody",        "platform": "Coursera"}],
    "javascript":       [{"type": "course",   "title": "The Complete JavaScript Course","platform": "Udemy"}],
    "typescript":       [{"type": "docs",     "title": "TypeScript Handbook",          "platform": "typescriptlang.org"}],
    "react":            [{"type": "course",   "title": "React - The Complete Guide",   "platform": "Udemy"}],
    "nodejs":           [{"type": "course",   "title": "Node.js Developer Course",     "platform": "Udemy"}],
    "docker":           [{"type": "course",   "title": "Docker & Kubernetes: The Practical Guide", "platform": "Udemy"}],
    "kubernetes":       [{"type": "course",   "title": "Certified Kubernetes Administrator", "platform": "Linux Foundation"}],
    "postgresql":       [{"type": "course",   "title": "PostgreSQL for Everybody",     "platform": "Coursera"}],
    "mongodb":          [{"type": "docs",     "title": "MongoDB University",           "platform": "MongoDB"}],
    "aws":              [{"type": "cert",     "title": "AWS Cloud Practitioner",       "platform": "AWS"}],
    "amazon_web_services": [{"type": "cert", "title": "AWS Solutions Architect",      "platform": "AWS"}],
    "tensorflow":       [{"type": "course",   "title": "Deep Learning Specialization", "platform": "Coursera"}],
    "pytorch":          [{"type": "course",   "title": "PyTorch for Deep Learning",   "platform": "Udemy"}],
    "machine_learning": [{"type": "course",   "title": "Machine Learning Specialization","platform": "Coursera"}],
    "deep_learning":    [{"type": "course",   "title": "Deep Learning Specialization", "platform": "Coursera"}],
    "cicd":             [{"type": "course",   "title": "CI/CD with GitHub Actions",   "platform": "Udemy"}],
    "terraform":        [{"type": "cert",     "title": "HashiCorp Terraform Associate","platform": "HashiCorp"}],
    "spark":            [{"type": "course",   "title": "Apache Spark with Python",    "platform": "Udemy"}],
    "kafka":            [{"type": "course",   "title": "Apache Kafka Series",         "platform": "Udemy"}],
    "sql":              [{"type": "course",   "title": "SQL for Data Science",        "platform": "Coursera"}],
    "git":              [{"type": "docs",     "title": "Pro Git Book",                "platform": "git-scm.com"}],
    "linux":            [{"type": "course",   "title": "Linux Command Line Basics",   "platform": "Udemy"}],
    "fastapi":          [{"type": "docs",     "title": "FastAPI Official Tutorial",   "platform": "fastapi.tiangolo.com"}],
    "django":           [{"type": "docs",     "title": "Django Official Tutorial",    "platform": "djangoproject.com"}],
    "rest":             [{"type": "article",  "title": "RESTful API Design Guide",    "platform": "restfulapi.net"}],
    "microservices":    [{"type": "course",   "title": "Microservices with Node.js",  "platform": "Udemy"}],
    "redis":            [{"type": "docs",     "title": "Redis University",            "platform": "Redis"}],
    "graphql":          [{"type": "docs",     "title": "GraphQL Official Learn",      "platform": "graphql.org"}],
    "nextjs":           [{"type": "docs",     "title": "Next.js Official Tutorial",   "platform": "nextjs.org"}],
    "flutter":          [{"type": "docs",     "title": "Flutter Codelabs",            "platform": "flutter.dev"}],
    "kotlin":           [{"type": "course",   "title": "Kotlin for Android",          "platform": "Udemy"}],
    "swift":            [{"type": "docs",     "title": "Swift Programming Guide",     "platform": "swift.org"}],
}

DEFAULT_RESOURCE = {"type": "search", "title": "Search on Udemy or Coursera", "platform": "General"}


def _get_resource(skill: str) -> dict:
    resources = SKILL_RESOURCES.get(skill)
    if resources and isinstance(resources, list):
        return resources[0]
    return DEFAULT_RESOURCE


def _estimate_score_gain(
    skill: str,
    current_matched: list[dict],
    jd_skills: list[str],
    graph_score: float,
) -> float:
    """
    Estimate how much graph_score would improve if this skill were added.
    Simple approximation: adding 1 exact match improves score by 1/len(jd_skills).
    """
    if not jd_skills:
        return 0.0
    return round(1.0 / len(jd_skills), 4)


def generate_suggestions(
    missing_skills: list[str],
    partial_matches: list[dict],
    jd_skills: list[str],
    graph_score: float,
    threshold: float = 0.7,
) -> dict:
    """
    Generate skill suggestions and counterfactual explanation.

    Args:
        missing_skills  : JD skills with no match (from evidence_mapper)
        partial_matches : matched records with match_type != 'exact'
        jd_skills       : full list of JD required skills
        graph_score     : current graph_score
        threshold       : score threshold to cross (default 0.7 = "good match")

    Returns:
        {
            "suggestions": [
                {
                    "skill":        str,
                    "priority":     int,     # 1=critical, 2=important, 3=nice-to-have
                    "reason":       str,
                    "score_gain":   float,   # estimated graph_score improvement
                    "resource":     dict,
                },
                ...
            ],
            "counterfactual": {
                "current_score":  float,
                "threshold":      float,
                "gap":            float,
                "skills_needed":  list[str],  # minimum skills to add to cross threshold
                "explanation":    str,
            }
        }
    """
    suggestions = []

    # Priority 1: missing skills (no match at all)
    for skill in missing_skills:
        gain = _estimate_score_gain(skill, [], jd_skills, graph_score)
        suggestions.append({
            "skill":      skill,
            "priority":   1,
            "reason":     f"'{skill}' is required by the JD but not found anywhere in your resume.",
            "score_gain": gain,
            "resource":   _get_resource(skill),
        })

    # Priority 2: parent→child gaps (you know the concept but not the specific tool)
    for record in partial_matches:
        if record["match_type"] == "parent_child":
            skill = record["jd_skill"]
            via   = record.get("matched_via", "")
            suggestions.append({
                "skill":      skill,
                "priority":   2,
                "reason":     (
                    f"You know '{via}' but the JD specifically wants '{skill}'. "
                    f"Hands-on practice with '{skill}' would strengthen this match."
                ),
                "score_gain": round(_estimate_score_gain(skill, [], jd_skills, graph_score) * 0.3, 4),
                "resource":   _get_resource(skill),
            })

    # Priority 3: sibling gaps (related but not the same)
    for record in partial_matches:
        if record["match_type"] == "sibling":
            skill = record["jd_skill"]
            via   = record.get("matched_via", "")
            suggestions.append({
                "skill":      skill,
                "priority":   3,
                "reason":     (
                    f"You know '{via}' which is related to '{skill}', "
                    f"but they are different tools. Adding '{skill}' would be a direct match."
                ),
                "score_gain": round(_estimate_score_gain(skill, [], jd_skills, graph_score) * 0.2, 4),
                "resource":   _get_resource(skill),
            })

    # Sort by priority then score_gain
    suggestions.sort(key=lambda x: (x["priority"], -x["score_gain"]))

    # ── Counterfactual ─────────────────────────────────────────────────────────
    gap = round(threshold - graph_score, 4)
    skills_needed = []
    simulated_score = graph_score

    if gap > 0:
        # Greedily add missing skills until threshold is crossed
        for s in suggestions:
            if simulated_score >= threshold:
                break
            skills_needed.append(s["skill"])
            simulated_score = round(simulated_score + s["score_gain"], 4)

        if simulated_score >= threshold:
            cf_explanation = (
                f"Your current skill match score is {graph_score:.0%}. "
                f"To reach the {threshold:.0%} threshold, add these {len(skills_needed)} skill(s): "
                f"{', '.join(skills_needed)}. "
                f"Estimated score after adding them: {simulated_score:.0%}."
            )
        else:
            cf_explanation = (
                f"Your current skill match score is {graph_score:.0%}. "
                f"Even adding all missing skills would bring you to {simulated_score:.0%}, "
                f"which is below the {threshold:.0%} threshold. "
                f"This role may require a significant skill pivot."
            )
    else:
        skills_needed = []
        cf_explanation = (
            f"Your skill match score is {graph_score:.0%}, already above the "
            f"{threshold:.0%} threshold. Focus on highlighting these skills in your resume."
        )

    return {
        "suggestions": suggestions,
        "counterfactual": {
            "current_score": graph_score,
            "threshold":     threshold,
            "gap":           max(gap, 0.0),
            "skills_needed": skills_needed,
            "explanation":   cf_explanation,
        },
    }

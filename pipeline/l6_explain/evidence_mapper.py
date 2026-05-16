"""
L6 — Evidence Mapper.

For each skill that matched between resume and JD, finds the actual
sentence(s) in the resume that prove the candidate has that skill.

Why this matters:
  Saying "docker matched at 0.7" is not explainable. Saying:
  "docker matched because you wrote: 'Deployed microservices on Docker
  and Kubernetes serving 10M requests/day'" is explainable.
  This is what separates ExplainHire from a keyword matcher.

Also identifies missing skills — JD requirements with no evidence in resume.
"""

import re


def _split_sentences(text: str) -> list[str]:
    """Split resume text into sentences. Handles bullet points too."""
    # Split on sentence boundaries and bullet points
    raw = re.split(r"(?<=[.!?])\s+|\n[-•*]\s*|\n+", text)
    sentences = []
    for s in raw:
        s = s.strip().strip("-•*").strip()
        if len(s) > 15:   # skip fragment lines
            sentences.append(s)
    return sentences


def _sentence_contains_skill(sentence: str, skill: str) -> bool:
    """Check if a sentence mentions a skill (node ID or readable form)."""
    sentence_lower = sentence.lower()
    variants = {
        skill.lower(),
        skill.lower().replace("_", " "),
        skill.lower().replace("_", "."),   # e.g. node.js
        skill.lower().replace("_", ""),    # e.g. nodejs -> nodejs
    }
    # Special common cases
    special = {
        "nodejs":       ["node.js", "node js", "nodejs"],
        "nextjs":       ["next.js", "next js", "nextjs"],
        "vuejs":        ["vue.js", "vue js"],
        "reactjs":      ["react.js", "react js"],
        "postgresql":   ["postgres", "postgresql"],
        "amazon_web_services": ["aws", "amazon web services"],
        "cicd":         ["ci/cd", "ci cd", "cicd"],
        "github_actions": ["github actions"],
        "gitlab_cicd":  ["gitlab ci", "gitlab cicd"],
        "tailwindcss":  ["tailwind css", "tailwind"],
    }
    if skill.lower() in special:
        variants.update(special[skill.lower()])

    for variant in variants:
        pattern = r"(?<![a-z0-9])" + re.escape(variant) + r"(?![a-z0-9])"
        if re.search(pattern, sentence_lower):
            return True
    return False


def _find_evidence(skill: str, matched_via: str, resume_text: str) -> list[str]:
    """
    Find sentences in resume text that mention the skill or its matched alias.
    Returns up to 2 best evidence sentences.
    """
    sentences = _split_sentences(resume_text)
    evidence = []

    search_terms = {skill}
    if matched_via and matched_via != skill:
        search_terms.add(matched_via)

    for sentence in sentences:
        for term in search_terms:
            if _sentence_contains_skill(sentence, term):
                # Avoid duplicates and overly short sentences
                if sentence not in evidence:
                    evidence.append(sentence)
                break

        if len(evidence) >= 2:
            break

    return evidence


def map_evidence(
    matched: list[dict],
    resume_text: str,
) -> dict:
    """
    Map each matched JD skill to supporting evidence in the resume.

    Args:
        matched     : list of match records from graph_match()["matched"]
        resume_text : full raw resume text

    Returns:
        {
            "evidence": [
                {
                    "jd_skill":    str,
                    "match_type":  str,
                    "matched_via": str,
                    "reasoning":   str,   # from graph_matcher
                    "evidence":    list[str],  # sentences from resume
                    "has_evidence": bool,
                },
                ...
            ],
            "missing_skills": [str],   # JD skills with no_match AND no evidence
            "coverage_with_evidence": float,  # % of JD skills with actual proof
        }
    """
    evidence_records = []
    missing_skills = []

    for record in matched:
        jd_skill   = record["jd_skill"]
        match_type = record["match_type"]
        matched_via = record.get("matched_via") or jd_skill

        if match_type == "no_match":
            missing_skills.append(jd_skill)
            evidence_records.append({
                "jd_skill":    jd_skill,
                "match_type":  match_type,
                "matched_via": None,
                "reasoning":   record.get("reasoning", ""),
                "evidence":    [],
                "has_evidence": False,
            })
            continue

        sentences = _find_evidence(jd_skill, matched_via, resume_text)

        evidence_records.append({
            "jd_skill":    jd_skill,
            "match_type":  match_type,
            "matched_via": matched_via,
            "reasoning":   record.get("reasoning", ""),
            "evidence":    sentences,
            "has_evidence": len(sentences) > 0,
        })

    total = len(matched)
    with_evidence = sum(1 for r in evidence_records if r["has_evidence"])
    coverage_with_evidence = round(with_evidence / total, 4) if total > 0 else 0.0

    return {
        "evidence":               evidence_records,
        "missing_skills":         missing_skills,
        "coverage_with_evidence": coverage_with_evidence,
    }

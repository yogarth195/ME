"""L2 — Skill extractor: scan text against ontology nodes + alias table."""

import json
import pickle
import re
from functools import lru_cache
from pathlib import Path

ONTOLOGY_DIR = Path(__file__).parent.parent.parent / "ontology"

# Section confidence multipliers: how much to trust a skill mention per section
SECTION_CONFIDENCE = {
    "experience":     1.0,
    "projects":       0.9,
    "skills":         0.8,
    "certifications": 0.75,
    "summary":        0.6,
    "education":      0.5,
}
DEFAULT_CONFIDENCE = 0.5


@lru_cache(maxsize=1)
def _load_resources() -> tuple:
    alias_path = ONTOLOGY_DIR / "alias_table.json"
    with open(alias_path, encoding="utf-8") as f:
        alias_table = {k: v for k, v in json.load(f).items() if k != "_comment"}

    graph_path = ONTOLOGY_DIR / "skill_ontology.gpickle"
    with open(graph_path, "rb") as f:
        G = pickle.load(f)

    skill_nodes = {n for n in G.nodes if not n.startswith("_alias_")}
    return alias_table, skill_nodes


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def extract_skills(text: str) -> list[str]:
    """
    Scan text against ontology nodes and alias table.
    Returns list of canonical skill node IDs found in the text.
    """
    alias_table, skill_nodes = _load_resources()
    normalized = _normalize_text(text)
    found = set()

    all_terms = sorted(
        list(alias_table.keys()) + list(skill_nodes),
        key=len,
        reverse=True,
    )

    for term in all_terms:
        term_lower = term.lower().replace("_", " ")
        pattern = r"(?<![a-z0-9_])" + re.escape(term_lower) + r"(?![a-z0-9_])"
        if re.search(pattern, normalized):
            if term in alias_table:
                found.add(alias_table[term])
            elif term in skill_nodes:
                found.add(term)

    return sorted(found)


def extract_skills_from_sections(sections: dict) -> dict:
    """
    Extract skills from each resume/JD section with per-section confidence.

    Returns:
        {
            "by_section": {
                "experience": ["docker", "nodejs"],
                "skills":     ["python", "react"],
                ...
            },
            "skill_records": [
                {
                    "skill":      "docker",
                    "count":      2,          # how many sections mention it
                    "sections":   ["experience", "projects"],
                    "confidence": 0.95,       # max section confidence seen
                },
                ...
            ],
            "all": ["docker", "nodejs", "python", ...]  # deduplicated canonical list
        }
    """
    by_section: dict[str, list] = {}
    skill_section_map: dict[str, list] = {}

    for section_name, text in sections.items():
        if not text:
            by_section[section_name] = []
            continue
        skills = extract_skills(text)
        by_section[section_name] = skills
        for skill in skills:
            skill_section_map.setdefault(skill, []).append(section_name)

    skill_records = []
    for skill, seen_in in skill_section_map.items():
        best_conf = max(
            SECTION_CONFIDENCE.get(s, DEFAULT_CONFIDENCE) for s in seen_in
        )
        skill_records.append({
            "skill":      skill,
            "count":      len(seen_in),
            "sections":   sorted(set(seen_in)),
            "confidence": round(best_conf, 4),
        })

    skill_records.sort(key=lambda r: (-r["confidence"], -r["count"], r["skill"]))

    return {
        "by_section":    by_section,
        "skill_records": skill_records,
        "all":           sorted(skill_section_map.keys()),
    }

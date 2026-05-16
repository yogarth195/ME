"""L3 — Skill normalization: raw skill strings → canonical ontology node IDs."""

import json
import pickle
import re
from functools import lru_cache
from pathlib import Path

ONTOLOGY_DIR = Path(__file__).parent.parent.parent / "ontology"


@lru_cache(maxsize=1)
def _load_resources() -> tuple:
    alias_path = ONTOLOGY_DIR / "alias_table.json"
    with open(alias_path, encoding="utf-8") as f:
        alias_table = {k: v for k, v in json.load(f).items() if k != "_comment"}

    graph_path = ONTOLOGY_DIR / "skill_ontology.gpickle"
    with open(graph_path, "rb") as f:
        G = pickle.load(f)

    skill_nodes = set(n for n in G.nodes if not n.startswith("_alias_"))
    return alias_table, skill_nodes


def normalize_skill(raw: str) -> str:
    """
    Normalize a single raw skill string to its canonical ontology node ID.

    Steps:
      1. Lowercase + strip
      2. Check alias_table → return canonical if found
      3. Check if it's already a valid ontology node → return as-is
      4. Try underscore variant (e.g. "machine learning" → "machine_learning")
      5. Return cleaned string as-is (unknown skill — logged for future expansion)

    Examples:
        normalize_skill("JS")           → "javascript"
        normalize_skill("k8s")          → "kubernetes"
        normalize_skill("TensorFlow")   → "tensorflow"
        normalize_skill("React.js")     → "react"
    """
    alias_table, skill_nodes = _load_resources()

    cleaned = raw.strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)

    # Direct alias lookup
    if cleaned in alias_table:
        return alias_table[cleaned]

    # Already a valid node
    if cleaned in skill_nodes:
        return cleaned

    # Try underscore variant ("machine learning" → "machine_learning")
    underscored = cleaned.replace(" ", "_").replace(".", "_").replace("-", "_")
    if underscored in skill_nodes:
        return underscored

    # Try without punctuation
    stripped = re.sub(r"[^a-z0-9\s]", "", cleaned).strip()
    if stripped in alias_table:
        return alias_table[stripped]
    if stripped in skill_nodes:
        return stripped

    return underscored  # return best-effort cleaned form


def normalize_skills(raw_skills: list[str]) -> list[str]:
    """
    Normalize a list of raw skill strings.
    Deduplicates and sorts the result.

    Example:
        normalize_skills(["JS", "k8s", "TensorFlow", "react.js"])
        → ["javascript", "kubernetes", "react", "tensorflow"]
    """
    seen = set()
    result = []
    for raw in raw_skills:
        canonical = normalize_skill(raw)
        if canonical and canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return sorted(result)

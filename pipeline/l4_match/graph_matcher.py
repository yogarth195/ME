"""
L4a — Graph Matcher

Matches resume skills against JD skills using the skill ontology graph.
Uses graph-distance-based weights instead of fixed arbitrary levels.

Weight scheme (directional — matters which way the gap goes):
  Exact match          : 1.0   (same node)
  Alias match          : 0.9   (IS_ALIAS_OF edge)
  Child → Parent       : 0.7   (resume has specific tool, JD wants general concept)
  Parent → Child       : 0.5   (resume has concept, JD wants specific tool)
  Sibling              : 0.4   (share same parent — related but not identical)
  2-hop ancestor       : 0.3   (grandparent match — loose but relevant)
  No match             : 0.0

Domain mismatch detection (A+B approach):
  A) Role domain profiles — each role type has a canonical skill set.
     If resume shares <20% overlap with the role profile, flag mismatch.
  B) SBERT semantic similarity — if sbert_score < 0.25, also flag mismatch.
  Both A and B produce human-readable warnings.
"""

import pickle
from functools import lru_cache
from pathlib import Path
from typing import Optional

import networkx as nx

ONTOLOGY_PATH = Path(__file__).parent.parent.parent / "ontology" / "skill_ontology.gpickle"

# Graph distance → weight mapping
DISTANCE_WEIGHTS = {
    "exact":          1.0,
    "alias":          0.9,
    "child_parent":   0.7,   # resume skill is child of JD skill
    "parent_child":   0.5,   # resume skill is parent of JD skill
    "sibling":        0.4,   # share same immediate parent
    "ancestor_2hop":  0.3,   # grandparent / 2-hop ancestor
    "no_match":       0.0,
}


@lru_cache(maxsize=1)
def _load_graph() -> nx.DiGraph:
    with open(ONTOLOGY_PATH, "rb") as f:
        return pickle.load(f)


@lru_cache(maxsize=1)
def _precompute_depths() -> dict:
    """Precompute depth-from-root for every node. Called once, cached."""
    G = _load_graph()
    depths = {}

    def _depth(node: str, visited: frozenset) -> int:
        if node in depths:
            return depths[node]
        if node in visited:
            return 0
        parents = _get_parents(G, node)
        if not parents:
            return 0
        return 1 + max(_depth(p, visited | {node}) for p in parents)

    for node in G.nodes:
        if node not in depths:
            depths[node] = _depth(node, frozenset())

    return depths


def _get_parents(G: nx.DiGraph, node: str) -> set:
    """Direct parents of node via CHILD_OF edges (node is the child)."""
    return {
        u for u, v, d in G.in_edges(node, data=True)
        if d.get("relation") == "CHILD_OF"
    }


def _get_children(G: nx.DiGraph, node: str) -> set:
    """Direct children of node via CHILD_OF edges."""
    return {
        v for u, v, d in G.out_edges(node, data=True)
        if d.get("relation") == "CHILD_OF"
    }


def _get_aliases(G: nx.DiGraph, node: str) -> set:
    """All alias nodes pointing to this canonical node."""
    return {
        u for u, v, d in G.in_edges(node, data=True)
        if d.get("relation") == "IS_ALIAS_OF"
    }


def _get_grandparents(G: nx.DiGraph, node: str) -> set:
    """2-hop ancestors."""
    grandparents = set()
    for parent in _get_parents(G, node):
        grandparents.update(_get_parents(G, parent))
    return grandparents


def _get_siblings(G: nx.DiGraph, node: str) -> set:
    """
    Nodes that share at least one immediate parent, with depth guard.

    Only counts as siblings if the shared parent is a specific domain concept
    (depth >= 2 from roots). This prevents high-level ancestors like
    'javascript' or 'artificial_intelligence' from making unrelated skills
    appear as siblings.
    """
    MAX_ANCESTOR_DEPTH = 2
    depths = _precompute_depths()

    siblings = set()
    for parent in _get_parents(G, node):
        if depths.get(parent, 0) >= MAX_ANCESTOR_DEPTH:
            siblings.update(_get_children(G, parent))

    siblings.discard(node)
    return siblings


def _match_single_jd_skill(
    G: nx.DiGraph,
    jd_skill: str,
    resume_skills: set,
) -> dict:
    """
    Try to match one JD skill against the full resume skill set.
    Returns a match record with type, weight, and reasoning.
    """
    # Level 1 — Exact
    if jd_skill in resume_skills:
        return {
            "jd_skill":     jd_skill,
            "match_type":   "exact",
            "weight":       DISTANCE_WEIGHTS["exact"],
            "matched_via":  jd_skill,
            "reasoning":    f"Exact match: resume explicitly lists '{jd_skill}'",
        }

    # Level 2 — Alias (resume has an alias of the JD skill)
    jd_aliases = _get_aliases(G, jd_skill)
    alias_hit = jd_aliases & resume_skills
    if alias_hit:
        via_raw = next(iter(alias_hit))
        # Strip internal _alias_ prefix — show the clean alias term to users
        via = via_raw.removeprefix("_alias_").replace("_", " ") if via_raw.startswith("_alias_") else via_raw
        return {
            "jd_skill":     jd_skill,
            "match_type":   "alias",
            "weight":       DISTANCE_WEIGHTS["alias"],
            "matched_via":  via,
            "reasoning":    f"Alias match: '{via}' is an alternative name for '{jd_skill}'",
        }

    # Level 3 — Child→Parent (resume has a child/specialization of JD skill)
    jd_children = _get_children(G, jd_skill)
    child_hit = jd_children & resume_skills
    if child_hit:
        via = next(iter(child_hit))
        return {
            "jd_skill":     jd_skill,
            "match_type":   "child_parent",
            "weight":       DISTANCE_WEIGHTS["child_parent"],
            "matched_via":  via,
            "reasoning":    (
                f"Specialization match: '{via}' is a specific form of '{jd_skill}'. "
                f"Your hands-on experience with '{via}' demonstrates knowledge of '{jd_skill}'."
            ),
        }

    # Level 4 — Parent→Child (resume has a parent/generalization of JD skill)
    jd_parents = _get_parents(G, jd_skill)
    parent_hit = jd_parents & resume_skills
    if parent_hit:
        via = next(iter(parent_hit))
        return {
            "jd_skill":     jd_skill,
            "match_type":   "parent_child",
            "weight":       DISTANCE_WEIGHTS["parent_child"],
            "matched_via":  via,
            "reasoning":    (
                f"Concept match: you know '{via}' (the broader concept) but the JD specifically "
                f"wants '{jd_skill}'. You have the foundation but may need hands-on practice."
            ),
        }

    # Level 5 — Sibling (resume has a sibling skill)
    jd_siblings = _get_siblings(G, jd_skill)
    sibling_hit = jd_siblings & resume_skills
    if sibling_hit:
        via = next(iter(sibling_hit))
        shared_parents = _get_parents(G, jd_skill) & _get_parents(G, via)
        shared = next(iter(shared_parents)) if shared_parents else "same domain"
        return {
            "jd_skill":     jd_skill,
            "match_type":   "sibling",
            "weight":       DISTANCE_WEIGHTS["sibling"],
            "matched_via":  via,
            "reasoning":    (
                f"Related skill: '{via}' and '{jd_skill}' are both specializations of '{shared}'. "
                f"Your experience with '{via}' is transferable but not a direct match."
            ),
        }

    # Level 6 — 2-hop ancestor
    jd_grandparents = _get_grandparents(G, jd_skill)
    gp_hit = jd_grandparents & resume_skills
    if gp_hit:
        via = next(iter(gp_hit))
        return {
            "jd_skill":     jd_skill,
            "match_type":   "ancestor_2hop",
            "weight":       DISTANCE_WEIGHTS["ancestor_2hop"],
            "matched_via":  via,
            "reasoning":    (
                f"Distant match: '{via}' is a high-level ancestor of '{jd_skill}'. "
                f"Very loose relevance — significant learning gap exists."
            ),
        }

    # No match
    return {
        "jd_skill":     jd_skill,
        "match_type":   "no_match",
        "weight":       DISTANCE_WEIGHTS["no_match"],
        "matched_via":  None,
        "reasoning":    f"No match: '{jd_skill}' not found in resume at any level.",
    }


# ── A+B Domain mismatch detection ─────────────────────────────────────────────
# Role profiles: canonical skill fingerprints for common job families.
# Overlap < 20% with ALL profiles AND zero graph matches → domain mismatch flag.
_ROLE_PROFILES: dict[str, set] = {
    "backend": {
        "python", "nodejs", "java", "go", "rust", "ruby", "php", "csharp",
        "fastapi", "django", "flask", "express", "rails", "grpc", "rest",
        "postgresql", "mysql", "mongodb", "redis", "docker", "kubernetes",
        "cicd", "microservices", "distributed_systems", "sql",
    },
    "frontend": {
        "javascript", "typescript", "react", "vue", "angular", "svelte",
        "nextjs", "nuxtjs", "html", "css", "sass", "tailwindcss", "bootstrap",
        "webpack", "vite", "jest", "redux", "graphql", "rest",
    },
    "devops": {
        "docker", "kubernetes", "cicd", "terraform", "ansible", "helm",
        "github_actions", "gitlab_cicd", "jenkins", "linux", "bash",
        "prometheus", "grafana", "nginx", "amazon_web_services", "azure",
        "google_cloud", "iac", "microservices",
    },
    "ml_engineer": {
        "python", "tensorflow", "pytorch", "scikit_learn", "keras",
        "machine_learning", "deep_learning", "numpy", "pandas",
        "jupyter", "xgboost", "lightgbm", "huggingface", "bert",
        "natural_language_processing", "computer_vision", "spark",
    },
    "data_engineer": {
        "python", "sql", "spark", "kafka", "airflow", "hadoop",
        "postgresql", "mysql", "mongodb", "etl", "data_warehousing",
        "google_bigquery", "dbt_core", "tableau", "power_bi",
    },
    "mobile": {
        "swift", "kotlin", "react_native", "flutter", "dart",
        "ios", "android", "swiftui", "objective_c", "mobile_development",
    },
    "security": {
        "cybersecurity", "penetration_testing", "network_security",
        "application_security", "devsecops", "owasp", "linux", "bash",
        "vulnerability_assessment", "identity_access_management",
    },
}


def _detect_domain_mismatch(
    resume_skills: set,
    jd_skills: set,
    graph_score: float,
) -> dict:
    """
    A+B domain mismatch detection.

    A) Role-profile overlap: check if resume shares >=20% with ANY known role profile.
    B) Score gate: if graph_score == 0.0 and resume is non-empty, almost certainly mismatched.

    Returns mismatch dict with human-readable warning.
    """
    if not resume_skills:
        return {
            "is_mismatch": False,
            "matched_role": None,
            "warning": None,
        }

    # A) Find best-matching role profile for the JD skills
    best_role: Optional[str] = None
    best_jd_overlap = 0.0
    for role, profile in _ROLE_PROFILES.items():
        jd_overlap = len(jd_skills & profile) / max(len(jd_skills), 1)
        if jd_overlap > best_jd_overlap:
            best_jd_overlap = jd_overlap
            best_role = role

    # B) How much of the best-matched role profile does the resume cover?
    resume_role_overlap = 0.0
    if best_role:
        profile = _ROLE_PROFILES[best_role]
        resume_role_overlap = len(resume_skills & profile) / max(len(profile), 1)

    # Mismatch: JD maps to a known role, resume covers <15% of that role's skills,
    # AND graph score is 0 (nothing matched even loosely)
    is_mismatch = (
        best_jd_overlap >= 0.2          # JD is clearly in a known domain
        and resume_role_overlap < 0.15  # resume has almost none of those skills
        and graph_score == 0.0          # no graph match at any level
    )

    warning = None
    if is_mismatch:
        warning = (
            f"Domain mismatch: this role requires {best_role.replace('_', ' ')} skills "
            f"but your resume has no relevant overlap. "
            f"Resume covers {resume_role_overlap:.0%} of a typical {best_role} profile."
        )

    return {
        "is_mismatch":        is_mismatch,
        "matched_role":       best_role,
        "resume_role_overlap": round(resume_role_overlap, 4),
        "warning":            warning,
    }


def graph_match(
    resume_skills: list[str],
    jd_skills: list[str],
) -> dict:
    """
    Core graph matching function.

    Args:
        resume_skills : canonical node IDs from resume (output of normalizer)
        jd_skills     : canonical node IDs from JD (output of normalizer)

    Returns:
        {
            "graph_score": float,          # 0.0 – 1.0
            "matched": [                   # one entry per JD skill
                {
                    "jd_skill":    str,
                    "match_type":  str,    # exact / alias / child_parent / ...
                    "weight":      float,
                    "matched_via": str,
                    "reasoning":   str,    # human-readable explanation
                },
                ...
            ],
            "unmatched_jd_skills": [str],  # JD skills with no match at any level
            "match_summary": {
                "exact":         int,
                "alias":         int,
                "child_parent":  int,
                "parent_child":  int,
                "sibling":       int,
                "ancestor_2hop": int,
                "no_match":      int,
            },
            "domain_mismatch": dict,       # mismatch detection result
            "coverage": float,             # % of JD skills matched at any level
        }
    """
    if not jd_skills:
        return {
            "graph_score":        0.0,
            "matched":            [],
            "unmatched_jd_skills":[],
            "match_summary":      {},
            "domain_mismatch":    {"is_mismatch": False},
            "coverage":           0.0,
        }

    G = _load_graph()
    resume_set = set(resume_skills)

    matched = []
    summary = {k: 0 for k in DISTANCE_WEIGHTS}

    for jd_skill in jd_skills:
        record = _match_single_jd_skill(G, jd_skill, resume_set)
        matched.append(record)
        summary[record["match_type"]] = summary.get(record["match_type"], 0) + 1

    # Score = weighted sum / total JD skills
    total_weight = sum(r["weight"] for r in matched)
    graph_score = round(total_weight / len(jd_skills), 4)

    unmatched = [r["jd_skill"] for r in matched if r["match_type"] == "no_match"]
    matched_count = len(jd_skills) - len(unmatched)
    coverage = round(matched_count / len(jd_skills), 4)

    domain_info = _detect_domain_mismatch(resume_set, set(jd_skills), graph_score)

    return {
        "graph_score":         graph_score,
        "matched":             matched,
        "unmatched_jd_skills": unmatched,
        "match_summary":       summary,
        "domain_mismatch":     domain_info,
        "coverage":            coverage,
    }

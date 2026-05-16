"""
L7 — Pipeline Runner.

Single entry point that wires L1 through L6 into one call.
This is what the Flask route calls — it takes a resume file path
and JD text, runs every layer, and returns one clean result dict.

Usage:
    from pipeline.l7_present.pipeline_runner import run_pipeline

    result = run_pipeline(
        resume_path = "/uploads/resume.pdf",
        jd_text     = "Senior Backend Engineer...",
    )
"""

import time
from pathlib import Path

from pipeline.l1_input.validator import validate_resume_file, validate_jd_text
from pipeline.l2_parse.resume_parser import parse_resume
from pipeline.l2_parse.jd_parser import parse_jd
from pipeline.l2_parse.skill_extractor import extract_skills, extract_skills_from_sections
from pipeline.l3_normalize.normalizer import normalize_skills
from pipeline.l4_match.graph_matcher import graph_match
from pipeline.l4_match.semantic_matcher import semantic_match
from pipeline.l4_match.structural_matcher import structural_match
from pipeline.l5_classify.predictor import predict
from pipeline.l6_explain.evidence_mapper import map_evidence
from pipeline.l6_explain.suggestion_engine import generate_suggestions


def run_pipeline(resume_path: str, jd_text: str) -> dict:
    """
    Run the full ExplainHire pipeline.

    Args:
        resume_path : absolute path to uploaded resume (PDF or DOCX)
        jd_text     : raw job description text

    Returns a dict with keys:
        status          : "ok" or "error"
        error           : error message if status == "error"
        label           : 1 (match) or 0 (no match)
        probability     : XGBoost confidence score
        graph_score     : ontology skill match score
        sbert_score     : semantic similarity score
        structural_score: structural fit score
        coverage        : % of JD skills matched
        matched         : per-skill match records with evidence
        missing_skills  : JD skills not found in resume
        suggestions     : ranked skill suggestions with resources
        counterfactual  : what to add to cross the match threshold
        explanation     : human-readable summary
        top_reasons     : top SHAP-driven reasons
        resume_meta     : {years_of_experience, education_level, file_name}
        jd_meta         : {job_title, required_years, required_education}
        timing_ms       : per-layer timing for profiling
    """
    t_start = time.perf_counter()
    timing  = {}

    # ── L1: Validate inputs ───────────────────────────────────────────────────
    t0 = time.perf_counter()
    resume_val = validate_resume_file(resume_path)
    if not resume_val["valid"]:
        return {"status": "error", "error": resume_val["error"]}

    jd_val = validate_jd_text(jd_text)
    if not jd_val["valid"]:
        return {"status": "error", "error": jd_val["error"]}
    timing["l1_validate_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    # ── L2: Parse resume + JD ─────────────────────────────────────────────────
    t0 = time.perf_counter()
    resume_parsed = parse_resume(resume_path)
    jd_parsed     = parse_jd(jd_text)
    timing["l2_parse_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    # ── L2: Extract skills ────────────────────────────────────────────────────
    t0 = time.perf_counter()
    resume_skill_data = extract_skills_from_sections(resume_parsed["sections"])
    resume_skills_raw = resume_skill_data["all"]

    jd_skills_raw = extract_skills(jd_text)
    timing["l2_extract_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    # ── L3: Normalize skills ──────────────────────────────────────────────────
    t0 = time.perf_counter()
    resume_skills = normalize_skills(resume_skills_raw)
    jd_skills     = normalize_skills(jd_skills_raw)
    timing["l3_normalize_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    # ── L4a: Graph match ──────────────────────────────────────────────────────
    t0 = time.perf_counter()
    graph_result = graph_match(
        resume_skills=resume_skills,
        jd_skills=jd_skills,
    )
    timing["l4a_graph_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    # ── L4b: Semantic match ───────────────────────────────────────────────────
    t0 = time.perf_counter()
    sbert_result = semantic_match(
        resume_text=resume_parsed["raw_text"],
        jd_text=jd_text,
    )
    timing["l4b_sbert_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    # ── L4c: Structural match ─────────────────────────────────────────────────
    t0 = time.perf_counter()
    structural_result = structural_match(
        resume_parsed=resume_parsed,
        jd_parsed=jd_parsed,
    )
    timing["l4c_structural_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    # ── L5: XGBoost prediction + SHAP ────────────────────────────────────────
    t0 = time.perf_counter()
    summary = graph_result["match_summary"]
    features = {
        "graph_score":        graph_result["graph_score"],
        "coverage":           graph_result["coverage"],
        "exact_matches":      summary.get("exact", 0),
        "partial_matches":    (
            summary.get("child_parent", 0) +
            summary.get("parent_child", 0) +
            summary.get("sibling", 0)
        ),
        "no_matches":         summary.get("no_match", 0),
        "sbert_score":        sbert_result["sbert_score"],
        "structural_score":   structural_result["structural_score"],
        "yoe_score":          structural_result["yoe_score"],
        "edu_score":          structural_result["edu_score"],
        "section_score":      structural_result["section_score"],
        "resume_yoe":         structural_result["resume_yoe"],
        "required_yoe":       structural_result["required_yoe"],
        "resume_edu_rank":    structural_result["resume_edu_rank"],
        "required_edu_rank":  structural_result["required_edu_rank"],
    }

    try:
        prediction = predict(features)
    except FileNotFoundError:
        # Model not trained yet — fall back to rule-based score
        combined = round(
            0.4 * graph_result["graph_score"] +
            0.35 * sbert_result["sbert_score"] +
            0.25 * structural_result["structural_score"],
            4,
        )
        prediction = {
            "label":       1 if combined >= 0.5 else 0,
            "probability": combined,
            "shap_values": {},
            "top_reasons": [],
            "explanation": f"Rule-based score: {combined:.0%} (model not trained yet).",
        }
    timing["l5_predict_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    # ── L6a: Evidence mapping ─────────────────────────────────────────────────
    t0 = time.perf_counter()
    evidence_result = map_evidence(
        matched=graph_result["matched"],
        resume_text=resume_parsed["raw_text"],
    )
    timing["l6a_evidence_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    # ── L6b: Suggestions + counterfactual ─────────────────────────────────────
    t0 = time.perf_counter()
    partial_matches = [
        r for r in graph_result["matched"]
        if r["match_type"] not in ("exact", "no_match")
    ]
    suggestion_result = generate_suggestions(
        missing_skills  = evidence_result["missing_skills"],
        partial_matches = partial_matches,
        jd_skills       = jd_skills,
        graph_score     = graph_result["graph_score"],
        threshold       = 0.7,
    )
    timing["l6b_suggest_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    timing["total_ms"] = round((time.perf_counter() - t_start) * 1000, 1)

    # ── Assemble final result ─────────────────────────────────────────────────
    return {
        "status":           "ok",
        "error":            None,

        # Scores
        "label":            prediction["label"],
        "probability":      prediction["probability"],
        "graph_score":      graph_result["graph_score"],
        "sbert_score":      sbert_result["sbert_score"],
        "structural_score": structural_result["structural_score"],
        "coverage":         graph_result["coverage"],

        # Skill match detail
        "resume_skills":    resume_skills,
        "jd_skills":        jd_skills,
        "matched":          evidence_result["evidence"],
        "missing_skills":   evidence_result["missing_skills"],
        "domain_mismatch":  graph_result["domain_mismatch"],

        # Explanation
        "explanation":      prediction["explanation"],
        "top_reasons":      prediction["top_reasons"],
        "shap_values":      prediction["shap_values"],

        # Suggestions + counterfactual
        "suggestions":      suggestion_result["suggestions"],
        "counterfactual":   suggestion_result["counterfactual"],

        # Structural breakdown
        "yoe_reasoning":    structural_result["yoe_reasoning"],
        "edu_reasoning":    structural_result["edu_reasoning"],
        "section_reasoning":structural_result["section_reasoning"],

        # Metadata
        "resume_meta": {
            "file_name":          resume_parsed["file_name"],
            "years_of_experience":resume_parsed["years_of_experience"],
            "education_level":    resume_parsed["education_level"],
        },
        "jd_meta": {
            "job_title":          jd_parsed["job_title"],
            "required_years":     jd_parsed["required_years"],
            "required_education": jd_parsed["required_education"],
        },

        "timing_ms": timing,
    }

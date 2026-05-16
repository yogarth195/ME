"""
L4b — Semantic Matcher

Computes cosine similarity between resume text and JD text using
sentence-transformers (all-MiniLM-L6-v2).

Why SBERT here:
  The graph matcher catches exact/related skill matches but misses
  contextual fit — a candidate who writes "built distributed systems
  at scale" without listing Kubernetes explicitly still semantically
  aligns with a JD that says "experience with large-scale infrastructure."
  SBERT captures this.

Model loads once at module level (singleton) — not per call.
"""

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _load_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def semantic_match(resume_text: str, jd_text: str) -> dict:
    """
    Compute semantic similarity between resume and JD.

    Args:
        resume_text : full resume raw text or concatenated sections
        jd_text     : full JD raw text

    Returns:
        {
            "sbert_score": float,       # 0.0 – 1.0 cosine similarity
            "interpretation": str,      # human-readable label
        }
    """
    if not resume_text.strip() or not jd_text.strip():
        return {"sbert_score": 0.0, "interpretation": "empty input"}

    model = _load_model()
    # all-MiniLM-L6-v2 token limit is 256 tokens (~1500 chars).
    # Hard-capping chars loses the most informative content (experience, projects).
    # Instead: keep the last 2000 chars which tend to hold the meatiest content,
    # then the model's own tokenizer truncates safely at its limit.
    resume_trunc = resume_text[-2000:] if len(resume_text) > 2000 else resume_text
    jd_trunc     = jd_text[-2000:]     if len(jd_text) > 2000     else jd_text

    embeddings = model.encode(
        [resume_trunc, jd_trunc],
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    score = round(_cosine_similarity(embeddings[0], embeddings[1]), 4)

    if score >= 0.75:
        interpretation = "Strong semantic alignment"
    elif score >= 0.55:
        interpretation = "Moderate semantic alignment"
    elif score >= 0.35:
        interpretation = "Weak semantic alignment"
    else:
        interpretation = "Poor semantic alignment — likely domain mismatch"

    return {
        "sbert_score":    score,
        "interpretation": interpretation,
    }

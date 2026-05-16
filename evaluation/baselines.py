"""
Baseline models for comparison against ExplainHire full pipeline.

Three baselines:
  1. TF-IDF cosine similarity — pure bag-of-words, no AI
  2. SBERT-only — neural semantic similarity, no graph or structural
  3. Graph-only — ontology skill match, no neural or structural

Each baseline takes the same feature row from annotation.csv and returns
a binary prediction (0 or 1) using a fixed threshold.
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ── Thresholds (tuned on training data distribution) ─────────────────────────
TFIDF_THRESHOLD  = 0.15   # TF-IDF cosine is low by nature — 0.15 is meaningful overlap
SBERT_THRESHOLD  = 0.55   # from semantic_matcher interpretation bands
GRAPH_THRESHOLD  = 0.50   # half or more of JD skills matched


def tfidf_predict(resume_text: str, jd_text: str) -> tuple[int, float]:
    """
    Baseline 1: TF-IDF cosine similarity.
    Pure word overlap — no semantics, no ontology.

    Returns (label, score)
    """
    if not resume_text.strip() or not jd_text.strip():
        return 0, 0.0

    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    try:
        tfidf = vec.fit_transform([resume_text, jd_text])
        score = float(cosine_similarity(tfidf[0], tfidf[1])[0][0])
    except Exception:
        return 0, 0.0

    return int(score >= TFIDF_THRESHOLD), round(score, 4)


def sbert_predict(sbert_score: float) -> tuple[int, float]:
    """
    Baseline 2: SBERT-only.
    Uses only semantic similarity — no graph matching, no structural signals.

    Returns (label, score)
    """
    return int(sbert_score >= SBERT_THRESHOLD), round(sbert_score, 4)


def graph_predict(graph_score: float) -> tuple[int, float]:
    """
    Baseline 3: Graph-only.
    Uses only ontology skill matching — no neural, no structural signals.

    Returns (label, score)
    """
    return int(graph_score >= GRAPH_THRESHOLD), round(graph_score, 4)


def graph_sbert_predict(graph_score: float, sbert_score: float) -> tuple[int, float]:
    """
    Ablation: Graph + SBERT combined (no structural matcher).
    Equal weight combination — tests if structural matcher adds value.

    Returns (label, score)
    """
    combined = round(0.5 * graph_score + 0.5 * sbert_score, 4)
    return int(combined >= 0.45), combined

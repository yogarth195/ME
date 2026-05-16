"""
L5 — Predictor.

Loads the trained XGBoost model and SHAP explainer.
Given a feature dict, returns:
  - label      : 1 (match) or 0 (no match)
  - probability: confidence score 0.0–1.0
  - shap_values: per-feature contribution to the prediction
  - explanation: human-readable breakdown of what drove the decision
"""

import pickle
from functools import lru_cache
from pathlib import Path

import numpy as np
import shap

MODELS_DIR = Path(__file__).parent.parent.parent / "models"


@lru_cache(maxsize=1)
def _load_model():
    model_path    = MODELS_DIR / "xgb_matcher.pkl"
    features_path = MODELS_DIR / "feature_names.pkl"

    if not model_path.exists():
        raise FileNotFoundError(
            "Model not found. Run: python pipeline/l5_classify/trainer.py"
        )

    with open(model_path, "rb") as f:
        model = pickle.load(f)
    with open(features_path, "rb") as f:
        feature_names = pickle.load(f)

    explainer = shap.TreeExplainer(model)
    return model, feature_names, explainer


def predict(features: dict) -> dict:
    """
    Run inference on a single feature dict.

    Args:
        features: dict with keys matching FEATURE_COLS in trainer.py
                  (graph_score, sbert_score, structural_score, ...)

    Returns:
        {
            "label":       int,    # 1=match, 0=no_match
            "probability": float,  # confidence 0.0–1.0
            "shap_values": dict,   # feature -> SHAP contribution
            "top_reasons": list,   # top 3 factors that drove the decision
            "explanation": str,    # human-readable summary
        }
    """
    model, feature_names, explainer = _load_model()

    # Build feature vector in correct order
    X = np.array([[features.get(f, 0.0) for f in feature_names]])

    label       = int(model.predict(X)[0])
    probability = round(float(model.predict_proba(X)[0][1]), 4)

    # SHAP values — contribution of each feature to this prediction
    shap_vals = explainer.shap_values(X)[0]
    shap_dict = {
        name: round(float(val), 4)
        for name, val in zip(feature_names, shap_vals)
    }

    # Top 3 reasons — features with largest absolute SHAP values
    sorted_shap = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)
    top_reasons = []
    for feat_name, shap_val in sorted_shap[:3]:
        feat_val = features.get(feat_name, 0.0)
        direction = "helped" if shap_val > 0 else "hurt"
        top_reasons.append({
            "feature":    feat_name,
            "value":      feat_val,
            "shap":       shap_val,
            "direction":  direction,
            "reasoning":  _feature_reasoning(feat_name, feat_val, shap_val),
        })

    # Human-readable summary
    if label == 1:
        explanation = (
            f"Strong match (confidence {probability:.0%}). "
            f"Primary driver: {top_reasons[0]['reasoning']}"
        )
    else:
        explanation = (
            f"Poor match (confidence {1-probability:.0%} that it's not a match). "
            f"Main reason: {top_reasons[0]['reasoning']}"
        )

    return {
        "label":       label,
        "probability": probability,
        "shap_values": shap_dict,
        "top_reasons": top_reasons,
        "explanation": explanation,
    }


def _feature_reasoning(feature: str, value: float, shap_val: float) -> str:
    """Generate a human-readable sentence for a SHAP-driven feature."""
    direction = "positively" if shap_val > 0 else "negatively"

    messages = {
        "graph_score":      f"Skill overlap score is {value:.0%} — {direction} impacted the match.",
        "sbert_score":      f"Semantic similarity is {value:.0%} — {direction} impacted the match.",
        "structural_score": f"Structural fit score is {value:.0%} — {direction} impacted the match.",
        "yoe_score":        f"Experience match score is {value:.0%} — {direction} impacted the match.",
        "edu_score":        f"Education match score is {value:.0%} — {direction} impacted the match.",
        "coverage":         f"Skill coverage is {value:.0%} of JD requirements — {direction} impacted.",
        "exact_matches":    f"{int(value)} exact skill matches — {direction} impacted.",
        "partial_matches":  f"{int(value)} partial skill matches — {direction} impacted.",
        "no_matches":       f"{int(value)} unmatched JD skills — {direction} impacted.",
        "resume_yoe":       f"Resume shows {int(value)} years of experience — {direction} impacted.",
        "required_yoe":     f"JD requires {int(value)} years of experience — {direction} impacted.",
    }
    return messages.get(feature, f"{feature}={value:.2f} {direction} impacted the match.")

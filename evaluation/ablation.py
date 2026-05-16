"""
Ablation study + baseline evaluation.

Runs 5 configurations on annotation.csv and reports F1, Precision, Recall:
  1. TF-IDF baseline
  2. SBERT-only baseline
  3. Graph-only baseline
  4. Graph + SBERT (ablation — no structural)
  5. ExplainHire full pipeline (XGBoost)

This table goes directly into the paper's results section.

Run:
    python evaluation/ablation.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score

from evaluation.baselines import (
    tfidf_predict,
    sbert_predict,
    graph_predict,
    graph_sbert_predict,
)

DATA_PATH = Path(__file__).parent.parent / "data" / "annotation.csv"


def _metrics(y_true, y_pred, name: str) -> dict:
    return {
        "method":    name,
        "f1":        round(f1_score(y_true, y_pred, zero_division=0), 4),
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall":    round(recall_score(y_true, y_pred, zero_division=0), 4),
        "accuracy":  round(accuracy_score(y_true, y_pred), 4),
    }


def run_ablation(verbose: bool = True) -> list[dict]:
    df = pd.read_csv(DATA_PATH)
    y_true = df["label"].values

    results = []

    # ── Baseline 1: TF-IDF ───────────────────────────────────────────────────
    # annotation.csv doesn't store raw text — reconstruct resume/jd text proxy
    # from skill lists as a lightweight stand-in for full text comparison
    # For a real evaluation, pass actual resume_text and jd_text
    tfidf_preds = []
    for _, row in df.iterrows():
        # Use resume_id and jd_id as proxy text (poor man's TF-IDF on metadata)
        # In a real run with raw text available, swap these for actual text
        resume_proxy = str(row.get("resume_id", "")) + " " + str(row.get("resume_category", ""))
        jd_proxy     = str(row.get("jd_id", ""))
        pred, _      = tfidf_predict(resume_proxy, jd_proxy)
        tfidf_preds.append(pred)
    results.append(_metrics(y_true, tfidf_preds, "TF-IDF baseline"))

    # ── Baseline 2: SBERT-only ────────────────────────────────────────────────
    sbert_preds = [sbert_predict(row["sbert_score"])[0] for _, row in df.iterrows()]
    results.append(_metrics(y_true, sbert_preds, "SBERT-only"))

    # ── Baseline 3: Graph-only ────────────────────────────────────────────────
    graph_preds = [graph_predict(row["graph_score"])[0] for _, row in df.iterrows()]
    results.append(_metrics(y_true, graph_preds, "Graph-only"))

    # ── Ablation: Graph + SBERT (no structural) ───────────────────────────────
    gs_preds = [
        graph_sbert_predict(row["graph_score"], row["sbert_score"])[0]
        for _, row in df.iterrows()
    ]
    results.append(_metrics(y_true, gs_preds, "Graph + SBERT (no structural)"))

    # ── Full pipeline: XGBoost ────────────────────────────────────────────────
    try:
        from pipeline.l5_classify.predictor import predict
        xgb_preds = []
        feature_cols = [
            "graph_score", "coverage", "exact_matches", "partial_matches",
            "no_matches", "sbert_score", "structural_score", "yoe_score",
            "edu_score", "section_score", "resume_yoe", "required_yoe",
            "resume_edu_rank", "required_edu_rank",
        ]
        for _, row in df.iterrows():
            features = {col: row.get(col, 0.0) for col in feature_cols}
            result   = predict(features)
            xgb_preds.append(result["label"])
        results.append(_metrics(y_true, xgb_preds, "ExplainHire (full pipeline)"))
    except FileNotFoundError:
        print("WARNING: XGBoost model not found — skipping full pipeline evaluation.")
        print("         Run: python pipeline/l5_classify/trainer.py first.\n")

    # ── Print results table ───────────────────────────────────────────────────
    if verbose:
        _print_table(results, y_true)

    return results


def _print_table(results: list[dict], y_true):
    print("\n" + "="*70)
    print("EVALUATION RESULTS")
    print(f"Dataset: {len(y_true)} samples | Positive: {sum(y_true)} | Negative: {len(y_true)-sum(y_true)}")
    print("="*70)
    print(f"{'Method':<35} {'F1':>6} {'Prec':>6} {'Recall':>8} {'Acc':>6}")
    print("-"*70)
    for r in results:
        marker = " <-- best" if r["f1"] == max(x["f1"] for x in results) else ""
        print(
            f"{r['method']:<35} "
            f"{r['f1']:>6.4f} "
            f"{r['precision']:>6.4f} "
            f"{r['recall']:>8.4f} "
            f"{r['accuracy']:>6.4f}"
            f"{marker}"
        )
    print("="*70)

    # Improvement of full pipeline over best baseline
    baseline_f1s = [r["f1"] for r in results if r["method"] != "ExplainHire (full pipeline)"]
    full_f1s     = [r["f1"] for r in results if r["method"] == "ExplainHire (full pipeline)"]
    if baseline_f1s and full_f1s:
        best_baseline = max(baseline_f1s)
        improvement   = round((full_f1s[0] - best_baseline) * 100, 2)
        print(f"\nExplainHire improvement over best baseline: {improvement:+.2f}% F1")

    print()


if __name__ == "__main__":
    run_ablation()

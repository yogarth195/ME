"""
L5 — XGBoost trainer.

Reads data/annotation.csv, trains an XGBoost classifier to predict
match/no-match from the combined feature set, saves the model + SHAP explainer.

Features used:
    graph_score, coverage, exact_matches, partial_matches, no_matches,
    sbert_score, structural_score, yoe_score, edu_score, section_score,
    resume_yoe, required_yoe, resume_edu_rank, required_edu_rank

Output:
    models/xgb_matcher.pkl   — trained XGBoost model
    models/feature_names.pkl — ordered feature list (needed by predictor + SHAP)

Run:
    python pipeline/l5_classify/trainer.py
"""

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DATA_PATH   = Path(__file__).parent.parent.parent / "data" / "annotation.csv"
MODELS_DIR  = Path(__file__).parent.parent.parent / "models"

FEATURE_COLS = [
    "graph_score",
    "coverage",
    "exact_matches",
    "partial_matches",
    "no_matches",
    "sbert_score",
    "structural_score",
    "yoe_score",
    "edu_score",
    "section_score",
    "resume_yoe",
    "required_yoe",
    "resume_edu_rank",
    "required_edu_rank",
]


def train():
    print("Loading annotation data...")
    df = pd.read_csv(DATA_PATH)
    print(f"  Rows: {len(df)} | Label 1: {df['label'].sum()} | Label 0: {(df['label']==0).sum()}")

    X = df[FEATURE_COLS].values
    y = df["label"].values

    # Handle class imbalance — tell XGBoost how lopsided the classes are
    neg = (y == 0).sum()
    pos = (y == 1).sum()
    scale_pos_weight = neg / pos
    print(f"  scale_pos_weight: {scale_pos_weight:.2f}")

    model = XGBClassifier(
        n_estimators      = 200,
        max_depth         = 4,
        learning_rate     = 0.05,
        subsample         = 0.8,
        colsample_bytree  = 0.8,
        scale_pos_weight  = scale_pos_weight,
        eval_metric       = "logloss",
        random_state      = 42,
    )

    # Cross-validation to get honest performance estimate
    print("\nRunning 5-fold stratified cross-validation...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    f1_scores  = cross_val_score(model, X, y, cv=cv, scoring="f1")
    acc_scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy")
    print(f"  CV F1       : {f1_scores.mean():.4f} (+/- {f1_scores.std():.4f})")
    print(f"  CV Accuracy : {acc_scores.mean():.4f} (+/- {acc_scores.std():.4f})")

    # Train final model on all data
    print("\nTraining final model on full dataset...")
    model.fit(X, y)

    # Full-data report (optimistic — for sanity check only, not final eval)
    y_pred = model.predict(X)
    print("\nFull-data classification report (sanity check):")
    print(classification_report(y, y_pred, target_names=["no_match", "match"]))
    print("Confusion matrix:")
    print(confusion_matrix(y, y_pred))

    # Feature importances
    print("\nFeature importances (gain):")
    importances = model.feature_importances_
    for name, imp in sorted(zip(FEATURE_COLS, importances), key=lambda x: -x[1]):
        bar = "#" * int(imp * 50)
        print(f"  {name:25} {imp:.4f}  {bar}")

    # Save
    MODELS_DIR.mkdir(exist_ok=True)
    model_path    = MODELS_DIR / "xgb_matcher.pkl"
    features_path = MODELS_DIR / "feature_names.pkl"

    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    with open(features_path, "wb") as f:
        pickle.dump(FEATURE_COLS, f)

    print(f"\nSaved model    -> {model_path}")
    print(f"Saved features -> {features_path}")


if __name__ == "__main__":
    train()

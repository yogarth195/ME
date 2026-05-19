"""
Benchmark ExplainHire against ResuméAtlas dataset.

Task: classify each resume to its job category.

Methods compared:
  1. TF-IDF + Logistic Regression  (Heakl et al. 2024 baseline, reported F1=0.61)
  2. SBERT embeddings + LR         (ExplainHire's neural component)
  3. SBERT embeddings + XGBoost    (ExplainHire's full classifier stack)

Run:
    python evaluation/benchmark_resumeatlas.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, accuracy_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
from sentence_transformers import SentenceTransformer

DATA_PATH = Path(__file__).parent.parent / "data" / "raw" / "resume_atlas_train.csv"

SBERT_MODEL = "all-MiniLM-L6-v2"


def run_tfidf_baseline(X_train_text, X_test_text, y_train, y_test):
    """Baseline: TF-IDF + Logistic Regression (reproducing Heakl et al.)."""
    print("\n[1/3] TF-IDF + Logistic Regression baseline...")
    vec = TfidfVectorizer(max_features=10000, ngram_range=(1, 2), sublinear_tf=True)
    X_tr = vec.fit_transform(X_train_text)
    X_te = vec.transform(X_test_text)
    clf  = LogisticRegression(max_iter=1000, C=1.0)
    clf.fit(X_tr, y_train)
    preds = clf.predict(X_te)
    f1  = f1_score(y_test, preds, average="macro", zero_division=0)
    acc = accuracy_score(y_test, preds)
    print(f"     macro F1 = {f1:.4f}  |  Accuracy = {acc:.4f}")
    return f1, acc


def encode_sbert(texts, model, batch_size=64):
    print(f"     Encoding {len(texts)} texts with SBERT (batch={batch_size})...")
    return model.encode(texts, batch_size=batch_size, show_progress_bar=True)


def run_sbert_lr(X_train_emb, X_test_emb, y_train, y_test):
    """ExplainHire component: SBERT embeddings + Logistic Regression."""
    print("\n[2/3] SBERT + Logistic Regression (ExplainHire neural component)...")
    clf = LogisticRegression(max_iter=1000, C=1.0)
    clf.fit(X_train_emb, y_train)
    preds = clf.predict(X_test_emb)
    f1  = f1_score(y_test, preds, average="macro", zero_division=0)
    acc = accuracy_score(y_test, preds)
    print(f"     macro F1 = {f1:.4f}  |  Accuracy = {acc:.4f}")
    return f1, acc


def run_sbert_xgb(X_train_emb, X_test_emb, y_train_enc, y_test_enc, y_test_labels, label_map):
    """ExplainHire component: SBERT embeddings + XGBoost (same classifier as pipeline)."""
    print("\n[3/3] SBERT + XGBoost (ExplainHire full stack)...")
    clf = XGBClassifier(
        n_estimators=200, max_depth=6, learning_rate=0.1,
        use_label_encoder=False, eval_metric="mlogloss",
        tree_method="hist", random_state=42, n_jobs=-1,
    )
    clf.fit(X_train_emb, y_train_enc)
    preds_enc = clf.predict(X_test_emb)
    preds     = [label_map[p] for p in preds_enc]
    f1  = f1_score(y_test_labels, preds, average="macro", zero_division=0)
    acc = accuracy_score(y_test_labels, preds)
    print(f"     macro F1 = {f1:.4f}  |  Accuracy = {acc:.4f}")
    return f1, acc


def main():
    print("Loading ResuméAtlas dataset...")
    df = pd.read_csv(DATA_PATH)
    print(f"  {len(df)} resumes, {df['Category'].nunique()} categories")

    df_train, df_test = train_test_split(
        df, test_size=0.2, random_state=42, stratify=df["Category"]
    )
    y_train = df_train["Category"].tolist()
    y_test  = df_test["Category"].tolist()

    X_train_text = df_train["Text"].astype(str).tolist()
    X_test_text  = df_test["Text"].astype(str).tolist()

    # ── Baseline ──────────────────────────────────────────────────────────────
    tfidf_f1, tfidf_acc = run_tfidf_baseline(X_train_text, X_test_text, y_train, y_test)

    # ── SBERT embeddings (shared for both ExplainHire runs) ───────────────────
    print(f"\nLoading SBERT model ({SBERT_MODEL})...")
    model = SentenceTransformer(SBERT_MODEL)

    X_train_emb = encode_sbert(X_train_text, model)
    X_test_emb  = encode_sbert(X_test_text,  model)

    # ── ExplainHire: SBERT + LR ───────────────────────────────────────────────
    sbert_lr_f1, sbert_lr_acc = run_sbert_lr(X_train_emb, X_test_emb, y_train, y_test)

    # ── ExplainHire: SBERT + XGBoost ─────────────────────────────────────────
    categories  = sorted(df["Category"].unique())
    cat_to_idx  = {c: i for i, c in enumerate(categories)}
    idx_to_cat  = {i: c for c, i in cat_to_idx.items()}
    y_train_enc = [cat_to_idx[c] for c in y_train]
    y_test_enc  = [cat_to_idx[c] for c in y_test]

    sbert_xgb_f1, sbert_xgb_acc = run_sbert_xgb(
        X_train_emb, X_test_emb, y_train_enc, y_test_enc, y_test, idx_to_cat
    )

    # ── Results table ─────────────────────────────────────────────────────────
    print("\n" + "="*65)
    print("BENCHMARK RESULTS — ResuméAtlas (Heakl et al., 2024)")
    print(f"Dataset: {len(df)} resumes | {df['Category'].nunique()} categories")
    print(f"Test set: {len(df_test)} resumes")
    print("="*65)
    print(f"{'Method':<42} {'Macro F1':>9} {'Accuracy':>9}")
    print("-"*65)
    print(f"{'TF-IDF + LR  [Heakl et al. reported: 0.61]':<42} {tfidf_f1:>9.4f} {tfidf_acc:>9.4f}")
    print(f"{'SBERT + LR   (ExplainHire neural component)':<42} {sbert_lr_f1:>9.4f} {sbert_lr_acc:>9.4f}")
    print(f"{'SBERT + XGB  (ExplainHire full stack)':<42} {sbert_xgb_f1:>9.4f} {sbert_xgb_acc:>9.4f}")
    print("="*65)

    best_eh = max(sbert_lr_f1, sbert_xgb_f1)
    print(f"\nExplainHire vs Heakl et al. reported baseline (0.61): {(best_eh - 0.61)*100:+.2f}% macro F1")
    print()


if __name__ == "__main__":
    main()

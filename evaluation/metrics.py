"""Shared evaluation metrics."""

from sklearn.metrics import (
    f1_score, precision_score, recall_score,
    accuracy_score, confusion_matrix, classification_report,
)


def full_report(y_true, y_pred, method_name: str = "") -> dict:
    print(f"\n--- {method_name} ---")
    print(classification_report(y_true, y_pred, target_names=["no_match", "match"]))
    cm = confusion_matrix(y_true, y_pred)
    print(f"Confusion matrix:\n{cm}\n")
    return {
        "f1":        round(f1_score(y_true, y_pred, zero_division=0), 4),
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall":    round(recall_score(y_true, y_pred, zero_division=0), 4),
        "accuracy":  round(accuracy_score(y_true, y_pred), 4),
    }

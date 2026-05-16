"""
Merge all data sources into a single annotation.csv and retrain the model.

Sources merged (in order, later sources override duplicates by resume_id+jd_id):
  1. data/annotation.csv       — synthetic rows (156 base + 11 YOE-mismatch)
  2. data/kaggle_rows.csv      — Kaggle resume dataset rows (if exists)
  3. data/friends_rows.csv     — friends' real resume rows (if exists)

Output: data/annotation.csv  (overwritten with merged data)

Run:
    python data/build_dataset.py

Then retrain:
    python pipeline/l5_classify/trainer.py
"""

import csv
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent

SOURCES = [
    DATA_DIR / "annotation.csv",
    DATA_DIR / "paired_rows.csv",
    DATA_DIR / "kaggle_rows.csv",
    DATA_DIR / "friends_rows.csv",
]

OUTPUT = DATA_DIR / "annotation.csv"

FIELDNAMES = [
    "resume_id", "jd_id", "resume_category",
    "graph_score", "coverage", "exact_matches", "partial_matches", "no_matches",
    "sbert_score", "structural_score", "yoe_score", "edu_score", "section_score",
    "resume_yoe", "required_yoe", "resume_edu_rank", "required_edu_rank", "label",
]


def _load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    seen_keys: set[tuple] = set()
    merged: list[dict] = []

    for source in SOURCES:
        rows = _load_csv(source)
        if not rows:
            if source != OUTPUT:
                print(f"  SKIP (not found): {source.name}")
            continue

        added = 0
        dupes = 0
        for row in rows:
            key = (row.get("resume_id", ""), row.get("jd_id", ""))
            if key in seen_keys:
                dupes += 1
                continue
            seen_keys.add(key)

            # Normalise: keep only known fields, fill missing with 0
            clean = {f: row.get(f, 0) for f in FIELDNAMES}
            merged.append(clean)
            added += 1

        print(f"  {source.name:30} -> {added:4} new rows  ({dupes} dupes skipped)")

    if not merged:
        print("No rows found in any source. Nothing to write.")
        return

    label_1 = sum(1 for r in merged if str(r["label"]) == "1")
    label_0 = len(merged) - label_1

    print(f"\nTotal rows: {len(merged)}")
    print(f"Label distribution: 1={label_1} ({label_1/len(merged)*100:.0f}%), 0={label_0} ({label_0/len(merged)*100:.0f}%)")

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(merged)

    print(f"\nWrote {len(merged)} rows -> {OUTPUT}")
    print("\nNext: python pipeline/l5_classify/trainer.py")


if __name__ == "__main__":
    print("Merging data sources...")
    main()

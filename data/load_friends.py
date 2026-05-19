"""
Load friends' PDF/DOCX resumes and pair with all available JDs to generate
feature rows for manual annotation.

Place resume files at: data/raw/friends/<name>.pdf   (any filename — no prefix needed)
Place JD text files at: data/raw/jds/<anything>.txt

Labels are set to -1 (unlabeled). Open friends_rows.csv in Excel/Sheets and
set each label to 1 (match) or 0 (no match) before running build_dataset.py.

Run:
    python data/load_friends.py
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.l2_parse.resume_parser import parse_resume
from pipeline.l2_parse.skill_extractor import extract_skills
from pipeline.l2_parse.jd_parser import parse_jd
from pipeline.l4_match.graph_matcher import graph_match
from pipeline.l4_match.semantic_matcher import semantic_match
from pipeline.l4_match.structural_matcher import structural_match

RAW_DIR     = Path(__file__).parent / "raw"
FRIENDS_DIR = RAW_DIR / "friends"
JDS_DIR     = RAW_DIR / "jds"
OUT_PATH    = Path(__file__).parent / "friends_rows.csv"

FIELDNAMES = [
    "resume_id", "jd_id", "resume_category",
    "graph_score", "coverage", "exact_matches", "partial_matches", "no_matches",
    "sbert_score", "structural_score", "yoe_score", "edu_score", "section_score",
    "resume_yoe", "required_yoe", "resume_edu_rank", "required_edu_rank", "label",
]




def _load_jds() -> list[dict]:
    if not JDS_DIR.exists():
        print(f"WARNING: JDs directory not found at {JDS_DIR}")
        return []
    jds = []
    for jd_file in sorted(JDS_DIR.glob("*.txt")):
        text = jd_file.read_text(encoding="utf-8", errors="ignore").strip()
        if text:
            jds.append({"id": jd_file.stem, "text": text})
    print(f"Loaded {len(jds)} JD file(s) from {JDS_DIR}")
    return jds


def _slug(name: str) -> str:
    """Convert filename to a clean ID: 'Rahul Verma' -> 'rahul_verma'"""
    return name.lower().replace(" ", "_").replace("-", "_")


def _compute_row(resume_text: str, resume_parsed: dict, resume_id: str,
                 jd: dict) -> dict | None:
    try:
        resume_skills = extract_skills(resume_text)
        jd_parsed     = parse_jd(jd["text"])
        jd_skills     = extract_skills(jd["text"])

        graph      = graph_match(resume_skills, jd_skills)
        sbert      = semantic_match(resume_text[-2000:], jd["text"][-2000:])
        structural = structural_match(resume_parsed, jd_parsed)
        summary    = graph["match_summary"]

        return {
            "resume_id":        resume_id,
            "jd_id":            jd["id"],
            "resume_category":  "general",
            "graph_score":      round(graph["graph_score"], 4),
            "coverage":         round(graph["coverage"], 4),
            "exact_matches":    summary.get("exact", 0),
            "partial_matches":  (
                summary.get("child_parent", 0) +
                summary.get("parent_child", 0) +
                summary.get("sibling", 0)
            ),
            "no_matches":       summary.get("no_match", 0),
            "sbert_score":      round(sbert["sbert_score"], 4),
            "structural_score": round(structural["structural_score"], 4),
            "yoe_score":        round(structural["yoe_score"], 4),
            "edu_score":        round(structural["edu_score"], 4),
            "section_score":    round(structural["section_score"], 4),
            "resume_yoe":       structural["resume_yoe"],
            "required_yoe":     structural["required_yoe"],
            "resume_edu_rank":  structural["resume_edu_rank"],
            "required_edu_rank": structural["required_edu_rank"],
            "label":            -1,   # <-- fill in manually: 1=match, 0=no match
        }
    except Exception as e:
        print(f"    ERROR computing row for {resume_id} x {jd['id']}: {e}")
        return None


def main():
    if not FRIENDS_DIR.exists():
        print(f"ERROR: {FRIENDS_DIR} does not exist.")
        return

    resume_files = sorted(
        list(FRIENDS_DIR.glob("*.pdf")) +
        list(FRIENDS_DIR.glob("*.docx")) +
        list(FRIENDS_DIR.glob("*.doc"))
    )
    if not resume_files:
        print(f"No PDF/DOCX files found in {FRIENDS_DIR}")
        return

    print(f"Found {len(resume_files)} resume file(s).")

    jds = _load_jds()
    if not jds:
        print("No JDs found. Add .txt files to data/raw/jds/ and re-run.")
        return

    rows    = []
    skipped = 0

    for resume_path in resume_files:
        try:
            resume_parsed = parse_resume(str(resume_path))
        except Exception as e:
            print(f"  SKIP {resume_path.name} — parse error: {e}")
            skipped += 1
            continue

        raw_text = resume_parsed.get("raw_text", "")
        if len(raw_text.strip()) < 100:
            print(f"  SKIP {resume_path.name} — too short or extraction failed")
            skipped += 1
            continue

        resume_id = f"friend_{_slug(resume_path.stem)}"
        print(f"\n  {resume_path.name}")

        for jd in jds:
            row = _compute_row(raw_text, resume_parsed, resume_id, jd)
            if row:
                rows.append(row)
                print(f"    -> {jd['id']:30} graph={row['graph_score']:.2f}  sbert={row['sbert_score']:.2f}  structural={row['structural_score']:.2f}")

    print(f"\nProcessed: {len(rows)} pairs  |  Skipped: {skipped} resume(s)")

    if not rows:
        print("No rows generated.")
        return

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved {len(rows)} rows -> {OUT_PATH}")
    print("\n*** Next step: open friends_rows.csv and set label column to 1 (match) or 0 (no match) ***")
    print("Then run: python data/build_dataset.py")


if __name__ == "__main__":
    main()

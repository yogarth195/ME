"""
Load Kaggle resume dataset and pair with real JDs to generate training rows.

Kaggle dataset: "Resume Dataset" by gauravduttakiit
  URL: kaggle.com/datasets/gauravduttakiit/resume-dataset
  File: Resume.csv
  Columns: ID, Resume_str, Resume_html, Category

Place downloaded file at: data/raw/kaggle_resumes.csv
Place JD text files at:   data/raw/jds/<domain>_<n>.txt

Run:
    python data/load_kaggle.py
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.l2_parse.skill_extractor import extract_skills
from pipeline.l2_parse.jd_parser import parse_jd
from pipeline.l4_match.graph_matcher import graph_match
from pipeline.l4_match.semantic_matcher import semantic_match
from pipeline.l4_match.structural_matcher import structural_match

RAW_DIR    = Path(__file__).parent / "raw"
JDS_DIR    = RAW_DIR / "jds"
KAGGLE_CSV = RAW_DIR / "kaggle_resumes.csv"
OUT_PATH   = Path(__file__).parent / "kaggle_rows.csv"

# Map Kaggle category labels → your domain keys
# Extend this if your Kaggle dataset has more categories
CATEGORY_MAP = {
    "data science":          "ml",
    "data scientist":        "ml",
    "machine learning":      "ml",
    "ml engineer":           "ml",
    "python developer":      "backend",
    "java developer":        "backend",
    "backend":               "backend",
    "web developer":         "frontend",
    "frontend":              "frontend",
    "react developer":       "frontend",
    "devops engineer":       "devops",
    "devops":                "devops",
    "cloud engineer":        "devops",
    "android":               "mobile",
    "ios developer":         "mobile",
    "mobile":                "mobile",
    "database":              "data_eng",
    "sql developer":         "data_eng",
    "data engineer":         "data_eng",
    "testing":               "qa",
    "dot net developer":     "backend",
    "dotnet":                "backend",
    "blockchain":            "blockchain",
    "hadoop":                "data_eng",
    "etl developer":         "data_eng",
    "network security engineer": "security",
    "pmo":                   None,   # skip non-tech roles
    "arts":                  None,
    "advocate":              None,
    "hr":                    None,
    "chef":                  None,
    "accountant":            None,
    "business analyst":      None,
    "sales":                 None,
    "health and fitness":    None,
    "teacher":               None,
    "automobile":            None,
    "aviation":              None,
    "banking":               None,
    "construction":          None,
    "consultant":            None,
    "digital media":         None,
    "finance":               None,
    "public relations":      None,
}


def _load_jds() -> dict[str, list[dict]]:
    """Load all JD text files from data/raw/jds/. Returns {domain: [jd_dict]}."""
    if not JDS_DIR.exists():
        print(f"WARNING: JDs directory not found at {JDS_DIR}")
        print("Create it and add .txt files named like: backend_1.txt, ml_1.txt")
        return {}

    jds: dict[str, list] = {}
    for jd_file in sorted(JDS_DIR.glob("*.txt")):
        domain = jd_file.stem.split("_")[0].lower()
        text   = jd_file.read_text(encoding="utf-8", errors="ignore").strip()
        if text:
            jds.setdefault(domain, []).append({
                "id":   jd_file.stem,
                "text": text,
            })

    print(f"Loaded JDs: {sum(len(v) for v in jds.values())} files across {len(jds)} domains")
    for domain, items in jds.items():
        print(f"  {domain}: {len(items)} JDs")
    return jds


def _compute_row(resume_text: str, resume_id: str, resume_domain: str,
                 jd: dict, label: int) -> dict | None:
    try:
        resume_skills = extract_skills(resume_text)
        jd_parsed     = parse_jd(jd["text"])
        jd_skills     = extract_skills(jd["text"])

        graph      = graph_match(resume_skills, jd_skills)
        sbert      = semantic_match(resume_text[:2000], jd["text"][:2000])
        resume_parsed = {
            "years_of_experience": 0,   # Kaggle dataset has no YOE — default 0
            "education_level":     "unknown",
            "sections": {
                "experience": "x" if any(w in resume_text.lower() for w in ["experience", "worked", "developed"]) else "",
                "education":  "x" if any(w in resume_text.lower() for w in ["education", "university", "degree", "b.tech", "bachelor"]) else "",
                "skills":     "x" if any(w in resume_text.lower() for w in ["skills", "technologies", "tools"]) else "",
                "projects":   "x" if any(w in resume_text.lower() for w in ["project", "built", "created"]) else "",
            },
        }
        structural = structural_match(resume_parsed, jd_parsed)
        summary    = graph["match_summary"]

        return {
            "resume_id":          resume_id,
            "jd_id":              jd["id"],
            "resume_category":    resume_domain,
            "graph_score":        graph["graph_score"],
            "coverage":           graph["coverage"],
            "exact_matches":      summary.get("exact", 0),
            "partial_matches":    (
                summary.get("child_parent", 0) +
                summary.get("parent_child", 0) +
                summary.get("sibling", 0)
            ),
            "no_matches":         summary.get("no_match", 0),
            "sbert_score":        sbert["sbert_score"],
            "structural_score":   structural["structural_score"],
            "yoe_score":          structural["yoe_score"],
            "edu_score":          structural["edu_score"],
            "section_score":      structural["section_score"],
            "resume_yoe":         structural["resume_yoe"],
            "required_yoe":       structural["required_yoe"],
            "resume_edu_rank":    structural["resume_edu_rank"],
            "required_edu_rank":  structural["required_edu_rank"],
            "label":              label,
        }
    except Exception as e:
        print(f"  ERROR {resume_id}: {e}")
        return None


def main():
    if not KAGGLE_CSV.exists():
        print(f"ERROR: Kaggle CSV not found at {KAGGLE_CSV}")
        print("Download from: kaggle.com/datasets/gauravduttakiit/resume-dataset")
        print("Save as: data/raw/kaggle_resumes.csv")
        return

    jds_by_domain = _load_jds()
    if not jds_by_domain:
        print("No JDs found. Add .txt files to data/raw/jds/ and re-run.")
        return

    print(f"\nLoading Kaggle resumes from {KAGGLE_CSV}...")
    rows = []
    skipped = 0
    processed = 0

    with open(KAGGLE_CSV, encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        all_resumes = list(reader)

    print(f"Total resumes in CSV: {len(all_resumes)}")

    # Sample max 5 resumes per category to keep dataset balanced
    MAX_PER_CATEGORY = 5
    category_counts: dict[str, int] = {}

    for i, resume_row in enumerate(all_resumes):
        raw_category = resume_row.get("Category", "").strip().lower()
        domain = CATEGORY_MAP.get(raw_category)

        if domain is None:
            skipped += 1
            continue

        if category_counts.get(domain, 0) >= MAX_PER_CATEGORY:
            continue

        resume_text = resume_row.get("Resume_str", "").strip()
        if len(resume_text) < 100:
            continue

        resume_id = f"kaggle_{i}_{domain}"
        category_counts[domain] = category_counts.get(domain, 0) + 1

        # Pair with JDs: same domain = label 1, one different domain = label 0
        matched_jds   = jds_by_domain.get(domain, [])
        unmatched_jds = [
            jd for d, jds in jds_by_domain.items()
            if d != domain
            for jd in jds[:1]   # one negative example per different domain
        ][:2]   # max 2 negative JDs per resume

        for jd in matched_jds[:2]:    # max 2 positive JDs per resume
            row = _compute_row(resume_text, resume_id, domain, jd, label=1)
            if row:
                rows.append(row)
                processed += 1
                print(f"  [1] {resume_id:35} x {jd['id']:20} graph={row['graph_score']:.2f} sbert={row['sbert_score']:.2f}")

        for jd in unmatched_jds[:1]:  # max 1 negative JD per resume
            row = _compute_row(resume_text, resume_id, domain, jd, label=0)
            if row:
                rows.append(row)
                processed += 1
                print(f"  [0] {resume_id:35} x {jd['id']:20} graph={row['graph_score']:.2f} sbert={row['sbert_score']:.2f}")

    print(f"\nProcessed: {processed} rows | Skipped: {skipped} non-tech resumes")

    if not rows:
        print("No rows generated. Check your JD files and Kaggle CSV format.")
        return

    fieldnames = list(rows[0].keys())
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    label_1 = sum(1 for r in rows if r["label"] == 1)
    label_0 = sum(1 for r in rows if r["label"] == 0)
    print(f"\nSaved {len(rows)} rows -> {OUT_PATH}")
    print(f"Label distribution: 1={label_1} ({label_1/len(rows)*100:.0f}%), 0={label_0} ({label_0/len(rows)*100:.0f}%)")
    print(f"\nNext: python data/build_dataset.py")


if __name__ == "__main__":
    main()

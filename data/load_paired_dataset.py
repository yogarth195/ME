"""
Load paired resume+JD dataset (resume_data.csv) and generate training rows.

Dataset: data/raw/dataset/csv/resume_data.csv
  - 9,544 rows, each row = one resume paired with one JD
  - matched_score column: >= 0.7 -> label 1, < 0.5 -> label 0, middle -> skip

Run:
    python data/load_paired_dataset.py              # default: 800 rows
    python data/load_paired_dataset.py --all        # all ~6200 usable rows (slow ~30 min)
    python data/load_paired_dataset.py --max 200    # quick test

Output: data/paired_rows.csv
Next:   python data/build_dataset.py
"""

import ast
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.l2_parse.skill_extractor import extract_skills
from pipeline.l2_parse.jd_parser import parse_jd
from pipeline.l4_match.graph_matcher import graph_match
from pipeline.l4_match.semantic_matcher import semantic_match
from pipeline.l4_match.structural_matcher import structural_match

CSV_PATH = Path(__file__).parent / "raw" / "dataset" / "csv" / "resume_data.csv"
OUT_PATH = Path(__file__).parent / "paired_rows.csv"

LABEL_HIGH  = 0.70   # matched_score >= this -> label 1
LABEL_LOW   = 0.50   # matched_score <  this -> label 0
DEFAULT_MAX = 800    # rows to process by default (balanced sample)

FIELDNAMES = [
    "resume_id", "jd_id", "resume_category",
    "graph_score", "coverage", "exact_matches", "partial_matches", "no_matches",
    "sbert_score", "structural_score", "yoe_score", "edu_score", "section_score",
    "resume_yoe", "required_yoe", "resume_edu_rank", "required_edu_rank", "label",
]

TODAY = datetime(2026, 5, 15)

EDU_RANK = {
    "phd": 5, "doctorate": 5,
    "masters": 4, "msc": 4, "mtech": 4, "mba": 4, "m.sc": 4, "m.tech": 4,
    "btech": 3, "bsc": 3, "b.tech": 3, "b.sc": 3, "bachelor": 3, "bca": 3, "mca": 4,
    "diploma": 2, "associate": 2,
    "highschool": 1,
    "unknown": 0,
}


# ── Field parsers ──────────────────────────────────────────────────────────────

def _parse_list_field(raw: str) -> list[str]:
    """Parse a field that looks like: ['Python', 'Java', 'Docker']"""
    if not raw or raw.strip() in ("", "[]", "['N/A']", "[None]"):
        return []
    try:
        val = ast.literal_eval(raw.strip())
        if isinstance(val, list):
            return [str(x).strip() for x in val if x and str(x).strip() not in ("N/A", "None", "none")]
        return [str(val)]
    except Exception:
        return [x.strip().strip("'\"") for x in raw.strip("[]").split(",") if x.strip()]


def _parse_date(s: str) -> datetime | None:
    s = s.strip().strip("'\"")
    if not s or s.lower() in ("n/a", "none", "till date", "current", "present"):
        return TODAY if s.lower() in ("till date", "current", "present") else None
    for fmt in ("%B %Y", "%b %Y", "%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    # "Jan 2019" style already covered; try year-only fallback
    m = re.search(r"\b(20\d{2}|19\d{2})\b", s)
    if m:
        return datetime(int(m.group(1)), 6, 1)
    return None


def _calc_yoe(start_dates_raw: str, end_dates_raw: str) -> float:
    starts = _parse_list_field(start_dates_raw)
    ends   = _parse_list_field(end_dates_raw)
    total_months = 0
    for s_str, e_str in zip(starts, ends):
        s = _parse_date(s_str)
        e = _parse_date(e_str) if e_str else TODAY
        if not s:
            continue
        if not e:
            e = TODAY
        diff = (e.year - s.year) * 12 + (e.month - s.month)
        if diff > 0:
            total_months += diff
    return round(total_months / 12, 1)


def _parse_edu_level(degree_names_raw: str) -> str:
    degrees = _parse_list_field(degree_names_raw)
    best = "unknown"
    best_rank = 0
    for d in degrees:
        d_lower = d.lower()
        for key, rank in EDU_RANK.items():
            if key in d_lower and rank > best_rank:
                best = key
                best_rank = rank
    return best


def _parse_required_yoe(exp_req: str) -> float:
    if not exp_req:
        return 0.0
    exp_req = exp_req.lower()
    # "at least 5 year(s)" / "5+ years" / "1 to 3 years" / "2-4 years"
    m = re.search(r"(\d+)\s*(?:to|-)\s*(\d+)", exp_req)
    if m:
        return float(m.group(1))   # take lower bound
    m = re.search(r"(\d+)\+?\s*year", exp_req)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+)", exp_req)
    if m:
        return float(m.group(1))
    return 0.0


def _parse_required_edu(edu_req: str) -> str:
    if not edu_req:
        return "unknown"
    edu_lower = edu_req.lower()
    for key in sorted(EDU_RANK, key=lambda k: -EDU_RANK[k]):
        if key in edu_lower:
            return key
    if "bachelor" in edu_lower or "b.sc" in edu_lower or "b.tech" in edu_lower:
        return "btech"
    if "master" in edu_lower or "m.sc" in edu_lower:
        return "masters"
    return "unknown"


# ── Text reconstruction ────────────────────────────────────────────────────────

def _build_resume_text(row: dict) -> str:
    parts = []
    obj = row.get("career_objective", "").strip()
    if obj:
        parts.append(obj)

    skills = _parse_list_field(row.get("skills", ""))
    if skills:
        parts.append("Skills: " + ", ".join(skills))

    resp = row.get("responsibilities", "").strip()
    if resp:
        parts.append("Experience:\n" + resp)

    degrees = _parse_list_field(row.get("degree_names", ""))
    if degrees:
        parts.append("Education: " + ", ".join(degrees))

    return "\n\n".join(parts)


def _build_jd_text(row: dict) -> str:
    job_key = next((k for k in row if "job_position_name" in k), None)
    title   = row.get(job_key, "").strip() if job_key else ""

    parts = []
    if title:
        parts.append(title)

    exp = row.get("experiencere_requirement", "").strip()
    if exp:
        parts.append("Experience required: " + exp)

    edu = row.get("educationaL_requirements", "").strip()
    if edu:
        parts.append("Education: " + edu)

    resp = row.get("responsibilities.1", "").strip()
    if resp:
        parts.append("Responsibilities:\n" + resp)

    skills_req = row.get("skills_required", "").strip()
    if skills_req:
        parts.append("Required skills:\n" + skills_req)

    return "\n\n".join(parts)


# ── Core row computation ───────────────────────────────────────────────────────

def _compute_row(resume_text: str, jd_text: str,
                 resume_yoe: float, edu_level: str,
                 resume_id: str, jd_id: str,
                 label: int) -> dict | None:
    try:
        resume_skills = extract_skills(resume_text)
        jd_parsed     = parse_jd(jd_text)
        jd_skills     = extract_skills(jd_text)

        graph      = graph_match(resume_skills, jd_skills)
        sbert      = semantic_match(resume_text[-2000:], jd_text[-2000:])

        resume_parsed = {
            "years_of_experience": resume_yoe,
            "education_level":     edu_level,
            "sections": {
                "experience": "x" if any(w in resume_text.lower() for w in ["experience", "worked", "responsibilities"]) else "",
                "education":  "x" if any(w in resume_text.lower() for w in ["education", "university", "degree", "b.tech", "bachelor"]) else "",
                "skills":     "x" if "skills" in resume_text.lower() else "",
                "projects":   "x" if any(w in resume_text.lower() for w in ["project", "built", "created"]) else "",
            },
        }
        structural = structural_match(resume_parsed, jd_parsed)
        summary    = graph["match_summary"]

        return {
            "resume_id":          resume_id,
            "jd_id":              jd_id,
            "resume_category":    "real",
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


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    # Parse args
    process_all = "--all" in sys.argv
    max_rows = DEFAULT_MAX
    if "--max" in sys.argv:
        idx = sys.argv.index("--max")
        max_rows = int(sys.argv[idx + 1])
    if process_all:
        max_rows = 999999

    if not CSV_PATH.exists():
        print(f"ERROR: dataset not found at {CSV_PATH}")
        return

    with open(CSV_PATH, encoding="utf-8-sig") as f:
        all_rows = list(csv.DictReader(f))

    print(f"Total rows in CSV: {len(all_rows)}")

    # Split into label-1 and label-0 candidates
    candidates_1 = []
    candidates_0 = []
    for i, row in enumerate(all_rows):
        try:
            score = float(row.get("matched_score", "").strip())
        except ValueError:
            continue
        if score >= LABEL_HIGH:
            candidates_1.append((i, row, 1))
        elif score < LABEL_LOW:
            candidates_0.append((i, row, 0))

    print(f"Label-1 candidates: {len(candidates_1)}")
    print(f"Label-0 candidates: {len(candidates_0)}")

    # Balance: equal label-1 and label-0, up to max_rows total
    half = max_rows // 2
    selected = candidates_1[:half] + candidates_0[:half]
    print(f"Processing {len(selected)} rows (max={max_rows}, balanced)...")
    print("This may take a few minutes — SBERT runs on each pair.\n")

    rows_out = []
    errors   = 0

    for idx, (i, row, label) in enumerate(selected):
        resume_text = _build_resume_text(row)
        jd_text     = _build_jd_text(row)

        if len(resume_text.strip()) < 50 or len(jd_text.strip()) < 30:
            errors += 1
            continue

        resume_yoe = _calc_yoe(row.get("start_dates", ""), row.get("end_dates", ""))
        edu_level  = _parse_edu_level(row.get("degree_names", ""))
        resume_id  = f"paired_{i}"
        jd_key     = next((k for k in row if "job_position_name" in k), None)
        jd_title   = row.get(jd_key, "row").strip()[:20].replace(" ", "_") if jd_key else f"jd_{i}"
        jd_id      = f"jd_{i}_{jd_title}"

        result = _compute_row(resume_text, jd_text, resume_yoe, edu_level,
                              resume_id, jd_id, label)
        if result:
            rows_out.append(result)

        # Progress every 50 rows
        if (idx + 1) % 50 == 0:
            print(f"  [{idx+1}/{len(selected)}] done so far: {len(rows_out)} rows")

    print(f"\nProcessed: {len(rows_out)} rows | Errors/skipped: {errors}")

    if not rows_out:
        print("No rows generated. Check the CSV path and field names.")
        return

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows_out)

    label_1 = sum(1 for r in rows_out if r["label"] == 1)
    label_0 = len(rows_out) - label_1
    print(f"Saved {len(rows_out)} rows -> {OUT_PATH}")
    print(f"Label distribution: 1={label_1}, 0={label_0}")
    print(f"\nNext: python data/build_dataset.py")


if __name__ == "__main__":
    main()

"""
Load friends' PDF/DOCX resumes and pair with real JDs to generate training rows.

Place resume files at: data/raw/friends/<name>.<pdf|docx>
Place JD text files at: data/raw/jds/<domain>_<n>.txt

Each resume filename should hint at the domain:
    backend_alice.pdf, ml_bob.pdf, frontend_carol.docx
If no domain hint found, the script will try to infer from skills.

Run:
    python data/load_friends.py
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.l1_input.pdf_extractor import extract_text_from_pdf
from pipeline.l1_input.docx_extractor import extract_text_from_docx
from pipeline.l2_parse.skill_extractor import extract_skills
from pipeline.l2_parse.jd_parser import parse_jd
from pipeline.l4_match.graph_matcher import graph_match
from pipeline.l4_match.semantic_matcher import semantic_match
from pipeline.l4_match.structural_matcher import structural_match

RAW_DIR      = Path(__file__).parent / "raw"
FRIENDS_DIR  = RAW_DIR / "friends"
JDS_DIR      = RAW_DIR / "jds"
OUT_PATH     = Path(__file__).parent / "friends_rows.csv"

DOMAIN_KEYWORDS = {
    "ml":        ["ml", "machine_learning", "data_science", "datascience", "ai"],
    "backend":   ["backend", "python", "java", "node", "django", "spring"],
    "frontend":  ["frontend", "react", "angular", "vue", "web"],
    "devops":    ["devops", "cloud", "kubernetes", "docker", "infra"],
    "mobile":    ["mobile", "android", "ios", "flutter"],
    "data_eng":  ["data_eng", "dataeng", "etl", "spark", "hadoop"],
    "security":  ["security", "pentest", "cyber"],
    "qa":        ["qa", "test", "quality"],
}


def _infer_domain_from_filename(stem: str) -> str | None:
    stem_lower = stem.lower()
    for domain, hints in DOMAIN_KEYWORDS.items():
        for hint in hints:
            if hint in stem_lower:
                return domain
    return None


def _infer_domain_from_skills(skills: list[str]) -> str | None:
    skill_set = set(s.lower() for s in skills)
    domain_overlap: dict[str, int] = {}
    for domain, hints in DOMAIN_KEYWORDS.items():
        overlap = sum(1 for h in hints if h in skill_set)
        if overlap:
            domain_overlap[domain] = overlap
    if not domain_overlap:
        return None
    return max(domain_overlap, key=lambda d: domain_overlap[d])


def _load_jds() -> dict[str, list[dict]]:
    if not JDS_DIR.exists():
        print(f"WARNING: JDs directory not found at {JDS_DIR}")
        return {}
    jds: dict[str, list] = {}
    for jd_file in sorted(JDS_DIR.glob("*.txt")):
        domain = jd_file.stem.split("_")[0].lower()
        text   = jd_file.read_text(encoding="utf-8", errors="ignore").strip()
        if text:
            jds.setdefault(domain, []).append({"id": jd_file.stem, "text": text})
    total = sum(len(v) for v in jds.values())
    print(f"Loaded JDs: {total} files across {len(jds)} domains")
    return jds


def _extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(str(path))
    if suffix in (".docx", ".doc"):
        return extract_text_from_docx(str(path))
    return ""


def _compute_row(resume_text: str, resume_id: str, domain: str,
                 jd: dict, label: int) -> dict | None:
    try:
        resume_skills = extract_skills(resume_text)
        jd_parsed     = parse_jd(jd["text"])
        jd_skills     = extract_skills(jd["text"])

        graph      = graph_match(resume_skills, jd_skills)
        sbert      = semantic_match(resume_text[-2000:], jd["text"][-2000:])

        resume_parsed = {
            "years_of_experience": 0,
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
            "resume_category":    domain,
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


FIELDNAMES = [
    "resume_id", "jd_id", "resume_category",
    "graph_score", "coverage", "exact_matches", "partial_matches", "no_matches",
    "sbert_score", "structural_score", "yoe_score", "edu_score", "section_score",
    "resume_yoe", "required_yoe", "resume_edu_rank", "required_edu_rank", "label",
]


def main():
    if not FRIENDS_DIR.exists():
        print(f"ERROR: friends directory not found at {FRIENDS_DIR}")
        print("Create it and add your friends' PDF/DOCX resumes.")
        print("Name them like: backend_alice.pdf, ml_bob.docx")
        return

    resume_files = list(FRIENDS_DIR.glob("*.pdf")) + list(FRIENDS_DIR.glob("*.docx")) + list(FRIENDS_DIR.glob("*.doc"))
    if not resume_files:
        print(f"No PDF/DOCX files found in {FRIENDS_DIR}")
        return

    print(f"Found {len(resume_files)} resume files.")

    jds_by_domain = _load_jds()
    if not jds_by_domain:
        print("No JDs found. Add .txt files to data/raw/jds/ and re-run.")
        return

    rows = []
    skipped = 0

    for resume_path in sorted(resume_files):
        resume_text = _extract_text(resume_path)
        if len(resume_text.strip()) < 100:
            print(f"  SKIP {resume_path.name} — too short or extraction failed")
            skipped += 1
            continue

        domain = _infer_domain_from_filename(resume_path.stem)
        if not domain:
            skills = extract_skills(resume_text)
            domain = _infer_domain_from_skills(skills)
        if not domain:
            print(f"  SKIP {resume_path.name} — cannot infer domain (rename file like: backend_alice.pdf)")
            skipped += 1
            continue

        resume_id = f"friend_{resume_path.stem}"
        print(f"\n  Resume: {resume_path.name} -> domain={domain}")

        matched_jds   = jds_by_domain.get(domain, [])
        unmatched_jds = [
            jd for d, jds in jds_by_domain.items()
            if d != domain
            for jd in jds[:1]
        ][:2]

        if not matched_jds:
            print(f"    No JDs found for domain={domain} — add {domain}_1.txt to data/raw/jds/")

        for jd in matched_jds[:3]:
            row = _compute_row(resume_text, resume_id, domain, jd, label=1)
            if row:
                rows.append(row)
                print(f"    [1] x {jd['id']:25} graph={row['graph_score']:.2f} sbert={row['sbert_score']:.2f}")

        for jd in unmatched_jds[:1]:
            row = _compute_row(resume_text, resume_id, domain, jd, label=0)
            if row:
                rows.append(row)
                print(f"    [0] x {jd['id']:25} graph={row['graph_score']:.2f} sbert={row['sbert_score']:.2f}")

    print(f"\nProcessed: {len(rows)} rows | Skipped: {skipped} resumes")

    if not rows:
        print("No rows generated.")
        return

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    label_1 = sum(1 for r in rows if r["label"] == 1)
    label_0 = sum(1 for r in rows if r["label"] == 0)
    print(f"\nSaved {len(rows)} rows -> {OUT_PATH}")
    print(f"Label distribution: 1={label_1}, 0={label_0}")
    print(f"\nNext: python data/build_dataset.py")


if __name__ == "__main__":
    main()

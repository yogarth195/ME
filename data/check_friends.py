"""
Pre-flight checker for friends' resumes before running load_friends.py.

Checks each PDF/DOCX in data/raw/friends/ against the pipeline's requirements
and prints a clear PASS / WARN / FAIL verdict per file.

Run:
    python data/check_friends.py
    python data/check_friends.py path/to/specific.pdf   # check one file
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.l2_parse.resume_parser import parse_resume
from pipeline.l2_parse.skill_extractor import extract_skills

FRIENDS_DIR = Path(__file__).parent / "raw" / "friends"

MAX_FILE_SIZE_MB = 5
MIN_TEXT_LENGTH  = 100
MIN_SKILLS       = 3
KEY_SECTIONS     = {"experience", "education", "skills"}

# ── ANSI colours (fallback to plain if terminal doesn't support) ─────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def _col(text, colour): return f"{colour}{text}{RESET}"


def check_resume(path: Path) -> dict:
    """Run all checks and return a result dict."""
    result = {
        "file":     path.name,
        "verdict":  "PASS",
        "issues":   [],
        "warnings": [],
        "info":     {},
    }

    def fail(msg):
        result["issues"].append(msg)
        result["verdict"] = "FAIL"

    def warn(msg):
        result["warnings"].append(msg)
        if result["verdict"] == "PASS":
            result["verdict"] = "WARN"

    # ── 1. File exists ─────────────────────────────────────────────────────
    if not path.exists():
        fail(f"File not found: {path}")
        return result

    # ── 2. Extension ───────────────────────────────────────────────────────
    if path.suffix.lower() not in (".pdf", ".docx", ".doc"):
        fail(f"Unsupported format '{path.suffix}' — use PDF or DOCX")
        return result

    # ── 3. File size ───────────────────────────────────────────────────────
    size_mb = path.stat().st_size / (1024 * 1024)
    result["info"]["size_mb"] = round(size_mb, 2)
    if size_mb > MAX_FILE_SIZE_MB:
        fail(f"File too large ({size_mb:.1f} MB > {MAX_FILE_SIZE_MB} MB limit)")

    # ── 4. Parse (extracts text + sections internally) ────────────────────
    parsed = {}
    try:
        parsed = parse_resume(str(path))
    except Exception as e:
        fail(f"Resume parser failed: {e}")
        return result

    raw_text = parsed.get("raw_text", "")
    text_len = len(raw_text.strip())
    result["info"]["text_chars"] = text_len

    if text_len < MIN_TEXT_LENGTH:
        fail(
            f"Extracted text too short ({text_len} chars < {MIN_TEXT_LENGTH}). "
            "PDF may be scanned/image-only or password-protected."
        )
        return result

    # ── 5. Section detection ───────────────────────────────────────────────
    sections_found = {
        k for k, v in parsed.get("sections", {}).items() if v and v.strip()
    }
    result["info"]["sections_found"]     = sorted(sections_found)
    result["info"]["education_level"]    = parsed.get("education_level", "unknown")
    result["info"]["years_of_experience"] = parsed.get("years_of_experience", 0)

    key_hit = KEY_SECTIONS & sections_found
    if not key_hit:
        fail(
            "None of the key sections detected (experience / education / skills). "
            f"Sections found: {sorted(sections_found) or 'none'}."
        )
    elif len(key_hit) < 2:
        warn(f"Only {len(key_hit)} of 3 key sections found ({sorted(key_hit)}). Structural score will be penalised.")

    # ── 6. Education level ─────────────────────────────────────────────────
    if parsed.get("education_level", "unknown") == "unknown":
        warn("Education level not detected — ensure degree name is visible in text.")

    # ── 7. Skill extraction ────────────────────────────────────────────────
    try:
        skills = extract_skills(raw_text)
    except Exception as e:
        warn(f"Skill extractor error: {e}")
        skills = []

    result["info"]["skills_found"]  = len(skills)
    result["info"]["sample_skills"] = skills[:8]

    if len(skills) == 0:
        fail("Zero skills matched the ontology — graph_score will be 0.")
    elif len(skills) < MIN_SKILLS:
        warn(f"Only {len(skills)} skill(s) matched ({skills}). Graph score will be low.")

    return result


def print_result(r: dict) -> None:
    verdict = r["verdict"]
    colour  = GREEN if verdict == "PASS" else YELLOW if verdict == "WARN" else RED
    icon    = "OK" if verdict == "PASS" else "!!" if verdict == "WARN" else "XX"

    print(f"\n{_col(icon, colour)} {_col(r['file'], BOLD)}  [{_col(verdict, colour)}]")

    info = r["info"]
    print(f"   Size: {info.get('size_mb', '?')} MB  |  "
          f"Text: {info.get('text_chars', '?')} chars  |  "
          f"Skills: {info.get('skills_found', '?')}  |  "
          f"Edu: {info.get('education_level', '?')}  |  "
          f"YOE: {info.get('years_of_experience', '?')}y")

    sections = info.get("sections_found", [])
    print(f"   Sections detected: {sections if sections else 'none'}")

    sample = info.get("sample_skills", [])
    if sample:
        print(f"   Sample skills: {', '.join(sample)}")

    for issue in r["issues"]:
        print(f"   {_col('FAIL', RED)}: {issue}")
    for w in r["warnings"]:
        print(f"   {_col('WARN', YELLOW)}: {w}")


def main():
    # Accept optional explicit file paths as CLI args
    if len(sys.argv) > 1:
        paths = [Path(p) for p in sys.argv[1:]]
    else:
        if not FRIENDS_DIR.exists():
            print(f"ERROR: {FRIENDS_DIR} does not exist.")
            print("Create it and drop your friends' resumes inside.")
            sys.exit(1)
        paths = sorted(
            list(FRIENDS_DIR.glob("*.pdf")) +
            list(FRIENDS_DIR.glob("*.docx")) +
            list(FRIENDS_DIR.glob("*.doc"))
        )

    if not paths:
        print(f"No PDF/DOCX files found in {FRIENDS_DIR}")
        sys.exit(0)

    print(f"\n{'='*60}")
    print(f"  ExplainHire Resume Pre-flight Checker")
    print(f"  Checking {len(paths)} file(s) ...")
    print(f"{'='*60}")

    results = [check_resume(p) for p in paths]

    for r in results:
        print_result(r)

    # ── Summary ──────────────────────────────────────────────────────────
    passed  = [r for r in results if r["verdict"] == "PASS"]
    warned  = [r for r in results if r["verdict"] == "WARN"]
    failed  = [r for r in results if r["verdict"] == "FAIL"]

    print(f"\n{'='*60}")
    print(f"  SUMMARY: {len(results)} checked  |  "
          f"{_col(f'{len(passed)} PASS', GREEN)}  "
          f"{_col(f'{len(warned)} WARN', YELLOW)}  "
          f"{_col(f'{len(failed)} FAIL', RED)}")

    if passed or warned:
        ready = [r["file"] for r in passed + warned]
        print(f"\n  Ready for load_friends.py ({len(ready)}):")
        for f in ready:
            tag = _col("PASS", GREEN) if any(r["file"] == f and r["verdict"] == "PASS" for r in results) else _col("WARN", YELLOW)
            print(f"    [{tag}] {f}")

    if failed:
        print(f"\n  Fix these before running load_friends.py ({len(failed)}):")
        for r in failed:
            print(f"    [{_col('FAIL', RED)}] {r['file']}")

    if not failed:
        print(f"\n  {_col('All files OK — run: python data/load_friends.py', GREEN)}")
    else:
        print(f"\n  Fix the FAIL items above, then re-run this checker.")

    print()


if __name__ == "__main__":
    main()

import sys
sys.path.insert(0, '.')
from pipeline.l4_match.graph_matcher import graph_match

result = graph_match(
    resume_skills=["kubernetes", "python"],
    jd_skills=["kubernetes", "docker", "python"],
)
for r in result["matched"]:
    print(f"{r['jd_skill']:20} → {r['match_type']:15} (w={r['weight']}) via={r['matched_via']}")
    print(f"  {r['reasoning']}")

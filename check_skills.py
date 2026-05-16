"""Quick check — extract skills from your resume."""

import json
from pipeline.l2_parse.resume_parser import parse_resume
from pipeline.l2_parse.skill_extractor import extract_skills_from_sections

result = parse_resume("data/raw/resumes/my resume .pdf")
skills = extract_skills_from_sections(result["sections"])

print("=== Skills by section ===")
for section, skill_list in skills.items():
    if section == "all":
        continue
    if skill_list:
        print(f"\n[{section}]")
        print(", ".join(skill_list))

print(f"\n=== ALL skills ({len(skills['all'])} found) ===")
print(", ".join(skills["all"]))

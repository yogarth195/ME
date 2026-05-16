import json
from pipeline.l2_parse.resume_parser import parse_resume

result = parse_resume("data/raw/resumes/my resume .pdf")
print(json.dumps(result, indent=2))

"""
Generate 40 YOE-mismatch rows and append to annotation.csv.

These are same-domain pairs where skills match well BUT the experience
gap is large enough that the pair should be labeled 0 (no match).

Without these rows, XGBoost never learns that a large YOE gap
overrides strong skill overlap.

Run:
    python data/generate_yoe_mismatch.py
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

DATA_PATH = Path(__file__).parent / "annotation.csv"

# ── Junior resumes (1-2 yrs) with strong skill sets ───────────────────────────
JUNIOR_RESUMES = [
    {
        "id": "r_junior_backend_1",
        "category": "backend",
        "years_of_experience": 1,
        "education_level": "btech",
        "text": """
Junior Backend Developer
EXPERIENCE
Backend Intern at Startup (2023-2024)
Built REST APIs using Python and FastAPI. Used PostgreSQL and Docker for local development.
Worked with Node.js and Express for small microservices.
SKILLS
Python, FastAPI, Node.js, PostgreSQL, Docker, REST, Git, MongoDB
EDUCATION
B.Tech Computer Science 2024
PROJECTS
REST API for task management using FastAPI and PostgreSQL.
""",
    },
    {
        "id": "r_junior_backend_2",
        "category": "backend",
        "years_of_experience": 1,
        "education_level": "btech",
        "text": """
Software Developer
EXPERIENCE
Developer Trainee (2023-2024)
Developed Node.js APIs with Express and MongoDB. Deployed with Docker.
SKILLS
Node.js, Express, MongoDB, Docker, Python, REST, PostgreSQL, Git
EDUCATION
B.Tech 2023
PROJECTS
E-commerce backend API with Node.js and MongoDB.
""",
    },
    {
        "id": "r_junior_ml_1",
        "category": "ml",
        "years_of_experience": 1,
        "education_level": "btech",
        "text": """
Junior Data Scientist
EXPERIENCE
ML Intern (2023-2024)
Built classification models using scikit-learn and Python. Used pandas and numpy for data processing.
Trained basic neural networks with PyTorch.
SKILLS
Python, scikit-learn, PyTorch, pandas, numpy, machine learning, SQL, Git
EDUCATION
B.Tech 2024
PROJECTS
Customer churn prediction with scikit-learn. Image classifier with PyTorch.
""",
    },
    {
        "id": "r_junior_frontend_1",
        "category": "frontend",
        "years_of_experience": 1,
        "education_level": "btech",
        "text": """
Junior Frontend Developer
EXPERIENCE
Frontend Intern (2023-2024)
Built React components and integrated REST APIs. Used TypeScript and Redux.
SKILLS
JavaScript, TypeScript, React, Redux, HTML, CSS, REST, Git, Next.js
EDUCATION
B.Tech 2024
PROJECTS
Portfolio website with React and Next.js. Dashboard UI with TypeScript.
""",
    },
    {
        "id": "r_junior_devops_1",
        "category": "devops",
        "years_of_experience": 1,
        "education_level": "btech",
        "text": """
Junior DevOps Engineer
EXPERIENCE
DevOps Intern (2023-2024)
Set up Docker containers and basic Kubernetes deployments. Wrote Terraform scripts.
Used GitHub Actions for CI/CD pipelines.
SKILLS
Docker, Kubernetes, Terraform, GitHub Actions, Linux, Bash, Git, AWS
EDUCATION
B.Tech 2024
PROJECTS
Dockerized microservices deployment. Basic Terraform AWS infrastructure.
""",
    },
]

# ── Senior JDs requiring 5+ years ─────────────────────────────────────────────
SENIOR_JDS = [
    {
        "id": "jd_senior_backend_5yr",
        "category": "backend",
        "text": """
Senior Backend Engineer

Requirements:
- 5+ years of backend development experience
- Expert-level Python or Node.js
- REST API and microservices architecture at scale
- PostgreSQL and MongoDB at production scale
- Docker and Kubernetes in production
- CI/CD pipelines and DevOps practices
- System design and architecture experience
- Bachelor's degree required, Masters preferred
""",
    },
    {
        "id": "jd_senior_backend_7yr",
        "category": "backend",
        "text": """
Principal Backend Engineer

Requirements:
- 7+ years of backend engineering experience
- Deep expertise in distributed systems and microservices
- Python, Node.js, and at least one compiled language
- PostgreSQL, MongoDB, Redis at scale
- Docker, Kubernetes, cloud infrastructure (AWS or GCP)
- Led teams of 5+ engineers
- Masters degree preferred
""",
    },
    {
        "id": "jd_senior_ml_5yr",
        "category": "ml",
        "text": """
Senior ML Engineer

Requirements:
- 5+ years machine learning engineering experience
- PyTorch and TensorFlow in production
- scikit-learn, XGBoost for classical ML pipelines
- Experience deploying models to production at scale
- Deep learning, NLP, computer vision experience
- Masters or PhD strongly preferred
""",
    },
    {
        "id": "jd_senior_frontend_5yr",
        "category": "frontend",
        "text": """
Senior Frontend Engineer

Requirements:
- 5+ years frontend development experience
- Expert React and TypeScript
- Next.js, Redux, GraphQL
- Led frontend architecture decisions
- Mentored junior developers
- Bachelor's degree required
""",
    },
    {
        "id": "jd_senior_devops_6yr",
        "category": "devops",
        "text": """
Senior DevOps / Platform Engineer

Requirements:
- 6+ years DevOps or platform engineering experience
- Kubernetes and Docker at scale (500+ pods)
- Terraform, Ansible for infrastructure as code
- AWS or GCP cloud architecture
- CI/CD pipelines, GitHub Actions or Jenkins
- Linux, Bash scripting
- Bachelor's degree required
""",
    },
    {
        "id": "jd_lead_backend_8yr",
        "category": "backend",
        "text": """
Engineering Lead - Backend

Requirements:
- 8+ years software engineering experience
- 3+ years in a tech lead or engineering lead role
- Python and Node.js at production scale
- Microservices, distributed systems design
- PostgreSQL, MongoDB, Redis, Kafka
- Docker, Kubernetes, AWS
- Experience hiring and growing engineering teams
""",
    },
    {
        "id": "jd_staff_ml_7yr",
        "category": "ml",
        "text": """
Staff ML Engineer

Requirements:
- 7+ years machine learning or data science experience
- Research background preferred (publications a plus)
- PyTorch, TensorFlow, HuggingFace transformers
- Large-scale model training and deployment
- NLP, computer vision, or recommendation systems
- PhD or Masters required
""",
    },
    {
        "id": "jd_senior_devops_5yr",
        "category": "devops",
        "text": """
DevOps Team Lead

Requirements:
- 5+ years DevOps experience
- Docker, Kubernetes cluster management
- Terraform infrastructure as code
- AWS certified preferred
- CI/CD pipeline design and maintenance
- Linux administration, Bash scripting
- Mentoring junior DevOps engineers
""",
    },
]


def compute_row(resume: dict, jd: dict, label: int) -> dict | None:
    try:
        resume_skills = extract_skills(resume["text"])
        jd_parsed     = parse_jd(jd["text"])
        jd_skills     = extract_skills(jd["text"])

        graph      = graph_match(resume_skills, jd_skills)
        sbert      = semantic_match(resume["text"].strip(), jd["text"].strip())
        resume_parsed = {
            "years_of_experience": resume["years_of_experience"],
            "education_level":     resume["education_level"],
            "sections": {
                "experience":  "x" if "experience" in resume["text"].lower() else "",
                "education":   "x" if "education"  in resume["text"].lower() else "",
                "skills":      "x" if "skills"     in resume["text"].lower() else "",
                "projects":    "x" if "projects"   in resume["text"].lower() else "",
            },
        }
        structural = structural_match(resume_parsed, jd_parsed)
        summary    = graph["match_summary"]

        return {
            "resume_id":       resume["id"],
            "jd_id":           jd["id"],
            "resume_category": resume["category"],
            "graph_score":     graph["graph_score"],
            "coverage":        graph["coverage"],
            "exact_matches":   summary.get("exact", 0),
            "partial_matches": (
                summary.get("child_parent", 0) +
                summary.get("parent_child", 0) +
                summary.get("sibling", 0)
            ),
            "no_matches":      summary.get("no_match", 0),
            "sbert_score":     sbert["sbert_score"],
            "structural_score":structural["structural_score"],
            "yoe_score":       structural["yoe_score"],
            "edu_score":       structural["edu_score"],
            "section_score":   structural["section_score"],
            "resume_yoe":      structural["resume_yoe"],
            "required_yoe":    structural["required_yoe"],
            "resume_edu_rank": structural["resume_edu_rank"],
            "required_edu_rank": structural["required_edu_rank"],
            "label":           label,
        }
    except Exception as e:
        print(f"  ERROR: {resume['id']} x {jd['id']} — {e}")
        return None


def main():
    if not DATA_PATH.exists():
        print(f"ERROR: {DATA_PATH} not found. Run generate_synthetic.py first.")
        return

    # Read existing fieldnames
    with open(DATA_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        existing_rows = list(reader)

    print(f"Existing rows: {len(existing_rows)}")
    print(f"Generating YOE-mismatch pairs (same domain, junior resume vs senior JD)...")

    new_rows = []
    for resume in JUNIOR_RESUMES:
        for jd in SENIOR_JDS:
            # Only pair same domain — skill overlap will be high
            # but YOE gap is 4-7 years → should be label 0
            if resume["category"] != jd["category"]:
                continue
            print(f"  {resume['id']:30} x {jd['id']:30} -> label=0", end=" ")
            row = compute_row(resume, jd, label=0)
            if row:
                new_rows.append(row)
                print(f"graph={row['graph_score']:.2f} yoe_score={row['yoe_score']:.2f} struct={row['structural_score']:.2f}")
            else:
                print("SKIPPED")

    # Append to annotation.csv
    with open(DATA_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerows(new_rows)

    total = len(existing_rows) + len(new_rows)
    print(f"\nAdded {len(new_rows)} YOE-mismatch rows.")
    print(f"Total rows now: {total}")
    print(f"\nNow retrain: python pipeline/l5_classify/trainer.py")


if __name__ == "__main__":
    main()

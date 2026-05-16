"""
Generate synthetic (resume, JD) pairs and run them through the full pipeline
to produce data/annotation.csv — ready for XGBoost training.

Covers 6 domains × multiple match qualities = ~240 labeled pairs.

Run:
    python data/generate_synthetic.py
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

# ── Synthetic resume templates ─────────────────────────────────────────────────

RESUMES = [

    # ── BACKEND ───────────────────────────────────────────────────────────────
    {
        "id": "r_backend_senior",
        "category": "backend",
        "years_of_experience": 5,
        "education_level": "btech",
        "text": """
John Doe | john@email.com

SUMMARY
Senior backend engineer with 5 years of experience building scalable REST APIs
and microservices. Strong Python and Node.js background.

EXPERIENCE
Senior Software Engineer — Flipkart (2021–2024)
- Built REST APIs using FastAPI and Python serving 10M requests/day
- Designed microservices architecture using Docker and Kubernetes
- Optimized PostgreSQL queries reducing latency by 40%
- Set up CI/CD pipelines using GitHub Actions

Software Engineer — Razorpay (2019–2021)
- Developed Node.js Express backend for payment processing
- Worked with MongoDB and Redis for caching
- Integrated REST APIs with third-party payment gateways

SKILLS
Python, Node.js, FastAPI, Express, PostgreSQL, MongoDB, Redis,
Docker, Kubernetes, GitHub Actions, REST, Git, Linux, microservices

EDUCATION
B.Tech Computer Science — DTU (2015–2019)

PROJECTS
- URL shortener with Redis caching and PostgreSQL persistence
- REST API rate limiter using token bucket algorithm
""",
    },
    {
        "id": "r_backend_mid",
        "category": "backend",
        "years_of_experience": 3,
        "education_level": "btech",
        "text": """
Priya Sharma | priya@email.com

SUMMARY
Backend developer with 3 years building APIs in Python and Java.

EXPERIENCE
Software Engineer — Swiggy (2021–2024)
- Built Django REST APIs for order management
- Used PostgreSQL and Redis for data storage
- Deployed services on Docker

SKILLS
Python, Django, PostgreSQL, Redis, Docker, Git, REST, SQL

EDUCATION
B.Tech — NSIT Delhi (2017–2021)

PROJECTS
- Blog platform backend using Django and PostgreSQL
- JWT authentication service
""",
    },
    {
        "id": "r_backend_junior",
        "category": "backend",
        "years_of_experience": 1,
        "education_level": "btech",
        "text": """
Rahul Gupta | rahul@email.com

SUMMARY
Fresh backend developer with internship experience in Python.

EXPERIENCE
Backend Intern — Startup (2023–2024)
- Wrote Flask APIs for internal tools
- Worked with MySQL database

SKILLS
Python, Flask, MySQL, Git, REST

EDUCATION
B.Tech Computer Science — NIT (2020–2024)

PROJECTS
- Student management system using Flask and MySQL
""",
    },

    # ── FRONTEND ──────────────────────────────────────────────────────────────
    {
        "id": "r_frontend_senior",
        "category": "frontend",
        "years_of_experience": 5,
        "education_level": "btech",
        "text": """
Aisha Khan | aisha@email.com

SUMMARY
Senior frontend engineer with 5 years building React applications.

EXPERIENCE
Senior Frontend Engineer — Zomato (2019–2024)
- Led React migration from Angular for customer-facing app
- Built reusable component library with TypeScript
- Implemented Next.js SSR for SEO improvement
- Used Redux for state management

Frontend Engineer — Housing.com (2018–2019)
- Built Vue.js property listing interface
- Worked with REST APIs and GraphQL

SKILLS
JavaScript, TypeScript, React, Next.js, Vue, Angular, Redux,
GraphQL, REST, HTML, CSS, Tailwind CSS, Webpack, Jest, Git

EDUCATION
B.Tech — IIT Delhi (2014–2018)

PROJECTS
- Design system with 50+ React components
- Real-time dashboard using WebSockets
""",
    },
    {
        "id": "r_frontend_mid",
        "category": "frontend",
        "years_of_experience": 2,
        "education_level": "btech",
        "text": """
Neha Patel | neha@email.com

SUMMARY
Frontend developer with 2 years React experience.

EXPERIENCE
Frontend Developer — EdTech Startup (2022–2024)
- Built React components for online learning platform
- Worked with TypeScript and REST APIs
- Used CSS and Bootstrap for styling

SKILLS
JavaScript, React, TypeScript, HTML, CSS, Bootstrap, REST, Git

EDUCATION
B.Tech — Amity University (2018–2022)

PROJECTS
- E-commerce product page in React
- Portfolio website with animations
""",
    },

    # ── DEVOPS ────────────────────────────────────────────────────────────────
    {
        "id": "r_devops_senior",
        "category": "devops",
        "years_of_experience": 6,
        "education_level": "btech",
        "text": """
Amit Singh | amit@email.com

SUMMARY
DevOps engineer with 6 years managing infrastructure and CI/CD pipelines.

EXPERIENCE
DevOps Lead — Paytm (2018–2024)
- Managed Kubernetes clusters on AWS serving 50M users
- Built CI/CD pipelines using Jenkins and GitHub Actions
- Automated infrastructure provisioning with Terraform and Ansible
- Set up Prometheus and Grafana monitoring dashboards
- Maintained Linux servers and Docker container fleet

SKILLS
Docker, Kubernetes, Terraform, Ansible, Jenkins, GitHub Actions,
Linux, Bash, Prometheus, Grafana, AWS, CI/CD, Helm, Nginx, Git

EDUCATION
B.Tech — BITS Pilani (2012–2016)

PROJECTS
- Zero-downtime deployment pipeline for microservices
- Auto-scaling Kubernetes setup on AWS EKS
""",
    },
    {
        "id": "r_devops_mid",
        "category": "devops",
        "years_of_experience": 3,
        "education_level": "btech",
        "text": """
Vikram Mehta | vikram@email.com

SUMMARY
DevOps engineer with 3 years in cloud and containerization.

EXPERIENCE
DevOps Engineer — Infosys (2021–2024)
- Set up Docker and Kubernetes deployments
- Wrote Terraform scripts for AWS infrastructure
- Maintained CI/CD with GitLab CI/CD

SKILLS
Docker, Kubernetes, Terraform, AWS, GitLab CI/CD, Linux, Bash, Git

EDUCATION
B.Tech — VIT (2017–2021)
""",
    },

    # ── ML / DATA SCIENCE ─────────────────────────────────────────────────────
    {
        "id": "r_ml_senior",
        "category": "ml",
        "years_of_experience": 4,
        "education_level": "mtech",
        "text": """
Dr. Sneha Rao | sneha@email.com

SUMMARY
ML Engineer with 4 years building production machine learning systems.

EXPERIENCE
ML Engineer — Amazon (2020–2024)
- Built recommendation system using deep learning and PyTorch
- Trained NLP models with BERT and HuggingFace transformers
- Used scikit-learn and XGBoost for classification pipelines
- Data processing with NumPy, Pandas, and Spark
- Deployed models on AWS using Docker

SKILLS
Python, PyTorch, TensorFlow, scikit-learn, XGBoost, NumPy, Pandas,
BERT, HuggingFace, machine learning, deep learning, NLP, Spark, Docker, AWS

EDUCATION
M.Tech Computer Science — IIT Bombay (2016–2018)
B.Tech — IIIT Hyderabad (2012–2016)

PROJECTS
- Sentiment analysis pipeline using BERT fine-tuning
- Fraud detection model with XGBoost achieving 94% F1
""",
    },
    {
        "id": "r_ml_mid",
        "category": "ml",
        "years_of_experience": 2,
        "education_level": "btech",
        "text": """
Karan Verma | karan@email.com

SUMMARY
Data scientist with 2 years building ML models.

EXPERIENCE
Data Scientist — Analytics Startup (2022–2024)
- Built classification models using scikit-learn
- Used Pandas and NumPy for data processing
- Visualized data with Matplotlib and Seaborn

SKILLS
Python, scikit-learn, Pandas, NumPy, Matplotlib, machine learning, SQL, Git

EDUCATION
B.Tech — Delhi University (2018–2022)

PROJECTS
- Customer churn prediction model
- Sales forecasting with time series
""",
    },

    # ── DATA ENGINEERING ──────────────────────────────────────────────────────
    {
        "id": "r_data_eng",
        "category": "data_eng",
        "years_of_experience": 4,
        "education_level": "btech",
        "text": """
Ritu Sharma | ritu@email.com

SUMMARY
Data engineer with 4 years building ETL pipelines and data warehouses.

EXPERIENCE
Data Engineer — Myntra (2020–2024)
- Built ETL pipelines using Apache Spark and Airflow
- Designed data warehouse on Google BigQuery
- Worked with Kafka for real-time data streaming
- Used SQL and dbt for data transformations

SKILLS
Python, Spark, Kafka, Airflow, SQL, PostgreSQL, Google BigQuery,
dbt, ETL, data warehousing, Hadoop, Docker, Git

EDUCATION
B.Tech — NSIT (2016–2020)

PROJECTS
- Real-time clickstream pipeline with Kafka and Spark
- Data warehouse migration to BigQuery
""",
    },

    # ── MOBILE ────────────────────────────────────────────────────────────────
    {
        "id": "r_mobile_senior",
        "category": "mobile",
        "years_of_experience": 5,
        "education_level": "btech",
        "text": """
Arjun Nair | arjun@email.com

SUMMARY
Mobile developer with 5 years building iOS and Android applications.

EXPERIENCE
Senior Mobile Developer — BYJU's (2019–2024)
- Built iOS apps using Swift and SwiftUI
- Developed Android apps using Kotlin
- Built cross-platform app using Flutter and Dart
- Integrated REST APIs for backend communication

SKILLS
Swift, SwiftUI, Kotlin, Flutter, Dart, iOS, Android,
React Native, REST, Git, mobile development

EDUCATION
B.Tech — Manipal University (2015–2019)

PROJECTS
- EdTech iOS app with 500K downloads
- Cross-platform quiz app in Flutter
""",
    },

    # ── COMPLETELY UNRELATED (for negative examples) ──────────────────────────
    {
        "id": "r_chef",
        "category": "chef",
        "years_of_experience": 5,
        "education_level": "diploma",
        "text": """
Raj Kumar | raj@email.com

SUMMARY
Professional chef with 5 years experience in fine dining restaurants.

EXPERIENCE
Head Chef — The Leela Palace (2019–2024)
- Managed kitchen team of 15 staff
- Created seasonal menus and managed food costs
- Specialized in North Indian and Continental cuisine

Chef de Partie — Taj Hotels (2017–2019)
- Prepared dishes for banquet events serving 500+ guests

SKILLS
Menu planning, kitchen management, food safety, team leadership,
French cuisine, pastry, inventory management

EDUCATION
Diploma in Hotel Management — IHM Delhi (2014–2017)
""",
    },
    {
        "id": "r_accountant",
        "category": "finance",
        "years_of_experience": 4,
        "education_level": "bachelors",
        "text": """
Meena Joshi | meena@email.com

SUMMARY
Chartered accountant with 4 years in financial reporting and taxation.

EXPERIENCE
Senior Accountant — Deloitte (2020–2024)
- Prepared financial statements and tax filings
- Managed accounts payable and receivable
- Conducted internal audits

SKILLS
Accounting, taxation, financial reporting, MS Excel, Tally, SAP,
auditing, GST, balance sheet, P&L

EDUCATION
B.Com — Delhi University (2016–2020)
""",
    },
]

# ── Synthetic JD templates ─────────────────────────────────────────────────────

JDS = [
    {
        "id": "jd_backend_senior",
        "category": "backend",
        "text": """
Senior Backend Engineer

We are looking for a Senior Backend Engineer with 4+ years of experience.

Requirements:
- 4+ years of experience in backend development
- Strong Python or Node.js skills
- Experience with REST APIs and microservices architecture
- PostgreSQL and MongoDB database experience
- Docker and Kubernetes for containerization
- CI/CD pipelines (GitHub Actions or Jenkins)
- Bachelor's degree in Computer Science or related field

Nice to have:
- Redis caching experience
- AWS or cloud experience
- GraphQL knowledge
""",
    },
    {
        "id": "jd_backend_mid",
        "category": "backend",
        "text": """
Backend Developer

We need a Backend Developer with 2+ years of experience.

Requirements:
- 2+ years backend development experience
- Python or Node.js
- REST API development
- SQL database experience (PostgreSQL or MySQL)
- Basic Docker knowledge
- Bachelor's degree required

Responsibilities:
- Build and maintain REST APIs
- Write clean, testable code
- Collaborate with frontend team
""",
    },
    {
        "id": "jd_backend_junior",
        "category": "backend",
        "text": """
Junior Backend Developer

Entry level position for fresh graduates.

Requirements:
- 0–1 years experience (internship counts)
- Python or JavaScript knowledge
- Basic understanding of REST APIs
- Any SQL database experience
- Bachelor's degree in CS or related

Responsibilities:
- Assist in building backend features
- Write unit tests
- Fix bugs and maintain documentation
""",
    },
    {
        "id": "jd_frontend_senior",
        "category": "frontend",
        "text": """
Senior Frontend Engineer

Requirements:
- 4+ years of frontend development experience
- Expert in React and TypeScript
- Next.js and server-side rendering experience
- State management with Redux
- GraphQL and REST API integration
- Testing with Jest
- Bachelor's degree required

Nice to have:
- Vue.js experience
- Design system experience
""",
    },
    {
        "id": "jd_frontend_mid",
        "category": "frontend",
        "text": """
Frontend Developer

Requirements:
- 2+ years frontend experience
- React and JavaScript
- HTML, CSS proficiency
- REST API integration
- Bachelor's degree

Responsibilities:
- Build responsive UI components
- Integrate with backend APIs
""",
    },
    {
        "id": "jd_devops_senior",
        "category": "devops",
        "text": """
Senior DevOps Engineer

Requirements:
- 5+ years DevOps experience
- Kubernetes and Docker expertise
- Terraform and Ansible for infrastructure as code
- CI/CD pipeline experience (Jenkins, GitHub Actions)
- AWS or cloud platform experience
- Linux and Bash scripting
- Monitoring with Prometheus and Grafana
- Bachelor's degree required
""",
    },
    {
        "id": "jd_devops_mid",
        "category": "devops",
        "text": """
DevOps Engineer

Requirements:
- 2+ years DevOps or infrastructure experience
- Docker and Kubernetes
- CI/CD pipelines
- Cloud experience (AWS preferred)
- Linux administration
- Bachelor's degree
""",
    },
    {
        "id": "jd_ml_senior",
        "category": "ml",
        "text": """
Senior ML Engineer

Requirements:
- 3+ years machine learning engineering experience
- PyTorch or TensorFlow
- NLP experience with transformers and BERT
- scikit-learn and XGBoost
- Python, NumPy, Pandas
- Experience deploying models to production
- Masters or PhD preferred, Bachelor's accepted

Nice to have:
- HuggingFace experience
- Spark for large-scale data processing
""",
    },
    {
        "id": "jd_ml_mid",
        "category": "ml",
        "text": """
Data Scientist

Requirements:
- 1+ years data science experience
- Python with scikit-learn and Pandas
- Machine learning model building
- SQL for data querying
- Bachelor's degree in CS, Statistics, or related
""",
    },
    {
        "id": "jd_data_eng",
        "category": "data_eng",
        "text": """
Data Engineer

Requirements:
- 3+ years data engineering experience
- Apache Spark and Airflow
- Kafka for real-time streaming
- SQL and data warehousing concepts
- Python for ETL pipelines
- Cloud data warehouse (BigQuery or Redshift)
- Bachelor's degree required
""",
    },
    {
        "id": "jd_mobile_senior",
        "category": "mobile",
        "text": """
Senior Mobile Developer

Requirements:
- 4+ years mobile development experience
- iOS development with Swift and SwiftUI
- Android development with Kotlin
- Cross-platform experience (Flutter or React Native)
- REST API integration
- Bachelor's degree required
""",
    },
    {
        "id": "jd_fullstack",
        "category": "backend",
        "text": """
Full Stack Developer

Requirements:
- 3+ years full stack experience
- React or Vue frontend
- Node.js or Python backend
- PostgreSQL or MongoDB
- REST API development
- Docker basics
- Bachelor's degree
""",
    },
]


def _label(resume_cat: str, jd_cat: str) -> int:
    """
    Auto-label based on category match.
    Adjacent categories get partial treatment but still label 1.
    """
    direct_match = {
        ("backend", "backend"), ("frontend", "frontend"),
        ("devops", "devops"), ("ml", "ml"),
        ("data_eng", "data_eng"), ("mobile", "mobile"),
        # Backend <-> fullstack is a reasonable match
        ("backend", "fullstack"), ("frontend", "fullstack"),
    }
    if (resume_cat, jd_cat) in direct_match or resume_cat == jd_cat:
        return 1
    return 0


def compute_features(resume: dict, jd_text: str, label: int) -> dict | None:
    try:
        resume_skills = extract_skills(resume["text"])
        jd_parsed     = parse_jd(jd_text)
        jd_skills     = extract_skills(jd_text)

        graph   = graph_match(resume_skills, jd_skills)
        sbert   = semantic_match(resume["text"].strip(), jd_text.strip())

        resume_parsed = {
            "years_of_experience": resume["years_of_experience"],
            "education_level":     resume["education_level"],
            "sections": {
                "experience":     "x" if "EXPERIENCE" in resume["text"] or "experience" in resume["text"].lower() else "",
                "education":      "x" if "EDUCATION"  in resume["text"] or "education"  in resume["text"].lower() else "",
                "skills":         "x" if "SKILLS"     in resume["text"] or "skills"     in resume["text"].lower() else "",
                "projects":       "x" if "PROJECTS"   in resume["text"] or "projects"   in resume["text"].lower() else "",
            },
        }
        structural = structural_match(resume_parsed, jd_parsed)

        return {
            "resume_id":          resume["id"],
            "jd_id":              jd_parsed["job_title"][:40],
            "resume_category":    resume["category"],
            # Features for XGBoost
            "graph_score":        graph["graph_score"],
            "coverage":           graph["coverage"],
            "exact_matches":      graph["match_summary"].get("exact", 0),
            "partial_matches":    (
                graph["match_summary"].get("child_parent", 0) +
                graph["match_summary"].get("parent_child", 0) +
                graph["match_summary"].get("sibling", 0)
            ),
            "no_matches":         graph["match_summary"].get("no_match", 0),
            "sbert_score":        sbert["sbert_score"],
            "structural_score":   structural["structural_score"],
            "yoe_score":          structural["yoe_score"],
            "edu_score":          structural["edu_score"],
            "section_score":      structural["section_score"],
            "resume_yoe":         structural["resume_yoe"],
            "required_yoe":       structural["required_yoe"],
            "resume_edu_rank":    structural["resume_edu_rank"],
            "required_edu_rank":  structural["required_edu_rank"],
            # Label
            "label":              label,
        }
    except Exception as e:
        print(f"  ERROR: {resume['id']} x {jd_text[:30]!r} — {e}")
        return None


def main():
    out_path = Path(__file__).parent / "annotation.csv"
    rows = []

    total = len(RESUMES) * len(JDS)
    print(f"Generating {total} pairs ({len(RESUMES)} resumes x {len(JDS)} JDs)...")

    for resume in RESUMES:
        for jd in JDS:
            label = _label(resume["category"], jd["category"])
            print(f"  {resume['id']:25} x {jd['id']:25} -> label={label}", end=" ")
            row = compute_features(resume, jd["text"], label)
            if row:
                rows.append(row)
                print(f"graph={row['graph_score']:.2f} sbert={row['sbert_score']:.2f} struct={row['structural_score']:.2f}")
            else:
                print("SKIPPED")

    if not rows:
        print("No rows generated — something went wrong.")
        return

    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    label_1 = sum(1 for r in rows if r["label"] == 1)
    label_0 = sum(1 for r in rows if r["label"] == 0)
    print(f"\nSaved {len(rows)} rows -> {out_path}")
    print(f"Label distribution: 1={label_1} ({label_1/len(rows)*100:.0f}%), 0={label_0} ({label_0/len(rows)*100:.0f}%)")


if __name__ == "__main__":
    main()

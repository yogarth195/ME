# ExplainHire — Neurosymbolic AI for Explainable Resume-Job Matching

**Final Year B.Tech Project · Delhi Technological University**

ExplainHire combines symbolic AI (ontology graph matching) with neural AI (SBERT
semantic similarity + XGBoost classification) to produce explainable match scores
between resumes and job descriptions. Every decision is backed by evidence: which
skills matched, which are missing, and what the candidate should learn next.

---

## Architecture Overview

```
L1 Input       →  PDF / DOCX resume + JD text
L2 Parse       →  spaCy NER + section detection → structured JSON
L3 Normalize   →  alias table → canonical ontology nodes
L4a Graph      →  3-level NetworkX traversal → GraphScore
L4b Semantic   →  SBERT cosine similarity → SBERTScore
L4c Structural →  experience / education / skill coverage → StructuralScore
L5 Classify    →  XGBoost [GraphScore, SBERTScore, StructuralScore, coverage] → label + SHAP
L6 Explain     →  evidence mapper → matched skills, missing skills, suggestions
L7 Present     →  Flask routes + Jinja2 + SQLite history
```

**Final Score** = `0.50 × GraphScore + 0.35 × SBERTScore + 0.15 × StructuralScore`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | Flask 3.0 + Jinja2 + Bootstrap 5 |
| Auth | Flask-Login + bcrypt |
| NER | spaCy `en_core_web_sm` |
| Semantic similarity | `sentence-transformers` `all-MiniLM-L6-v2` |
| Ontology / graph | NetworkX |
| Classification | XGBoost |
| Explainability | SHAP |
| Resume parsing | PyMuPDF (PDF) + python-docx (DOCX) |
| Storage | SQLite via Flask-SQLAlchemy |

---

## Project Structure

```
ExplainHire/
├── app/                        # Flask application
│   ├── __init__.py             # App factory
│   ├── models.py               # SQLAlchemy models (User, MatchHistory)
│   ├── routes/
│   │   ├── auth.py             # /login, /register, /logout
│   │   ├── match.py            # /match (main pipeline endpoint)
│   │   └── history.py          # /history, /result/<id>
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── result.html
│   │   ├── history.html
│   │   └── partials/           # reusable Jinja2 fragments
│   └── static/
│       ├── css/
│       ├── js/
│       └── uploads/            # temporary resume storage
├── pipeline/
│   ├── l1_input/               # file validation + loading
│   ├── l2_parse/               # NER parser + section detector
│   ├── l3_normalize/           # alias normalization
│   ├── l4_match/               # graph, semantic, structural matchers
│   ├── l5_classify/            # XGBoost trainer + predictor
│   ├── l6_explain/             # evidence mapper + suggestion engine
│   └── l7_present/             # Flask integration helpers
├── ontology/
│   ├── skill_ontology.gpickle  # compiled NetworkX graph
│   ├── alias_table.json        # raw skill → canonical node map
│   └── learning_resources.json # skill → learning URL map
├── data/
│   ├── raw/
│   │   ├── resumes/            # Kaggle snehaanbhawal/resume-dataset
│   │   └── job_descriptions/   # Kaggle arshkon/linkedin-job-postings
│   ├── processed/              # feature CSVs after pipeline run
│   └── annotations/
│       └── annotation.csv      # resume_id, jd_id, label (0/1/2)
├── models/                     # saved XGBoost model + SHAP explainer
├── evaluation/                 # baseline comparisons + ablation scripts
├── tests/                      # unit + integration tests
├── notebooks/                  # EDA + experiment notebooks
├── instance/                   # SQLite DB (git-ignored)
├── config.py                   # all constants (paths, weights, thresholds)
├── requirements.txt
└── run.py                      # entry point: `python run.py`
```

---

## Setup

### 1. Clone & create virtual environment

```bash
git clone <repo-url>
cd ExplainHire
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 3. Configure environment

Create a `.env` file in the project root:

```
SECRET_KEY=your-secret-key-here
```

### 4. Initialise the database

```bash
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

### 5. Run

```bash
python run.py
```

Open `http://127.0.0.1:5000` in your browser.

---

## Dataset

| Dataset | Source |
|---|---|
| Resumes | [Kaggle snehaanbhawal/resume-dataset](https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset) |
| Job descriptions | [Kaggle arshkon/linkedin-job-postings](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings) |
| Domains | Web Dev · ML/DS · DevOps · Mobile · Cybersecurity |
| Labels | 0 = Not Recommended · 1 = Maybe · 2 = Recommended |

---

## Evaluation

- **Baselines**: TF-IDF cosine · SBERT-only · Graph-only
- **Metrics**: Macro F1 · Precision · Recall · Accuracy · Confusion Matrix
- **Ablation**: remove one pipeline component at a time

---

## Authors

B.Tech Final Year Project · Department of Computer Science  
Delhi Technological University · 2025–26

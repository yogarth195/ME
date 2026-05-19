# ExplainHire — Neurosymbolic AI for Explainable Resume–Job Matching

**B.Tech Final Year Project · Department of Computer Science & Engineering**
**Delhi Technological University · 2025–26**

> **Authors:** Yoosha Raza (2K22/CO/521) · Yanshu (2K22/CO/507) · Yogarth (2K22/CO/519)
> **Faculty Coordinator:** Gull Kaur

---

## What is ExplainHire?

ExplainHire is a **neurosymbolic AI system** that takes a resume (PDF) and a job description (text) and tells you:

- **Does this person match the job?** — Match / No Match with confidence %
- **Why?** — Skill-by-skill breakdown with proof sentences from the resume
- **What's missing?** — Ranked list of skills to learn to improve the match score

Unlike standard ATS systems that do keyword matching, ExplainHire combines:
- **Symbolic AI** — a 434-node skill ontology graph (O*NET-derived)
- **Neural AI** — SBERT sentence embeddings fine-tuned on real recruitment data
- **Structural signals** — years of experience gap, education level, section coverage
- **Explainability** — SHAP feature attribution + sentence-level evidence

---

## Key Results

| Method | Macro F1 |
|---|---|
| TF-IDF baseline | 0.037 |
| SBERT-only | 0.484 |
| Graph-only | 0.747 |
| Graph + SBERT (no structural) | 0.832 |
| **ExplainHire (full pipeline)** | **0.951** |

**Cross-validated F1 = 0.9045** (5-fold stratified, honest estimate on held-out data)

**External benchmark:** F1 = 0.720 on ResuméAtlas (Heakl et al., 2024), outperforming their reported TF-IDF baseline (F1 = 0.61) by **+11.06%**

---

## Architecture — 7-Layer Pipeline

```
PDF Resume + Job Description Text
            │
            ▼
L1  Input Validation    — file type, size, readable text
            │
            ▼
L2  Parse               — skills, YOE, education, section detection
            │
            ▼
L3  Normalize           — alias table (800+ entries) → canonical ontology nodes
            │
            ▼
L4a Graph Matcher       — 434-node O*NET skill graph, 6-level weighted traversal
L4b Semantic Matcher    — fine-tuned SBERT all-MiniLM-L6-v2, cosine similarity
L4c Structural Matcher  — YOE gap, education gap, section coverage
            │
            ▼
L5  XGBoost Classifier  — 14 features, SHAP explainability, CV F1 = 0.9045
            │
            ▼
L6  Explainer           — evidence mapper + skill gap analyser (ranked by impact)
            │
            ▼
L7  Flask Web App       — drag-drop upload, dark/light theme, match history
```

### Graph Matching Weights

| Relationship | Weight |
|---|---|
| Exact match | 1.0 |
| Alias match | 0.9 |
| Child → Parent | 0.7 |
| Parent → Child | 0.5 |
| Sibling (shared parent) | 0.4 |
| Two-hop path | 0.3 |
| No match | 0.0 |

---

## SBERT Fine-Tuning

The base model `all-MiniLM-L6-v2` was fine-tuned on **887 real resume–JD pairs** using CosineSimilarityLoss:

- **636 positive pairs** (label = 1, good match)
- **251 negative pairs** (label = 0, no match)
- **Epochs:** 4 · **Batch size:** 16 · **Final loss:** 0.069
- **Saved to:** `models/sbert_finetuned/`

The pipeline automatically loads the fine-tuned model when present.

---

## Training Data

| Source | Rows | Description |
|---|---|---|
| Synthetic pairs | 167 | Hand-crafted edge cases |
| [Kaggle Resume Dataset](https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset) | 800 | Real resumes, 24 job categories |
| Friends dataset | 887 | 144 real B.Tech resumes × 17 real JDs from Naukri/LinkedIn |
| **Total** | **1,854** | |

**17 real job descriptions** were manually collected from Naukri and LinkedIn covering roles including: Full Stack Developer, Data Scientist, Backend Engineer, Flutter Developer, ML Engineer, Java Backend Developer, MERN Stack Developer, Golang Developer, and more.

---

## Tech Stack

| Component | Technology |
|---|---|
| Web framework | Flask 3.0 + Jinja2 + Bootstrap 5 |
| Resume parsing | PyMuPDF (PDF) + python-docx (DOCX) |
| Skill ontology | NetworkX DiGraph · O*NET database |
| Semantic matching | sentence-transformers `all-MiniLM-L6-v2` (fine-tuned) |
| Classification | XGBoost |
| Explainability | SHAP TreeExplainer |
| Ontology visualiser | vis-network (JavaScript) |
| Storage | SQLite via Flask-SQLAlchemy |
| Auth | Flask-Login + bcrypt |

---

## Project Structure

```
ExplainHire/
├── app/                        # Flask web application
│   ├── routes/
│   │   ├── auth.py             # /login /register /logout
│   │   ├── match.py            # /match  (main pipeline endpoint)
│   │   ├── history.py          # /history /result/<id>
│   │   └── ontology_view.py    # /ontology (interactive graph explorer)
│   └── templates/              # Jinja2 HTML templates
├── pipeline/
│   ├── l1_input/               # file validation
│   ├── l2_parse/               # resume + JD parser, skill extractor
│   ├── l3_normalize/           # alias normalisation
│   ├── l4_match/               # graph, SBERT, structural matchers
│   │   └── finetune_sbert.py   # SBERT fine-tuning script
│   ├── l5_classify/            # XGBoost trainer + predictor
│   ├── l6_explain/             # evidence mapper + skill gap analyser
│   └── l7_present/             # pipeline orchestrator
├── ontology/
│   ├── skill_ontology.gpickle  # compiled 434-node NetworkX graph
│   ├── alias_table.json        # 800+ surface forms → canonical nodes
│   └── learning_resources.json # skill → learning URL map
├── data/
│   ├── raw/
│   │   ├── friends/            # 144 real B.Tech student resumes (PDF)
│   │   └── jds/                # 17 real industry job descriptions
│   ├── annotation.csv          # 1854 labeled resume–JD pairs
│   ├── load_friends.py         # generates resume × JD feature pairs
│   └── build_dataset.py        # merges all sources into annotation.csv
├── evaluation/
│   ├── ablation.py             # ablation study (5 configurations)
│   ├── baselines.py            # TF-IDF, SBERT-only, Graph-only baselines
│   └── benchmark_resumeatlas.py # external benchmark on ResuméAtlas
├── models/
│   ├── xgb_matcher.pkl         # trained XGBoost model
│   └── sbert_finetuned/        # fine-tuned SBERT model
├── paper/
│   └── explainHire_ieee.tex    # IEEE conference paper (LaTeX)
├── config.py
├── requirements.txt
└── run.py
```

---

## Setup

### 1. Clone and create virtual environment

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
pip install accelerate>=1.1.0
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

Open `http://127.0.0.1:5050` in your browser.

---

## Reproducing Results

### Train XGBoost from scratch
```bash
python data/build_dataset.py
python pipeline/l5_classify/trainer.py
```

### Run ablation study
```bash
python evaluation/ablation.py
```

### Run ResuméAtlas benchmark
```bash
python evaluation/benchmark_resumeatlas.py
```

### Fine-tune SBERT
```bash
python pipeline/l4_match/finetune_sbert.py
```

---

## Comparison with Prior Work

| System | Method | F1 | Explainable |
|---|---|---|---|
| PJFNN (Zhu et al., 2018) | CNN joint representation | 0.800 | No |
| Li et al., 2020 (EMNLP) | BERT + multi-head attention | 0.792* | No |
| Bian et al., 2020 (CIKM) | Graph + BERT multi-view | ~0.78 | No |
| conSultantBERT (Lavi et al., 2021) | Fine-tuned SBERT | 0.749 | No |
| **ExplainHire (ours)** | **Neurosymbolic pipeline** | **0.951** | **Yes** |

*Accuracy reported; dataset differs.

---

## Paper

> **ExplainHire: Neurosymbolic Resume–Job Matching with Explainable Skill Graph Fusion**
> Yoosha Raza, Yanshu, Yogarth · Delhi Technological University · 2026
> IEEE Conference Paper · `paper/explainHire_ieee.tex`

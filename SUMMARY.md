# ExplainHire — Project Summary

---

## What Is This Project?

**ExplainHire** is your Final Year B.Tech project at Delhi Technological University.

It is a **Neurosymbolic AI system** that takes a candidate's resume and a job description,
matches them intelligently, and — most importantly — **explains why** the match score
is what it is.

> "You scored 72%. You have Python and ML, but you're missing Docker and Kubernetes.
> Here's where to learn them."

That explainability is what separates it from a plain similarity scorer.
It combines two AI paradigms:

| Paradigm | What it contributes |
|---|---|
| **Symbolic AI** | Ontology graph — understands that "ML" = "machine_learning", and that TensorFlow is a child of deep_learning |
| **Neural AI** | SBERT understands meaning ("developed models" ≈ "built ML pipelines"), XGBoost classifies the final verdict |

---

## What Was Done (Session 1)

The **full project scaffold** was created — no ML code yet, just clean structure.

### Files created (42 files, 19 directories):

```
ExplainHire/
├── run.py                  ← Start the app: python run.py
├── config.py               ← Single source of truth for ALL settings
├── requirements.txt        ← Every dependency, pinned to exact version
├── README.md               ← Setup instructions
├── .gitignore
├── .env.example            ← Copy to .env and set your SECRET_KEY
│
├── app/                    ← Flask web application
│   ├── __init__.py         ← App factory (create_app)
│   ├── models.py           ← Database tables: User, MatchHistory
│   └── routes/
│       ├── auth.py         ← /login, /register, /logout
│       ├── match.py        ← /match  (runs the AI pipeline)
│       └── history.py      ← /history, /result/<id>
│
├── pipeline/               ← The AI brain, split into 7 layers
│   ├── l1_input/           ← Validate uploaded file
│   ├── l2_parse/           ← Read PDF/DOCX → structured JSON
│   ├── l3_normalize/       ← "JS" → "javascript", "k8s" → "kubernetes"
│   ├── l4_match/           ← Three parallel scorers (graph, semantic, structural)
│   ├── l5_classify/        ← XGBoost: Not Recommended / Maybe / Recommended
│   ├── l6_explain/         ← Why? Matched skills, missing skills, learning links
│   └── l7_present/         ← Glues pipeline to Flask
│
├── ontology/               ← The skill knowledge graph
│   ├── alias_table.json    ← Raw skill → canonical node (e.g. "ml" → "machine_learning")
│   ├── learning_resources.json ← Skill → free course links
│   └── build_ontology.py   ← Script to compile the NetworkX graph
│
├── data/
│   ├── raw/                ← Put Kaggle datasets here (not in git)
│   └── annotations/
│       └── annotation.csv  ← resume_id, jd_id, label — your training data
│
├── models/                 ← Saved XGBoost model after training
├── evaluation/             ← Baselines, metrics, ablation study scripts
├── tests/                  ← Unit + integration tests per layer
└── notebooks/              ← Jupyter EDA / experiments
```

---

## Does It Have a UI?

**Yes.** It is a Flask web app with Bootstrap 5 templates.

The UI lives in:
```
app/templates/          ← HTML pages (Jinja2)
app/static/css/         ← Stylesheets
app/static/js/          ← JavaScript
```

### Pages planned:

| Route | Page | What it does |
|---|---|---|
| `/` | `index.html` | Landing page / upload form |
| `/register` | `register.html` | Create account |
| `/login` | `login.html` | Login |
| `/match` | — | POST endpoint: receives resume + JD, runs pipeline, redirects to result |
| `/result/<id>` | `result.html` | Shows score, matched skills, missing skills, suggestions, SHAP chart |
| `/history` | `history.html` | All past matches for the logged-in user |

The templates **have not been written yet** — they come in the last build phase (L7).

---

## The AI Pipeline — Plain English

```
You upload a resume (PDF/DOCX) + paste a job description
                    ↓
L1  Validate the file is safe and readable
                    ↓
L2  Extract raw text → find sections (Experience, Education, Skills)
    → run spaCy NER to pull out skill entities
                    ↓
L3  Normalize: "JS" → "javascript", "Postgres" → "postgresql"
                    ↓
    ┌──────────────────────────────────────────────────┐
L4a │ Graph Score (50%)                                │
    │ Walk the skill ontology graph:                   │
    │  exact match = 1.0 · alias match = 0.9           │
    │  parent/sibling = 0.6                            │
    ├──────────────────────────────────────────────────┤
L4b │ Semantic Score (35%)                             │
    │ SBERT embeds resume text + JD text               │
    │ Cosine similarity → catches paraphrases          │
    ├──────────────────────────────────────────────────┤
L4c │ Structural Score (15%)                           │
    │ Does the resume have the right experience level? │
    │ Correct education? Skill coverage ratio?         │
    └──────────────────────────────────────────────────┘
                    ↓
L5  FinalScore = 0.50×Graph + 0.35×SBERT + 0.15×Structural
    XGBoost classifies → Label 0 / 1 / 2
    SHAP explains which features drove the score
                    ↓
L6  Build the explanation:
    ✅ Matched skills (with the sentence from resume that proves it)
    ❌ Missing skills
    📚 Top 5 learning suggestions with links
                    ↓
L7  Flask renders result page + saves to SQLite history
```

---

## What You Still Need To Do

Build in this order — each layer feeds the next.

### Phase 1 — Data & Ontology (do before any ML)
- [ ] Download resume dataset from Kaggle (`snehaanbhawal/resume-dataset`) → `data/raw/resumes/`
- [ ] Download JD dataset from Kaggle (`arshkon/linkedin-job-postings`) → `data/raw/job_descriptions/`
- [ ] Fill `ontology/alias_table.json` with comprehensive skill aliases
- [ ] Write `ontology/build_ontology.py` to build the NetworkX graph with `CHILD_OF` and `IS_ALIAS_OF` edges
- [ ] Create `data/annotations/annotation.csv` with labeled resume-JD pairs (0/1/2)

### Phase 2 — Pipeline Modules (build & test one at a time)
- [ ] **L2** `resume_parser.py` — PDF/DOCX → raw text + sections + spaCy NER skills
- [ ] **L2** `jd_parser.py` — JD text → required skills, experience level
- [ ] **L3** `normalizer.py` — raw skills → canonical nodes via alias table
- [ ] **L4a** `graph_matcher.py` — 3-level traversal → GraphScore + evidence list
- [ ] **L4b** `semantic_matcher.py` — SBERT embed + cosine → SBERTScore
- [ ] **L4c** `structural_matcher.py` — section coverage → StructuralScore
- [ ] **L5** `trainer.py` — train XGBoost on annotation.csv, save model
- [ ] **L5** `predictor.py` — load model, run inference, return label + SHAP
- [ ] **L6** `evidence_mapper.py` — build matched/missing skill lists with proof
- [ ] **L6** `suggestion_engine.py` — missing skills → top-N learning links
- [ ] **L7** `pipeline_runner.py` — orchestrate L1→L6 into one function call

### Phase 3 — Web App
- [ ] Write Flask routes (`auth.py`, `match.py`, `history.py`)
- [ ] Write HTML templates (base, index, result, history, login, register)
- [ ] Wire up file upload + form handling

### Phase 4 — Evaluation (for the paper/report)
- [ ] `evaluation/baselines.py` — TF-IDF cosine, SBERT-only, Graph-only
- [ ] `evaluation/metrics.py` — Macro F1, Precision, Recall, Confusion Matrix
- [ ] `evaluation/ablation.py` — remove one component at a time, compare

---

## Quick Setup (when you're ready to run it)

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows

# 2. Install all dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 3. Create .env file
echo SECRET_KEY=anything-secret > .env

# 4. Init the database
python -c "from app import create_app, db; app=create_app(); ctx=app.app_context(); ctx.push(); db.create_all()"

# 5. Run
python run.py
# → open http://127.0.0.1:5000
```

---

## Key Design Decisions (already locked in `config.py`)

| Setting | Value | Reason |
|---|---|---|
| GraphScore weight | 50% | Ontology is the core symbolic contribution |
| SBERTScore weight | 35% | Captures semantic paraphrasing |
| StructuralScore weight | 15% | Supporting signal, not primary |
| Exact match weight | 1.0 | Perfect canonical match |
| Alias match weight | 0.9 | Same skill, different name |
| Related skill weight | 0.6 | Parent/sibling node in graph |
| "Maybe" threshold | ≥ 0.40 | FinalScore cutoff for label 1 |
| "Recommended" threshold | ≥ 0.70 | FinalScore cutoff for label 2 |

---

## Next Step

Tell me when the structure looks good and we start with **L2 — Resume Parser**
(`pipeline/l2_parse/resume_parser.py`).

That is the foundation everything else reads from.

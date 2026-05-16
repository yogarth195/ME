# ExplainHire — Project Summary

## What is it?

A system that takes a resume (PDF) and a job description (text) and tells you:
- Does this person match the job? (Yes/No + confidence %)
- Why? (which skills matched, which didn't)
- What's missing? (which skills to add to get the job)

---

## The Problem

Most resume screeners are black boxes — they give a score but no explanation.
Keyword matchers miss synonyms ("Node.js" ≠ "nodejs" to a dumb matcher).
No existing tool tells a candidate *what to learn* to improve their match.

---

## The Solution — 7-Layer Pipeline

```
User uploads PDF resume + pastes Job Description
                    |
                    v
┌───────────────────────────────────────────┐
│  L1 — INPUT VALIDATION                    │
│  Check file type (PDF/DOCX), size < 5MB   │
└───────────────────┬───────────────────────┘
                    |
                    v
┌───────────────────────────────────────────┐
│  L2 — PARSE                               │
│  Extract: skills, years of experience,    │
│  education level, resume sections         │
└───────────────────┬───────────────────────┘
                    |
                    v
┌───────────────────────────────────────────┐
│  L3 — ONTOLOGY (Knowledge Graph)          │
│  434 skill nodes, NetworkX DiGraph        │
│  Knows: PyTorch → deep_learning →         │
│         machine_learning                  │
│  Built from O*NET occupational database   │
└───────────────────┬───────────────────────┘
                    |
                    v
┌───────────────────────────────────────────┐
│  L4 — MATCH (3 independent signals)       │
│                                           │
│  Signal 1: Graph Score (symbolic)         │
│  Skill ontology matching, 6 levels:       │
│  exact(1.0) → alias(0.9) →               │
│  child/parent(0.7/0.5) → sibling(0.4)    │
│                                           │
│  Signal 2: SBERT Score (neural)           │
│  Sentence embeddings, semantic similarity │
│  Resume text vs JD text → 0.0 to 1.0     │
│                                           │
│  Signal 3: Structural Score (rule-based)  │
│  YOE gap + education gap + sections       │
└───────────────────┬───────────────────────┘
                    |
                    v
         14 numeric features extracted
                    |
                    v
┌───────────────────────────────────────────┐
│  L5 — CLASSIFY (XGBoost)                  │
│  Trained on 967 labeled resume-JD pairs   │
│  Fuses all 14 features → match/no-match   │
│  + probability score                      │
│  SHAP explains which feature drove score  │
└───────────────────┬───────────────────────┘
                    |
                    v
┌───────────────────────────────────────────┐
│  L6 — EXPLAIN                             │
│  Evidence mapper: finds sentences in      │
│  resume proving each matched skill        │
│  Skill gap: which skills to add to        │
│  cross the match threshold                │
└───────────────────┬───────────────────────┘
                    |
                    v
┌───────────────────────────────────────────┐
│  L7 — PRESENT (Flask UI)                  │
│  Verdict + confidence                     │
│  3 score cards (skill/semantic/structural)│
│  Skill-by-skill breakdown with evidence   │
│  Skill gap analysis + learning resources  │
└───────────────────────────────────────────┘
```

---

## Key Components Explained Simply

### Skill Ontology (L3)
A knowledge graph where skills have parent-child relationships.

```
machine_learning
├── deep_learning
│   ├── pytorch
│   ├── tensorflow
│   └── huggingface
├── scikit_learn
└── xgboost

project_management
├── agile
├── scrum
├── jira
└── confluence
```

If your resume has "PyTorch" and the JD asks for "Machine Learning" —
a keyword matcher scores 0. Our graph matcher scores 0.5 (child→parent match).

### Three Signals (L4)
| Signal | What it measures | Example |
|---|---|---|
| Graph score | Skill overlap via ontology | PyTorch vs ML → 0.5 |
| SBERT score | Overall semantic similarity | Resume text vs JD text → 0.72 |
| Structural score | YOE gap, education gap | 3yr exp vs 5yr required → 0.4 |

### XGBoost (L5)
Learns the best way to combine all 3 signals from 967 labeled examples.
Not a deep learning model — interpretable, fast, works well on tabular features.
SHAP shows which feature pushed the score up or down for each prediction.

---

## Results

| Method | F1 Score |
|---|---|
| TF-IDF (keyword matching) | 0.09 |
| SBERT only (neural) | 0.64 |
| Graph only (ontology) | 0.66 |
| Graph + SBERT (no structural) | 0.69 |
| **ExplainHire (full pipeline)** | **0.90** |

**+21% F1 over best single baseline.**
Cross-validated F1 = 0.803 (honest estimate on unseen data).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Resume parsing | Python, regex, pdfplumber |
| Skill ontology | NetworkX, O*NET database |
| Semantic matching | SBERT (all-MiniLM-L6-v2) |
| Classifier | XGBoost |
| Explainability | SHAP TreeExplainer |
| Web app | Flask 3.x, Jinja2 |
| UI | HTML/CSS, dark/light theme |

---

## Training Data

| Source | Rows | Type |
|---|---|---|
| Synthetic (hand-crafted) | 167 | Controlled coverage |
| Real paired dataset | 800 | resume_data.csv, real resumes + JDs |
| **Total** | **967** | |

---

## What Makes it Different

1. **Explainability** — not just a score, shows *why* with evidence sentences from the resume
2. **Ontology matching** — understands skill relationships, not just keywords
3. **Skill gap analysis** — tells candidates exactly what to learn
4. **Three-signal fusion** — symbolic + neural + structural, each adds value

---

## Project Title
> "Automated Resume Screening using NLP and Structured Skill Graphs:
> A Hybrid Symbolic-Neural Pipeline with Explainable Predictions"

---

## File Structure
```
ExplainHire/
├── ontology/          skill knowledge graph (434 nodes)
├── pipeline/
│   ├── l1_input/      validation
│   ├── l2_parse/      resume + JD parsing
│   ├── l4_match/      graph + SBERT + structural matchers
│   ├── l5_classify/   XGBoost trainer + predictor
│   ├── l6_explain/    evidence mapper + skill gap
│   └── l7_present/    pipeline runner
├── app/               Flask UI
├── data/              training data + scripts
├── evaluation/        ablation study + baselines
└── models/            saved XGBoost model
```

# ExplainHire — Locked Build Steps

> One step at a time. Do not start Step N+1 until Step N passes its Done Check.
> Come back to Claude after each step with: "Step X done" and get the next code block.

---

## STEP 0 — Environment Setup
**Goal:** Flask starts. Datasets exist. API key works.

```
cd ExplainHire
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

- Copy `.env.example` → `.env`
- Add to `.env`:
  ```
  LLM_PROVIDER=claude
  LLM_API_KEY=sk-ant-...
  SECRET_KEY=any-random-string
  ```
- Download datasets from Kaggle:
  - Resume dataset: `kaggle datasets download snehaanbhawal/resume-dataset`
  - JD dataset: `kaggle datasets download arshkon/linkedin-job-postings`
  - Unzip resumes → `data/raw/resumes/`
  - Unzip JDs → `data/raw/job_descriptions/`

**Done check:** `python run.py` → Flask starts on http://127.0.0.1:5000 with no errors.

---

## STEP 1 — Ontology: alias_table.json (expanded)
**File:** `ontology/alias_table.json`
**Goal:** At least 80 alias mappings across 5 domains.

Claude writes: Full alias_table.json covering Web, ML/DS, DevOps, Mobile, Cyber, Data, Cloud.

**Done check:** File has 80+ keys. `json.load()` works without errors.

---

## STEP 2 — Ontology: build_ontology.py
**File:** `ontology/build_ontology.py`
**Goal:** Build and save `skill_ontology.gpickle` with 200+ nodes, 300+ edges.

Claude writes: Full script with hardcoded edge definitions (CHILD_OF + IS_ALIAS_OF) across all domains, NetworkX DiGraph, saved with `nx.write_gpickle`.

**Done check:**
```python
python ontology/build_ontology.py
# Output: "Graph built: 212 nodes, 318 edges"
```
`skill_ontology.gpickle` exists in `ontology/`.

---

## STEP 3 — Resume Parser
**File:** `pipeline/l2_parse/resume_parser.py`
**Goal:** Parse PDF/DOCX → structured dict with sections + years_of_experience + education_level.

Claude writes: Full parser using PyMuPDF + python-docx, section detection by heading keywords, YOE extraction via regex on experience section.

**Done check:** Run on 3 real PDFs from `data/raw/resumes/`. Output dict has all 4 sections populated. No crashes.

---

## STEP 4 — JD Parser
**File:** `pipeline/l2_parse/jd_parser.py`
**Goal:** Parse raw JD text → structured dict with required_skills, preferred_skills, required_years, required_education.

Claude writes: Full parser using regex + keyword detection.

**Done check:** Run on 3 JD strings from `data/raw/job_descriptions/`. Output looks correct.

---

## STEP 5 — LLM Skill Extractor
**File:** `pipeline/l2_parse/skill_extractor.py` ← new file
**Goal:** Call Claude Haiku with structured prompt → return list of raw skill strings.

Claude writes: Full extractor using `anthropic` SDK, structured JSON-output prompt, error handling, logging to `logs/llm_calls.jsonl`.

**Done check:** Run on 5 resume texts. Compare vs. spaCy NER output. LLM finds 2–3x more skills. Log file exists.

---

## STEP 6 — Normalizer
**File:** `pipeline/l3_normalize/normalizer.py`
**Goal:** `["JS", "k8s", "TensorFlow"]` → `["javascript", "kubernetes", "tensorflow"]`

Claude writes: Full normalizer using alias_table.json → ontology graph → passthrough logic.

**Done check:**
```python
from pipeline.l3_normalize.normalizer import normalize_skills
assert normalize_skills(["JS", "k8s", "TensorFlow"]) == ["javascript", "kubernetes", "tensorflow"]
```

---

## STEP 7 — Graph Matcher
**File:** `pipeline/l4_match/graph_matcher.py`
**Goal:** Match resume skills vs JD skills using ontology (exact → alias → parent). Return score + breakdown.

Claude writes: Full matcher with 3-level traversal, weight logic (1.0 / 0.9 / 0.6), score calculation.

**Done check:**
```python
# JD: ["kubernetes", "docker", "python"]
# Resume: ["k8s", "python"]
# Expected: kubernetes matched via alias (0.9), python exact (1.0), docker unmatched
# graph_score = (0.9 + 1.0) / 3 = 0.633
```
Unit test in `tests/test_matchers.py` passes.

---

## STEP 8 — Semantic Matcher
**File:** `pipeline/l4_match/semantic_matcher.py`
**Goal:** SBERT cosine similarity between resume text and JD text → float 0–1.

Claude writes: Module-level model singleton (loads once), single function returning float.

**Done check:** Returns sensible float for 3 test pairs. Loads model only once per session.

---

## STEP 9 — Structural Matcher
**File:** `pipeline/l4_match/structural_matcher.py`
**Goal:** Compare years_of_experience + education_level + skill_coverage → structural_score 0–1.

Claude writes: Three sub-scores averaged, with documented thresholds.

**Done check:** Sensible scores for overqualified, underqualified, and matched test cases.

---

## STEP 10 — Annotation CSV (Training Data)
**File:** `data/annotations/annotation.csv`
**Goal:** 200 labeled resume-JD pairs. Labels: 0=Not Recommended, 1=Maybe, 2=Recommended. ~67 per class.

Process:
1. Pick 200 pairs from Kaggle datasets
2. Run Steps 7+9 scores on each → auto-label: <0.40 → 0, 0.40–0.70 → 1, ≥0.70 → 2
3. Manually review and correct 50 of them

Claude writes: Script `data/scripts/auto_label.py` to generate initial labels.

**Done check:** CSV has 200 rows. All 3 classes represented. No nulls.

---

## STEP 11 — XGBoost Classifier (Trainer)
**File:** `pipeline/l5_classify/trainer.py`
**Goal:** Train XGBoost on 10 features from annotation.csv. 5-fold CV. Save model + SHAP explainer.

Claude writes: Full trainer with feature list, 5-fold CV, saved artifacts to `models/`.

**Done check:** `python pipeline/l5_classify/trainer.py` runs. Prints per-fold F1. Saves `models/xgb_model.pkl` and `models/shap_explainer.pkl`.

---

## STEP 12 — Predictor
**File:** `pipeline/l5_classify/predictor.py`
**Goal:** Load model → predict label + final_score + SHAP values for one sample.

Claude writes: Full predictor returning typed dict with label, label_name, final_score, shap_values.

**Done check:** `predict(features_dict)` returns correct structure. Macro F1 > 0.70 on held-out set.

---

## STEP 13 — Counterfactual Engine
**File:** `pipeline/l6_explain/counterfactual.py` ← new file
**Goal:** For each missing JD skill, compute score delta if candidate had it. Return ranked list. Flag label changes.

Claude writes: Full counterfactual function with 2-step chain ("add Docker → then Kubernetes → reach 82%").

**Done check:** For a label=1 case, function correctly identifies which 1–2 skills push to label=2. Returns `label_change: True` on those.

---

## STEP 14 — Evidence Mapper
**File:** `pipeline/l6_explain/evidence_mapper.py`
**Goal:** For each matched skill, find the exact sentence in the resume proving it.

Claude writes: Sentence splitter + skill-in-sentence lookup. Returns proof sentence or empty string.

**Done check:** For "PyTorch" in a real resume, returns the sentence mentioning it.

---

## STEP 15 — Suggestion Engine
**File:** `pipeline/l6_explain/suggestion_engine.py`
**Goal:** For missing skills, return learning resources from `ontology/learning_resources.json`.

Claude writes: Simple lookup function + populates learning_resources.json with 30+ skills.

**Done check:** `get_suggestions(["docker", "kubernetes"])` returns dicts with title + url for each.

---

## STEP 16 — LLM Summary Generator
**File:** `pipeline/l6_explain/llm_summary.py` ← new file
**Goal:** Pass match result to Claude Haiku → get 3-sentence recruiter-style plain-English summary.

Claude writes: Full function with structured prompt, logged to `logs/llm_calls.jsonl`.

**Done check:** Output for a test case reads like a real recruiter wrote it. No bullet points. Specific skill names mentioned.

---

## STEP 17 — Bias Audit Module  ← USP
**File:** `pipeline/l6_explain/bias_audit.py` ← new file
**Goal:** Run same JD against 4 synthetic resumes differing only in candidate name. Assert scores within ±2%.

Claude writes: Synthetic resume generator + audit function + pass/fail report.

**Done check:** Running audit on 3 JDs shows score variance < 2%. Report saved to `logs/bias_audit.json`.

---

## STEP 18 — Resume Format Checker  ← USP
**File:** `pipeline/l1_input/format_checker.py` ← new file
**Goal:** Pre-pipeline check. Detect ATS-hostile formatting: tables, text boxes, images with text, missing sections.

Claude writes: PyMuPDF-based checker returning list of warnings.

**Done check:** Detects table in a known resume. Returns warning string. Warnings shown to user before match runs.

---

## STEP 19 — Pipeline Runner
**File:** `pipeline/l7_present/pipeline_runner.py`
**Goal:** One function orchestrates Steps 0–18 in order. Returns complete result dict.

Claude writes: Full `run_pipeline(resume_path, jd_text)` calling every layer.

**Done check:** `run_pipeline("test_resume.pdf", jd_text)` returns dict with: score, label, matched_skills, missing_skills, counterfactuals, evidence, suggestions, summary, bias_report, format_warnings.

---

## STEP 20 — Flask Routes
**Files:** `app/routes/auth.py`, `app/routes/match.py`, `app/routes/history.py`
**Goal:** Register, login, logout, submit match, view result, view history.

Claude writes: All 3 route files with Flask-Login, bcrypt, file upload handling, DB writes.

**Done check:** Can register, login, upload resume + JD, see result, view history. No 500 errors.

---

## STEP 21 — Flask Templates (UI)
**Files:** `app/templates/`
**Goal:** base, index, login, register, result, history pages in Bootstrap 5.

Claude writes: All templates. result.html is the main deliverable: score gauge, verdict badge, matched/missing skills, counterfactuals section, SHAP chart, LLM summary, suggestions.

**Done check:** Full flow looks professional. No broken layouts. Test on Chrome.

---

## STEP 22 — Evaluation: Baselines
**File:** `evaluation/baselines.py`
**Goal:** Implement TF-IDF cosine, SBERT-only, Graph-only baselines. Label by thresholding score.

Claude writes: All 3 baselines as callable functions returning label predictions.

**Done check:** All 3 run on the 200 annotated pairs without errors.

---

## STEP 23 — Evaluation: Metrics + Ablation
**Files:** `evaluation/metrics.py`, `evaluation/ablation.py`
**Goal:** Accuracy, Macro F1, per-class P/R, confusion matrix for ExplainHire + all 3 baselines + 4 ablation variants.

Claude writes: Full metrics script printing comparison table. Saves confusion matrices as PNGs.

**Done check:** ExplainHire Macro F1 > 0.70. ExplainHire beats all 3 baselines. Removing graph causes the largest F1 drop (proves your contribution).

---

## STEP 24 — Report Writing
**Goal:** Complete the DTU B.Tech Project-II report.

Fill in order:
1. Title page, Declaration, Certificate, Acknowledgements ← fill now
2. List of Abbreviations ← fill now
3. Introduction ← write after Step 0
4. Literature Survey ← write after Step 0 (reading only, no code)
5. Objectives & Research Gaps ← write after Step 0
6. Methodology ← write after Step 19
7. Results & Findings ← write after Step 23
8. Conclusion & Future Work ← write last
9. References (IEEE format, 10+ papers)

Claude helps: Draft each section when you reach it.

**Done check:** All sections filled. 10+ IEEE references. All figures/tables referenced in text. Supervisor approval.

---

## STEP 25 — User Study
**Goal:** 25+ responses comparing ExplainHire vs plain percentage score.

Process:
1. Pick 5 resume-JD pairs (one per domain)
2. Run ExplainHire → screenshot result pages
3. Create Google Form with Q1–Q5 (as per build plan)
4. Share with classmates, seniors, LinkedIn
5. Collect 25+ responses

**Done check:** 25+ form responses. ExplainHire scores higher on Q2 (usefulness), Q4 (actionability), Q5 (trust). Export CSV for paper.

---

## Summary Timeline

| Steps | What | Days |
|---|---|---|
| 0 | Environment | 1 |
| 1–2 | Ontology | 2–3 |
| 3–5 | Parsers + LLM extractor | 3–4 |
| 6–9 | Normalizer + Matchers | 3–4 |
| 10–12 | Training data + Classifier | 3–4 |
| 13–18 | Explain + USP modules | 3–4 |
| 19 | Pipeline runner | 1 |
| 20–21 | Flask + UI | 4–5 |
| 22–23 | Evaluation | 2–3 |
| 24 | Report writing | parallel |
| 25 | User study | 1 weekend |
| **Total** | | **~30 days** |

---

## Rules

1. **Never skip a Done Check.** If it doesn't pass, fix it before moving on.
2. **Tell Claude "Step X done"** to get the full production-grade code for Step X+1.
3. **Write the report in parallel** — Introduction and Literature Survey can be written during Steps 1–5.
4. **Log everything** — every LLM call, every pipeline run, every error. You'll need stats for the paper.
5. **Commit after every step** — `git commit -m "Step X: <module name> complete"`.

# ExplainHire — Exact Build Plan

Do these in order. Do not skip ahead.
Each phase has a clear "done when" condition.

---

## Phase 0 — Environment Setup
**Time: 1 day**

- [ ] Create and activate a Python 3.10 virtual environment
- [ ] `pip install -r requirements.txt`
- [ ] `python -m spacy download en_core_web_sm`
- [ ] Get a Claude API key (claude.ai → API) OR an OpenAI key for GPT-4o-mini
      → add to `.env` as `LLM_API_KEY=...` and `LLM_PROVIDER=claude` or `openai`
- [ ] Download resume dataset: kaggle datasets download snehaanbhawal/resume-dataset
      → unzip to `data/raw/resumes/`
- [ ] Download JD dataset: kaggle datasets download arshkon/linkedin-job-postings
      → unzip to `data/raw/job_descriptions/`
- [ ] Run `python run.py` — Flask should start even with empty routes

**Done when:** Flask starts, both datasets are in `data/raw/`, API key is in `.env`

---

## Phase 1 — Ontology (The Brain)
**Time: 3-4 days**

This is the most important phase. Everything else is worthless without a good ontology.

### Step 1.1 — Build alias_table.json comprehensively
File: `ontology/alias_table.json`

Add at minimum these mappings (expand as you find more in the datasets):
```
Web Dev:    js→javascript, ts→typescript, react.js→react, vue.js→vue,
            node.js→nodejs, express.js→express, next.js→nextjs

ML/DS:      ml→machine_learning, dl→deep_learning, nlp→natural_language_processing,
            cv→computer_vision, tf→tensorflow, pytorch→pytorch, sklearn→scikit_learn,
            xgb→xgboost, hf→huggingface, llm→large_language_models

DevOps:     k8s→kubernetes, ci/cd→cicd, aws→amazon_web_services,
            gcp→google_cloud, az→azure, gh actions→github_actions

Mobile:     rn→react_native, flutter→flutter, ios→ios_development,
            android→android_development

Cyber:      pen test→penetration_testing, pentest→penetration_testing,
            soc→security_operations, appsec→application_security
```

### Step 1.2 — Source the ontology from real data
File: `ontology/build_ontology.py`

Use these free, authoritative sources:
- **Stack Overflow tags** — download from: https://data.stackexchange.com/stackoverflow/query/
  Query: `SELECT TagName, Count FROM Tags WHERE Count > 1000 ORDER BY Count DESC`
  This gives you ~2000 real tech skills ranked by usage
- **O*NET** — download Technology Skills from: https://www.onetcenter.org/database.html
  File: `Technology Skills.xlsx` — free, structured, government-maintained

Build the graph edges like this:
```
CHILD_OF edges (parent → child):
  machine_learning → deep_learning
  deep_learning → computer_vision
  deep_learning → natural_language_processing
  javascript → react
  javascript → nodejs
  javascript → vue
  cloud → aws, gcp, azure
  containerization → docker → kubernetes

IS_ALIAS_OF edges:
  ml IS_ALIAS_OF machine_learning
  k8s IS_ALIAS_OF kubernetes
  (everything in alias_table.json)
```

### Step 1.3 — Write build_ontology.py
Script that:
1. Reads your edge definitions
2. Builds a `networkx.DiGraph`
3. Saves to `ontology/skill_ontology.gpickle`

**Done when:** `build_ontology.py` runs, creates `skill_ontology.gpickle`,
graph has at least 200 nodes and 300 edges across 5 domains.

---

## Phase 2 — Resume + JD Parser (L2)
**Time: 2-3 days**

### Step 2.1 — resume_parser.py
File: `pipeline/l2_parse/resume_parser.py`

Must do:
- Accept a file path (PDF or DOCX)
- Use PyMuPDF for PDF, python-docx for DOCX
- Extract raw text
- Detect sections: find "Experience", "Education", "Skills", "Projects" headings
  (look for lines that are ALL CAPS, or match keyword list from config.py)
- Return structured dict:
```python
{
  "raw_text": "...",
  "sections": {
    "experience": "...",
    "education": "...",
    "skills": "...",
    "projects": "..."
  },
  "years_of_experience": 3,   # count years mentioned in experience section
  "education_level": "B.Tech" # highest degree found
}
```

### Step 2.2 — jd_parser.py
File: `pipeline/l2_parse/jd_parser.py`

Simpler — JDs are plain text:
- Accept raw JD string
- Extract: required skills section, preferred skills, experience requirement, education requirement
- Return same structured dict format

**Done when:** Pass 5 real resumes through parser, output looks correct, sections are detected.

---

## Phase 3 — LLM Skill Extraction (replaces spaCy NER)
**Time: 1-2 days**

File: `pipeline/l2_parse/skill_extractor.py`  ← new file

This is the single most impactful change over the original design.

Write one function:
```python
def extract_skills_llm(text: str, section: str = "resume") -> list[str]:
    """
    Call Claude Haiku or GPT-4o-mini with a structured prompt.
    Returns a list of raw skill strings found in the text.
    """
```

Prompt to use:
```
You are a technical recruiter AI. Extract all technical skills, tools,
frameworks, programming languages, platforms, and methodologies from
the following {section} text.

Rules:
- Only extract real technical skills (not soft skills like "teamwork")
- Return each skill exactly as written in the text
- Return JSON: {"skills": ["Python", "FastAPI", "Docker", ...]}
- If no skills found, return {"skills": []}

Text:
{text}
```

Use Claude Haiku (`claude-haiku-4-5-20251001`) — it's fast and cheap enough
for this task (~$0.001 per resume).

**Done when:** Run extractor on 5 resumes, compare output vs. spaCy.
LLM should catch 2-3x more skills. Log the difference.

---

## Phase 4 — Normalizer (L3)
**Time: 1 day**

File: `pipeline/l3_normalize/normalizer.py`

Function:
```python
def normalize_skills(raw_skills: list[str]) -> list[str]:
    """
    raw_skills: ["JS", "react.js", "Machine Learning"]
    returns:    ["javascript", "react", "machine_learning"]
    """
```

Logic:
1. Lowercase each skill
2. Check alias_table.json — if found, replace with canonical ID
3. If not in alias table, check if the skill node exists directly in the ontology graph
4. If neither, keep as-is (unknown skill — log it for future ontology expansion)

**Done when:** `normalize(["JS", "k8s", "TensorFlow"])` returns
`["javascript", "kubernetes", "tensorflow"]`

---

## Phase 5 — Graph Matcher (L4a)
**Time: 2-3 days**

File: `pipeline/l4_match/graph_matcher.py`

This is your core scientific contribution. Get it right.

```python
def graph_match(
    resume_skills: list[str],   # canonical node IDs
    jd_skills: list[str],       # canonical node IDs
    graph: nx.DiGraph
) -> dict:
    """
    Returns:
    {
      "graph_score": 0.74,
      "matched": [
        {"skill": "pytorch", "level": 1, "weight": 1.0,
         "match_type": "exact"},
        {"skill": "tensorflow", "level": 2, "weight": 0.9,
         "match_type": "alias", "via": "tf"},
        {"skill": "deep_learning", "level": 3, "weight": 0.6,
         "match_type": "parent", "resume_skill": "pytorch"}
      ],
      "unmatched_jd_skills": ["kubernetes", "docker"]
    }
    """
```

Matching logic per JD skill:
1. **Level 1** — exact node match in resume_skills → weight 1.0
2. **Level 2** — find IS_ALIAS_OF neighbors of JD skill → check if any are in resume_skills → weight 0.9
3. **Level 3** — find CHILD_OF parent/siblings of JD skill → check if any are in resume_skills → weight 0.6
4. Score = sum(matched weights) / len(jd_skills)

**Done when:** Unit test with known inputs returns correct scores.
Test case: JD needs `["kubernetes", "docker", "python"]`,
resume has `["k8s", "python"]` → should match kubernetes via alias + python exact.

---

## Phase 6 — Semantic Matcher (L4b)
**Time: 1 day**

File: `pipeline/l4_match/semantic_matcher.py`

```python
def semantic_match(resume_text: str, jd_text: str) -> float:
    """
    Embed both texts with SBERT all-MiniLM-L6-v2.
    Return cosine similarity as SBERTScore (0.0 to 1.0).
    """
```

Keep it simple — one function, one score.
Cache the SBERT model at module level so it loads once.

**Done when:** Returns a float between 0 and 1 for any two texts.

---

## Phase 7 — Structural Matcher (L4c)
**Time: 1 day**

File: `pipeline/l4_match/structural_matcher.py`

```python
def structural_match(resume: dict, jd: dict) -> dict:
    """
    resume: output from resume_parser
    jd:     output from jd_parser
    Returns: {"structural_score": 0.65, "breakdown": {...}}
    """
```

Score three things:
1. **Experience coverage** (0-1): resume years_of_experience >= jd required_years → 1.0, else ratio
2. **Education match** (0-1): resume education_level meets jd requirement → 1.0 or 0.5 or 0.0
3. **Skill coverage ratio** (0-1): len(matched_skills) / len(jd_skills)

StructuralScore = mean of the three.

**Done when:** Returns sensible scores for 3 test cases (overqualified, underqualified, matched).

---

## Phase 8 — Classifier (L5)
**Time: 2-3 days**

### Step 8.1 — Create annotation.csv
File: `data/annotations/annotation.csv`

You need labeled training data. Strategy:
- Take 200 resume-JD pairs from your Kaggle datasets
- Use the rule-based FinalScore to auto-label them as a starting point:
  score < 0.40 → label 0, 0.40-0.70 → label 1, >= 0.70 → label 2
- Manually review and correct ~50 of them
- Aim for balanced classes: ~67 per class

### Step 8.2 — trainer.py
File: `pipeline/l5_classify/trainer.py`

Features to use (not just 4 — use more):
```python
features = [
    "graph_score",
    "sbert_score",
    "structural_score",
    "skill_coverage_ratio",
    "exact_match_count",
    "alias_match_count",
    "related_match_count",
    "years_experience_delta",   # resume_years - jd_required_years
    "education_match_score",
    "unmatched_jd_skill_count"
]
```

Using 10 features instead of 4 makes XGBoost actually justified.
Train with 5-fold CV. Save: model + SHAP explainer.

### Step 8.3 — predictor.py
File: `pipeline/l5_classify/predictor.py`

```python
def predict(features: dict) -> dict:
    """
    Returns:
    {
      "label": 2,
      "label_name": "Recommended",
      "final_score": 0.74,
      "shap_values": {"graph_score": 0.12, "sbert_score": 0.08, ...}
    }
    """
```

**Done when:** Macro F1 > 0.70 on held-out test set across all 3 classes.

---

## Phase 9 — Counterfactual Explanations (Your Killer Feature)
**Time: 2 days**

File: `pipeline/l6_explain/counterfactual.py`  ← new file, does not exist yet

This is the thing that makes your project different from everything else.

```python
def compute_counterfactuals(
    resume_skills: list[str],
    jd_skills: list[str],
    unmatched_jd_skills: list[str],
    current_score: float,
    predictor,
    graph_matcher,
    semantic_matcher,
    structural_matcher
) -> list[dict]:
    """
    For each missing JD skill, compute what the score would be
    if the candidate had that skill.

    Returns ranked list:
    [
      {
        "skill": "docker",
        "score_delta": +0.14,
        "new_score": 0.68,
        "new_label": "Recommended",
        "label_change": True   ← this is the important one
      },
      {
        "skill": "kubernetes",
        "score_delta": +0.09,
        "new_score": 0.63,
        "new_label": "Maybe",
        "label_change": False
      }
    ]
    Sort by score_delta descending.
    """
```

Show only the top 3 in the UI.
Highlight in RED if adding that skill changes the label.

**Done when:** For a test case where label=1 (Maybe), the function correctly
identifies which 1-2 skills would push it to label=2 (Recommended).

---

## Phase 10 — Evidence Mapper + Suggestion Engine (L6)
**Time: 1-2 days**

### evidence_mapper.py
For each matched skill, find the sentence in the resume that proves it:
```python
def find_proof_sentence(skill: str, resume_text: str) -> str:
    """
    Find the sentence containing this skill mention.
    Return the full sentence as proof.
    """
    sentences = resume_text.split('.')
    for s in sentences:
        if skill.lower() in s.lower():
            return s.strip()
    return ""
```

### suggestion_engine.py
For top-N missing skills, look up `learning_resources.json`:
```python
def get_suggestions(missing_skills: list[str], n: int = 5) -> list[dict]:
    # returns list of {skill, resources: [{title, url}]}
```

### LLM Summary Generation (new addition)
File: `pipeline/l6_explain/llm_summary.py`  ← new file

```python
def generate_summary(match_result: dict) -> str:
    """
    Pass structured match result to Claude Haiku.
    Get back 3-sentence professional plain-English explanation.
    """
```

Prompt:
```
You are an AI hiring assistant. Write a 3-sentence professional explanation
of the following resume-job match result for a hiring manager.
Be specific about skills. Do not add information not present in the data.
Do not use bullet points. Use plain sentences.

Match data:
- Final Score: {score}%
- Verdict: {label_name}
- Matched skills: {matched_skills}
- Missing skills: {missing_skills}
- Top improvement: adding {top_counterfactual_skill} would raise score by {delta}%
```

**Done when:** Output for a test case reads like a real recruiter wrote it.

---

## Phase 11 — Pipeline Runner (L7)
**Time: 1 day**

File: `pipeline/l7_present/pipeline_runner.py`

One function that orchestrates everything:
```python
def run_pipeline(resume_path: str, jd_text: str) -> dict:
    """
    Full L1→L6 execution.
    Returns the complete result dict ready for Flask/Jinja2.
    """
    # 1. Validate file (L1)
    # 2. Parse resume + JD (L2)
    # 3. Extract skills via LLM (L3a)
    # 4. Normalize skills (L3b)
    # 5. Load ontology graph
    # 6. Graph match (L4a)
    # 7. Semantic match (L4b)
    # 8. Structural match (L4c)
    # 9. Predict + SHAP (L5)
    # 10. Counterfactuals (L6a)
    # 11. Evidence + suggestions (L6b)
    # 12. LLM summary (L6c)
    # 13. Return full result dict
```

**Done when:** `run_pipeline("test_resume.pdf", jd_text)` returns a complete dict
with score, label, matched skills, missing skills, counterfactuals, and summary.

---

## Phase 12 — Flask Routes + UI
**Time: 3-4 days**

### Routes
- `auth.py` — register (bcrypt hash), login (Flask-Login), logout
- `match.py` — POST `/match`: save uploaded file, call `run_pipeline`, save to DB, redirect to result
- `history.py` — GET `/history`: list user's past matches; GET `/result/<id>`: show one result

### Templates (build in this order)
1. `base.html` — Bootstrap 5 navbar, flash messages block, content block
2. `index.html` — two-panel form: file upload (left) + JD textarea (right) + submit button
3. `login.html` / `register.html` — standard auth forms
4. `result.html` — the most important page:
   - Big score gauge (CSS/JS circle)
   - Verdict badge (green/yellow/red)
   - LLM summary paragraph
   - Two columns: ✅ Matched Skills | ❌ Missing Skills
   - Counterfactuals section: "Adding these skills would change your result:"
   - SHAP bar chart (matplotlib → base64 PNG embedded)
   - Learning suggestions with links
5. `history.html` — table of past matches

**Done when:** Full flow works: register → login → upload resume + JD → see result page → view history.

---

## Phase 13 — Evaluation
**Time: 2-3 days**

File: `evaluation/baselines.py`

Implement three baselines:
1. **TF-IDF cosine** — vectorize resume + JD, cosine similarity, threshold to label
2. **SBERT-only** — just semantic_matcher score, threshold to label
3. **Graph-only** — just graph_matcher score, threshold to label

File: `evaluation/metrics.py`

For ExplainHire AND all 3 baselines, compute and print:
- Accuracy
- Macro F1
- Per-class Precision + Recall
- Confusion matrix (save as PNG)

File: `evaluation/ablation.py`

Run 4 experiments:
1. Full system (Graph + SBERT + Structural)
2. No graph (SBERT + Structural only)
3. No SBERT (Graph + Structural only)
4. No structural (Graph + SBERT only)

Report F1 for each. The drop when you remove graph should be the largest — that proves your contribution.

**Done when:** You have a table showing ExplainHire beats all 3 baselines on Macro F1.
That table goes directly into your paper as Table 2.

---

## Phase 14 — User Study
**Time: 1 weekend**

You need this for publication. It is not optional.

**What to build:** A simple Google Form.

**Who to survey:** 25-30 people — classmates, seniors, LinkedIn connections who have
applied for jobs. They do not need to be technical.

**How to run it:**
1. Pick 5 real resume-JD pairs (one per domain)
2. Run ExplainHire on each, get the result page
3. Take screenshots of the result page
4. Take screenshots of a plain percentage score (just "72% match" with no explanation)
5. Show each person both versions of one result, ask:

```
Q1. How useful is Explanation A (plain %) for understanding the match? [1-5]
Q2. How useful is Explanation B (ExplainHire full output) for understanding the match? [1-5]
Q3. Which explanation would help you decide whether to apply for this job? [A / B]
Q4. How actionable is the "skills to add" advice? [1-5]
Q5. Overall, do you trust ExplainHire's reasoning? [1-5]
```

**Done when:** You have 25+ responses. ExplainHire should score higher on Q2, Q4, Q5.
That is your user study section. One paragraph in the paper.

---

## What You Submit (Paper Structure)

Once all phases are done, your paper writes itself:

```
1. Introduction        — hiring AI black-box problem, need for explainability
2. Related Work        — resume matching papers, XAI papers, neurosymbolic AI
3. System Architecture — your 7-layer pipeline diagram
4. Methodology         — graph matching (your contribution), LLM extraction,
                         counterfactual explanations (your contribution)
5. Experiments         — dataset, baselines, ablation table, F1 results
6. User Study          — Table: ExplainHire vs plain score, 25 participants
7. Conclusion
```

---

## Total Time Estimate

| Phase | Days |
|---|---|
| 0 — Setup | 1 |
| 1 — Ontology | 3-4 |
| 2 — Parsers | 2-3 |
| 3 — LLM Extractor | 1-2 |
| 4 — Normalizer | 1 |
| 5 — Graph Matcher | 2-3 |
| 6 — Semantic Matcher | 1 |
| 7 — Structural Matcher | 1 |
| 8 — Classifier | 2-3 |
| 9 — Counterfactuals | 2 |
| 10 — Evidence + Summary | 1-2 |
| 11 — Pipeline Runner | 1 |
| 12 — Flask + UI | 3-4 |
| 13 — Evaluation | 2-3 |
| 14 — User Study | 2 |
| **Total** | **~30-35 days** |

Working 4-5 hours/day: **6-8 weeks.**
Working full-time: **4-5 weeks.**

---

## When To Talk To Me Next

Come back when you finish each phase. Do not try to do multiple phases at once.
Say: "Phase 1 done, let's build Phase 2" — and I will write the full code for that module.

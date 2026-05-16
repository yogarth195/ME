# Honest Review — Is ExplainHire Worth Publishing?

---

## The Honest Answer

**As currently designed: No, not in any serious venue.**

In its current form this is a well-structured undergraduate project.
It would pass a viva, impress a college jury, and maybe get into a low-tier
journal (IJRASET, IJERT). That's it.

Here is exactly why — and then exactly how to fix it.

---

## What Is Weak Right Now

### 1. The scoring weights are made up
```python
FinalScore = 0.50 × GraphScore + 0.35 × SBERTScore + 0.15 × StructuralScore
```
You chose 50/35/15 from intuition. Any reviewer will ask:
> "Why not 60/30/10? How did you determine these weights?"

If you cannot answer that with data, it is not science — it is guessing.

### 2. XGBoost on 4 features is trivially simple
You are training XGBoost on `[GraphScore, SBERTScore, StructuralScore, skill_coverage_ratio]`.
That is 4 numbers. A logistic regression would do the same job.
XGBoost on 4 features adds no value. A reviewer will notice this immediately.

### 3. spaCy `en_core_web_sm` is a bad skill extractor
`en_core_web_sm` is a general-purpose model. It does not know that
"FastAPI", "Langchain", "RAG", "LoRA" are skills.
It will miss 40-60% of real tech skills silently. Your whole pipeline
depends on extraction being good. If extraction is weak, everything downstream is wrong.

### 4. The "ontology" as designed is a keyword lookup with hierarchy
A JSON alias table + a NetworkX graph with `CHILD_OF` edges is essentially
a beefed-up fuzzy string match. It is not meaningfully different from a synonym dictionary.
This is not a knowledge graph in the research sense.

### 5. SBERT `all-MiniLM-L6-v2` is a 2021 model
It is fine for demos. But in 2026 there are much better open embedding models
(BGE, E5, NV-Embed). Using the oldest, smallest model signals you did not
survey the literature.

### 6. No novel contribution is clearly stated
Research requires one of:
- A new method that did not exist before
- A new dataset
- A new evaluation showing an existing method works somewhere it was not tested
- A new framing that unifies prior work

Right now the project is: "I combined SBERT + graph matching + XGBoost for resumes."
Three CS papers from 2020-2022 already did this. Without a novel angle it is not publishable.

---

## What IS Actually Good (Your Real USPs)

Do not abandon these — they are genuinely interesting:

**1. The neurosymbolic fusion is a real research direction.**
Combining symbolic reasoning (graph) with neural representations (SBERT) and
learning-based classification (XGBoost) is legitimate. The framing matters.
Call it "a neurosymbolic architecture for interpretable skill matching" —
because that is what it is, and that framing is publishable if executed well.

**2. The 3-level graph traversal with weighted evidence is novel enough.**
Most resume matchers do exact keyword match or pure embedding similarity.
Ontology-aware matching with `exact → alias → related` levels with different weights
is a real methodological contribution. It is your strongest idea.

**3. Explainability is genuinely underexplored in hiring AI.**
SHAP on hiring systems is not common. The evidence mapper (proof sentences) is
original. If you do it well, this is the publishable part.

---

## How To Make This Stand Out

### Fix 1 — Learn the fusion weights, don't hardcode them

Instead of `0.50 × Graph + 0.35 × SBERT + 0.15 × Structural`,
learn the weights as part of training:

```python
# During training, let XGBoost learn feature importance
# Then report: "the model assigned weight X to GraphScore"
# That is a finding — not an assumption
```

Even better: use a **small MLP** instead of XGBoost to learn a non-linear
combination of the three scores. Then you can say:
> "We learn the fusion function rather than assuming linearity."

That one change makes Section 3 of your paper defensible.

### Fix 2 — Replace spaCy NER with an LLM for skill extraction

This is the single highest-ROI change you can make.

```python
# Current (weak):
skills = spacy_ner(resume_text)  # misses "RAG", "LoRA", "FastAPI"

# Better: call Claude / GPT-4o-mini with a structured prompt
prompt = """
Extract all technical skills, tools, frameworks, and technologies 
from the following resume text. Return a JSON list.
Text: {resume_text}
"""
skills = llm_extract(prompt)  # catches everything
```

You keep the graph + SBERT + XGBoost as-is.
The LLM only does extraction. This is a clean separation.
Cost: ~$0.001 per resume with GPT-4o-mini or Claude Haiku.

**Paper claim:** "We use LLM-assisted skill extraction to address the coverage
limitations of general-purpose NER models in technical domain text."
That is a cited contribution.

### Fix 3 — Add Counterfactual Explanations

This is your killer feature. No existing resume tool does this properly.

> "If you add **Docker** and **Kubernetes**, your score increases from 54% to 73%
> and your label changes from Maybe → Recommended."

Implementation: for each missing skill in the ontology, compute the score delta
if that skill were present. Sort by impact. Show top 3.

```python
def counterfactual_impact(resume_skills, jd_skills, missing_skill):
    augmented = resume_skills + [missing_skill]
    new_score = run_pipeline(augmented, jd_skills)
    return new_score - original_score
```

This turns your explainability from passive ("here is why the score is X")
to actionable ("here is what to do to get hired").
No paper in resume matching has done this at the skill-graph level.
This is publishable on its own.

### Fix 4 — Build the Ontology from Real Data

Right now the ontology is hand-written. That does not scale and reviewers will ask
"how complete is it?"

Mine your ontology from real sources:
- **Stack Overflow tags** — 60,000+ tech tags with relationships
- **LinkedIn Skills taxonomy** — publicly crawlable
- **O*NET** — US government occupational database, free, structured

Then you can say:
> "Our ontology contains N skills across 5 domains, derived from Stack Overflow
> tag co-occurrence graphs and O*NET skill taxonomies."

That is a data contribution. It makes the paper more solid.

### Fix 5 — Run a User Study (Even Small)

20-30 people rating explanation quality is enough for a paper.

Survey question: "On a scale of 1-5, how useful was the explanation in
understanding why you did or did not match this job?"

Compare ExplainHire explanations vs. a plain percentage score.
If ExplainHire scores higher (it will), that is a human-evaluation result.
Most NLP/IR papers include this. It costs you one afternoon.

### Fix 6 — Use LLM to Generate Natural Language Explanations

After the pipeline runs, pass the structured output to an LLM:

```
Input:  matched_skills=[Python, ML], missing_skills=[Docker, K8s],
        graph_score=0.61, sbert_score=0.74, label=1
        
Prompt: "Write a 3-sentence professional explanation of this match result
         for a hiring manager. Be specific. Do not hallucinate skills."

Output: "The candidate demonstrates strong alignment in core ML competencies,
         including Python and machine learning, which are central to the role.
         However, the position requires significant DevOps experience —
         particularly Docker and Kubernetes — which are absent from the resume.
         Upskilling in containerization would substantially improve candidacy."
```

This makes the UI feel like a real product, not a research demo.

---

## Revised Architecture (What Makes It Special)

```
L1  Input: PDF/DOCX + JD
           ↓
L2  Parse: PyMuPDF/docx → raw text + sections
           ↓
L3  Extract: LLM (Claude Haiku / GPT-4o-mini) → structured skill list
    [NEW — replaces weak spaCy NER]
           ↓
L4  Normalize: alias table → canonical ontology nodes
    [Ontology built from SO tags + O*NET, not hand-written]
           ↓
L5a Graph Match:      3-level traversal → GraphScore + evidence
L5b Semantic Match:   SBERT (or BGE) cosine → SBERTScore  
L5c Structural Match: section coverage → StructuralScore
           ↓
L6  Classify: small MLP learns fusion weights → label + feature attribution
    [NEW — replaces hardcoded 0.50/0.35/0.15 and weak XGBoost-on-4-features]
           ↓
L7  Explain:
    - Matched skills with proof sentences          (existing)
    - Missing skills ranked by counterfactual impact [NEW — your killer feature]
    - LLM-generated natural language summary       [NEW]
    - SHAP chart showing which score drove the verdict (existing)
           ↓
L8  Present: Flask + Bootstrap UI
```

---

## What Venue Could This Get Into?

With the changes above:

| Target | Realistic? | What it needs |
|---|---|---|
| **ACL / EMNLP / NAACL** (top NLP) | No | Too competitive, needs deeper NLP contribution |
| **ECIR / SIGIR** (Information Retrieval) | Possible | Strong eval + counterfactual novelty |
| **AAAI Student Track** | Yes | Neurosymbolic framing + user study |
| **ACM RecSys** | Yes | Frame as a recommendation system with explanations |
| **arXiv + workshop paper** | Definitely | Good enough for NeurIPS / ACL workshop |
| **Springer / Elsevier SCI journal** | Yes | With full ablation + user study |

The realistic target for a B.Tech project that executes fixes 1-5:
**A workshop at EMNLP / AAAI, or a mid-tier SCI journal.**
That is genuinely impressive for undergrad work.

---

## Priority Order — What To Do First

```
Priority 1 (changes the scientific validity):
  ✦ Learn fusion weights — don't hardcode them
  ✦ LLM-based skill extraction — replaces spaCy NER
  ✦ Build ontology from real sources (SO tags + O*NET)

Priority 2 (creates the novel contribution):
  ✦ Counterfactual explanations — your killer feature
  ✦ Run ablation study (remove one component, measure F1 drop)

Priority 3 (makes it feel like a real product + helps user study):
  ✦ LLM-generated natural language summary
  ✦ 20-person user study on explanation quality

Priority 4 (polish):
  ✦ Swap all-MiniLM-L6-v2 for BGE-small or E5-small
  ✦ Full confusion matrix + significance tests in evaluation
```

---

## One-Line Summary

The ontology graph + counterfactual skill-gap explanation is your real USP.
Everything else (SBERT, XGBoost, Flask) is infrastructure.
Double down on the graph and the counterfactuals — that is what no one else is doing.

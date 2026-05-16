# ExplainHire — Audit Fixes

## P0 — Paper-breaking (fix before anything else)

| # | Problem | File | Fix |
|---|---------|------|-----|
| 1 | XGBoost trained on 156 synthetic rows — circular, CV F1 meaningless | `data/annotation.csv` | Add real data OR label 100 pairs manually OR explicitly call it a feasibility study in paper |
| 2 | No baseline comparison — cannot claim superiority over anything | `evaluation/baselines.py` | Implement TF-IDF, SBERT-only, graph-only baselines. Report F1 table |
| 3 | No ablation study — cannot prove all 3 matchers add value | `evaluation/ablation.py` | Run 4 configs: graph-only, SBERT-only, graph+SBERT, full. Report F1 |
| 4 | "Neurosymbolic" claim not justified — it's a late-fusion ensemble | Paper + README | Rename to "hybrid symbolic-neural pipeline with late fusion" everywhere |

---

## P1 — Jury will grill you on these

| # | Problem | File | Fix |
|---|---------|------|-----|
| 5 | Model says 100% match for 1yr candidate on 5yr JD | `data/generate_synthetic.py` | Add 40 rows: same-domain but large YOE gap → label 0. Retrain |
| 6 | XGBoost outputs raw % — 100% confidence is dangerous | `pipeline/l5_classify/predictor.py` + UI | Apply `CalibratedClassifierCV`. Show Strong/Moderate/Weak not % |
| 7 | "I have no experience with Docker" → shown as Docker evidence | `pipeline/l6_explain/evidence_mapper.py` | Check for negation markers within 5 tokens of skill mention. Skip as evidence |
| 8 | Zero negation handling in skill extractor | `pipeline/l2_parse/skill_extractor.py` | Split on negation words (no, not, without). Exclude post-negation tokens |
| 9 | "Counterfactual" is just a gap list — not minimum-change | `pipeline/l6_explain/suggestion_engine.py` | Rename to "skill gap analysis" in paper. OR compute which single skill causes largest XGBoost probability jump |
| 10 | Bias audit listed as USP — does not exist | `evaluation/bias_audit.py` (new) | Run 10 identical resumes with different names. Record score variance |

---

## P2 — Will hurt demo quality

| # | Problem | File | Fix |
|---|---------|------|-----|
| 11 | 266 ontology nodes — real JDs have skills outside it, capping graph_score | `ontology/build_ontology.py` | Add: agile, scrum, jira, system_design, oop, data_structures, algorithms, figma, swagger, spring_boot, dotnet, gcp, azure_devops, eks, gke |
| 12 | SHAP feature names meaningless to recruiters | `app/routes/match.py` + `result.html` | Replace SHAP section with evidence mapper as primary explanation. Move SHAP to debug/details only |
| 13 | Suggestions don't show skill proximity | `pipeline/l6_explain/suggestion_engine.py` | Use match_type from graph to add: "You know X (sibling) — Y is a short learning curve" |
| 14 | Every underscore node needs alias for space form | `ontology/alias_table.json` | Write test: every node with `_` must have space-form alias. Fix missing ones |

---

## P3 — Polish

| # | Problem | Fix |
|---|---------|-----|
| 15 | MiniLM vs mpnet-base-v2 not compared | Run both on same 20 pairs. Report speed vs accuracy tradeoff in paper |
| 16 | Resume parser fails on ~40% of real resumes (2-col, scanned) | Acknowledge in paper as known limitation. Add pdfplumber as future work |
| 17 | "Counterfactual" word used in UI | Rename to "What would change this?" in result.html |

---

## Fix order

```
Phase 1 (2 days) — Fix the AI
  5 → 8 → 11 → 6 → 9

Phase 2 (1 day) — Evaluate
  2 → 3 → 10

Phase 3 (half day) — Polish
  12 → 13 → 7 → 14 → 17

Phase 4 — Paper
  Write results section using Phase 2 numbers
  Rename neurosymbolic → hybrid (fix 4) in paper
```

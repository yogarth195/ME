# ExplainHire — Status & Roadmap

## What's Done

| Component | Status | Notes |
|---|---|---|
| L1 Input validation | Done | PDF/DOCX, size check |
| L2 Resume + JD parser | Done | Skills, YOE, education extraction |
| L3 Skill ontology | Done | 266 nodes, manual build |
| L4 Graph matcher | Done | 6-level directional matching |
| L4 SBERT matcher | Done | all-MiniLM-L6-v2, off-the-shelf |
| L4 Structural matcher | Done | YOE gap, education gap, sections |
| L5 XGBoost classifier | Done | Trained on 967 rows |
| L6 Evidence mapper | Done | Sentence-level proof per skill |
| L6 Skill gap analyzer | Done | Which skills to add to cross threshold |
| L7 Flask UI | Done | Dark theme, drag-drop, result page |
| Ablation table | Done | F1: TF-IDF 0.09 → Full pipeline 0.88 |
| Real data pipeline | Done | 800 paired rows from resume_data.csv |

---

## What's NOT Done Yet

| Task | Priority | Effort |
|---|---|---|
| Add friends' PDFs to training data | High | 1 hour |
| O*NET ontology update | High | 2 hours |
| Human-annotated test set (50 pairs) | High | 1 day |
| Confidence calibration (CalibratedClassifierCV) | Medium | 30 min |
| Negation handling in evidence mapper | Medium | 1 hour |
| Bias audit script | Medium | 1 hour |
| Rename "counterfactual" → "skill gap analysis" in UI | Low | 10 min |
| Paper writeup | High | ongoing |

---

## What is Production Grade

- PDF extraction and validation
- Flask UI end to end
- Pipeline runner (L1 → L7)
- SHAP explanations
- Evidence sentences

## What is NOT Production Grade

- **Ontology** — 266 manual nodes, missing agile/scrum/jira/kafka/redis etc.
- **Training data** — 967 rows, labels from third-party score not human judgment
- **SBERT** — off-the-shelf, not fine-tuned on recruitment data
- **YOE extraction** — regex-based, fails on non-standard resume formats
- **No auth, no database** — single user, no history

---

## How to Defend Weaknesses

| Weakness | Defence |
|---|---|
| Synthetic + semi-real training data | "Feasibility study — we demonstrate the architecture works. Human annotation is future work." |
| SBERT not fine-tuned | "Off-the-shelf SBERT already gives 0.64 F1. Fine-tuning on domain data is a clear extension." |
| Ontology hand-built | "O*NET integration is planned. Current ontology covers core tech skills sufficient for evaluation." |
| No human labels | "We use a held-out test split from a third-party paired dataset. Human annotation is future work." |
| XGBoost not deep learning | "XGBoost is interpretable and works well on tabular features. SHAP support is a key design choice." |

---

## Where Fine-Tuning is Required

| What | Why | How |
|---|---|---|
| SBERT | General model, not recruitment-specific | Fine-tune on resume-JD pairs with contrastive loss — needs ~5000 labeled pairs |
| Ontology | Missing real-world skills | O*NET integration (next step) |
| XGBoost thresholds | Trained on unverified labels | Retrain after human annotation |

---

## Immediate Next Steps (in order)

### Step 1 — Friends' PDFs (1 hour)
1. Rename PDFs with domain prefix: `backend_name.pdf`, `ml_name.pdf`
2. Place in `data/raw/friends/`
3. Create 5-6 JD files in `data/raw/jds/` from LinkedIn/Naukri
4. Run: `python data/load_friends.py`
5. Run: `python data/build_dataset.py`
6. Run: `python pipeline/l5_classify/trainer.py`

### Step 2 — O*NET Ontology Update (2 hours)
1. Go to `onetcenter.org/database.html`
2. Download "Tools and Technology" table as Excel
3. Place at `data/raw/onet_tools.xlsx`
4. I write `ontology/update_from_onet.py`
5. Run it — adds 50-100 real skill nodes to the graph
6. Rebuild ontology: `python ontology/build_ontology.py`

### Step 3 — Human Test Set (1 day)
1. Pick 50 resume-JD pairs from your data
2. Ask 3 friends to label them match/no-match (15-20 each, 30 min)
3. Test model on those 50 — report that F1 separately in paper

### Step 4 — Paper
- You have all numbers now
- Read 3-4 related papers first (use the prompt I gave you)
- Write: Abstract, Introduction, Architecture, Evaluation, Limitations, Conclusion

---

## Key Numbers for Paper

| Metric | Value |
|---|---|
| Training rows | 967 (167 synthetic + 800 real) |
| CV F1 | 0.767 |
| Full-data F1 | 0.883 |
| Best baseline F1 (SBERT-only) | 0.645 |
| Improvement over best baseline | +23.91% |
| Ontology nodes | 266 skills + 270 aliases |
| Pipeline layers | 7 |

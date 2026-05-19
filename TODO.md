# ExplainHire — TODO Checklist

## Must Do (Paper Blockers)

- [ ] Rename friends' PDFs with domain prefix (backend_name.pdf, ml_name.pdf etc.)
- [ ] Put PDFs in `data/raw/friends/`
- [ ] Put 5 JD files in `data/raw/jds/`
- [ ] Run `python data/load_friends.py`
- [ ] Run `python data/build_dataset.py`
- [ ] Run `python pipeline/l5_classify/trainer.py`
- [ ] Pick 50 resume-JD pairs for human annotation
- [ ] Get 3 friends to label them match/no-match
- [ ] Test model on human-labeled set, note F1
- [ ] Write the paper

## Should Do (Improves Paper)

- [ ] Fix theme toggle button
- [ ] Rename "counterfactual" → "skill gap analysis" in UI
- [ ] Confidence calibration (Strong / Moderate / Weak)

## Nice to Have (Post Submission)

- [ ] Copy-paste 10-15 more JDs from LinkedIn/Naukri
- [ ] Bias audit script
- [ ] React UI

## Done

- [x] 7-layer pipeline (L1-L7)
- [x] Skill ontology (434 nodes, O*NET integrated)
- [x] XGBoost classifier (CV F1 = 0.803)
- [x] SHAP explanations
- [x] Evidence mapper
- [x] Skill gap analyzer
- [x] Flask UI (dark/light theme)
- [x] Ablation table (full pipeline F1 = 0.90, +21% over baseline)
- [x] Real training data (967 rows)
- [x] Pipeline visualization page

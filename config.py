"""
Central configuration for ExplainHire.
All paths, model names, weights, and thresholds live here.
"""

import os
from pathlib import Path

# ── Root paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
ONTOLOGY_DIR = BASE_DIR / "ontology"
UPLOAD_DIR = BASE_DIR / "app" / "static" / "uploads"

# ── Flask / auth ──────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-before-production")
DATABASE_URI = f"sqlite:///{INSTANCE_DIR / 'explainHire.db'}"
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB upload limit
ALLOWED_EXTENSIONS = {"pdf", "docx"}

# ── Data files ────────────────────────────────────────────────────────────────
RAW_RESUMES_DIR = DATA_DIR / "raw" / "resumes"
RAW_JDS_DIR = DATA_DIR / "raw" / "job_descriptions"
PROCESSED_DIR = DATA_DIR / "processed"
ANNOTATION_FILE = DATA_DIR / "annotations" / "annotation.csv"

# ── Ontology ──────────────────────────────────────────────────────────────────
ONTOLOGY_GRAPH_FILE = ONTOLOGY_DIR / "skill_ontology.gpickle"
ALIAS_TABLE_FILE = ONTOLOGY_DIR / "alias_table.json"
SKILL_DOMAINS = ["web_dev", "ml_ds", "devops", "mobile", "cybersecurity"]

# ── NLP models ────────────────────────────────────────────────────────────────
SPACY_MODEL = "en_core_web_sm"
SBERT_MODEL = "all-MiniLM-L6-v2"

# ── Saved ML model ────────────────────────────────────────────────────────────
XGBOOST_MODEL_FILE = MODELS_DIR / "xgboost_classifier.json"
SHAP_EXPLAINER_FILE = MODELS_DIR / "shap_explainer.pkl"

# ── Scoring weights (must sum to 1.0) ─────────────────────────────────────────
WEIGHT_GRAPH = 0.50
WEIGHT_SBERT = 0.35
WEIGHT_STRUCTURAL = 0.15

assert abs(WEIGHT_GRAPH + WEIGHT_SBERT + WEIGHT_STRUCTURAL - 1.0) < 1e-9, \
    "Scoring weights must sum to 1.0"

# ── Graph matching edge weights ────────────────────────────────────────────────
GRAPH_LEVEL1_WEIGHT = 1.0   # exact canonical match
GRAPH_LEVEL2_WEIGHT = 0.9   # alias match via IS_ALIAS_OF
GRAPH_LEVEL3_WEIGHT = 0.6   # parent / child / sibling via CHILD_OF

# ── Classification thresholds ─────────────────────────────────────────────────
# Label 0 = Not Recommended, 1 = Maybe, 2 = Recommended
LABEL_NAMES = {0: "Not Recommended", 1: "Maybe", 2: "Recommended"}
SCORE_THRESHOLD_MAYBE = 0.40          # FinalScore >= 0.40 → at least Maybe
SCORE_THRESHOLD_RECOMMENDED = 0.70   # FinalScore >= 0.70 → Recommended

# ── Structural scoring ────────────────────────────────────────────────────────
EXPERIENCE_SECTION_KEYWORDS = ["experience", "work history", "employment"]
EDUCATION_SECTION_KEYWORDS = ["education", "qualification", "degree"]
SKILLS_SECTION_KEYWORDS = ["skills", "technical skills", "competencies"]

# ── Evaluation ────────────────────────────────────────────────────────────────
RANDOM_SEED = 42
TEST_SPLIT = 0.20
VAL_SPLIT = 0.10
CV_FOLDS = 5

# ── Learning suggestions ──────────────────────────────────────────────────────
LEARNING_RESOURCE_MAP_FILE = ONTOLOGY_DIR / "learning_resources.json"
MAX_SUGGESTIONS = 5

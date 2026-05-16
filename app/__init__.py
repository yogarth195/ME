from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(app.instance_path, 'explainHire.db')}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        from app import models  # registers user_loader
        db.create_all()

    from app.routes.auth import auth_bp
    from app.routes.match import match_bp
    from app.routes.history import history_bp
    from app.routes.ontology_view import ontology_bp
    from app.routes.pipeline_view import pipeline_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(match_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(ontology_bp)
    app.register_blueprint(pipeline_bp)

    # ── Template filters ──────────────────────────────────────────────────────
    @app.template_filter("pct")
    def pct_filter(value):
        try:
            return f"{float(value):.0%}"
        except (TypeError, ValueError):
            return "–"

    @app.template_filter("abs")
    def abs_filter(value):
        try:
            return abs(float(value))
        except (TypeError, ValueError):
            return 0

    @app.template_filter("friendly_name")
    def friendly_name_filter(value):
        mapping = {
            "graph_score":      "Skill match",
            "sbert_score":      "Semantic fit",
            "structural_score": "Structural fit",
            "yoe_score":        "Experience gap",
            "edu_score":        "Education fit",
            "coverage":         "JD coverage",
            "exact_matches":    "Exact matches",
            "partial_matches":  "Partial matches",
            "no_matches":       "Missing skills",
            "resume_yoe":       "Years exp.",
            "required_yoe":     "Required exp.",
        }
        return mapping.get(value, value.replace("_", " ").title())

    @app.template_filter("friendly_match")
    def friendly_match_filter(value):
        mapping = {
            "exact":        "Exact",
            "alias":        "Alias",
            "child_parent": "Specific→General",
            "parent_child": "General→Specific",
            "sibling":      "Related",
            "ancestor_2hop":"Distant",
            "no_match":     "Missing",
        }
        return mapping.get(value, value)

    @app.template_filter("interpretation")
    def interpretation_filter(value):
        try:
            v = float(value)
            if v >= 0.75: return "Strong alignment"
            if v >= 0.55: return "Moderate alignment"
            if v >= 0.35: return "Weak alignment"
            return "Poor alignment"
        except (TypeError, ValueError):
            return "–"

    return app

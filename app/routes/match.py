"""Match routes — upload + analyze."""

import os
import uuid
from pathlib import Path

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

match_bp = Blueprint("match", __name__)

UPLOAD_FOLDER = Path(__file__).parent.parent.parent / "uploads"
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}


def _allowed(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


@match_bp.route("/")
def index():
    return render_template("index.html")


@match_bp.route("/analyze", methods=["POST"])
def analyze():
    resume_file = request.files.get("resume")
    jd_text     = request.form.get("jd_text", "").strip()

    if not resume_file or not resume_file.filename:
        flash("Please upload a resume file.", "error")
        return redirect(url_for("match.index"))

    if not _allowed(resume_file.filename):
        flash("Only PDF and DOCX files are supported.", "error")
        return redirect(url_for("match.index"))

    if not jd_text:
        flash("Please paste a job description.", "error")
        return redirect(url_for("match.index"))

    if len(jd_text) < 50:
        flash("Job description is too short — paste the full JD.", "error")
        return redirect(url_for("match.index"))

    # Save uploaded file with a unique name
    UPLOAD_FOLDER.mkdir(exist_ok=True)
    ext = Path(resume_file.filename).suffix.lower()
    saved_name = f"{uuid.uuid4().hex}{ext}"
    save_path  = UPLOAD_FOLDER / saved_name
    resume_file.save(str(save_path))

    try:
        from pipeline.l7_present.pipeline_runner import run_pipeline
        result = run_pipeline(resume_path=str(save_path), jd_text=jd_text)
    except Exception as e:
        flash(f"Analysis failed: {str(e)}", "error")
        return redirect(url_for("match.index"))
    finally:
        # Clean up uploaded file after processing
        if save_path.exists():
            save_path.unlink()

    if result["status"] == "error":
        flash(result["error"], "error")
        return redirect(url_for("match.index"))

    return render_template("result.html", r=result)

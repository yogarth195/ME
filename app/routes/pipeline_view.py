from flask import Blueprint, render_template

pipeline_bp = Blueprint("pipeline", __name__)

@pipeline_bp.route("/how-it-works")
def how_it_works():
    return render_template("pipeline.html")

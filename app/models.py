"""SQLAlchemy models — placeholder, to be fleshed out in L7."""
from app import db, login_manager
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    history = db.relationship("MatchHistory", backref="user", lazy=True)


class MatchHistory(db.Model):
    __tablename__ = "match_history"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    resume_filename = db.Column(db.String(256))
    jd_snippet = db.Column(db.Text)
    final_score = db.Column(db.Float)
    label = db.Column(db.Integer)
    result_json = db.Column(db.Text)   # full JSON blob of L6 output
    created_at = db.Column(db.DateTime, server_default=db.func.now())

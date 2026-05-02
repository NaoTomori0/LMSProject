from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import Submission
from app import cache

bp = Blueprint("cabinet", __name__, url_prefix="/cabinet")


@bp.route("/")
@login_required
@cache.cached(timeout=30, key_prefix=lambda: f"cabinet_{current_user.id}")
def index():
    submissions = (
        Submission.query.filter_by(user_id=current_user.id)
        .order_by(Submission.created_at.desc())
        .all()
    )
    return render_template("cabinet/index.html", submissions=submissions)

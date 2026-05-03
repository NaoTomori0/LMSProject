from flask import Blueprint, render_template, abort
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

    # Статистика
    total_submissions = len(submissions)
    passed_submissions = [s for s in submissions if s.status == "passed"]
    total_passed = len(passed_submissions)
    success_percent = (
        (total_passed / total_submissions * 100) if total_submissions > 0 else 0
    )
    total_score = sum(s.score for s in passed_submissions if s.score is not None)
    avg_score = (total_score / total_passed) if total_passed > 0 else 0

    stats = {
        "total_submissions": total_submissions,
        "total_passed": total_passed,
        "success_percent": round(success_percent, 1),
        "total_score": total_score,
        "avg_score": round(avg_score, 1),
    }

    return render_template("cabinet/index.html", submissions=submissions, stats=stats)


@bp.route("/submission/<int:id>")
@login_required
def view_submission(id):
    submission = Submission.query.get_or_404(id)
    # Показываем только свои решения
    if submission.user_id != current_user.id:
        abort(403)
    return render_template("cabinet/submission_detail.html", submission=submission)

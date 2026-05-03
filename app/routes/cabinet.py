from flask import Blueprint, render_template, abort, flash, request, redirect, url_for
from flask_login import login_required, current_user
from app.models import Submission, User
from app import cache
from .main import db

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

    # Уникальные задания, по которым есть отправки
    unique_assignments = set()
    best_by_assignment = {}  # assignment_id -> max_score
    passed_set = set()  # assignment_id, где есть хотя бы один passed
    total_score = 0
    total_attempts = 0

    for s in submissions:
        total_attempts += 1
        uid = s.assignment_id
        unique_assignments.add(uid)

        score = s.score if s.score is not None else 0
        # Обновляем максимум для задания
        if uid not in best_by_assignment or score > best_by_assignment[uid]:
            best_by_assignment[uid] = score

        if s.status == "passed":
            passed_set.add(uid)

    # Суммируем лучшие баллы по каждому заданию
    total_score = sum(best_by_assignment.values())

    # Количество уникальных заданий, по которым пытались
    unique_count = len(unique_assignments)
    # Процент успеха: отношение пройденных заданий к уникальным
    success_percent = (len(passed_set) / unique_count * 100) if unique_count > 0 else 0

    stats = {
        "total_attempts": total_attempts,
        "unique_assignments": unique_count,
        "passed_assignments": len(passed_set),
        "success_percent": round(success_percent, 1),
        "total_score": total_score,
        "best_by_assignment": best_by_assignment,  # можно не передавать, но пригодится
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


@bp.route("/edit-profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        new_username = request.form.get("username", "").strip()
        if not new_username:
            flash("Имя пользователя не может быть пустым", "danger")
            return render_template("cabinet/edit_profile.html")
        # Проверяем, что ник не занят другим пользователем
        existing = User.query.filter(
            User.username == new_username, User.id != current_user.id
        ).first()
        if existing:
            flash("Это имя уже занято", "danger")
            return render_template("cabinet/edit_profile.html")
        current_user.username = new_username
        db.session.commit()
        cache.clear()
        flash("Никнейм обновлён", "success")
        return redirect(url_for("cabinet.index"))
    return render_template("cabinet/edit_profile.html")

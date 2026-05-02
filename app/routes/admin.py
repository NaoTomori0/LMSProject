from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models import Assignment, Submission
from flask import abort, send_from_directory, current_app, copy_current_request_context
import os
import threading
from app import create_app
from app.models import Assignment, Submission, TestScript
from app.utils import run_check_docker

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


@bp.route("/scripts")
@login_required
@admin_required
def list_scripts():
    scripts = TestScript.query.order_by(TestScript.created_at.desc()).all()
    return render_template("admin/scripts.html", scripts=scripts)


@bp.route("/scripts/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_script():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        language = request.form.get("language", "python")
        script_body = request.form.get("script_body", "").strip()

        if not name or not script_body:
            flash("Название и код скрипта обязательны", "danger")
            return render_template("admin/script_form.html", script=None)

        script = TestScript(
            name=name,
            description=description,
            language=language,
            script_body=script_body,
        )
        db.session.add(script)
        db.session.commit()
        flash("Скрипт создан", "success")
        return redirect(url_for("admin.list_scripts"))

    return render_template("admin/script_form.html", script=None)


@bp.route("/scripts/<int:id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_script(id):
    script = TestScript.query.get_or_404(id)
    if request.method == "POST":
        script.name = request.form.get("name", "").strip()
        script.description = request.form.get("description", "").strip()
        script.language = request.form.get("language", "python")
        script.script_body = request.form.get("script_body", "").strip()
        db.session.commit()
        flash("Скрипт обновлён", "success")
        return redirect(url_for("admin.list_scripts"))
    return render_template("admin/script_form.html", script=script)


@bp.route("/scripts/<int:id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_script(id):
    script = TestScript.query.get_or_404(id)
    db.session.delete(script)
    db.session.commit()
    flash("Скрипт удалён", "info")
    return redirect(url_for("admin.list_scripts"))


@bp.route("/")
@login_required
@admin_required
def index():
    assignments = Assignment.query.order_by(Assignment.created_at.desc()).all()
    submissions = (
        Submission.query.order_by(Submission.created_at.desc()).limit(20).all()
    )
    return render_template(
        "admin/index.html", assignments=assignments, submissions=submissions
    )


@bp.route("/assignment/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_assignment():
    scripts = TestScript.query.all()
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        check_type = request.form.get("check_type", "manual")
        is_public = request.form.get("is_public") == "on"

        assignment = Assignment(
            title=title,
            description=description,
            check_type=check_type,
            is_public=is_public,
        )
        db.session.add(assignment)
        db.session.flush()  # чтобы получить assignment.id

        # Обрабатываем выбранные скрипты для каждого языка
        languages = ["python", "cpp", "javascript", "java"]
        for lang in languages:
            script_id = request.form.get(f"script_{lang}")
            if script_id:
                script = TestScript.query.get(int(script_id))
                if script:
                    link = AssignmentScript(
                        assignment_id=assignment.id,
                        test_script_id=script.id,
                        language=lang,
                    )
                    db.session.add(link)
        db.session.commit()
        flash("Задание создано", "success")
        return redirect(url_for("admin.index"))

    return render_template("admin/new_assignment.html", scripts=scripts)


@bp.route("/assignment/<int:id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_assignment(id):
    a = Assignment.query.get_or_404(id)
    db.session.delete(a)
    db.session.commit()
    flash("Задание удалено", "info")
    return redirect(url_for("admin.index"))


@bp.route("/submission/<int:id>", methods=["GET", "POST"])
@login_required
@admin_required
def view_submission(id):
    submission = Submission.query.get_or_404(id)
    if request.method == "POST":
        status = request.form.get("status")
        score = request.form.get("score", type=float)
        feedback = request.form.get("feedback", "").strip()

        if status not in ("pending", "passed", "failed", "checked"):
            flash("Неверный статус", "danger")
            return redirect(url_for("admin.view_submission", id=id))

        submission.status = status
        submission.score = score
        submission.feedback = feedback
        db.session.commit()
        return redirect(url_for("admin.index"))

    return render_template("admin/submission_detail.html", submission=submission)


from flask import send_from_directory, current_app


@bp.route("/submission/<int:submission_id>/uploads/<path:filename>")
@login_required
@admin_required
def download_file(submission_id, filename):
    # Можно добавить проверку, что submission существует
    submission = Submission.query.get_or_404(submission_id)
    if filename not in (submission.answer_file or "").split(","):
        abort(404)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"], filename, as_attachment=True
    )


@bp.route("/assignment/<int:id>/run-auto-check")
@login_required
@admin_required
def run_auto_check(id):
    assignment = Assignment.query.get_or_404(id)
    if assignment.check_type != "auto" or not assignment.test_script_id:
        flash("Для этого задания не настроен автотест", "warning")
        return redirect(url_for("admin.index"))

    script = TestScript.query.get(assignment.test_script_id)
    if not script:
        flash("Скрипт не найден", "danger")
        return redirect(url_for("admin.index"))

    # Получаем все непроверенные решения этого задания
    submissions = Submission.query.filter_by(
        assignment_id=assignment.id, status="pending"
    ).all()
    if not submissions:
        flash("Нет решений для проверки", "info")
        return redirect(url_for("admin.index"))

    from app.utils import run_check

    count = 0
    for sub in submissions:
        result = run_check(script.script_body, sub.answer_text or "")
        sub.status = "passed" if result.get("passed") else "failed"
        sub.score = result.get("score", 0)
        sub.feedback = result.get("feedback", "")
        count += 1

    db.session.commit()
    flash(f"Проверено {count} решений", "success")
    return redirect(url_for("admin.index"))


def recheck_all_background(assignment_id, script_id, folder):
    """Фоновая задача для перепроверки всех решений задания."""
    app = create_app()  # создаём новое приложение для изоляции контекста
    with app.app_context():
        from app.models import Assignment, TestScript, Submission
        from app.utils import run_check_docker

        assignment = Assignment.query.get(assignment_id)
        if not assignment:
            return
        script = TestScript.query.get(script_id)
        if not script:
            return
        submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
        for sub in submissions:
            if sub.answer_file:
                files = sub.answer_file.split(",")
                input_path = os.path.join(folder, files[0])
                is_file = True
            else:
                input_path = sub.answer_text or ""
                is_file = False
            try:
                result = run_check_docker(script.script_body, input_path, is_file)
                sub.status = "passed" if result.get("passed") else "failed"
                sub.score = result.get("score", 0)
                sub.feedback = result.get("feedback", "")
            except Exception as e:
                sub.status = "failed"
                sub.score = 0
                sub.feedback = f"Ошибка: {str(e)}"
        db.session.commit()


@bp.route("/assignment/<int:id>/recheck-all")
@login_required
@admin_required
def recheck_all(id):
    assignment = Assignment.query.get_or_404(id)
    if assignment.check_type != "auto" or not assignment.test_script_id:
        flash("Для этого задания не настроен автотест", "warning")
        return redirect(url_for("admin.index"))

    # Запускаем фоновый поток
    thread = threading.Thread(
        target=recheck_all_background,
        args=(
            assignment.id,
            assignment.test_script_id,
            current_app.config["UPLOAD_FOLDER"],
        ),
    )
    thread.start()

    flash(
        "Перепроверка всех решений запущена в фоне. Обновите страницу через некоторое время.",
        "info",
    )
    return redirect(url_for("admin.index"))

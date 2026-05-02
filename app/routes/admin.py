from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    send_from_directory,
    current_app,
)
from flask_login import login_required, current_user
from functools import wraps
from app import db, create_app
from app.models import Assignment, Submission, TestScript, AssignmentScript
import os
import threading
from app.utils import run_check_docker

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


# -------------------------------------------------------------
# Управление скриптами
# -------------------------------------------------------------
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


# -------------------------------------------------------------
# Главная страница админки
# -------------------------------------------------------------
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


# -------------------------------------------------------------
# Создание / удаление задания
# -------------------------------------------------------------
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
        script_id = (
            request.form.get("script_id", type=int) if check_type == "auto" else None
        )

        assignment = Assignment(
            title=title,
            description=description,
            check_type=check_type,
            is_public=is_public,
        )
        db.session.add(assignment)
        db.session.flush()

        # Если выбрана автоматическая проверка и указан скрипт – привязываем его ко всем языкам
        if check_type == "auto" and script_id:
            script = TestScript.query.get(script_id)
            if script:
                languages = ["python", "cpp", "javascript", "java"]
                for lang in languages:
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


# -------------------------------------------------------------
# Ручная проверка решения
# -------------------------------------------------------------
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


# -------------------------------------------------------------
# Скачивание прикреплённого файла
# -------------------------------------------------------------
@bp.route("/submission/<int:submission_id>/uploads/<path:filename>")
@login_required
@admin_required
def download_file(submission_id, filename):
    submission = Submission.query.get_or_404(submission_id)
    if filename not in (submission.answer_file or "").split(","):
        abort(404)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"], filename, as_attachment=True
    )


# -------------------------------------------------------------
# Автоматическая проверка (один раз, только непроверенные)
# -------------------------------------------------------------
@bp.route("/assignment/<int:id>/run-auto-check")
@login_required
@admin_required
def run_auto_check(id):
    assignment = Assignment.query.get_or_404(id)
    if assignment.check_type != "auto":
        flash("Для этого задания не настроен автотест", "warning")
        return redirect(url_for("admin.index"))

    pending_subs = Submission.query.filter_by(
        assignment_id=assignment.id, status="pending"
    ).all()
    if not pending_subs:
        flash("Нет решений для проверки", "info")
        return redirect(url_for("admin.index"))

    count = 0
    for sub in pending_subs:
        if not sub.language:
            continue  # нет языка – пропускаем
        assigned_script = AssignmentScript.query.filter_by(
            assignment_id=assignment.id, language=sub.language
        ).first()
        if not assigned_script:
            continue
        script = assigned_script.test_script
        if not script:
            continue

        if sub.answer_file:
            files = sub.answer_file.split(",")
            input_path = os.path.join(current_app.config["UPLOAD_FOLDER"], files[0])
            is_file = True
        else:
            input_path = sub.answer_text or ""
            is_file = False

        try:
            result = run_check_docker(
                script.script_body, input_path, is_file, language=sub.language
            )
            sub.status = "passed" if result.get("passed") else "failed"
            sub.score = result.get("score", 0)
            sub.feedback = result.get("feedback", "")
            count += 1
        except Exception as e:
            sub.status = "failed"
            sub.score = 0
            sub.feedback = f"Ошибка: {str(e)}"

    db.session.commit()
    flash(f"Проверено {count} решений", "success")
    return redirect(url_for("admin.index"))


# -------------------------------------------------------------
# Фоновая перепроверка всех решений (с учётом языка)
# -------------------------------------------------------------
def recheck_all_background(assignment_id, upload_folder):
    app = create_app()
    with app.app_context():
        assignment = Assignment.query.get(assignment_id)
        if not assignment or assignment.check_type != "auto":
            return

        submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
        for sub in submissions:
            if not sub.language:
                continue
            assigned_script = AssignmentScript.query.filter_by(
                assignment_id=assignment_id, language=sub.language
            ).first()
            if not assigned_script:
                continue
            script = assigned_script.test_script
            if not script:
                continue

            if sub.answer_file:
                files = sub.answer_file.split(",")
                input_path = os.path.join(upload_folder, files[0])
                is_file = True
            else:
                input_path = sub.answer_text or ""
                is_file = False

            try:
                result = run_check_docker(
                    script.script_body, input_path, is_file, language=sub.language
                )
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
    if assignment.check_type != "auto":
        flash("Для этого задания не настроен автотест", "warning")
        return redirect(url_for("admin.index"))

    thread = threading.Thread(
        target=recheck_all_background,
        args=(assignment.id, current_app.config["UPLOAD_FOLDER"]),
    )
    thread.start()
    flash(
        "Перепроверка всех решений запущена в фоне. Обновите страницу через некоторое время.",
        "info",
    )
    return redirect(url_for("admin.index"))

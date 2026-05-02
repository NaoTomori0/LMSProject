from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    abort,
)
from datetime import datetime
from app import db, cache
from app.models import Assignment, Submission, TestScript, AssignmentScript
from flask_login import current_user
import os
from werkzeug.utils import secure_filename
import uuid

bp = Blueprint("main", __name__)

ALLOWED_EXTENSIONS = {
    "py",
    "js",
    "cpp",
    "c",
    "java",
    "txt",
    "pdf",
    "zip",
    "rar",
    "7z",
    "docx",
}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# --------------------------------------------------------------
# Главная страница со списком заданий (с учётом групп)
# --------------------------------------------------------------
@bp.route("/")
@cache.cached(timeout=60, unless=lambda: current_user.is_authenticated)
def index():
    if current_user.is_authenticated:
        # Публичные задания + задания из групп пользователя
        user_group_ids = [g.id for g in current_user.groups]
        assignments = (
            Assignment.query.filter(
                (Assignment.is_public == True)
                | (Assignment.group_id.in_(user_group_ids))
            )
            .order_by(Assignment.created_at.desc())
            .all()
        )
    else:
        assignments = (
            Assignment.query.filter_by(is_public=True)
            .order_by(Assignment.created_at.desc())
            .all()
        )
    return render_template(
        "index.html", assignments=assignments, year=datetime.now().year
    )


# --------------------------------------------------------------
# Отправка решения (с проверкой доступа и отложенной проверкой в Celery)
# --------------------------------------------------------------
@bp.route("/assignment/<int:assignment_id>/submit", methods=["GET", "POST"])
def submit_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)

    # Проверка доступа к заданию
    if not assignment.is_public:
        if not current_user.is_authenticated:
            abort(403)
        if assignment.group_id is not None and assignment.group_id not in [
            g.id for g in current_user.groups
        ]:
            abort(403)

    if request.method == "POST":
        answer_text = request.form.get("answer", "").strip()
        files = request.files.getlist("files")
        language = request.form.get("language", "python")

        if not answer_text and (not files or all(f.filename == "" for f in files)):
            flash("Нужно ввести текст решения или загрузить файл(ы)", "danger")
            return render_template("submit.html", assignment=assignment)

        # Создаём заявку
        submission = Submission(
            assignment_id=assignment.id,
            answer_text=answer_text,
            language=language,
        )
        if current_user.is_authenticated:
            submission.user_id = current_user.id
        else:
            guest_name = request.form.get("guest_name", "").strip()
            guest_email = request.form.get("guest_email", "").strip()
            if not guest_name or not guest_email:
                flash("Для гостей обязательно укажите имя и email", "danger")
                return render_template("submit.html", assignment=assignment)
            submission.guest_name = guest_name
            submission.guest_email = guest_email

        # Сохраняем файлы
        uploaded_filenames = []
        for f in files:
            if f.filename == "":
                continue
            if not allowed_file(f.filename):
                flash(f"Недопустимый тип файла: {f.filename}", "danger")
                return render_template("submit.html", assignment=assignment)
            filename = secure_filename(f.filename)
            unique_name = f"{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
            f.save(filepath)
            uploaded_filenames.append(unique_name)

        if uploaded_filenames:
            submission.answer_file = ",".join(uploaded_filenames)

        db.session.add(submission)
        db.session.commit()
        cache.clear()

        # Автоматическая проверка через Celery (если задание с автотестом)
        if assignment.check_type == "auto":
            try:
                from app.tasks import check_submission_task

                task = check_submission_task.delay(
                    submission.id, current_app.config["UPLOAD_FOLDER"]
                )
                flash(
                    "Ваше решение принято и поставлено в очередь на проверку. "
                    "Результат появится в личном кабинете.",
                    "info",
                )
            except Exception as e:
                flash(f"Ошибка при постановке в очередь проверки: {e}", "danger")
        else:
            flash("Решение успешно отправлено на проверку!", "success")

        return redirect(url_for("main.index"))

    return render_template("submit.html", assignment=assignment)

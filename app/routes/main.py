from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
)
from datetime import datetime
from app import db
from app.models import Assignment, Submission, TestScript
from flask_login import current_user
import os
from werkzeug.utils import secure_filename
import uuid

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    assignments = Assignment.query.order_by(Assignment.created_at.desc()).all()
    return render_template(
        "index.html", assignments=assignments, year=datetime.now().year
    )


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


@bp.route("/assignment/<int:assignment_id>/submit", methods=["GET", "POST"])
def submit_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    if request.method == "POST":
        answer_text = request.form.get("answer", "").strip()
        files = request.files.getlist("files")

        # Проверка, что хоть что-то есть
        if not answer_text and (not files or all(f.filename == "" for f in files)):
            flash("Нужно ввести текст решения или загрузить файл(ы)", "danger")
            return render_template("submit.html", assignment=assignment)

        # Создаём заявку
        submission = Submission(assignment_id=assignment.id, answer_text=answer_text)
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

        # === Автоматическая проверка (если задание с автотестом) ===
        if assignment.check_type == "auto" and assignment.test_script_id:
            script = TestScript.query.get(assignment.test_script_id)
            if script:
                from app.utils import run_check_docker

                # Определяем входные данные для скрипта
                if uploaded_filenames:
                    # Берём первый загруженный файл как ответ
                    input_path = os.path.join(
                        current_app.config["UPLOAD_FOLDER"], uploaded_filenames[0]
                    )
                    is_file = True
                else:
                    input_path = submission.answer_text or ""
                    is_file = False

                try:
                    result = run_check_docker(script.script_body, input_path, is_file)
                    submission.status = "passed" if result.get("passed") else "failed"
                    submission.score = result.get("score", 0)
                    submission.feedback = result.get("feedback", "")
                    db.session.commit()
                    flash(
                        f'Автопроверка: {"✅ Пройдено" if submission.status == "passed" else "❌ Не пройдено"}. '
                        f"{submission.feedback}",
                        "success" if submission.status == "passed" else "warning",
                    )
                except Exception as e:
                    flash(f"Ошибка при выполнении проверки: {e}", "danger")
            else:
                flash(
                    "Скрипт автотеста не найден. Решение сохранено, ожидает проверки.",
                    "warning",
                )
        else:
            flash("Решение успешно отправлено на проверку!", "success")

        return redirect(url_for("main.index"))

    return render_template("submit.html", assignment=assignment)

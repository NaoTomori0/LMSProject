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
from app.models import (
    Assignment,
    Submission,
    TestScript,
    AssignmentScript,
    GroupInvite,
    QuizAnswer,
    QuizOption,
    QuizQuestion,
)
from flask_login import current_user, login_required
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


def grade_quiz(submission):
    total = 0
    for answer in submission.quiz_answers:
        question = answer.question
        if question.question_type == "open":
            answer.score = None  # будет проверено вручную
            continue
        correct_ids = [str(o.id) for o in question.options if o.is_correct]
        selected_ids = (answer.selected_options or "").split(",")
        if question.question_type == "single":
            if selected_ids == correct_ids:
                answer.score = question.max_score
                total += question.max_score
            else:
                answer.score = 0
        elif question.question_type == "multiple":
            if set(selected_ids) == set(correct_ids):
                answer.score = question.max_score
                total += question.max_score
            else:
                answer.score = 0
    submission.score = total
    open_count = QuizAnswer.query.filter(
        QuizAnswer.submission_id == submission.id,
        QuizAnswer.question.has(question_type="open"),
    ).count()
    if open_count == 0:
        submission.status = "passed" if total > 0 else "failed"
    else:
        submission.status = "pending"


# --------------------------------------------------------------
# Главная страница
# --------------------------------------------------------------
@bp.route("/")
@cache.cached(timeout=60, unless=lambda: current_user.is_authenticated)
def index():
    if current_user.is_authenticated:
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
# Отправка решения
# --------------------------------------------------------------
@bp.route("/assignment/<int:assignment_id>/submit", methods=["GET", "POST"])
def submit_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)

    # Проверка дедлайна
    if assignment.deadline and datetime.utcnow() > assignment.deadline:
        flash("Срок сдачи задания истёк.", "danger")
        return redirect(url_for("main.index"))

    # Проверка попыток (только для авторизованных)
    if assignment.max_attempts > 0 and current_user.is_authenticated:
        attempt_count = Submission.query.filter_by(
            assignment_id=assignment.id, user_id=current_user.id
        ).count()
        if attempt_count >= assignment.max_attempts:
            flash("Вы исчерпали лимит попыток для этого задания.", "danger")
            return redirect(url_for("main.index"))

    # Проверка доступа (группы)
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

        # Создание заявки
        submission = Submission(
            assignment_id=assignment.id,
            answer_text=answer_text,
            language=language,
        )
        # Присваиваем user_id сразу, независимо от типа задания
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

        db.session.add(submission)
        db.session.flush()  # получаем submission.id

        # Обработка тестовых ответов
        if assignment.check_type == "quiz":
            for question in assignment.quiz_questions.order_by(QuizQuestion.order):
                if question.question_type in ("single", "multiple"):
                    selected = request.form.getlist(f"q_{question.id}")
                    selected_str = ",".join(selected) if selected else ""
                    answer = QuizAnswer(
                        submission_id=submission.id,
                        question_id=question.id,
                        selected_options=selected_str,
                    )
                else:
                    open_answer = request.form.get(f"q_{question.id}", "")
                    answer = QuizAnswer(
                        submission_id=submission.id,
                        question_id=question.id,
                        open_answer=open_answer,
                    )
                db.session.add(answer)

            db.session.flush()
            grade_quiz(submission)  # оценка (учитывает вес вопроса)
            db.session.commit()
            cache.clear()
            flash(
                f"Тест принят. Ваш результат: {submission.score} балл(ов).", "success"
            )
            return redirect(url_for("main.index"))

        # Если не тест, продолжаем заполнение
        # Сохранение файлов
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

        db.session.commit()
        cache.clear()

        # Авто- или ручная проверка
        if assignment.check_type == "auto":
            try:
                from app.tasks import check_submission_task

                check_submission_task.delay(
                    submission.id, current_app.config["UPLOAD_FOLDER"]
                )
                flash("Решение принято и поставлено в очередь на проверку.", "info")
            except Exception as e:
                flash(f"Ошибка при постановке в очередь проверки: {e}", "danger")
        else:
            flash("Решение успешно отправлено на проверку!", "success")

        return redirect(url_for("main.index"))

    return render_template("submit.html", assignment=assignment)


# --------------------------------------------------------------
# Приглашение в группу
# --------------------------------------------------------------
@bp.route("/join/<token>")
@login_required
def join_group(token):
    invite = GroupInvite.query.filter_by(token=token, is_active=True).first()
    if not invite:
        flash("Приглашение недействительно или просрочено.", "danger")
        return redirect(url_for("main.index"))
    if invite.expires_at and invite.expires_at < datetime.utcnow():
        invite.is_active = False
        db.session.commit()
        flash("Срок действия приглашения истёк.", "danger")
        return redirect(url_for("main.index"))
    if invite.max_uses > 0 and invite.uses >= invite.max_uses:
        invite.is_active = False
        db.session.commit()
        flash("Лимит использований приглашения исчерпан.", "danger")
        return redirect(url_for("main.index"))
    group = invite.group
    if current_user in group.members:
        flash("Вы уже состоите в этой группе.", "info")
    else:
        group.members.append(current_user)
        invite.uses += 1
        db.session.commit()
        cache.clear()
        flash(f"Вы вступили в группу «{group.name}».", "success")
    return redirect(url_for("main.index"))

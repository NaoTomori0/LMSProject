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
from app import db, create_app, cache
from app.models import (
    Assignment,
    Submission,
    TestScript,
    AssignmentScript,
    Group,
    User,
    GroupInvite,
    QuizQuestion,
    QuizOption,
    QuizAnswer,
)
from datetime import datetime, timedelta
import os
from app.tasks import recheck_all_task
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
        cache.clear()
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
        cache.clear()
        # Запуск перепроверки зависимых заданий
        affected = AssignmentScript.query.filter_by(test_script_id=script.id).all()
        assignment_ids = list(set([a.assignment_id for a in affected]))
        for assignment_id in assignment_ids:
            recheck_all_task.delay(assignment_id, current_app.config["UPLOAD_FOLDER"])
        flash(
            f"Скрипт обновлён. Запущена перепроверка для {len(assignment_ids)} заданий.",
            "success",
        )
        return redirect(url_for("admin.list_scripts"))
    return render_template("admin/script_form.html", script=script)


@bp.route("/scripts/<int:id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_script(id):
    script = TestScript.query.get_or_404(id)
    db.session.delete(script)
    db.session.commit()
    cache.clear()
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
# Создание задания
# -------------------------------------------------------------
@bp.route("/assignment/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_assignment():
    scripts = TestScript.query.all()
    groups = Group.query.all()
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        check_type = request.form.get("check_type", "manual")

        # Дедлайн и попытки
        deadline_str = request.form.get("deadline", "").strip()
        deadline = (
            datetime.strptime(deadline_str, "%Y-%m-%dT%H:%M") if deadline_str else None
        )
        max_attempts = request.form.get("max_attempts", 0, type=int)

        script_id = (
            request.form.get("script_id", type=int) if check_type == "auto" else None
        )

        # Видимость
        visibility = request.form.get("visibility", "public")
        group_id = None
        is_public = False
        if visibility == "public":
            is_public = True
        elif visibility == "authenticated":
            is_public = False
        elif visibility == "group":
            is_public = False
            group_id = request.form.get("group_id", type=int) or None
            if not group_id:
                flash("Выберите группу для группового задания", "danger")
                return render_template(
                    "admin/new_assignment.html", scripts=scripts, groups=groups
                )

        assignment = Assignment(
            title=title,
            description=description,
            check_type=check_type,
            is_public=is_public,
            group_id=group_id,
            deadline=deadline,
            max_attempts=max_attempts,
        )
        db.session.add(assignment)
        db.session.flush()

        # Привязка скриптов для auto
        if check_type == "auto" and script_id:
            script = TestScript.query.get(script_id)
            if script:
                languages = ["python", "cpp", "javascript", "java"]
                for lang in languages:
                    db.session.add(
                        AssignmentScript(
                            assignment_id=assignment.id,
                            test_script_id=script.id,
                            language=lang,
                        )
                    )

        # Сохранение вопросов для quiz
        if check_type == "quiz":
            question_texts = request.form.getlist("question_text")
            question_scores = request.form.getlist("question_score")
            question_types = request.form.getlist("question_type")
            for idx, q_text in enumerate(question_texts):
                if not q_text.strip():
                    continue
                q_type = question_types[idx] if idx < len(question_types) else "single"
                question = QuizQuestion(
                    assignment_id=assignment.id,
                    question_text=q_text.strip(),
                    question_type=q_type,
                    order=idx,
                    max_score=(
                        float(question_scores[idx])
                        if idx < len(question_scores)
                        else 1.0
                    ),
                )
                db.session.add(question)
                db.session.flush()

                opt_texts = request.form.getlist(f"option_text_{idx}[]")
                if q_type == "single":
                    correct_value = request.form.get(f"option_correct_{idx}")
                    correct_indices = (
                        [correct_value] if correct_value is not None else []
                    )
                else:
                    correct_indices = request.form.getlist(f"option_correct_{idx}[]")

                for opt_idx, opt_text in enumerate(opt_texts):
                    if not opt_text.strip():
                        continue
                    is_correct = str(opt_idx) in correct_indices
                    db.session.add(
                        QuizOption(
                            question_id=question.id,
                            option_text=opt_text.strip(),
                            is_correct=is_correct,
                        )
                    )

        db.session.commit()
        cache.clear()
        flash("Задание создано", "success")
        return redirect(url_for("admin.index"))

    return render_template("admin/new_assignment.html", scripts=scripts, groups=groups)


# -------------------------------------------------------------
# Редактирование задания
# -------------------------------------------------------------
@bp.route("/assignment/<int:id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_assignment(id):
    assignment = Assignment.query.get_or_404(id)
    scripts = TestScript.query.all()
    groups = Group.query.all()

    if assignment.is_public:
        current_visibility = "public"
    elif assignment.group_id:
        current_visibility = "group"
    else:
        current_visibility = "authenticated"

    if request.method == "POST":
        assignment.title = request.form.get("title")
        assignment.description = request.form.get("description")
        assignment.check_type = request.form.get("check_type", "manual")

        # Дедлайн и попытки
        deadline_str = request.form.get("deadline", "").strip()
        assignment.deadline = (
            datetime.strptime(deadline_str, "%Y-%m-%dT%H:%M") if deadline_str else None
        )
        assignment.max_attempts = request.form.get("max_attempts", 0, type=int)

        # Видимость
        visibility = request.form.get("visibility", "public")
        group_id = None
        is_public = False
        if visibility == "public":
            is_public = True
        elif visibility == "authenticated":
            is_public = False
        elif visibility == "group":
            is_public = False
            group_id = request.form.get("group_id", type=int) or None
            if not group_id:
                flash("Выберите группу для группового задания", "danger")
                return render_template(
                    "admin/edit_assignment.html",
                    assignment=assignment,
                    scripts=scripts,
                    groups=groups,
                    current_visibility=current_visibility,
                )
        assignment.is_public = is_public
        assignment.group_id = group_id

        # Удаляемые старые привязки скриптов и вопросы
        AssignmentScript.query.filter_by(assignment_id=assignment.id).delete()
        QuizOption.query.filter(
            QuizOption.question.has(assignment_id=assignment.id)
        ).delete()
        QuizAnswer.query.filter(
            QuizAnswer.question.has(assignment_id=assignment.id)
        ).delete()
        QuizQuestion.query.filter_by(assignment_id=assignment.id).delete()

        # Скрипты для auto
        if assignment.check_type == "auto":
            script_id = request.form.get("script_id", type=int)
            if script_id:
                script = TestScript.query.get(script_id)
                if script:
                    for lang in ["python", "cpp", "javascript", "java"]:
                        db.session.add(
                            AssignmentScript(
                                assignment_id=assignment.id,
                                test_script_id=script.id,
                                language=lang,
                            )
                        )

        # Обработка тестов
        if assignment.check_type == "quiz":
            question_texts = request.form.getlist("question_text")
            question_types = request.form.getlist("question_type")
            question_scores = request.form.getlist("question_score")

            for idx, q_text in enumerate(question_texts):
                if not q_text.strip():
                    continue
                q_type = question_types[idx] if idx < len(question_types) else "single"
                try:
                    max_score = (
                        float(question_scores[idx])
                        if idx < len(question_scores)
                        else 1.0
                    )
                except (ValueError, IndexError):
                    max_score = 1.0

                question = QuizQuestion(
                    assignment_id=assignment.id,
                    question_text=q_text.strip(),
                    question_type=q_type,
                    order=idx,
                    max_score=max_score,
                )
                db.session.add(question)
                db.session.flush()

                # Варианты ответов
                opt_texts = request.form.getlist(f"option_text_{idx}[]")
                if q_type == "single":
                    correct_value = request.form.get(f"option_correct_{idx}")
                    correct_indices = (
                        [correct_value] if correct_value is not None else []
                    )
                else:
                    correct_indices = request.form.getlist(f"option_correct_{idx}[]")

                for opt_idx, opt_text in enumerate(opt_texts):
                    if not opt_text.strip():
                        continue
                    is_correct = str(opt_idx) in correct_indices
                    db.session.add(
                        QuizOption(
                            question_id=question.id,
                            option_text=opt_text.strip(),
                            is_correct=is_correct,
                        )
                    )

        db.session.commit()
        cache.clear()

        # Аннулирование потерявших доступ
        if assignment.group_id:
            group = Group.query.get(assignment.group_id)
            subs = Submission.query.filter_by(assignment_id=assignment.id).all()
            for sub in subs:
                if sub.user and sub.user not in group.members:
                    sub.status = "failed"
                    sub.score = 0
                    sub.feedback = "Задание стало доступно только участникам группы. Ваше решение аннулировано."
            db.session.commit()

        if assignment.check_type == "auto":
            recheck_all_task.delay(assignment.id, current_app.config["UPLOAD_FOLDER"])
            flash("Задание обновлено. Запущена полная перепроверка.", "success")
        else:
            flash("Задание обновлено.", "success")

        return redirect(url_for("admin.index"))

    from sqlalchemy.orm import joinedload

    questions = (
        assignment.quiz_questions.order_by(QuizQuestion.order)
        .options(joinedload(QuizQuestion.options))
        .all()
    )

    return render_template(
        "admin/edit_assignment.html",
        assignment=assignment,
        scripts=scripts,
        groups=groups,
        current_visibility=current_visibility,
        questions=questions,
    )


# -------------------------------------------------------------
# Удаление задания
# -------------------------------------------------------------
@bp.route("/assignment/<int:id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_assignment(id):
    a = Assignment.query.get_or_404(id)
    db.session.delete(a)
    db.session.commit()
    cache.clear()
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
        cache.clear()
        return redirect(url_for("admin.index"))
    return render_template("admin/submission_detail.html", submission=submission)


# -------------------------------------------------------------
# Скачивание файла
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
# Авто-проверка (только pending)
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
            continue
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
    cache.clear()
    flash(f"Проверено {count} решений", "success")
    return redirect(url_for("admin.index"))


# -------------------------------------------------------------
# Массовая перепроверка (через Celery)
# -------------------------------------------------------------
@bp.route("/assignment/<int:id>/recheck-all")
@login_required
@admin_required
def recheck_all(id):
    assignment = Assignment.query.get_or_404(id)
    if assignment.check_type != "auto":
        flash("Для этого задания не настроен автотест", "warning")
        return redirect(url_for("admin.index"))

    recheck_all_task.delay(assignment.id, current_app.config["UPLOAD_FOLDER"])
    cache.clear()
    flash("Перепроверка всех решений запущена в фоне через Celery.", "info")
    return redirect(url_for("admin.index"))


# -------------------------------------------------------------
# Управление группами
# -------------------------------------------------------------
@bp.route("/groups")
@login_required
@admin_required
def list_groups():
    groups = Group.query.order_by(Group.created_at.desc()).all()
    return render_template("admin/groups.html", groups=groups)


@bp.route("/groups/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_group():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Введите название группы", "danger")
            return render_template("admin/group_form.html", group=None)
        if Group.query.filter_by(name=name).first():
            flash("Группа с таким названием уже существует", "danger")
            return render_template("admin/group_form.html", group=None)
        group = Group(name=name, created_by=current_user.id)
        group.members.append(current_user)  # админ автоматически в группе
        db.session.add(group)
        db.session.commit()
        cache.clear()
        flash("Группа создана", "success")
        return redirect(url_for("admin.list_groups"))
    return render_template("admin/group_form.html", group=None)


@bp.route("/groups/<int:id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_group(id):
    group = Group.query.get_or_404(id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Название не может быть пустым", "danger")
            return render_template("admin/group_form.html", group=group)
        existing = Group.query.filter(Group.name == name, Group.id != id).first()
        if existing:
            flash("Группа с таким названием уже есть", "danger")
            return render_template("admin/group_form.html", group=group)
        group.name = name
        db.session.commit()
        cache.clear()
        flash("Группа обновлена", "success")
        return redirect(url_for("admin.list_groups"))
    return render_template("admin/group_form.html", group=group)


@bp.route("/groups/<int:id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_group(id):
    group = Group.query.get_or_404(id)
    db.session.delete(group)
    db.session.commit()
    cache.clear()
    flash("Группа удалена", "info")
    return redirect(url_for("admin.list_groups"))


# Участники
@bp.route("/groups/<int:id>/members")
@login_required
@admin_required
def manage_members(id):
    group = Group.query.get_or_404(id)
    all_users = User.query.filter(User.role != "admin").order_by(User.username).all()
    return render_template("admin/group_members.html", group=group, all_users=all_users)


@bp.route("/groups/<int:id>/members/add", methods=["POST"])
@login_required
@admin_required
def add_member(id):
    group = Group.query.get_or_404(id)
    user_id = request.form.get("user_id", type=int)
    if not user_id:
        flash("Выберите пользователя", "danger")
        return redirect(url_for("admin.manage_members", id=id))
    user = User.query.get_or_404(user_id)
    if user not in group.members:
        group.members.append(user)
        db.session.commit()
        cache.clear()
        flash(f"{user.username} добавлен в группу", "success")
    else:
        flash("Пользователь уже в группе", "info")
    return redirect(url_for("admin.manage_members", id=id))


@bp.route("/groups/<int:id>/members/remove/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def remove_member(id, user_id):
    group = Group.query.get_or_404(id)
    user = User.query.get_or_404(user_id)
    if user.is_admin():
        flash("Нельзя удалить администратора из группы", "danger")
        return redirect(url_for("admin.manage_members", id=id))
    if user in group.members:
        group.members.remove(user)
        db.session.commit()
        cache.clear()
        flash(f"{user.username} удалён из группы", "info")
    return redirect(url_for("admin.manage_members", id=id))


# Приглашения
@bp.route("/groups/<int:id>/invites")
@login_required
@admin_required
def list_invites(id):
    group = Group.query.get_or_404(id)
    invites = (
        GroupInvite.query.filter_by(group_id=id)
        .order_by(GroupInvite.created_at.desc())
        .all()
    )
    return render_template("admin/group_invites.html", group=group, invites=invites)


@bp.route("/groups/<int:id>/invites/create", methods=["POST"])
@login_required
@admin_required
def create_invite(id):
    group = Group.query.get_or_404(id)
    max_uses = request.form.get("max_uses", 0, type=int)
    expires_days = request.form.get("expires_days", 0, type=int)
    invite = GroupInvite(
        group_id=group.id,
        created_by=current_user.id,
        max_uses=max_uses,
        expires_at=(
            datetime.utcnow() + timedelta(days=expires_days)
            if expires_days > 0
            else None
        ),
    )
    db.session.add(invite)
    db.session.commit()
    cache.clear()
    return redirect(url_for("admin.list_invites", id=id))


@bp.route("/groups/<int:id>/invites/<int:invite_id>/deactivate", methods=["POST"])
@login_required
@admin_required
def deactivate_invite(id, invite_id):
    invite = GroupInvite.query.get_or_404(invite_id)
    invite.is_active = False
    db.session.commit()
    cache.clear()
    flash("Ссылка деактивирована", "info")
    return redirect(url_for("admin.list_invites", id=id))

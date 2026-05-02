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
from app import db, create_app, cache  # <-- добавлен cache
from app.models import (
    Assignment,
    Submission,
    TestScript,
    AssignmentScript,
    Group,
    User,
    GroupInvite,
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
        cache.clear()  # очистка кеша
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
        cache.clear()  # очистка кеша
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
    cache.clear()  # очистка кеша
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
    groups = Group.query.all()
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        check_type = request.form.get("check_type", "manual")
        # ВСЕГДА получаем group_id, независимо от чекбокса
        group_id = request.form.get("group_id", type=int) or None
        script_id = (
            request.form.get("script_id", type=int) if check_type == "auto" else None
        )

        # Если задание привязано к группе, оно НЕ должно быть публичным
        is_public = False if group_id else request.form.get("is_public") == "on"

        assignment = Assignment(
            title=title,
            description=description,
            check_type=check_type,
            is_public=is_public,
            group_id=group_id,
        )
        db.session.add(assignment)
        db.session.flush()

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
        cache.clear()
        flash("Задание создано", "success")
        return redirect(url_for("admin.index"))

    return render_template("admin/new_assignment.html", scripts=scripts, groups=groups)


@bp.route("/assignment/<int:id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_assignment(id):
    a = Assignment.query.get_or_404(id)
    db.session.delete(a)
    db.session.commit()
    cache.clear()  # очистка кеша
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
        cache.clear()  # очистка кеша
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
    cache.clear()  # очистка кеша
    flash(f"Проверено {count} решений", "success")
    return redirect(url_for("admin.index"))


# -------------------------------------------------------------
# Фоновая перепроверка всех решений (через Celery)
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
    cache.clear()  # очистка кеша
    flash("Перепроверка всех решений запущена в фоне через Celery.", "info")
    return redirect(url_for("admin.index"))


# Новые маршруты для групп
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

        # Проверяем уникальность
        if Group.query.filter_by(name=name).first():
            flash("Группа с таким названием уже существует", "danger")
            return render_template("admin/group_form.html", group=None)

        group = Group(name=name, created_by=current_user.id)
        # Добавляем создателя (админа) в группу автоматически
        group.members.append(current_user)
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

        # Проверка уникальности
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


# Управление участниками
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
    # Запрет удаления администраторов
    if user.is_admin():
        flash("Нельзя удалить администратора из группы", "danger")
        return redirect(url_for("admin.manage_members", id=id))
    if user in group.members:
        group.members.remove(user)
        db.session.commit()
        cache.clear()
        flash(f"{user.username} удалён из группы", "info")
    return redirect(url_for("admin.manage_members", id=id))


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

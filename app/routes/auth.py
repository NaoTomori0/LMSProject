from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from app import db, oauth, cache  # добавлен cache
from app.models import User, GroupInvite
from datetime import datetime
from app.utils import (
    generate_verification_code,
    send_verification_email,
    verify_admin_permanent_token,
)
import secrets

bp = Blueprint("auth", __name__, url_prefix="/auth")


# ---------- Быстрый вход администратора ----------
@bp.route("/admin-login/<token>")
def admin_login(token):
    admin_id = verify_admin_permanent_token(token)
    if not admin_id:
        flash("Неверный токен доступа", "danger")
        return redirect(url_for("main.index"))
    user = User.query.get(admin_id)
    if not user or not user.is_admin():
        flash("Пользователь не является администратором", "danger")
        return redirect(url_for("main.index"))
    login_user(user)
    flash("Вы вошли как администратор (постоянная ссылка)", "success")
    return redirect(url_for("admin.index"))


# ---------- Регистрация ----------
@bp.route("/sign_in", methods=["GET", "POST"])
def sign_in():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if User.query.filter_by(email=email).first():
            flash("Email уже используется", "danger")
            return render_template("sign_in.html", year=datetime.now().year)
        if User.query.filter_by(username=username).first():
            flash("Имя пользователя занято", "danger")
            return render_template("sign_in.html", year=datetime.now().year)

        user = User(username=username, email=email, role="user", email_verified=False)
        user.set_password(password)
        code = generate_verification_code()
        user.verification_code = code
        db.session.add(user)
        db.session.commit()

        print(f"===== Verification code for {email}: {code} =====")
        session["pending_verification_email"] = email
        flash("На ваш email отправлен код подтверждения. Введите его ниже.", "info")
        return redirect(url_for("auth.verify_email"))

    return render_template("sign_in.html", year=datetime.now().year)


# ---------- Вход ----------
@bp.route("/log_in", methods=["GET", "POST"])
def log_in():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if not user.email_verified:
                code = generate_verification_code()
                user.verification_code = code
                db.session.commit()
                session["pending_verification_email"] = user.email
                send_verification_email(user)
                flash("Ваш email не подтверждён. Новый код отправлен.", "warning")
                return redirect(url_for("auth.verify_email"))

            login_user(user)
            flash("Вы вошли в систему", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.index"))
        else:
            flash("Неверный email или пароль", "danger")

    return render_template("log_in.html", year=datetime.now().year)


# ---------- Выход ----------
@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))


# ---------- Google OAuth ----------
@bp.route("/login/google")
def google_login():
    redirect_uri = url_for("auth.google_auth", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@bp.route("/google/callback")
def google_auth():
    token = oauth.google.authorize_access_token()
    user_info = token.get("userinfo")
    if not user_info:
        flash("Ошибка данных Google", "danger")
        return redirect(url_for("auth.log_in"))

    email = user_info["email"]
    user = User.query.filter_by(email=email).first()
    if not user:
        username = email.split("@")[0]
        if User.query.filter_by(username=username).first():
            username = f"{username}_{secrets.token_hex(2)}"
        user = User.create_with_random_password(email, username)
        db.session.add(user)
        db.session.commit()

    login_user(user)
    return redirect(url_for("main.index"))


# ---------- GitHub OAuth ----------
@bp.route("/login/github")
def github_login():
    redirect_uri = url_for("auth.github_auth", _external=True)
    return oauth.github.authorize_redirect(redirect_uri)


@bp.route("/github/callback")
def github_auth():
    token = oauth.github.authorize_access_token()
    resp = oauth.github.get("user")
    user_info = resp.json()
    email = user_info.get("email")
    if not email:
        emails = oauth.github.get("user/emails").json()
        email = next(e["email"] for e in emails if e["primary"])

    user = User.query.filter_by(email=email).first()
    if not user:
        username = user_info.get("login") or email.split("@")[0]
        if User.query.filter_by(username=username).first():
            username = f"{username}_{secrets.token_hex(2)}"
        user = User.create_with_random_password(email, username)
        db.session.add(user)
        db.session.commit()

    login_user(user)
    return redirect(url_for("main.index"))


# ---------- Подтверждение email ----------
@bp.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    email = session.get("pending_verification_email")
    if not email:
        return redirect(url_for("auth.sign_in"))

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("Пользователь не найден", "danger")
            return redirect(url_for("auth.sign_in"))

        if user.verification_code == code:
            user.email_verified = True
            user.verification_code = None
            db.session.commit()
            session.pop("pending_verification_email", None)
            cache.clear()  # очистка кеша
            login_user(user)
            flash("Email подтверждён! Добро пожаловать.", "success")
            return redirect(url_for("main.index"))
        else:
            flash("Неверный код. Попробуйте ещё раз.", "danger")

    return render_template("verify_email.html")


@bp.route("/verify-email/resend")
def resend_code():
    email = session.get("pending_verification_email")
    if not email:
        flash("Сессия истекла. Пожалуйста, начните регистрацию заново.", "warning")
        return redirect(url_for("auth.sign_in"))

    user = User.query.filter_by(email=email).first()
    if not user:
        return redirect(url_for("auth.sign_in"))
    if user.email_verified:
        flash("Ваш email уже подтверждён. Войдите в систему.", "info")
        return redirect(url_for("auth.log_in"))

    code = generate_verification_code()
    user.verification_code = code
    db.session.commit()
    send_verification_email(user)
    flash("Новый код отправлен.", "info")
    return redirect(url_for("auth.verify_email"))


@bp.route("/invite/<token>")
@login_required
def accept_invite(token):
    invite = GroupInvite.query.filter_by(token=token, is_active=True).first_or_404()
    if invite.expires_at and invite.expires_at < datetime.utcnow():
        flash("Срок действия ссылки истёк.", "danger")
        return redirect(url_for("main.index"))
    if invite.max_uses > 0 and invite.uses >= invite.max_uses:
        flash(
            "Ссылка больше не действительна (достигнут лимит использований).", "danger"
        )
        return redirect(url_for("main.index"))

    group = invite.group
    if current_user not in group.members:
        group.members.append(current_user)
        invite.uses += 1
        db.session.commit()
        cache.clear()
        flash(f"Вы успешно вступили в группу «{group.name}».", "success")
    else:
        flash("Вы уже состоите в этой группе.", "info")
    return redirect(url_for("cabinet.index"))

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from app import db, oauth
from app.models import User
from datetime import datetime
from app.utils import generate_verification_code
import secrets
from flask import session  # если ещё нет
from app.utils import generate_verification_code, send_verification_email
import os

bp = Blueprint("auth", __name__, url_prefix="/auth")


# ---------- стандартная регистрация ----------

from app.utils import verify_admin_login_token
from app.models import User
from flask_login import login_user


@bp.route("/auth/admin-login/<token>")
def admin_login(token):
    admin_id = verify_admin_login_token(token)
    if not admin_id:
        flash("Неверный или истёкший токен доступа", "danger")
        return redirect(url_for("main.index"))

    user = User.query.get(admin_id)
    if not user or not user.is_admin():
        flash("Пользователь не является администратором", "danger")
        return redirect(url_for("main.index"))

    login_user(user)
    flash("Вы вошли как администратор", "success")
    return redirect(url_for("admin.index"))


@bp.route("/sign_in", methods=["GET", "POST"])
def sign_in():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # ... валидация и проверка уникальности (как раньше) ...
        if User.query.filter_by(email=email).first():
            flash("Email уже используется", "danger")
            return render_template("sign_in.html", year=datetime.now().year)
        if User.query.filter_by(username=username).first():
            flash("Имя пользователя занято", "danger")
            return render_template("sign_in.html", year=datetime.now().year)

        # Создаём пользователя, но не активируем
        user = User(username=username, email=email, role="user", email_verified=False)
        user.set_password(password)

        # Генерируем код
        code = generate_verification_code()
        user.verification_code = code
        db.session.add(user)
        db.session.commit()

        # Для разработки: выводим код в консоль
        print(f"===== Verification code for {email}: {code} =====")

        # Сохраняем email в сессии, чтобы знать, кого верифицируем
        session["pending_verification_email"] = email

        flash("На ваш email отправлен код подтверждения. Введите его ниже.", "info")
        return redirect(url_for("auth.verify_email"))

    return render_template("sign_in.html", year=datetime.now().year)


# ---------- стандартный вход ----------
@bp.route("/log_in", methods=["GET", "POST"])
def log_in():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            # === НАЧАЛО ДОБАВЛЕННОГО БЛОКА ===
            if not user.email_verified:
                code = generate_verification_code()
                user.verification_code = code
                db.session.commit()
                session["pending_verification_email"] = user.email
                send_verification_email(user)
                flash("Ваш email не подтверждён. Новый код отправлен.", "warning")
                return redirect(url_for("auth.verify_email"))
            # === КОНЕЦ ДОБАВЛЕННОГО БЛОКА ===

            login_user(user)
            flash("Вы вошли в систему", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.index"))
        else:
            flash("Неверный email или пароль", "danger")

    return render_template("log_in.html", year=datetime.now().year)


# ---------- выход ----------
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


@bp.route("/auth/google/callback")
def google_auth():
    token = oauth.google.authorize_access_token()
    user_info = token.get("userinfo")
    if not user_info:
        flash("Ошибка данных Google", "danger")
        return redirect(url_for("auth.log_in"))

    email = user_info["email"]
    user = User.query.filter_by(email=email).first()
    if not user:
        # Генерируем username из email
        username = email.split("@")[0]
        # Убедимся, что username уникален
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


@bp.route("/auth/github/callback")
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
            user.verification_code = None  # очищаем код
            db.session.commit()
            session.pop("pending_verification_email", None)
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
    flash("Новый код отправлен. Проверьте консоль (или почту)", "info")
    return redirect(url_for("auth.verify_email"))

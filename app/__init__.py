import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth
from config import Config
from datetime import datetime
from flask_mail import Mail
from datetime import timedelta
from dotenv import load_dotenv
from flask_caching import Cache

cache = Cache()

load_dotenv()

# для импорта
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = "auth.log_in"
oauth = OAuth()
mail = Mail()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    oauth.init_app(app)

    mail.init_app(app)

    # Регистрация OAuth провайдеров
    oauth.register(
        name="google",
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    oauth.register(
        name="github",
        client_id=app.config["GITHUB_CLIENT_ID"],
        client_secret=app.config["GITHUB_CLIENT_SECRET"],
        authorize_url="https://github.com/login/oauth/authorize",
        access_token_url="https://github.com/login/oauth/access_token",
        api_base_url="https://api.github.com",
        client_kwargs={"scope": "user:email"},
    )

    # создать папку uploads если её нет
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Контекстный процессор для переменной year
    @app.context_processor
    def inject_globals():
        return {"year": datetime.utcnow().year}

    @app.cli.command("create-admin")
    def create_admin():
        import os
        from app.models import User

        username = os.getenv("ADMIN_USERNAME", "admin")
        email = os.getenv("ADMIN_EMAIL", "admin@lms.local")
        password = os.getenv("ADMIN_PASSWORD")
        if not password:
            print("❌ ADMIN_PASSWORD не задан в .env")
            return

        with app.app_context():
            user = User.query.filter_by(email=email).first()
            if user:
                user.username = username
                user.set_password(password)
                user.email_verified = True
                user.verification_code = None
                db.session.commit()
                print(f"✅ Администратор {user.username} обновлён и подтверждён")
            else:
                admin = User(
                    username=username, email=email, role="admin", email_verified=True
                )
                admin.set_password(password)
                db.session.add(admin)
                db.session.commit()
                print(f"✅ Администратор {username} создан и подтверждён")

    @app.cli.command("gen-admin-login")
    def gen_admin_login():
        import os
        from app.utils import generate_admin_permanent_token

        with app.app_context():
            from app.models import User

            admin = User.query.filter_by(role="admin").first()
            if not admin:
                print(
                    "❌ Администратор не найден. Создайте его через flask create-admin"
                )
                return
            token = generate_admin_permanent_token(admin.id)
            base_url = os.getenv("BASE_URL", "http://127.0.0.1:5555")
            print("✅ Постоянная ссылка для входа администратора (не истекает):")
            print(f"{base_url}/auth/admin-login/{token}")

    # Регистрация блюпринтов
    from app.routes import auth, main, admin, cabinet

    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(cabinet.bp)

    @app.template_filter("localtime")
    def localtime_filter(dt, offset_str="0"):
        if dt is None:
            return ""
        try:
            offset = int(offset_str)
        except (ValueError, TypeError):
            offset = 0
        local_dt = dt + timedelta(minutes=offset)
        return local_dt.strftime("%d.%m.%Y %H:%M")

    # контекстный процессор передающий смещение из куки
    @app.context_processor
    def inject_utc_offset():
        from flask import request

        offset = request.cookies.get("timezone_offset", "0")
        return {"utc_offset": offset}

    # from sqlalchemy import event

    # with app.app_context():

    #     @event.listens_for(db.engine, "connect")
    #     def _set_wal(dbapi_connection, connection_record):
    #         cursor = dbapi_connection.cursor()
    #         cursor.execute("PRAGMA journal_mode=WAL;")
    #         cursor.close()

    cache.init_app(
        app,
        config={
            "CACHE_TYPE": "redis",
            "CACHE_REDIS_URL": app.config.get("REDIS_URL", "redis://localhost:6379/0"),
            "CACHE_DEFAULT_TIMEOUT": 60,
        },
    )

    return app

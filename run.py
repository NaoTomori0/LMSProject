from dotenv import load_dotenv

load_dotenv()
from app import create_app

app = create_app()


@app.cli.command("create-admin")
def create_admin():
    import os
    from app import db
    from app.models import User

    username = os.getenv("ADMIN_USERNAME", "admin")
    email = os.getenv("ADMIN_EMAIL", "admin@lms.local")
    password = os.getenv("ADMIN_PASSWORD")

    if not password:
        print("Ошибка: ADMIN_PASSWORD не задан в .env")
        return

    if not User.query.filter_by(role="admin").first():
        admin = User(username=username, email=email, role="admin")
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Администратор {username} создан")
    else:
        print("Администратор уже существует")


if __name__ == "__main__":
    app.run(port=5555, debug=False)

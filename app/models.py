from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets

# Порядок важен: сначала модели, на которые нет ссылок, потом зависимые


# Добавить после класса Submission
class AssignmentScript(db.Model):
    __tablename__ = "assignment_script"
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(
        db.Integer, db.ForeignKey("assignment.id"), nullable=False
    )
    test_script_id = db.Column(
        db.Integer, db.ForeignKey("test_script.id"), nullable=False
    )
    language = db.Column(
        db.String(20), nullable=False
    )  # 'python', 'cpp', 'javascript', 'java'

    assignment = db.relationship(
        "Assignment", backref=db.backref("language_scripts", lazy="dynamic")
    )
    test_script = db.relationship("TestScript")


class TestScript(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    script_body = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(20), default="python")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=True
    )  # NULL для гостя
    assignment_id = db.Column(
        db.Integer, db.ForeignKey("assignment.id"), nullable=False
    )
    guest_name = db.Column(db.String(100), nullable=True)
    guest_email = db.Column(db.String(120), nullable=True)
    answer_text = db.Column(db.Text, nullable=True)
    answer_file = db.Column(db.String(256), nullable=True)
    status = db.Column(db.String(20), default="pending")
    score = db.Column(db.Float, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    langusage = db.Column(db.String(20), nullable=True)
    # Связь с пользователем (обратная ссылка 'submissions' создается через backref)
    user = db.relationship("User", backref=db.backref("submissions", lazy="dynamic"))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default="user")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    email_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(6), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == "admin"

    @staticmethod
    def create_with_random_password(email, username=None):
        user = User(email=email, username=username or email.split("@")[0], role="user")
        user.set_password(secrets.token_urlsafe(16))
        return user


@login.user_loader
def load_user(id):
    return User.query.get(int(id))

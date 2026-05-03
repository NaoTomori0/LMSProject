from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets
import uuid

# ------------------------------------------------------------
# Таблица связи пользователей и групп (многие-ко-многим)
# ------------------------------------------------------------
user_group = db.Table(
    "user_group",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("group_id", db.Integer, db.ForeignKey("group.id"), primary_key=True),
)


# ------------------------------------------------------------
# TestScript
# ------------------------------------------------------------
class TestScript(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    script_body = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(20), default="python")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ------------------------------------------------------------
# Assignment
# ------------------------------------------------------------
class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    check_type = db.Column(db.String(20), default="manual")
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Привязка к группе (если задание не публичное, а только для конкретной группы)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=True)
    group = db.relationship("Group", backref=db.backref("assignments", lazy="dynamic"))

    deadline = db.Column(db.DateTime, nullable=True)  # дедлайн
    max_attempts = db.Column(db.Integer, default=0)  # 0 – без ограничений

    # Каскадное удаление Submission и AssignmentScript
    submissions = db.relationship(
        "Submission", backref="assignment", lazy="dynamic", cascade="all, delete-orphan"
    )
    language_scripts = db.relationship(
        "AssignmentScript",
        backref="assignment",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )


# ------------------------------------------------------------
# AssignmentScript
# ------------------------------------------------------------
class AssignmentScript(db.Model):
    __tablename__ = "assignment_script"
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(
        db.Integer, db.ForeignKey("assignment.id"), nullable=False
    )
    test_script_id = db.Column(
        db.Integer, db.ForeignKey("test_script.id"), nullable=False
    )
    language = db.Column(db.String(20), nullable=False)

    test_script = db.relationship("TestScript")


# ------------------------------------------------------------
# User
# ------------------------------------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default="user")
    email_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(6), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    submissions = db.relationship("Submission", backref="user", lazy="dynamic")

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


# ------------------------------------------------------------
# Group
# ------------------------------------------------------------
class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship(
        "User", secondary=user_group, backref=db.backref("groups", lazy="dynamic")
    )


# ------------------------------------------------------------
# Submission
# ------------------------------------------------------------
class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    assignment_id = db.Column(
        db.Integer, db.ForeignKey("assignment.id"), nullable=False
    )
    guest_name = db.Column(db.String(100), nullable=True)
    guest_email = db.Column(db.String(120), nullable=True)
    answer_text = db.Column(db.Text, nullable=True)
    answer_file = db.Column(db.String(256), nullable=True)
    language = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), default="pending")
    score = db.Column(db.Float, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class GroupInvite(db.Model):
    __tablename__ = "group_invite"
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    token = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    max_uses = db.Column(db.Integer, default=0)
    uses = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Эта строка заменяет всё: и прямую связь, и обратную ссылку 'invites' для Group
    group = db.relationship(
        "Group",
        backref=db.backref("invites", lazy="dynamic", cascade="all, delete-orphan"),
    )


class QuizQuestion(db.Model):
    __tablename__ = "quiz_question"
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(
        db.Integer, db.ForeignKey("assignment.id"), nullable=False
    )
    question_text = db.Column(db.Text, nullable=False)
    max_score = db.Column(db.Float, default=1.0, nullable=False)
    question_type = db.Column(
        db.String(20), default="single"
    )  # single / multiple / open
    order = db.Column(db.Integer, default=0)  # порядок отображения
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    options = db.relationship(
        "QuizOption", backref="question", lazy="dynamic", cascade="all, delete-orphan"
    )
    assignment = db.relationship(
        "Assignment",
        backref=db.backref(
            "quiz_questions", lazy="dynamic", cascade="all, delete-orphan"
        ),
    )


class QuizOption(db.Model):
    __tablename__ = "quiz_option"
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(
        db.Integer, db.ForeignKey("quiz_question.id"), nullable=False
    )
    option_text = db.Column(db.String(500), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)  # для single/multiple


class QuizAnswer(db.Model):
    __tablename__ = "quiz_answer"
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(
        db.Integer, db.ForeignKey("submission.id"), nullable=False
    )
    question_id = db.Column(
        db.Integer, db.ForeignKey("quiz_question.id"), nullable=False
    )
    selected_options = db.Column(
        db.String(500), nullable=True
    )  # ID выбранных вариантов через запятую
    open_answer = db.Column(db.Text, nullable=True)  # для open-вопросов
    score = db.Column(
        db.Float, nullable=True
    )  # балл за вопрос (выставляется скриптом или вручную)

    submission = db.relationship(
        "Submission",
        backref=db.backref(
            "quiz_answers", lazy="dynamic", cascade="all, delete-orphan"
        ),
    )
    question = db.relationship("QuizQuestion")

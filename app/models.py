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
    invites = db.relationship(
        "GroupInvite", backref="group", lazy="dynamic", cascade="all, delete-orphan"
    )
    # Участники группы (многие-ко-многим к User)
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
    max_uses = db.Column(db.Integer, default=0)  # 0 — без ограничений
    uses = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    group = db.relationship("Group", backref=db.backref("invites", lazy="dynamic"))

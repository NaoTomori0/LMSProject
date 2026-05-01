import subprocess
import tempfile
import os
import json
import random
import string
from flask_mail import Message
from flask import current_app
from app import mail
import shutil


def generate_verification_code():
    return "".join(random.choices(string.digits, k=6))


def run_check(script_body, answer_text, timeout=5):
    # Создаем временные файлы
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script_body)
        script_path = f.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(answer_text)
        input_path = f.name

    try:
        proc = subprocess.run(
            ["python3", script_path, input_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = proc.stdout.strip()
        result = json.loads(
            output
        )  # Ожидаем JSON {"passed": true/false, "score": ..., "feedback": "..."}
    except subprocess.TimeoutExpired:
        result = {
            "passed": False,
            "score": 0,
            "feedback": "Скрипт превысил лимит времени",
        }
    except Exception as e:
        result = {"passed": False, "score": 0, "feedback": str(e)}
    finally:
        os.unlink(script_path)
        os.unlink(input_path)
    return result


def send_verification_email(user):
    if not current_app.config.get("MAIL_USERNAME"):
        print(
            f"===== Verification code for {user.email}: {user.verification_code} ====="
        )
        return
    msg = Message(
        subject="Подтверждение email",
        sender=current_app.config["MAIL_USERNAME"],
        recipients=[user.email],
    )
    msg.body = f"Ваш код подтверждения: {user.verification_code}"
    mail.send(msg)


DOCKER_IMAGE = "lms-sandbox"

import shutil

docker_path = shutil.which("docker") or "/usr/bin/docker"


def run_check_docker(script_body, answer_input, is_file_path=False, timeout=5):
    sandbox_dir = tempfile.mkdtemp(prefix="lms_sandbox_")
    try:
        # Сохраняем скрипт проверки
        checker_path = os.path.join(sandbox_dir, "checker.py")
        with open(checker_path, "w", encoding="utf-8") as f:
            f.write(script_body)
        os.chmod(checker_path, 0o444)

        # Готовим ответ
        if is_file_path:
            answer_name = os.path.basename(answer_input)
            dest = os.path.join(sandbox_dir, answer_name)
            shutil.copy(answer_input, dest)
            os.chmod(dest, 0o444)
            answer_arg = f"/sandbox/{answer_name}"
        else:
            answer_name = "answer.txt"
            answer_path = os.path.join(sandbox_dir, answer_name)
            with open(answer_path, "w", encoding="utf-8") as f:
                f.write(answer_input or "")
            os.chmod(answer_path, 0o444)
            answer_arg = "/sandbox/answer.txt"

        # --- Строгая изоляция ---
        container_cmd = [
            docker_path,
            "run",
            "--rm",
            "--network",
            "none",
            "--memory",
            "256m",
            "--cpus",
            "0.5",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "-v",
            f"{sandbox_dir}:/sandbox:ro",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,exec,size=64M",  # ← разрешили выполнение
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            DOCKER_IMAGE,
            "python3",
            "/sandbox/checker.py",
            answer_arg,
        ]

        proc = subprocess.run(
            container_cmd, capture_output=True, text=True, timeout=timeout + 3
        )
        output = proc.stdout.strip()
        if proc.returncode != 0:
            raise Exception(
                f"Docker error (exit {proc.returncode}): {proc.stderr.strip()}"
            )

        result = json.loads(output)
    except subprocess.TimeoutExpired:
        result = {
            "passed": False,
            "score": 0,
            "feedback": "Проверка превысила лимит времени",
        }
    except Exception as e:
        result = {"passed": False, "score": 0, "feedback": f"Ошибка: {str(e)}"}
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)
    return result


from itsdangerous import URLSafeSerializer
from flask import current_app


def generate_admin_permanent_token(admin_user_id):
    s = URLSafeSerializer(
        current_app.config["SECRET_KEY"], salt="admin-permanent-login"
    )
    return s.dumps({"admin_id": admin_user_id})


def verify_admin_permanent_token(token):
    s = URLSafeSerializer(
        current_app.config["SECRET_KEY"], salt="admin-permanent-login"
    )
    try:
        data = s.loads(token)
        return data["admin_id"]
    except:
        return None

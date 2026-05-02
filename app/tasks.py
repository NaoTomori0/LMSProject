import os
from .celery_app import celery
from .utils import run_check_docker


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def check_submission_task(self, submission_id, upload_folder):
    from . import create_app

    app = create_app()
    with app.app_context():
        from .models import Submission, AssignmentScript
        from . import db

        submission = Submission.query.get(submission_id)
        if not submission:
            return {"status": "error", "msg": "Submission not found"}

        assignment_script = AssignmentScript.query.filter_by(
            assignment_id=submission.assignment_id, language=submission.language
        ).first()
        if not assignment_script:
            return {"status": "skipped", "msg": "No script for this language"}

        script = assignment_script.test_script
        if not script:
            return {"status": "skipped", "msg": "Script not found"}

        if submission.answer_file:
            files = submission.answer_file.split(",")
            input_path = os.path.join(upload_folder, files[0])
            is_file = True
        else:
            input_path = submission.answer_text or ""
            is_file = False

        try:
            result = run_check_docker(
                script.script_body, input_path, is_file, language=submission.language
            )
            submission.status = "passed" if result.get("passed") else "failed"
            submission.score = result.get("score", 0)
            submission.feedback = result.get("feedback", "")
            db.session.commit()
            return {
                "status": "done",
                "passed": result.get("passed"),
                "score": result.get("score"),
            }
        except Exception as e:
            self.retry(exc=e)


@celery.task
def recheck_all_task(assignment_id, upload_folder):
    from . import create_app

    app = create_app()
    with app.app_context():
        from .models import Submission, AssignmentScript
        from . import db

        submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
        count = 0
        for sub in submissions:
            if not sub.language:
                continue
            assignment_script = AssignmentScript.query.filter_by(
                assignment_id=assignment_id, language=sub.language
            ).first()
            if not assignment_script:
                continue
            script = assignment_script.test_script
            if not script:
                continue

            if sub.answer_file:
                files = sub.answer_file.split(",")
                input_path = os.path.join(upload_folder, files[0])
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
            except Exception:
                pass
        db.session.commit()
        return {"status": "done", "checked": count}

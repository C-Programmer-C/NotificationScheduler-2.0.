from conf.logging_config import conf_logger
conf_logger()
import logging
from dateutil.parser import isoparse
from flask import Flask, request, jsonify
from datetime import timezone
from waitress import serve
from app.db_utils import insert_task, has_task, init_db
from app.utils import normalize_due, create_iso_date_with_duration
import sqlite3
from app.utils import log_and_abort, last_comment_has_bot

app = Flask(__name__)

logger = logging.getLogger(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(silent=True)

    if not data:
        return log_and_abort("invalid or missing json")

    task = data.get("task")
    if not task:
        return log_and_abort("task not found")

    task_id = data.get("task_id") or (task or {}).get("id")

    if not task_id:
        return log_and_abort("task_id not found")

    logger.info("get new task #%s", task_id)

    duration_minutes = task.get("duration")

    due = task.get("due") or task.get("due_date")

    if not due:
        return log_and_abort("due not found", task_id)

    if not duration_minutes:
        due = normalize_due(due) if isinstance(due, str) else None
    elif isinstance(duration_minutes, int):
        due = create_iso_date_with_duration(due, duration_minutes)
        due = normalize_due(due)



    create_date_raw = task.get("create_date")
    last_modified_raw = task.get("last_modified_date")

    create_date = isoparse(create_date_raw) if create_date_raw else None
    last_modified_date = isoparse(last_modified_raw) if last_modified_raw else None

    if not create_date or not last_modified_date:
        return log_and_abort("failed to get task #{task_id} update or creation date.")

    create_date_utc = create_date.astimezone(timezone.utc)
    last_modified_date_utc = last_modified_date.astimezone(timezone.utc)

    comments = task.get("comments", [])

    is_new_task = create_date_utc == last_modified_date_utc or last_comment_has_bot(comments)


    if is_new_task:
        logger.info(f"creation and update dates match in task #{task_id}.")

        try:
             task_exists = has_task(task_id)
        except Exception:
            logger.exception(f"Failed to check existence of task #{task_id}.")
            return None

        if not task_exists:
            try:
                insert_task(task_id, due, due)
                logger.info(f"task #{task_id} has been successfully added to the database.")
                return '', 200
            except sqlite3.Error:
                logger.exception(f"Failed to insert task #{task_id} into the database.")
                return jsonify({"error": "internal server error"}), 500
        else:
            logger.info(f"task #{task_id} already exists in the database.")

    else:
        logger.info(f"creation and update dates not match in task #{task_id}")

    return '', 200

if __name__ == '__main__':
    init_db()
    serve(app, host="0.0.0.0", port=8080)

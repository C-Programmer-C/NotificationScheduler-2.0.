import logging
from conf.logging_config import conf_logger
conf_logger()
from app.db_utils import db_connect, fetch_candidates, try_lock_task
from app.process_task import process_task
from app.pyrus_api import get_token
import time
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.utils import now_utc, to_iso
from conf.config import settings

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def recover_stale_locks():
    expiry = now_utc() - timedelta(minutes=settings.LOCK_EXPIRY_MINUTES)
    conn = db_connect()
    try:
        cur = conn.execute("SELECT task_id FROM active_tasks WHERE processing = 1 AND locked_at <= ?", (to_iso(expiry),))
        stale = [r["task_id"] for r in cur.fetchall()]
        if stale:
            logger.info("recovering stale locks for tasks: %s", stale)
            conn.executemany("UPDATE active_tasks SET processing = 0, locked_at = NULL WHERE task_id = ?", [(tid,) for tid in stale])
            conn.commit()
    finally:
        conn.close()

def scanner_main():
    with ThreadPoolExecutor(max_workers=settings.MAX_WORKERS) as exe:
        while True:
            try:
                auth_token = get_token(login, security_key)
                logger.debug("token successfully received.")
            except Exception:
                logger.exception("failed to get access token")
            try:
                recover_stale_locks()
                candidates = fetch_candidates(settings.LIMIT_PROCESS_TASKS)
                if not candidates:
                    logger.debug("not found tasks for processing.")
                    time.sleep(settings.SCAN_INTERVAL)
                    continue

                futures = {}
                for task_id in candidates:
                    if try_lock_task(task_id):
                        fut = exe.submit(process_task, task_id, auth_token)
                        futures[fut] = task_id
                    else:
                        logger.info("task #%s already processing when trying to grab task.", task_id)

                for fut in as_completed(futures):
                    tid = futures[fut]
                    try:
                        fut.result()
                        logger.info("task #%s successfully finished.", tid)
                    except Exception:
                        logger.exception("error during processing task #%s.", tid)
            except Exception:
                logger.exception("failed to search tasks.")
            time.sleep(settings.SCAN_INTERVAL)


if __name__ == '__main__':
    login = settings.LOGIN
    security_key = settings.SECURITY_KEY
    scanner_main()
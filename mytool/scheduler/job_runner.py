import time
import logging
from db.session_manager import get_session
from db.models import Job


def arbitrary_job(**kwargs):
    """
    Placeholder for arbitrary, IO- or CPU-bound jobs.
    Simulates job execution by sleeping for 5 seconds.
    """
    job_key = kwargs.get('key')
    logging.info(f"Job {job_key}: Starting arbitrary_job")
    time.sleep(5)  # Simulate an IO-bound operation
    logging.info(f"Job {job_key}: Finished arbitrary_job")


def run_job(job_key: int, status_key: str, tries: int, delay: float, backoff: float):
    """
    Executes a job and updates its status to 'Done' with retry logic.
    """
    attempt = 1
    current_delay = delay
    while attempt <= tries:
        try:
            with get_session() as session:
                # this is for testing purposes
                if attempt == 1:
                    raise Exception("Test exception")
                job = session.query(Job).get(job_key)
                if job is None:
                    logging.warning(f"Job {job_key} not found")
                    return
                logging.info(f"Running {job}")
                # Simulate the job execution
                arbitrary_job(key=job.key)
                job.update_state('Done', session, status_key=status_key)
            break  # Exit the loop if job succeeds
        except Exception as e:
            if attempt == tries:
                logging.error(f"Job {job_key} failed after {tries} attempts with exception: {e}")
                break
            else:
                logging.warning(f"Job {job_key} failed on attempt {attempt} with exception: {e}. Retrying in {current_delay} seconds...")
                time.sleep(current_delay)
                current_delay *= backoff
                attempt += 1

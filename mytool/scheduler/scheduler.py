import sys
import signal
import time
import logging
import threading
from typing import Iterator
import concurrent.futures
from db.session_manager import get_session
from db.models import Job
from .job_runner import run_job


def get_jobs(session) -> Iterator[Job]:
    """
    Yields each job in the job table regardless of status.
    """
    jobs = session.query(Job).all()
    for job in jobs:
        logging.info(f"Fetched {job}")
        yield job


def scheduler_run(max_concurrent_jobs: int, status_key: str, ready_val: str, tries: int, delay: float, backoff: float):
    """
    Runs the scheduler to execute jobs concurrently based on the specified status column.
    """
    logging.info("Starting scheduler...")
    logging.info(f"Max concurrent jobs: {max_concurrent_jobs}, Status key: '{status_key}', Ready value: '{ready_val}'")
    logging.info(f"Retry configuration - Tries: {tries}, Delay: {delay}, Backoff: {backoff}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_jobs) as executor:
        futures = set()
        interrupted = threading.Event()

        def signal_handler(signum, frame):
            logging.info("Received interrupt signal, shutting down gracefully...")
            interrupted.set()
            executor.shutdown(wait=False)

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            while not interrupted.is_set():
                with get_session() as session:
                    try:
                        # Fetch all jobs
                        for job in get_jobs(session):
                            # Check if the job is ready to run based on status_key and ready_val
                            current_status = getattr(job, status_key, None)
                            if current_status == ready_val:
                                # Update the job's status to 'Started'
                                job.update_state('Started', session, status_key=status_key)
                                # Submit the job to the executor with retry parameters
                                future = executor.submit(run_job, job.key, status_key, tries, delay, backoff)
                                futures.add(future)
                    except AttributeError as ae:
                        logging.error(f"Attribute error: {ae}")

                if not futures:
                    # If no jobs are pending, wait before checking again
                    time.sleep(1)
                    continue

                # Wait for the first future to complete
                done, _ = concurrent.futures.wait(
                    futures, timeout=1, return_when=concurrent.futures.FIRST_COMPLETED
                )

                for future in done:
                    if future.exception() is not None:
                        logging.error(f"Job failed with exception: {future.exception()}")
                    futures.remove(future)
                time.sleep(0.5)

            # Wait for all running jobs to complete before exiting
            concurrent.futures.wait(
                futures, return_when=concurrent.futures.ALL_COMPLETED)
        except Exception as e:
            logging.error(f"Scheduler encountered an exception: {e}")
            sys.exit(1)

        finally:
            executor.shutdown(wait=True)

        logging.info("Scheduler shut down gracefully")
        sys.exit(0)
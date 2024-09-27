import sys
import signal
import time
import logging
import threading
from typing import Iterator
import concurrent.futures
from mytool.db.session_manager import get_session
from mytool.db.models import Job
from mytool.scheduler.job_runner import run_job

def get_jobs(session) -> Iterator[Job]:
    """
    Yields each job in the job table regardless of status.
    """
    jobs = session.query(Job).all()  # Fetch all jobs from the database
    for job in jobs:
        logging.info(f"Fetched {job}")
        yield job  # Yield each job to the caller

def scheduler_run(max_concurrent_jobs: int, status_key: str, ready_val: str, tries: int, delay: float, backoff: float):
    """
    Runs the scheduler to execute jobs concurrently based on the specified status column.
    
    Parameters:
    - max_concurrent_jobs: Maximum number of jobs to run concurrently
    - status_key: The column used to track job status (e.g., 'state')
    - ready_val: The value of the status that indicates a job is ready to run (e.g., 'Pending')
    - tries: Number of retries for failed jobs
    - delay: Initial delay between retries
    - backoff: Backoff multiplier for retry delays
    """
    logging.info("Starting scheduler...")
    logging.info(f"Max concurrent jobs: {max_concurrent_jobs}, Status key: '{status_key}', Ready value: '{ready_val}'")
    logging.info(f"Retry configuration - Tries: {tries}, Delay: {delay}, Backoff: {backoff}")

    # Create a ThreadPoolExecutor to manage concurrent job execution
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_jobs) as executor:
        interrupted = threading.Event()  # Event to detect interruptions (SIGINT/SIGTERM)

        def signal_handler(signum, frame):
            """
            Signal handler to gracefully shut down the scheduler when an interrupt signal is received.
            """
            logging.info("Received interrupt signal, shutting down gracefully...")
            interrupted.set()  # Set the interruption flag
            executor.shutdown(wait=False)  # Stop accepting new jobs, but let the current jobs finish

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)  # Handle Ctrl+C (SIGINT)
        signal.signal(signal.SIGTERM, signal_handler)  # Handle termination signals (SIGTERM)

        try:
            while not interrupted.is_set():  # Continue running until an interrupt is received
                futures = set()  # Set to store the futures representing running jobs
                with get_session() as session:  # Get a new session from the session manager
                    try:
                        # Fetch all jobs from the database
                        for job in get_jobs(session):
                            # Check if the job is ready to run based on status_key and ready_val
                            current_status = getattr(job, status_key, None)
                            if current_status == ready_val:
                                # Update the job's status to 'Started'
                                job.update_state('Started', session, status_key=status_key)
                                # Submit the job to the executor with retry parameters
                                future = executor.submit(run_job, job.key, status_key, tries, delay, backoff)
                                futures.add(future)  # Add the future to the set
                    except AttributeError as ae:
                        logging.error(f"Attribute error: {ae}")

                # If no jobs are pending, wait for a while before checking again
                if not futures:
                    time.sleep(5)  # Sleep for 5 seconds before checking for new jobs
                    continue  # Continue to the next iteration

                # Wait for the first future to complete
                done, _ = concurrent.futures.wait(
                    futures, timeout=1, return_when=concurrent.futures.ALL_COMPLETED
                )

                for future in done:  # Process each completed job
                    if future.exception() is not None:  # If there was an exception during job execution
                        logging.error(f"Job failed with exception: {future.exception()}")
                time.sleep(0.5)  # Sleep briefly before the next iteration

        except Exception as e:
            # Log any exception that happens within the scheduler
            logging.error(f"Scheduler encountered an exception: {e}")
            sys.exit(1)  # Exit the program with a non-zero status code

        finally:
            # Ensure all running jobs are completed before shutting down
            executor.shutdown(wait=True)

        logging.info("Scheduler shut down gracefully")  # Final log message after shutdown

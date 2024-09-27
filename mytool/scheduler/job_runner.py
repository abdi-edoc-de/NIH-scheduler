import time
import logging
from mytool.db.session_manager import get_session
from mytool.db.models import Job


def arbitrary_job(**kwargs):
    """
    Placeholder for an arbitrary job function that simulates some IO- or CPU-bound work.
    In this example, it simulates the job execution by sleeping for 5 seconds.
    
    Parameters:
    - kwargs: A dictionary of keyword arguments. The 'key' is used to log the job's unique identifier.
    """
    job_key = kwargs.get('key')  # Retrieve the job's key from the passed arguments
    logging.info(f"Job {job_key}: Starting arbitrary_job")
    time.sleep(5)  # Simulate a time-consuming IO-bound operation (e.g., downloading data)
    logging.info(f"Job {job_key}: Finished arbitrary_job")


def run_job(job_key: int, status_key: str, tries: int, delay: float, backoff: float):
    """
    Executes a job from the database identified by its key, with retry logic if the job fails.
    
    Parameters:
    - job_key: The unique key identifying the job in the database.
    - status_key: The status column name used to track the job's progress (e.g., 'state').
    - tries: The maximum number of retry attempts if the job fails.
    - delay: The initial delay between retry attempts, in seconds.
    - backoff: The multiplier to increase the delay between retries (exponential backoff).
    """
    attempt = 1  # Start with the first attempt
    current_delay = delay  # Set the initial delay

    # Continue trying until the job succeeds or the maximum number of retries is reached
    while attempt <= tries:
        try:
            with get_session() as session:  # Open a session using the context manager
                # Simulate an exception during the first attempt for testing purposes
                if attempt == 1:
                    raise Exception("Test exception")
                
                # Fetch the job from the database using the provided job_key
                job = session.query(Job).get(job_key)
                if job is None:
                    logging.warning(f"Job {job_key} not found")  # Log if the job is not found
                    return
                
                logging.info(f"Running {job}")
                
                # Simulate the job's actual execution using the arbitrary_job function
                arbitrary_job(key=job.key)
                
                # Update the job status to 'Done' once execution is completed
                job.update_state('Done', session, status_key=status_key)
            
            # Exit the loop if the job completes successfully
            break

        except Exception as e:
            # If this is the last attempt, log the failure and stop retrying
            if attempt == tries:
                logging.error(f"Job {job_key} failed after {tries} attempts with exception: {e}")
                
            # Log the failure and retry after a delay
            logging.warning(f"Job {job_key} failed on attempt {attempt} with exception: {e}. Retrying in {current_delay} seconds...")
            time.sleep(current_delay)  # Wait for the specified delay before retrying
            current_delay *= backoff  # Increase the delay using exponential backoff
            attempt += 1  # Increment the attempt counter

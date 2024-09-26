"""
`scheduler` is a module that executes a number of expensive jobs concurrently,
based on a queue represented by a database table that contains entries with
"state" fields that say when they are ready for execution.

| key | state   | arbitrary config fields ... |
|:---:|:-------:|:----------------------------|
| 001 |  Done   | ... |
| 002 |  Done   | ... |
| 003 | Started | ... |
| 004 | Pending | ... |
| 005 | Pending | ... |
| ... |   ...   | ... |

A machine that's set up to pull jobs from the schedule will use the following
command, for example, to invoke the scheduler:

```sh
scheduler --status-key state --ready-val Pending --max-concurrent-jobs 5
```

You may add additional arguments if they are needed. For the purposes of the
exercise, the actual job the scheduler is running is hard-coded into the
module. You can use the `arbitrary_job` function as a stand-in for it. The
timer delay in the function represents the io bound nature of the job. Set it
to whatever is most useful for testing.

Some additional requirements / considerations:

*   The scheduler must gracefully shut down when the calling process receives
    an interrupt signal.
*   The scheduler must gracefully resolve race conditions if multiple instances
    are running. A job must not be run in more than one instance.

Some bonus questions:

*   How would you optimize the `get_jobs` function?
*   Are there tools that you would use instead of writing this script to manage
    the job scheduling? How would the entire solution change to adopt them?
*   What would you do differently if the job was CPU-bound rather than
    IO-bound? Particularly since Python is not a parallel language (i.e. GIL).
*   How should someone deploying a scheduler-powered job determine their value
    for `--max-concurrent-jobs`?

"""

import argparse
import time
import sys
import threading
import signal
import concurrent.futures
import logging

from typing import Iterator

from sqlalchemy import create_engine, Column, Integer, String, inspect
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed logs
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# SQLAlchemy setup
engine = create_engine('sqlite:///jobs_orm.db', echo=False)  # Set echo=True for SQL debugging
Base = declarative_base()  # Corrected import to sqlalchemy.orm.declarative_base
SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)


class Job(Base):
    __tablename__ = 'jobs'

    key = Column(Integer, primary_key=True)
    state = Column(String)


    def __init__(self, **kwargs):
        """
        Initialize the Job with dynamic status_key.
        """
        for column in self.__table__.columns.keys():
            if column in kwargs:
                setattr(self, column, kwargs[column])

    def update_state(self, new_state: str, session, status_key: str = 'state'):
        """
        Update the state or any specified status column.
        """
        if not hasattr(self, status_key):
            raise AttributeError(f"Job has no attribute '{status_key}'")
        setattr(self, status_key, new_state)
        logging.info(f"Job {self.key}: '{status_key}' updated to '{new_state}'")
        session.commit()

    def __str__(self):
        """
        Provide a comprehensive string representation of the Job instance.
        """
        attrs = {column.name: getattr(self, column.name) for column in self.__table__.columns}
        return f"Job({attrs})"


@contextmanager
def get_session():
    """
    Context manager for SQLAlchemy sessions to ensure proper resource management.
    """
    session = Session()
    try:
        yield session
    finally:
        session.close()


def arbitrary_job(**kwargs):
    """
    This is a placeholder for arbitrary, IO- or CPU-bound jobs run using
    subprocess, etc.

    It takes arguments derived from a subset of database columns.

    State is updated as a side effect of the process
    """

    job_key = kwargs.get('key')
    logging.info(f"Job {job_key}: Starting arbitrary_job")
    time.sleep(5)  # Simulate an IO-bound operation
    logging.info(f"Job {job_key}: Finished arbitrary_job")


def init_db(status_key: str):
    """
    Initializes the database and populates it with sample jobs if empty.
    Sets the status based on the provided status_key.
    """
    Base.metadata.create_all(engine)
    with get_session() as session:
        count = session.query(Job).count()
        if count == 0:
            sample_jobs = []
            # Create 5 pending jobs
            for _ in range(5):
                job = Job()
                setattr(job, status_key, 'Pending')
                sample_jobs.append(job)

            # Create a 'Done' job
            job_done = Job()
            setattr(job_done, status_key, 'Done')
            sample_jobs.append(job_done)

            # Create a 'Started' job
            job_started = Job()
            setattr(job_started, status_key, 'Started')
            sample_jobs.append(job_started)

            session.add_all(sample_jobs)
            session.commit()
            logging.info("Initialized the database with sample jobs.")

            # Print all jobs
            jobs = session.query(Job).all()
            for job in jobs:
                logging.info(f"{job} --- created")
        else:
            logging.info("Database already initialized with existing jobs.")


def get_jobs(session) -> Iterator[Job]:
    """
    Yields each job in the job table, regardless of status, in order.
    """
    jobs = session.query(Job).all()
    for job in jobs:
        logging.info(f"Fetched {job}")
        yield job


def run_job(job_key: int, status_key: str):
    """
    Executes a job and updates its status to 'Done'.
    """
    with get_session() as session:
        try:
            job = session.query(Job).get(job_key)
            if job is None:
                logging.warning(f"Job {job_key} not found")
                return
            logging.info(f"Running {job}")
            # Simulate the job execution
            arbitrary_job(key=job.key)
            job.update_state('Done', session, status_key=status_key)
        except Exception as e:
            logging.error(f"Job {job_key} failed with exception: {e}")


def scheduler_run(max_concurrent_jobs: int, status_key: str, ready_val: str):
    """
    Runs the scheduler to execute jobs concurrently based on the specified status column.
    """
    logging.info("Starting scheduler...")
    logging.info(f"Max concurrent jobs: {max_concurrent_jobs}, Status key: '{status_key}', Ready value: '{ready_val}'")

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
                                # Submit the job to the executor
                                future = executor.submit(run_job, job.key, status_key)
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


def main():
    """
    The main function starts the scheduler with arguments.

    The basic structure here, parsing arguments, and running `scheduler_run`
    can be modified as you will. `max_concurrent_jobs`, `status_key`, and
    `ready_val` are required arguments. You can add others if you think they're
    needed.

    `scheduler_run` is a placeholder for what you will implement. A scheduler
    must fetch the pending jobs and add them for execution.

    It can be a single function as shown below, or you can initialize an object
    here, then have it start running the scheduler.
    """
    parser = argparse.ArgumentParser(description="Job Scheduler")
    parser.add_argument(
        "--max-concurrent-jobs",
        type=int,
        default=2,
        help="Maximum number of concurrent jobs (default: 2)"
    )
    parser.add_argument(
        "--status-key",
        type=str,
        default="state",
        help="Column name to use for job status (e.g., 'state', 'status') (default: 'state')"
    )
    parser.add_argument(
        "--ready-val",
        type=str,
        default="Pending",
        help="Value indicating a job is ready to run (default: 'Pending')"
    )

    args = parser.parse_args()
    max_concurrent_jobs = args.max_concurrent_jobs
    status_key = args.status_key
    ready_val = args.ready_val

    # initializing the DB with status key
    init_db(status_key)

    # Ensure the specified status_key exists in the 'jobs' table
    inspector = inspect(engine)
    columns = [column['name'] for column in inspector.get_columns('jobs')]
    if status_key not in columns:
        logging.error(f"Error: The status key '{status_key}' is not a valid column in the 'jobs' table.")
        sys.exit(1)
    else:
        logging.info(f"Using status key '{status_key}' for job scheduling.")

    try:
        scheduler_run(max_concurrent_jobs, status_key, ready_val)
        with get_session() as session:
            jobs = session.query(Job).all()
            for job in jobs:
                logging.info(f"{job} last")
    except Exception as e:
        logging.error(f"Main encountered an exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

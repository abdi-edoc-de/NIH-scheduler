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
import sqlite3
import concurrent.futures

from typing import Iterator

# region API


def arbitrary_job(**kwargs):
    """
    This is a placeholder for arbitrary, IO- or CPU-bound jobs run using
    subprocess, etc.

    It takes arguments derived from a subset of database columns.

    State is updated as a side effect of the process
    """
    job_key = kwargs.get('key')
    print(f"Job {job_key}: Starting arbitrary_job")
    time.sleep(5)  # Simulate an IO-bound operation
    print(f"Job {job_key}: Finished arbitrary_job")


def init_db():
    conn = sqlite3.connect('jobs.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            key INTEGER PRIMARY KEY,
            state TEXT
        )
    """)
    # Insert sample data if the table is empty
    cursor.execute("SELECT COUNT(*) FROM jobs")
    count = cursor.fetchone()[0]
    if count == 0:
        sample_jobs = [
            ('Pending',),
            ('Pending',),
            ('Pending',),
            ('Pending',),
            ('Pending',),
            ('Started',)
        ]
        cursor.executemany(
            "INSERT INTO jobs (state) VALUES ( ? )", sample_jobs
        )
    conn.commit()
    cursor.execute("SELECT * FROM jobs")
    # Display all jobs for verification

    for row in cursor.fetchall():
        print(dict(row), '--- created')
    conn.close()


class Job(dict):
    """
    A job object is a dict wrapping the table entry. Local state is
    fetched when the object is instantiated (not lazily synced).
    Setting keys on the dict will update the value in the dictionary.
    """

    def __init__(self, row, status_key='state'):
        super().__init__(row)
        self.key = self['key']
        self.status_key = status_key

    def update_state(self, new_state, conn):
        """
        Updates the job's state in both the object and the database.
        """
        self[self.status_key] = new_state
        print("key: ", self.key, "state: ", new_state, '--- updated')
        with conn:
            conn.execute(
                f"UPDATE jobs SET {self.status_key} = ? WHERE key = ?",
                (new_state, self.key)
            )

    def __str_(self):
        return str(self)



def get_jobs(conn, status_key) -> Iterator[Job]:
    """
    Yields each job in the job table, regardless of status, in order.

    Retrieves all jobs from the database.
    
    :param conn: SQLite database connection.
    :param status_key: Column name to filter jobs.
    :return: Iterator of Job objects.
    """
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM jobs ")
    rows = cursor.fetchall()

    for row in rows:
        job = Job(row, status_key=status_key)
        yield job


def run_job(job):
    """
    Executes the arbitrary job and updates its state to 'Done'.
    
    :param job: Job object to execute.
    """
    
    print(f"Running job {job['key']} state: {job['state']}")
    conn = sqlite3.connect('jobs.db')
    conn.row_factory = sqlite3.Row
    try:
        job.update_state('Done', conn)
        conn.close()
    except Exception as e:
        print(f"Job {job['key']} failed with exception: {e}")
        # job.update_status('Pending', conn)


def scheduler_run(max_concurrent_jobs, status_key, ready_val):
    """
    Runs the scheduler with given parameters.

    :param max_concurrent_jobs: The number of jobs to run concurrently.
    :param status_key: The column name in the jobs table to check for job status.
    :param ready_val: The value of the `status_key` column indicating a job is ready to run.
    """

    print("Starting scheduler...")
    print( 'max_concurrent_jobs:', max_concurrent_jobs, 'status_key:', status_key, 'ready_val:', ready_val)

    # Connect to the SQLite database
    conn = sqlite3.connect('jobs.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Lock to prevent race conditions during database operations
    db_lock = threading.Lock()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_jobs) as executor:
        futures = set()
        interrupted = threading.Event()

        def signal_handler(signum, frame):

            """
            Handles interrupt signals to gracefully shut down the scheduler.

            :param signum: Signal number.
            :param frame: Signal frame.
            """

            print("Received interrupt signal, shutting down gracefully...")
            interrupted.set()
            executor.shutdown(wait=False)

            print("Received interrupt signal, shutting down gracefully...")
            interrupted.set()
            executor.shutdown(wait=False)

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            while not interrupted.is_set():
                # Fetch jobs 
                with db_lock:
                    for job in get_jobs(conn, status_key):
                        if job[status_key] != ready_val:
                            continue # Skip jobs not ready to run
                        job.update_state('Started', conn)
                        future = executor.submit(run_job, job)
                        futures.add(future)
                    # Wait for any job to complete
                    done, futures = concurrent.futures.wait(
                        futures, timeout=1, return_when=concurrent.futures.FIRST_COMPLETED
                    )

                    # Handle any exceptions from completed jobs
                    for future in futures:
                        if future.exception() is not None:
                            print(
                                f"Job {future.result().key} failed with exception: {future.exception()}")
                            
                    time.sleep(0.5) # Short delay before next iteration

            # Wait for all running jobs to complete before exiting
            concurrent.futures.wait(
                futures, return_when=concurrent.futures.ALL_COMPLETED)

        except Exception as e:
            print(e)
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
    init_db()
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-concurrent-jobs", action="store", type=int)
    parser.add_argument("--status-key", action="store",
                        type=str, default="state")
    parser.add_argument("--ready-val", action="store",
                        type=str, default="Pending")

    args = parser.parse_args()
    max_concurrent_jobs = args.max_concurrent_jobs
    status_key = args.status_key
    ready_val = args.ready_val

    try:
        # Initialize database connection
        conn = sqlite3.connect('jobs.db')
        conn.row_factory = sqlite3.Row
        
        # Start the scheduler
        scheduler_run(max_concurrent_jobs, status_key, ready_val)

        # Display final job states after scheduler finishes
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs")
        rows = cursor.fetchall()
        for job in rows:
            print(dict(job), 'latest job state')

    except Exception as e:
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()

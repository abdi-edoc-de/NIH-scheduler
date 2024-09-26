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
    # if count == 1:
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
        self[self.status_key] = new_state
        print(self.key, new_state)
        with conn:
            conn.execute(
                f"UPDATE jobs SET {self.status_key} = ? WHERE key = ?",
                (new_state, self.key)
            )

    def __str_(self):
        return str(self)

    def refresh(self):
        self.conn = sqlite3.connect('jobs.db')
        self.conn.row_factory = sqlite3.Row

    def close(self):
        self.conn.close()


def get_jobs(conn, status_key, ready_val) -> Iterator[Job]:
    """
    Yields each job in the job table, regardless of status, in order.
    """
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM jobs WHERE {status_key} = ?", (ready_val,))
    rows = cursor.fetchall()

    for row in rows:
        job = Job(row, status_key=status_key)
        # print(job)
        # if job[status_key] == ready_val:
        print(job)
        yield job


def run_job(job):
    # print(f"Running job {job['key']}")
    print(job)
    job.refresh()
    conn = sqlite3.connect('jobs.db')
    conn.row_factory = sqlite3.Row
    try:
        job.update_state('Done', conn)
        conn.close()
    except Exception as e:
        print(f"Job {job['key']} failed with exception: {e}")
        # job.update_status('Pending', conn)


def scheduler_run(max_concurrent_jobs, status_key, ready_val):
    print("Starting scheduler...")
    print(max_concurrent_jobs, status_key, ready_val)
    # Connect to the SQLite database
    conn = sqlite3.connect('jobs.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Lock for database operations
    db_lock = threading.Lock()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_jobs) as executor:
        futures = set()
        interrupted = threading.Event()

        def signal_handler(signum, frame):
            print("Received interrupt signal, shutting down gracefully...")
            interrupted.set()
            executor.shutdown(wait=False)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            while not interrupted.is_set():
                # Fetch jobs ready to run
                with db_lock:
                    for job in get_jobs(conn, status_key, ready_val):
                        job.update_state('Started', conn)
                        future = executor.submit(run_job, job)
                        futures.add(future)
                    done, futures = concurrent.futures.wait(
                        futures, timeout=1, return_when=concurrent.futures.FIRST_COMPLETED
                    )

                    for future in futures:
                        if future.exception() is not None:
                            print(
                                f"Job {future.result().key} failed with exception: {future.exception()}")
                    time.sleep(0.5)
            concurrent.futures.wait(
                futures, return_when=concurrent.futures.ALL_COMPLETED)

        except Exception as e:
            print(e)
            sys.exit(1)


def main():
    """
    The main function starts the scheduler with arguments.
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
        conn = sqlite3.connect('jobs.db')
        conn.row_factory = sqlite3.Row
        jobs = []

        scheduler_run(max_concurrent_jobs, status_key, ready_val)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs")
        rows = cursor.fetchall()
        for job in rows:
            print(dict(job), 'last')

    except Exception as e:
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()

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
import logging
from mytool.db.models import init_db, is_valid_column, Job
from mytool.db.session_manager import get_session
from mytool.utils.logger import configure_logging
from mytool.scheduler.scheduler import scheduler_run
import sys

def main():
    """
    The main function starts the job scheduler with command-line arguments.
    This function is the entry point of the program, where database initialization,
    argument parsing, validation, and scheduler execution take place.
    """
    # Configure the logging for the application
    configure_logging()

    # Create an ArgumentParser object to handle command-line arguments
    parser = argparse.ArgumentParser(description="Job Scheduler")

    # Add arguments for configuring the scheduler's behavior
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
    parser.add_argument(
        "--tries",
        type=int,
        default=3,
        help="Number of retry attempts for failed jobs (default: 3)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Initial delay between retries in seconds (default: 2.0)"
    )
    parser.add_argument(
        "--backoff",
        type=float,
        default=2.0,
        help="Backoff multiplier for retry delays (default: 2.0)"
    )

    # Parse the arguments provided via the command line
    args = parser.parse_args()
    
    # Assign the parsed argument values to variables for later use
    max_concurrent_jobs = args.max_concurrent_jobs
    status_key = args.status_key
    ready_val = args.ready_val
    tries = args.tries
    delay = args.delay
    backoff = args.backoff
    
    # Initialize the database with sample jobs if it is empty,
    # and use the provided status_key to track the job status.
    init_db(status_key)

    # Validate that the provided status_key is a valid column in the Job model
    if is_valid_column(status_key):
        logging.error(f"Error: The status key '{status_key}' is not a valid column in the 'jobs' table.")
        sys.exit(1)  # Exit if the column is invalid
    else:
        logging.info(f"Using status key '{status_key}' for job scheduling.")

    # Log the retry configuration details
    logging.info(f"Retry configuration - Tries: {tries}, Delay: {delay}, Backoff: {backoff}")

    try:
        # Run the scheduler with the provided arguments to process jobs concurrently
        scheduler_run(max_concurrent_jobs, status_key, ready_val, tries, delay, backoff)
        print("Scheduler finished running.")

        # After the scheduler has completed, retrieve and log the latest job states
        with get_session() as session:
            jobs = session.query(Job).all()
            for job in jobs:
                logging.info(f"{job} --- latest job state")
    
    # Catch any exceptions that occur during the scheduler execution
    except Exception as e:
        logging.error(f"Main encountered an exception: {e}")
        sys.exit(1)  # Exit the program with an error code


if __name__ == "__main__":
    # Entry point of the script, which calls the main function
    main()

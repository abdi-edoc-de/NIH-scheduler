
# Installation Guide for NIH Scheduler

This guide walks you through installing the **NIH Scheduler** tool from the [GitHub repository](https://github.com/abdi-edoc-de/NIH-scheduler.git) into a Python virtual environment.

## Prerequisites

Before you begin, make sure you have:

- Python 3.6 or higher installed on your system.
- `pip` (Python package installer) available.

## Step-by-Step Instructions

### 1. Create a Virtual Environment

First, you'll want to create a virtual environment to isolate the installation. A virtual environment allows you to keep project dependencies separate from the system-wide packages.

To create a virtual environment:

#### On MacOS/Linux

```bash
# Navigate to your project directory
cd /path/to/your/project

# Create a virtual environment called 'venv'
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

#### On Windows

```bash
# Navigate to your project directory
cd \path\to\your\project

# Create a virtual environment called 'venv'
python -m venv venv

# Activate the virtual environment
venv\Scripts\activate
```

Once the environment is activated, your terminal prompt will show `(venv)` to indicate that you're inside the virtual environment.

### 2. Install NIH Scheduler from GitHub

With your virtual environment activated, run the following command to install the **NIH Scheduler** directly from the GitHub repository:

```bash
pip3 install git+https://github.com/abdi-edoc-de/NIH-scheduler.git
```

This command pulls the latest code from the GitHub repository and installs it into your virtual environment.

### 3. Verify the Installation

After the installation completes, you can verify that the tool was installed correctly by checking the `nih_scheduler` command. Run the following:

```bash
nih_scheduler --help
```

If the installation was successful, this should display a help menu with the available command-line options for the scheduler.

### Example Output

```bash
Usage: nih_scheduler [OPTIONS]

Options:
  --max-concurrent-jobs INTEGER  Maximum number of concurrent jobs.
  --status-key TEXT              Column name to use for job status.
  --ready-val TEXT               Value indicating a job is ready to run.
  --tries INTEGER                Number of retry attempts for failed jobs.
  --delay FLOAT                  Initial delay between retries.
  --backoff FLOAT                Backoff multiplier for retry delays.
  --help                         Show this message and exit.
```

### 4. Running the Scheduler

Once installed, you can now use the `nih_scheduler` command to schedule and execute jobs. Here’s an example:

```bash
nih_scheduler --status-key state --ready-val Pending --max-concurrent-jobs 5 --tries 3 --delay 2.0 --backoff 2.0
```

This will:

- Use the `state` column to check the job's status.
- Run jobs with a `Pending` status.
- Allow a maximum of 5 concurrent jobs.
- Retry failed jobs 3 times, with an initial delay of 2 seconds between retries, using a backoff multiplier of 2.

## Deactivating the Virtual Environment

Once you're done, you can deactivate the virtual environment by running:

```bash
deactivate
```

This will return you to your system's default Python environment.

---

## Troubleshooting

If you encounter any issues, try the following:

1. **Make sure the virtual environment is activated** before running the `nih_scheduler` command.
2. **Check for typos** in the command, especially in the GitHub URL or while creating/activating the virtual environment.
3. **Ensure Python 3.6 or above is installed** by running `python3 --version` or `python --version` (depending on your OS).

---

# Bonus Questions

---

## 1, Optimizing the `get_jobs` Function

### 1. Filter Directly in the Query

- **Benefit:** Reduces data fetched from the database.
- **Implementation:**

    ```python
    def get_jobs(session, status_key, ready_val, batch_size=100):
        return session.query(Job).filter(getattr(Job, status_key) == ready_val).yield_per(batch_size)
    ```

### 2. Use Batching with `yield_per`

- **Benefit:** Lowers memory usage by processing jobs in chunks.
- **Implementation:**

    ```python
    for job in get_jobs(session, 'state', 'Pending', batch_size=100):
        process_job(job)
    ```

### 3. Index Relevant Columns

- **Benefit:** Speeds up query filtering.
- **Implementation:**

    ```python
    class Job(Base):
        __tablename__ = 'jobs'
        key = Column(Integer, primary_key=True)
        state = Column(String, index=True)
        # ...
    ```

### 4. Select Only Necessary Columns

- **Benefit:** Minimizes data transfer and processing overhead.
- **Implementation:**

    ```python
    def get_jobs(session, status_key, ready_val, columns=None, batch_size=100):
        if columns:
            query = session.query(*[getattr(Job, col) for col in columns]).filter(getattr(Job, status_key) == ready_val).yield_per(batch_size)
        else:
            query = session.query(Job).filter(getattr(Job, status_key) == ready_val).yield_per(batch_size)
        for job in query:
            yield job
    ```

### 5. Implement Asynchronous Retrieval (If Applicable)

- **Benefit:** Enhances concurrency for IO-bound operations.
- **Implementation:**

    ```python
    async def get_jobs_async(session, status_key, ready_val, batch_size=100):
        stmt = select(Job).where(getattr(Job, status_key) == ready_val).limit(batch_size)
        result = await session.execute(stmt)
        for job in result.scalars():
            yield job
    ```

---

## 2. Are there tools that you would use instead of writing this script to manage the job scheduling? How would the entire solution change to adopt them?

When building applications that require task scheduling or asynchronous job processing, we can leverage the following tools to manage and schedule jobs efficiently. These tools provide out-of-the-box features like scalability, retries, monitoring, and fault tolerance, making them a great choice over custom job scheduling scripts.

### 1. Celery

- **What it is:** A distributed task queue for running jobs asynchronously across multiple workers.
- **Benefits:** Scalability, built-in retries, task scheduling, result storage, and task monitoring (with Flower).

**Changes to the Solution:**

- Define tasks using Celery's task decorator.

```python
from celery import Celery

app = Celery('tasks', broker='redis://localhost:6379/0')

@app.task
def execute_job(job_id):
    # Job logic
    print(f"Executing job {job_id}")
```

- Jobs are scheduled and executed asynchronously using `delay()`.

```python
execute_job.delay(job_id)
```

- Run Celery workers to handle task execution.

```bash
celery -A tasks worker --loglevel=info
```

- Monitoring is done via the Flower dashboard for Celery.

### 2. RQ (Redis Queue)

- **What it is:** A simple job queue using Redis to queue tasks.
- **Benefits:** Easy to set up, lightweight, ideal for smaller applications.

**Changes to the Solution:**

- Queue jobs in Redis using RQ.

```python
from rq import Queue
from redis import Redis

redis_conn = Redis()
q = Queue(connection=redis_conn)

def execute_job(job_id):
    print(f"Executing job {job_id}")

q.enqueue(execute_job, job_id)
```

- Run RQ workers to process jobs.

```bash
rq worker
```

- RQ includes a simple dashboard for monitoring task status.

### 3. APScheduler

- **What it is:** A lightweight in-process scheduler that allows scheduling jobs at intervals, cron schedules, or specific times.
- **Benefits:** Simple and flexible scheduling with minimal setup.

**Changes to the Solution:**

- Schedule jobs using intervals or cron-like expressions.

  ```python
  from apscheduler.schedulers.background import BackgroundScheduler

  scheduler = BackgroundScheduler()

  def execute_job(job_id):
      print(f"Executing job {job_id}")

  scheduler.add_job(execute_job, 'interval', minutes=5, args=[job_id])
  scheduler.start()
  ```

- Jobs can be persisted in a database for robustness if needed.

### 4. Airflow

- **What it is:** A workflow automation platform for managing complex workflows with dependencies.
- **Benefits:** Supports DAGs (Directed Acyclic Graphs) for workflows, has a web UI for monitoring, and supports retries.

**Changes to the Solution:**

- Define workflows as DAGs.

  ```python
  from airflow import DAG
  from airflow.operators.python_operator import PythonOperator
  from datetime import datetime

  def execute_job(**kwargs):
      job_id = kwargs['job_id']
      print(f"Executing job {job_id}")

  default_args = {
      'start_date': datetime(2023, 1, 1),
  }

  dag = DAG('job_scheduler', default_args=default_args, schedule_interval='@daily')

  task = PythonOperator(
      task_id='execute_job',
      python_callable=execute_job,
      op_kwargs={'job_id': 123},
      dag=dag,
  )
  ```

- Use Airflow’s web interface for monitoring tasks and workflows.
- Run Airflow workers for distributed execution.

### Conclusion

Using these tools simplifies job scheduling and execution, offering features like:

- **Scalability:** Distributed execution across workers or containers.
- **Retries and Fault Tolerance:** Automatic retries, error handling, and fault tolerance.
- **Monitoring:** Real-time monitoring via dashboards like Flower (for Celery), RQ dashboard, or Airflow UI.
- **Asynchronous Execution:** Jobs are processed in the background, improving application performance.

By adopting these tools, you reduce the need for custom scheduling logic, and your solution becomes more robust, scalable, and maintainable.

---
 


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

After the installation completes, you can verify that the tool was installed correctly by checking the `scheduler` command. Run the following:

```bash
scheduler --help
```

If the installation was successful, this should display a help menu with the available command-line options for the scheduler.

### Example Output

```bash
Usage: scheduler [OPTIONS]

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

Once installed, you can now use the `scheduler` command to schedule and execute jobs. Here’s an example:

```bash
scheduler --status-key state --ready-val Pending --max-concurrent-jobs 5 --tries 3 --delay 2.0 --backoff 2.0
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

1. **Make sure the virtual environment is activated** before running the `scheduler` command.
2. **Check for typos** in the command, especially in the GitHub URL or while creating/activating the virtual environment.
3. **Ensure Python 3.6 or above is installed** by running `python3 --version` or `python --version` (depending on your OS).

---

# Bonus Questions

---

## 1. Optimizing the `get_jobs` Function

### 1.1 Filter Directly in the Query

- **Benefit:** Reduces data fetched from the database.
- **Implementation:**

    ```python
    def get_jobs(session, status_key, ready_val, batch_size=100):
        return session.query(Job).filter(getattr(Job, status_key) == ready_val).yield_per(batch_size)
    ```

### 1.2 Use Batching with `yield_per`

- **Benefit:** Lowers memory usage by processing jobs in chunks.
- **Implementation:**

    ```python
    for job in get_jobs(session, 'state', 'Pending', batch_size=100):
        process_job(job)
    ```

### 1.4 Index Relevant Columns

- **Benefit:** Speeds up query filtering.
- **Implementation:**

    ```python
    class Job(Base):
        __tablename__ = 'jobs'
        key = Column(Integer, primary_key=True)
        state = Column(String, index=True)
        # ...
    ```

### 1.5 Select Only Necessary Columns

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

### 1.6 Implement Asynchronous Retrieval (If Applicable)

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

Instead of writing our own script to handle job scheduling, we can use the following tools to manage and schedule jobs efficiently. These tools provide out-of-the-box features like scalability, retries, monitoring, and fault tolerance, making them a better choice than custom job scheduling scripts. If the problem is already solved, we shouldn't reinvent the wheel.

### 2.1 Celery

- **What it is:** A distributed task queue for running jobs asynchronously across multiple workers.
- **Benefits:** Scalability, built-in retries, task scheduling, result storage, and task monitoring.

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

### 2.2 RQ (Redis Queue)

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

### 2.3 APScheduler

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

### 2.4 Airflow

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

# 3. What would you do differently if the job was CPU-bound rather than IO-bound? Particularly since Python is not a parallel language (i.e. GIL)

If the job was CPU-bound rather than IO-bound, several adjustments would be needed to optimize performance, especially considering Python's Global Interpreter Lock (GIL), which limits true parallelism for CPU-bound tasks.

**Key Differences Between CPU-bound and IO-bound Jobs:**

- **CPU-bound jobs:** Tasks that require intensive computation, fully utilizing the CPU.
- **IO-bound jobs:** Tasks that spend time waiting for external inputs/outputs, like file I/O or network requests, where the CPU is idle during waits.

Since Python's GIL only allows one thread to execute Python bytecode at a time, multithreading doesn’t provide true parallelism for CPU-bound tasks. Therefore, for CPU-bound jobs, we need to bypass the GIL and utilize multiple CPU cores effectively.

## 3.1 Use `multiprocessing` Instead of `Threading`

- **Why:** Python’s **GIL** allows only one thread to execute at a time, limiting the effectiveness of multithreading for CPU-bound tasks. **Multiprocessing** spawns separate processes, each with its own Python interpreter and memory space, allowing true parallelism.

- **How:**
  - Use **`ProcessPoolExecutor`** or the **`multiprocessing`** module to run CPU-bound tasks in separate processes, taking full advantage of multiple CPU cores.
  
  ```python
  from concurrent.futures import ProcessPoolExecutor
  import os

  def cpu_bound_task(job_id):
      print(f"Job {job_id}: Performing CPU-intensive task")
      result = sum(i * i for i in range(10000000))  # Example of CPU-bound work
      print(f"Job {job_id}: Completed with result {result}")

  if __name__ == "__main__":
      with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
          for job_id in range(10):
              executor.submit(cpu_bound_task, job_id)
  ```

  - **Result:** Each process runs independently on its own CPU core, bypassing the GIL and allowing for efficient parallel execution of CPU-bound jobs.

## 3.2 Leverage C Libraries for Performance (Cython)

- **Why:** **Cython** is used to convert Python code to C, allowing you to optimize CPU-heavy parts of your application. Cython can bypass the GIL in performance-critical sections, allowing C-level speed for CPU-bound tasks.

- **How:**
  - Write performance-critical sections in Cython and compile them into C code. This reduces the overhead of Python's GIL for CPU-bound computations.

    **Example:**
    In a `.pyx` file (`cpu_bound_task.pyx`):

    ```cython
    def cpu_bound_task(int job_id):
        cdef int i, result = 0
        for i in range(100000000):
            result += i
        print(f"Job {job_id}: Finished computation, result = {result}")
    ```

    To compile the `.pyx` file, use:

    ```bash
    cythonize -i cpu_bound_task.pyx
    ```

    After compiling, you can call this function from Python and get the performance benefits of C code for CPU-bound tasks:

    ```python
    from cpu_bound_task import cpu_bound_task
    cpu_bound_task(1)
    ```

## 3.3 Offload to a Different Language (e.g., Go, Rust)

- **Why:** For tasks that are extremely CPU-intensive, you can offload computation-heavy parts of your application to languages that don’t have a GIL, such as **Go** or **Rust**. These languages are designed for concurrency and parallelism, allowing better CPU usage.

- **How:** Implement the performance-critical sections of your application in Go or Rust, and interface with Python using:
  - **FFI (Foreign Function Interface):** Allows direct interaction with shared libraries written in C, Go, or Rust.
  - **Microservices architecture:** Write the CPU-intensive portions of the code in Go or Rust, expose them as services via REST or gRPC APIs, and call these services from your Python application.

## 3.4 Adjust `--max-concurrent-jobs` for CPU-bound Tasks

- **Why:** CPU-bound tasks consume significant processing power. Running too many CPU-bound jobs simultaneously can lead to CPU contention and performance degradation.

- **How:** Set the `--max-concurrent-jobs` parameter based on the number of CPU cores. Use `os.cpu_count()` to dynamically set the number of parallel jobs equal to the number of CPU cores:

    ```python
    import os
    max_concurrent_jobs = os.cpu_count()  # Set the number of jobs to match available CPU cores
    ```

  - **Result:** This ensures that each job runs on a separate core, maximizing CPU efficiency and avoiding performance bottlenecks.

## 3.5 Consider Using Alternative Python Implementations (e.g., PyPy)

- **Why:** Python’s **PyPy** is a Just-in-Time (JIT) compiled Python implementation that speeds up execution for CPU-bound tasks. PyPy may significantly outperform CPython for certain types of CPU-intensive tasks.

- **How:** Use **PyPy** to execute your CPU-bound tasks, allowing JIT compilation to optimize the performance:

    ```bash
    pypy script.py
    ```

## Conclusion

To handle CPU-bound tasks differently:

1. **Use `multiprocessing`** to bypass the GIL, utilizing multiple CPU cores for parallel processing.
2. **Leverage Cython** to convert CPU-heavy sections of code to C for better performance.
3. **Offload CPU-heavy tasks** to efficient, concurrency-friendly languages like Go or Rust.
4. **Adjust `--max-concurrent-jobs`** based on available CPU cores to avoid contention and optimize CPU usage.
5. **Consider PyPy** for its JIT compilation, which can offer a significant speed boost for CPU-bound tasks.

---

# 4. How should someone deploying a scheduler-powered job determine their value for `--max-concurrent-jobs`?

When deploying a scheduler-powered job, determining the value for `--max-concurrent-jobs` requires consideration of several factors such as job type (CPU-bound or IO-bound), system resources, and performance requirements. Here's how to approach it:

### 4.1 **Understand the Job Type**

- **CPU-bound jobs:** These tasks use a significant amount of CPU resources. Running too many concurrent jobs can cause CPU contention, which will reduce performance.
  - **Recommendation:** Set the number of concurrent jobs to the number of CPU cores.
  - Example:

       ```python
       max_concurrent_jobs = os.cpu_count()  # Matches the number of CPU cores
       ```

- **IO-bound jobs:** These tasks spend much of their time waiting for input/output operations (e.g., network requests, file I/O). In this case, you can run more jobs concurrently, as they aren't bottlenecked by CPU availability.
  - **Recommendation:** Set the number of concurrent jobs to higher than the number of CPU cores (e.g., 2-5× the core count).
  - Example:

       ```python
       max_concurrent_jobs = os.cpu_count() * 5  # More jobs can run in parallel
       ```

### 4.2 **Consider System Resources**

- **CPU cores:** Use `os.cpu_count()` to determine the number of physical CPU cores, ensuring that CPU-bound tasks don’t exceed this number.
- **Memory (RAM):** Ensure that each job’s memory requirement doesn’t exceed the available system memory. Too many jobs using too much memory can cause system thrashing (swap usage).
  - **Recommendation:** Calculate the total available memory and the memory per job:

       ```python
       max_concurrent_jobs = total_system_memory / memory_per_job
       ```

### 4.3 **Test and Benchmark**

- **Start conservatively:** Begin with fewer concurrent jobs and gradually increase based on system performance and resource usage.
- **Monitor resource utilization:** Tools like `htop`, `top`, or cloud service monitoring tools can help you observe CPU, memory, and I/O usage during job execution.
- **Adjust accordingly:** Based on how the system performs, adjust `--max-concurrent-jobs`. If the system remains underutilized, you can safely increase the number of jobs. If the system becomes slow or overloaded, reduce the number.

### 4.4 **Factor in External Dependencies**

- **External APIs or databases:** If the jobs depend on external systems (e.g., APIs or databases), you should ensure that those systems can handle multiple concurrent requests without slowing down. If not, reduce the number of concurrent jobs accordingly to avoid overwhelming them.

### 4.5 **Dynamic Scaling**

- **Advanced Scaling:** In dynamic systems, you can adjust `--max-concurrent-jobs` based on real-time performance metrics. Using autoscaling techniques, you can increase or decrease the number of concurrent jobs based on the load on your system and external dependencies.

### 4.6 **Short-running vs Long-running Jobs**

- **Short-running jobs:** If your jobs are short in duration, you may be able to set a higher number of concurrent jobs to optimize throughput.
- **Long-running jobs:** Fewer concurrent jobs may be ideal for longer-running processes to prevent overloading the system for extended periods.

### Example Calculation

For a system with:

- 8 CPU cores
- 32 GB of RAM
- Each job uses 1 GB of RAM

You could set:

- **CPU-bound tasks:** `--max-concurrent-jobs=8`
- **IO-bound tasks:** `--max-concurrent-jobs=32` (assuming the system can handle it).

### Conclusion

To determine the value for `--max-concurrent-jobs`:

1. Identify whether the task is CPU-bound or IO-bound.
2. Evaluate the available system resources (CPU, memory).
3. Test and monitor system performance to fine-tune the number of jobs.
4. Factor in the capacity of any external systems the job interacts with.
5. Adjust dynamically based on system performance, if possible.

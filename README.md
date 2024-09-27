
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

#### On MacOS/Linux:

```bash
# Navigate to your project directory
cd /path/to/your/project

# Create a virtual environment called 'venv'
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

#### On Windows:

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

## Updating NIH Scheduler

If there are updates to the repository and you want to reinstall or update your existing installation, run:

```bash
pip3 install --upgrade git+https://github.com/abdi-edoc-de/NIH-scheduler.git
```

This will pull the latest changes from the repository and update the package in your virtual environment.

---

Let me know if you need further assistance or encounter any issues during the installation process!

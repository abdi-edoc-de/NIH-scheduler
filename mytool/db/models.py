import logging
from sqlalchemy import Column, Integer, String, inspect
from sqlalchemy.orm import declarative_base
from .session_manager import get_session, get_engine

# Define the base class for SQLAlchemy models
Base = declarative_base()

class Job(Base):
    """
    The Job class represents a job in the database. 
    Each job has a primary key 'key' and a 'state' to track the job's current status.
    """
    __tablename__ = 'jobs'

    key = Column(Integer, primary_key=True)  # Primary key for the job
    state = Column(String)  # Represents the current state of the job (e.g., Pending, Started, Done)

    def __init__(self, **kwargs):
        """
        Initialize the Job with dynamic attributes. 
        The attributes are initialized based on the passed kwargs.
        """
        for column in self.__table__.columns.keys():
            if column in kwargs:
                setattr(self, column, kwargs[column])

    def update_state(self, new_state: str, session, status_key: str = 'state'):
        """
        Update the state of the job or any other specified status_key column.
        
        Parameters:
        - new_state: The new state value to set.
        - session: The current SQLAlchemy session.
        - status_key: The column name that will be updated (defaults to 'state').
        """
        if not hasattr(self, status_key):
            raise AttributeError(f"Job has no attribute '{status_key}'")
        setattr(self, status_key, new_state)  # Update the status attribute with the new value
        session.commit()  # Commit the changes to the database

    def __str__(self):
        """
        Returns a string representation of the Job object, 
        showing all its attributes for easy logging and debugging.
        """
        attrs = {column.name: getattr(self, column.name) for column in self.__table__.columns}
        return f"Job({attrs})"


# Initialize the database with sample data if it is empty
def init_db(status_key: str):
    """
    Initializes the database and populates it with sample jobs if it's empty.
    The status of each job is set based on the provided status_key.
    
    Parameters:
    - status_key: The column that will store the job's status (e.g., 'state').
    """
    Base.metadata.create_all(get_engine())  # Create tables if they don't exist
    with get_session() as session:
        try:
            # Check if there are any jobs already in the database
            count = session.query(Job).count()
            if count == 0:
                # If no jobs, create some sample jobs
                sample_jobs = []
                # Create 5 'Pending' jobs
                for _ in range(5):
                    job = Job()
                    setattr(job, status_key, 'Pending')  # Set the status to 'Pending'
                    sample_jobs.append(job)

                # Create a 'Done' job
                job_done = Job()
                setattr(job_done, status_key, 'Done')  # Set the status to 'Done'
                sample_jobs.append(job_done)

                # Create a 'Started' job
                job_started = Job()
                setattr(job_started, status_key, 'Started')  # Set the status to 'Started'
                sample_jobs.append(job_started)

                session.add_all(sample_jobs)  # Add all jobs to the session
                session.commit()  # Commit the transaction to save the jobs to the database
                logging.info("Initialized the database with sample jobs.")

                # Log all created jobs for reference
                jobs = session.query(Job).all()
                for job in jobs:
                    logging.info(f"{job} --- created")
            else:
                logging.info("Database already initialized with existing jobs.")
        except Exception as e:
            logging.error(f"Error during database initialization: {e}")  # Log any errors during the initialization
        finally:
            session.close()  # Ensure the session is closed after use


def is_valid_column(column_name: str) -> bool:
    """
    Checks if the provided column name is a valid attribute of the Job class.
    
    Parameters:
    - column_name: The name of the column to check for validity.
    
    Returns:
    - True if the column exists in the jobs table, False otherwise.
    """
    inspector = inspect(get_engine())  # Get the database engine for inspection
    # Get the list of column names for the 'jobs' table and check if the column_name is present
    return column_name not in [column['name'] for column in inspector.get_columns('jobs')]

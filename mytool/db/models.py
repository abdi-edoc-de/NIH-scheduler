import logging
from sqlalchemy import  Column, Integer, String, inspect
from sqlalchemy.orm import declarative_base
from .session_manager import get_session, get_engine



Base = declarative_base()


class Job(Base):
    __tablename__ = 'jobs'

    key = Column(Integer, primary_key=True)
    state = Column(String)

    def __init__(self, **kwargs):
        
                
        for column in self.__table__.columns.keys():
            if column in kwargs:
                setattr(self, column, kwargs[column])

    def update_state(self, new_state: str, session, status_key: str = 'state'):
        if not hasattr(self, status_key):
            raise AttributeError(f"Job has no attribute '{status_key}'")
        setattr(self, status_key, new_state)
        session.commit()

    def __str__(self):
        attrs = {column.name: getattr(self, column.name) for column in self.__table__.columns}
        return f"Job({attrs})"


# Initialize the database
def init_db(status_key: str):
    """
    Initializes the database and populates it with sample jobs if empty.
    Sets the status based on the provided status_key.
    """
    Base.metadata.create_all(get_engine())
    with get_session() as session:
        try:
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
        except Exception as e:
            logging.error(f"Error during database initialization: {e}")
        finally:
            session.close()


def is_valid_column(column_name: str) -> bool:
    """
    Checks if the provided column name is a valid attribute of the Job class.
    """
    inspector = inspect(get_engine())       
    return column_name not in [column['name'] for column in inspector.get_columns('jobs')]
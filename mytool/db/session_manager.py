# session_manager.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager

# SQLAlchemy engine and session setup
engine = create_engine('sqlite:///jobs_orm.db', echo=False)  # Set echo=True for SQL debugging
SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)

def get_engine():
    """
    Returns the SQLAlchemy engine.
    """
    return engine

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

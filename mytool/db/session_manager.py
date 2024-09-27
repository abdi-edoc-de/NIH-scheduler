from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# SQLAlchemy engine and session setup
# The engine is responsible for managing the connection to the SQLite database.
# 'sqlite:///jobs_orm.db' creates an SQLite database file named 'jobs_orm.db' in the current directory.
# Set echo=True to enable SQL statement logging, useful for debugging.
# Set echo=True for SQL debugging
engine = create_engine('sqlite:///jobs.db', echo=False)

# SessionFactory creates new SQLAlchemy sessions, which represent interactions with the database.
# sessionmaker is bound to the engine, meaning all sessions will use the specified database.
SessionFactory = sessionmaker(bind=engine)

# ScopedSession ensures thread-safe usage of the session in concurrent programs by providing
# one session per thread or context. This helps manage the lifecycle of sessions more efficiently.
Session = scoped_session(SessionFactory)


def get_engine():
    """
    Returns the SQLAlchemy engine.
    This is useful when other parts of the application need direct access to the engine,
    such as for metadata operations, schema creation, or for inspecting the database structure.
    """
    return engine


@contextmanager
def get_session():
    """
    Context manager for SQLAlchemy sessions to ensure proper resource management.

    The session is opened when the context is entered and closed automatically when the context is exited,
    ensuring no resources (like connections) are left open and helping to prevent memory leaks.

    Using this approach ensures that the session is properly closed even if an exception occurs.
    """
    session = Session()  # Create a new session
    try:
        yield session  # Yield the session for database operations
    finally:
        session.close()  # Ensure the session is closed after operations

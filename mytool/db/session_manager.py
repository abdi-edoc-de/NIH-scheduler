from contextlib import contextmanager
from .models import Session

@contextmanager
def get_session():
    session = Session()
    try:
        yield session
    finally:
        session.close()

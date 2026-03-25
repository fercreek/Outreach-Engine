"""SQLite database setup with SQLModel (async-ready)."""

from sqlmodel import SQLModel, create_engine, Session

from app.config import settings

# Use check_same_thread=False for FastAPI's async context
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False},
)


def create_db_and_tables() -> None:
    """Create all tables defined by SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency — yields a DB session per request."""
    with Session(engine) as session:
        yield session

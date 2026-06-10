from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base metadata registry for SQLAlchemy models and Alembic."""

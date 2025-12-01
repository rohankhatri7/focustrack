from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# base setup for ORM models
DB_PATH = Path(__file__).resolve().parent / "focus_track.db"
engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
Base = declarative_base()

def get_session():
    return SessionLocal()

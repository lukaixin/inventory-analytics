from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import DATABASE_URL
engine = create_engine(DATABASE_URL, pool_pre_ping=not DATABASE_URL.startswith("duckdb:"), connect_args={} if DATABASE_URL.startswith("duckdb:") else {"connect_timeout": 5})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

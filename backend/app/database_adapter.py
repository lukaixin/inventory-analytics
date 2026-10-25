"""Small dialect boundary: business services do not branch on storage engine."""
from __future__ import annotations
from contextlib import contextmanager
from threading import RLock
from sqlalchemy import select
from .config import DATABASE_URL
from .models import ImportBatch

_duck_write_lock=RLock()

@contextmanager
def write_lock(db):
    """Serialize every local DuckDB mutation before it opens a write transaction."""
    if DATABASE_URL.startswith("duckdb:"):
        with _duck_write_lock:
            db.rollback()  # discard a request's earlier read snapshot before the locked write
            yield
    else:
        yield

@contextmanager
def import_write_lock(db, batch_id):
    """DuckDB is a single local writer; PostgreSQL uses row locking when enabled later."""
    if DATABASE_URL.startswith("duckdb:"):
        with write_lock(db):
            yield db.get(ImportBatch,batch_id)
    else:
        yield db.execute(select(ImportBatch).where(ImportBatch.id==batch_id).with_for_update()).scalar_one()

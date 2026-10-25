from __future__ import annotations
import os
from logging.config import fileConfig
from alembic import context
from alembic.ddl.impl import DefaultImpl
from sqlalchemy import engine_from_config, pool
from app.models import Base
from app.config import DATABASE_URL

class DuckDBImpl(DefaultImpl):
    """Alembic has no bundled DuckDB implementation; generic DDL is sufficient here."""
    __dialect__ = "duckdb"

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction(): context.run_migrations()

def run_migrations_online():
    url=config.get_main_option("sqlalchemy.url")
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool, connect_args={} if url.startswith("duckdb:") else {"connect_timeout": 5})
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction(): context.run_migrations()

if context.is_offline_mode(): run_migrations_offline()
else: run_migrations_online()

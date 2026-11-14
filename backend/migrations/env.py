"""Alembic environment. Uses the app's settings and models, so DATABASE_URL drives everything."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import text
from sqlmodel import SQLModel

import app.models  # noqa: F401  (registers the tables on SQLModel.metadata)
from app.db import engine

if context.config.config_file_name and context.config.attributes.get("configure_logging", True):
    fileConfig(context.config.config_file_name, disable_existing_loggers=False)

target_metadata = SQLModel.metadata
options = dict(target_metadata=target_metadata, compare_type=True, render_as_batch=engine.dialect.name == "sqlite")

if context.is_offline_mode():
    context.configure(url=engine.url.render_as_string(hide_password=False), literal_binds=True, **options)
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        context.configure(connection=connection, **options)
        with context.begin_transaction():
            if engine.dialect.name == "postgresql":
                # Replicas starting together queue here, so only one migrates at a time.
                # The lock is released when this transaction ends.
                connection.execute(text("SELECT pg_advisory_xact_lock(7243911)"))
            context.run_migrations()

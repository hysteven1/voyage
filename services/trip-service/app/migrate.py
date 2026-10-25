"""Serialize schema upgrades across concurrent deployment Jobs. Never downgrade."""

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.database import engine


def main():
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as lock:
        lock.execute(text("SET lock_timeout = '120s'"))
        lock.execute(text("SELECT pg_advisory_lock(863209415)"))
        try:
            command.upgrade(Config("alembic.ini"), "head")
        finally:
            lock.execute(text("SELECT pg_advisory_unlock(863209415)"))


if __name__ == "__main__":
    main()

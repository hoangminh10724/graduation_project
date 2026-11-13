from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.db import get_engine


def test_initial_migration(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    config = Config(Path(__file__).resolve().parents[1] / "alembic.ini")
    engine = get_engine()
    tables = {"users", "sessions", "cards", "reviews", "attempts", "dialogue_turns"}
    try:
        command.upgrade(config, "head")
        assert tables <= set(inspect(engine).get_table_names())
        command.check(config)

        command.downgrade(config, "base")
        assert tables.isdisjoint(inspect(engine).get_table_names())
    finally:
        engine.dispose()
        get_engine.cache_clear()

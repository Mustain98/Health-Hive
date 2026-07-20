"""Minimal test harness — no pytest in this environment, so tests are plain scripts.

Run one with `python tests/<name>.py` from `backend/`; it exits non-zero on failure.
`check()` reports every assertion rather than stopping at the first, because these
tests describe behaviour and it is more useful to see the whole picture at once.
"""
from __future__ import annotations

import sys

from sqlmodel import SQLModel, Session, create_engine

import app.models  # noqa: F401  — registers every table on SQLModel.metadata

# JSONB is Postgres-only and SQLite cannot compile it. These three tables belong to the
# meal/food domain, which no setup-chat test touches, so they are simply not created.
_PG_ONLY_TABLES = {"food_item", "meal"}


class Results:
    def __init__(self, title: str) -> None:
        self.failures: list[str] = []
        print(f"\n=== {title} ===")

    def check(self, label: str, cond: bool, detail: str = "") -> bool:
        print(("  PASS  " if cond else "  FAIL  ") + label + (f"   [{detail}]" if detail else ""))
        if not cond:
            self.failures.append(label)
        return cond

    def section(self, label: str) -> None:
        print(f"\n-- {label}")

    def finish(self) -> None:
        if self.failures:
            print(f"\nFAILED ({len(self.failures)}): " + "; ".join(self.failures))
            sys.exit(1)
        print("\nall checks passed")
        sys.exit(0)


def make_engine():
    """A fresh in-memory database with the tables these tests need."""
    engine = create_engine("sqlite://")
    tables = [t for name, t in SQLModel.metadata.tables.items() if name not in _PG_ONLY_TABLES]
    SQLModel.metadata.create_all(engine, tables=tables)
    return engine


def session(engine) -> Session:
    return Session(engine)

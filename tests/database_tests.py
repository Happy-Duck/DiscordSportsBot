# database_tests.py
# Dev inspection script: run directly to dump the bot DB's tables and sample rows.
# Usage (from the project root): python tests/database_tests.py

import asyncio
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine  # pyright: ignore
from sqlalchemy import text  # pyright: ignore

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.db_skeleton import DATABASE_URL  # noqa: E402

DB_PATH = DATABASE_URL


async def list_tables():
    engine = create_async_engine(DB_PATH)  # added absolute pathing
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = [row[0] for row in result]
        print(tables)


async def list_table_columns():
    engine = create_async_engine(DB_PATH)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = [row[0] for row in result]

        if not tables:
            print("No tables found in the database.")
            return

        for table in tables:
            print(f"\n*** Table: {table} ***")
            cols_result = await conn.execute(text(f"PRAGMA table_info({table});"))
            columns = [r[1] for r in cols_result]

            if not columns:
                print("(No columns found)")
            else:
                for col in columns:
                    print(f"  - {col}")
    await engine.dispose()


async def show_first_five_members():
    engine = create_async_engine(DB_PATH)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT * FROM members LIMIT 5;"))
        rows = result.mappings().all()
        if not rows:
            print("\nNo member records found.")
        else:
            print("\nFirst 5 members:")
            for row in rows:
                print(dict(row))
    await engine.dispose()


async def show_first_five_player_subs():
    engine = create_async_engine(DB_PATH)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT * FROM player_subscriptions LIMIT 5;"))
        rows = result.mappings().all()
        if not rows:
            print("\nNo member records found.")
        else:
            print("\nFirst 5 player subs:")
            for row in rows:
                print(dict(row))
    await engine.dispose()


async def show_first_five_team_subs():
    engine = create_async_engine(DB_PATH)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT * FROM team_subscriptions LIMIT 5;"))
        rows = result.mappings().all()
        if not rows:
            print("\nNo member records found.")
        else:
            print("\nFirst 5 team subs:")
            for row in rows:
                print(dict(row))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(list_tables())
    asyncio.run(list_table_columns())
    asyncio.run(show_first_five_members())
    asyncio.run(show_first_five_player_subs())
    asyncio.run(show_first_five_team_subs())

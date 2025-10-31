import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# This is where we can unit test our code with absolute basic print statements; set this up for now
# to reflect that the SportsBot:  (1) Contains the tables we require
# and (2) the DBMS is organized as expected

# As we continue to work on the project, this is how


async def list_tables():
    engine = create_async_engine("sqlite+aiosqlite:///./sportsbot.db")
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table';")
        )
        tables = [row[0] for row in result]
        print(tables)


async def list_table_columns():
    engine = create_async_engine("sqlite+aiosqlite:///./sportsbot.db")
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table';")
        )
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


asyncio.run(list_tables())
asyncio.run(list_table_columns())

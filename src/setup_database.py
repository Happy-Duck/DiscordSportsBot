# setup_database.py

import asyncio
from src.db_skeleton import init_db


async def main():
    await init_db()
    print("All tables created.")

if __name__ == "__main__":
    asyncio.run(main())

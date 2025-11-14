import asyncio
import os
import sys


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_PATH = os.path.join(BASE_DIR, "..", "src")
SRC_PATH = os.path.abspath(SRC_PATH)
DB_PATH = os.path.join(SRC_PATH, "sportsbot.db")

sys.path.insert(0, SRC_PATH)

from database import initialize_database, test_database, add_player_to_team, clear_dummy_data


async def run_tests():
    await clear_dummy_data()  # ONLY while the DB does NOT contain real data

    status = await initialize_database()
    print(status)

    print("\n*** Adding Test Team ***")
    team_test = await test_database()
    print(team_test)

    print("\n*** Adding Test Player ***")
    player_test = await add_player_to_team("Test Player", "Test Team FC")
    print(player_test)

if __name__ == "__main__":
    asyncio.run(run_tests())

# SportsAPIClient.py

import aiohttp
import asyncio
import time
import json
from . import DataClass
import os
from dotenv import load_dotenv

# API_Football_key is required if you want to use it.
# Default Sports_DB_Key is 3.
# Ideally, keys should be injectable, but for MVP this is fine.


load_dotenv()
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
if not API_FOOTBALL_KEY:
    raise RuntimeError("API_FOOTBALL_KEY not found. Go to .env and set API_FOOTBALL_KEY locally.")

SPORTS_DB_KEY = "3"

SPORTS_DB_URL = f"https://www.thesportsdb.com/api/v1/json/{SPORTS_DB_KEY}"


# The class SportsAPIClient will be responsible for giving back the player info.
class SportsAPIClient:

    # Maintain a single session per server to avoid creating many sessions
    def __init__(self, session):
        self.session = session

    async def get_player(self, player):
        # check for either apifootball/sports_db/or both? for now just using sports_DB
        async with self.session.get(f"{SPORTS_DB_URL}/searchplayers.php?p={player}") as response:

            # kinda wacky not the try/catch.. but... we can prob check the server instead as well.
            if (200 > response.status or response.status >= 300):
                return "Server Down"

            response_object = await response.json()

            player_list = response_object.get("player")

            # format json so only necessary information is sent and return
            player_info = []

            for potential_player in player_list:
                print(type(potential_player))
                player_info.append(DataClass.Player().from_api_json(potential_player))

        return player_info

    async def get_team(self, team):
        # check for either apifootball/sports_db or both? for now just using sports_DB
        async with self.session.get(f"{SPORTS_DB_URL}/searchteams.php?t={team}") as response:

            # kinda wacky not the try/catch.. but... works
            if (200 > response.status or response.status >= 300):
                return "Server Down"

            response_object = await response.json()

            team_list = response_object.get("teams")

            # format json so only necessary information is sent and return
            team_info = []

            print(team_list[0])

            for potential_team in team_list:
                team_info.append(DataClass.Team().from_api_json(potential_team))

        return team_info


# # for testing for now
# async def main():
#     async with aiohttp.ClientSession() as session:
#         curr_session = SportsAPIClient(session)
#         test_player = "Danny_Welbeck"
#         test_team = "Arsenal"

#         player_info = await curr_session.get_player(test_player)
#         team_info = await curr_session.get_team(test_team)
#         print(player_info)
#         print(team_info)
#         print("nooo")

# asyncio.run(main())

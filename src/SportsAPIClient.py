# SportsAPIClient.py

import aiohttp
import asyncio
import time
import json
from DataClass import Player, Team # pyright: ignore
import os
from dotenv import load_dotenv

# API_Football_key is required if you want to use it.
# Default Sports_DB_Key is 3.
# Ideally, keys should be injectable, but for MVP this is fine.

load_dotenv()
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
# Note: API_FOOTBALL_KEY is optional and may not be set in test environments
# Tests will be skipped if the key is not available

AF_Headers = {
    'x-apisports-key': API_FOOTBALL_KEY
    }

API_FOOTBALL_End_Point = "v3.football.api-sports.io"


# The class SportsAPIClient will be responsible for giving back the player info.
class SportsAPIClient:

    # Maintain a single session per server to avoid creating many sessions
    def __init__(self, session):
        self.session = session

    async def AF_get_player_profile(self, player):
        URL = "https://v3.football.api-sports.io/players/profiles"
        params = {
            "search": player,
            }
        
        async with self.session.get(URL, headers = AF_Headers, params=params) as response:
            if (response.status == 204):
                return ""
            elif (response.status == 499 or response.status == 500):
                return response.status
            
            player_list = await response.json()
            
        return player_list['response']

    async def AF_get_player_teams(self, player_id):
        # if (response.errors !=):
        #     return "server is currently down"
        URL = "https://v3.football.api-sports.io/players/teams"
        params = {
            "player": player_id,
            }
        
        async with self.session.get(URL, headers = AF_Headers, params=params) as response:
            if (response.status == 204):
                return []
            elif (response.status == 499 or response.status == 500):
                return response.status
            
            player_list = await response.json()
            
        return player_list['response']
        
    
    # async def AF_Get_League_ID(self, player_id):
        

    async def AF_get_player_stat(self, id, season):
        # default latest season
        # if (response.errors !=):
        #     return "server is currently down"
        URL = "https://v3.football.api-sports.io/players"
        params = {
            "id": id,
            "season": season,
            }
        
        async with self.session.get(URL, headers = AF_Headers, params=params) as response:
            if (response.status == 204):
                return []
            elif (response.status == 499 or response.status == 500):
                return response.status
            
            player_list = await response.json()

        return player_list['response']


# # for testing for now
# async def main():
#     print("something")
#     async with aiohttp.ClientSession() as session:
#         curr_session = SportsAPIClient(session)
#         test_player = "Federico Bernardeschi"

#         # player_list = await curr_session.AF_get_player_profile(test_player.split()[1])
#         # print(player_list)
        
#         player_stats = await curr_session.AF_get_player_stat(id = 873, season=2023)
#         print(player_stats)
        
#         # team_info = await curr_session.AF_get_team(test_team)
        
#         # for future test. messi -> memberid = 154 / brazil team = 26 / 

# asyncio.run(main())

# SportsAPIClient.py

import aiohttp
import asyncio
import json
from DataClass import Player, Team  # pyright: ignore
import os
from dotenv import load_dotenv
import unicodedata

# API_Football_key is required if you want to use it.
# Default Sports_DB_Key is 3.
# Ideally, keys should be injectable, but for MVP this is fine.

load_dotenv()
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
# Note: API_FOOTBALL_KEY is optional and may not be set in test environments
# Tests will be skipped if the key is not available

AF_Headers = {"x-apisports-key": API_FOOTBALL_KEY}

  AF_Headers = {"x-apisports-key": API_FOOTBALL_KEY}

SPORTS_DB_KEY = "3"

SPORTS_DB_URL = f"https://www.thesportsdb.com/api/v1/json/{SPORTS_DB_KEY}"

API_FOOTBALL_End_Point = "v3.football.api-sports.io"


# The class SportsAPIClient will be responsible for giving back the player info.
class SportsAPIClient:

    # Maintain a single session per server to avoid creating many sessions
    def __init__(self, session):
        self.session = session

    async def get_player(self, player):
        # check for either apifootball/sports_db/or both? for now just using sports_DB
        async with self.session.get(
            f"{SPORTS_DB_URL}/searchplayers.php?p={player}"
        ) as response:

            if not response:
                print("No response from api")
                return "Server Dowm"

            # kinda wacky not the try/catch.. but... we can prob check the server instead as well.
            if 200 > response.status or response.status >= 300:
                return "Server Down"

            response_object = await response.json()

            player_list = response_object.get("player")

            # format json so only necessary information is sent and return
            player_info = []

            for potential_player in player_list:
                print(type(potential_player))
                player_info.append(Player().from_api_json(potential_player))

        return player_info

    async def get_team(self, team):
        # check for either apifootball/sports_db or both? for now just using sports_DB
        async with self.session.get(
            f"{SPORTS_DB_URL}/searchteams.php?t={team}"
        ) as response:

            # kinda wacky not the try/catch.. but... works
            if 200 > response.status or response.status >= 300:
                return "Server Down"

            response_object = await response.json()

            team_list = response_object.get("teams")

            # format json so only necessary information is sent and return
            team_info = []

            print(team_list[0])

            for potential_team in team_list:
                team_info.append(Team().from_api_json(potential_team))

        return team_info

    async def AF_get_player_profile(self, player):
        URL = "https://v3.football.api-sports.io/players/profiles"
        params = {
            "search": player,
        }

        async with self.session.get(URL, headers=AF_Headers, params=params) as response:
            if response.status == 204:
                return ""
            elif response.status == 499 or response.status == 500:
                return response.status

            player_list = await response.json()

        return player_list["response"]

    async def AF_get_player_teams(self, player_id):
        # if (response.errors !=):
        #     return "server is currently down"
        URL = "https://v3.football.api-sports.io/players/teams"
        params = {
            "player": player_id,
            }
        
        async with self.session.get(URL, headers=AF_Headers, params=params) as response:
            if response.status == 204:
                return ""
            elif response.status == 499 or response.status == 500:
                return response.status

            player_list = await response.json()

        return player_list["response"]

    # async def AF_Get_League_ID(self, player_id):

    async def AF_get_player_stat(self, id, season):
        # default latest season
        # if (response.errors !=):
        #     return "server is currently down"
        URL = "https://v3.football.api-sports.io/players"
        params = {
            "id": id,
            "season": season,
              "search": name,
        }

        async with self.session.get(URL, headers=AF_Headers, params=params) as response:
            if response.status == 204:
                return ""
            elif response.status == 499 or response.status == 499:
                return response.status

            player_list = await response.json()

        return player_list['response']
    
    async def AF_get_team_profile(self, team_name):
        URL = "https://v3.football.api-sports.io/teams"
        
        params = {
            "name": team_name,
        }
        
        async with self.session.get(URL, headers = AF_Headers, params=params) as response:
            if (response.status == 204):
                return []
            elif (response.status == 499 or response.status == 500):
                return response.status
            team_profile = await response.json()

        return team_profile['response']
        
    async def AF_get_team_league_id(self, team_id, season=2023):
        URL = "https://v3.football.api-sports.io/leagues"
        
        params = {
            "season": season,
            "team": team_id,
        }
        
        async with self.session.get(URL, headers = AF_Headers, params=params) as response:
            if (response.status == 204):
                return []
            elif (response.status == 499 or response.status == 500):
                return response.status
            team_league_list = await response.json()
        return team_league_list['response']
    
    async def AF_get_team_stat(self, team_id, league_id, season=2023):
        URL = "https://v3.football.api-sports.io/teams/statistics"
        params = {
            "league": league_id,
            "season": season,
            "team": team_id,
        }
        async with self.session.get(URL, headers = AF_Headers, params=params) as response:
            if (response.status == 204):
                return []
            elif (response.status == 499 or response.status == 500):
                return response.status
            team_statistics = await response.json()
        return team_statistics['response']
        return player_list["response"]

    # async def AF_get_team(self, team_name):
    #     # latest season you can get from APIFootball
    #     season = 2023

    #     return ""


# # for testing for now

# def save_data(data, filename="output.json"):
#     with open(filename, "w") as f:
#         json.dump(data, f, indent=4)

# def load_data(filename="output.json"):
#     with open(filename, "r") as f:
#         return json.load(f)

# async def main():
#     team_name = "manchester united"
#     async with aiohttp.ClientSession() as session:
#         curr_session = SportsAPIClient(session)
#         response = await curr_session.AF_get_team_profile(team_name)
#         print(response)
        
#         response2 = await curr_session.AF_get_team_league_id(team_id = response[0]['team']['id'])
#         print(response2)
        
#         response3 = await curr_session.AF_get_team_stat(team_id=33, league_id=39)
#         print(response3)
#         # team_info = await curr_session.AF_get_team(test_team)

#         # for future test. messi -> memberid = 154 / brazil team = 26 /

# asyncio.run(main())


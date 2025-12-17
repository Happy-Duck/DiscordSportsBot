# SportsAPIClient.py

import aiohttp
import asyncio
import json
import os
from .DataClass import Player, Team  # pyright: ignore
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
                return "Server Down"

            # kinda wacky not the try/catch.. but... we can prob check the server instead as well.
            if 200 > response.status or response.status >= 300:
                return "Server Down"

            response_object = await response.json()

            player_list = response_object.get("player")

            # format json so only necessary information is sent and return
            player_info = []

            for potential_player in player_list:
                # print(type(potential_player))
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

    async def af_get_player_profile(self, last_name):
        url = "https://v3.football.api-sports.io/players/profiles"
        params = {
            "search": last_name,
        }

        async with self.session.get(url, headers=AF_Headers, params=params) as response:
            if response.status == 204:
                return {"status": "player profile not found", "data": None}
            elif response.status == 499 or response.status == 500:
                return {"status": "server down", "data": None}

            player_list = await response.json()
        return {"status": "success", "data": player_list["response"]}

    async def af_get_player_stat(self, id, season=2023):
        url = "https://v3.football.api-sports.io/players"
        params = {
            "id": id,
            "season": season,
        }

        async with self.session.get(url, headers=AF_Headers, params=params) as response:
            if response.status == 204:
                return {"status": "player statistics not found", "data": None}
            elif response.status == 499 or response.status == 500:
                return {"status": "server down", "data": None}

            player_stat = await response.json()
        return {"status": "success", "data": player_stat["response"]}

    async def AF_get_team_profile(self, team_name):
        URL = "https://v3.football.api-sports.io/teams"

        params = {
            "name": team_name,
        }
        async with self.session.get(URL, headers=AF_Headers, params=params) as response:
            if response.status == 204:
                return {"status": "team profile not found", "data": None}
            elif response.status == 499 or response.status == 500:
                return {"status": "server down", "data": None}
            team_profile = await response.json()
        return {"status": "success", "data": team_profile["response"]}

    async def AF_get_team_league_id(self, team_id, season=2023):
        URL = "https://v3.football.api-sports.io/leagues"

        params = {
            "season": season,
            "team": team_id,
        }

        async with self.session.get(URL, headers=AF_Headers, params=params) as response:
            if response.status == 204:
                return {"status": "team league not found", "data": None}
            elif response.status == 499 or response.status == 500:
                return {"status": "server down", "data": None}
            team_league_list = await response.json()
        return {"status": "success", "data": team_league_list["response"]}

    async def AF_get_team_stat(self, team_id, league_id, season=2023):
        URL = "https://v3.football.api-sports.io/teams/statistics"
        params = {
            "league": league_id,
            "season": season,
            "team": team_id,
        }
        async with self.session.get(URL, headers=AF_Headers, params=params) as response:
            if response.status == 204:
                return {"status": "team stat not found", "data": None}
            elif response.status == 499 or response.status == 500:
                return {"status": "server down", "data": None}
            team_statistics = await response.json()
        return {"status": "success", "data": team_statistics["response"]}

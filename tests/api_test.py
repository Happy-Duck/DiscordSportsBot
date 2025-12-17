# api_test.py
import os
import pytest
import aiohttp
import sys
import json
from pathlib import Path
from src.SportsAPIClient import SportsAPIClient

PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)  # getting the root cause the tests are in /tests - painful to figure out this issue by the way
sys.path.insert(0, str(PROJECT_ROOT))

pytestmark = pytest.mark.skipif(
    not os.getenv("API_FOOTBALL_KEY"),
    reason="API_FOOTBALL_KEY not found. Go to .env and set API_FOOTBALL_KEY locally.",
)

# we should be able to follow a similar pattern to test other api stuff

@pytest.mark.asyncio
async def test_real_get_team_request():

    async with aiohttp.ClientSession() as sess:
        url = "https://www.thesportsdb.com/api/v1/json/3/searchteams.php"
        async with sess.get(url, params={"t": "inter miami"}) as resp:
            raw = await resp.json()
            print(raw, "\n")
        assert "Inter Miami" in json.dumps(raw)

        async with sess.get(url, params={"t": "arsenal"}) as resp:
            raw = await resp.json()
            print(raw, "\n")
        assert "Arsenal" in json.dumps(raw)

        async with sess.get(url, params={"t": "manchester united"}) as resp:
            raw = await resp.json()
            print(raw, "\n")
        assert "Manchester United" in json.dumps(raw)


@pytest.mark.asyncio
async def test_af_get_player_profile():
    async with aiohttp.ClientSession() as session:
        client = SportsAPIClient(session)
        result1 = await client.af_get_player_profile("Messi")
        result1 = result1["data"]
        argentina_messi = None
        for players in result1:
            player = players.get("player")
            if player.get("id") == 154:
                argentina_messi = player
        assert argentina_messi is not None
        assert argentina_messi.get("name") == "L. Messi"
        assert argentina_messi.get("firstname") == "Lionel Andrés"
        assert argentina_messi.get("lastname") == "Messi Cuccittini"
        assert argentina_messi.get("nationality") == "Argentina"

@pytest.mark.asyncio
async def test_af_get_player_stat():
    async with aiohttp.ClientSession() as session:
        client = SportsAPIClient(session)
        result1 = await client.af_get_player_stat(id=154, season=2023)
        player = result1["data"][0]
        player_info = player["player"]
        player_stat = player["statistics"][0]
        
        assert player_info["name"] == "L. Messi"
        assert player_info["id"] == 154
        assert player_info["nationality"] == "Argentina"
        assert player_stat["team"]["id"] == 9568 
        assert player_stat["league"]["id"] == 253
        assert player_stat["games"]["appearences"] == 6

@pytest.mark.asyncio
async def test_AF_get_team_profile():
    async with aiohttp.ClientSession() as session:
        client = SportsAPIClient(session)
        result1 = await client.AF_get_team_profile(team_name = "manchester united")
        team = result1["data"][0]

        assert team["team"]["id"] == 33
        assert team["team"]["name"] == "Manchester United"
        assert team["team"]["founded"] == 1878
        assert team["venue"]["id"] == 556 
        assert team["venue"]["name"] == "Old Trafford"
        assert team["venue"]["city"] == "Manchester" 

@pytest.mark.asyncio
async def test_AF_get_team_league_id():
    async with aiohttp.ClientSession() as session:
        client = SportsAPIClient(session)
        result1 = await client.AF_get_team_league_id(team_id = 33, season=2023)
        team1 = result1["data"][0]["league"]
        assert team1["id"] == 667
        assert team1["name"] == "Friendlies Clubs"
        assert team1["type"] == "Cup"

        team3 = result1["data"][2]["league"]
        assert team3["id"] == 39
        assert team3["name"] == "Premier League"
        assert team3["type"] == "League"

@pytest.mark.asyncio
async def test_AF_get_team_stat():
    async with aiohttp.ClientSession() as session:
        client = SportsAPIClient(session)
        result1 = await client.AF_get_team_stat(team_id = 33, league_id = 39, season=2023)
        stat1 = result1["data"]
        
        assert stat1["league"]["id"] == 39
        assert stat1["team"]["id"] == 33
        assert stat1["fixtures"]["played"]["total"] == 38 
        assert stat1["fixtures"]["wins"]["total"] == 18 
        assert stat1["fixtures"]["draws"]["total"] == 6
        assert stat1["fixtures"]["loses"]["total"] == 14


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
async def test_real_get_player_request():

    async with aiohttp.ClientSession() as sess:
        url = "https://www.thesportsdb.com/api/v1/json/3/searchplayers.php"
        async with sess.get(url, params={"p": "messi"}) as resp:
            raw = await resp.json()
            print(raw, "\n")
        assert "Lionel Messi" in json.dumps(raw)

        async with sess.get(url, params={"p": "ronaldo"}) as resp:
            raw = await resp.json()
            print(raw, "\n")
        assert "Cristiano Ronaldo" in json.dumps(raw)

        async with sess.get(url, params={"p": "mbappe"}) as resp:
            raw = await resp.json()
            print(raw, "\n")
        assert "Kylian Mbapp" in json.dumps(raw)


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
async def test_af_get_player_teams():
    async with aiohttp.ClientSession() as session:
        client = SportsAPIClient(session)
        team_played_1 = await client.af_get_player_teams("154")

        expected_list_of_teams_1 = [
            "Argentina", "Inter Miami", "Paris Saint Germain", "Barcelona", "Argentina U23"
        ]
        expected_list_of_id_1 = [26, 9568, 85, 529, 10187]

        received_list_of_teams_1 = [
            team.get("team").get("name") for team in team_played_1
        ]
        received_list_of_id_1 = [
            team.get("team").get("id") for team in team_played_1
        ]

        for expected_team in expected_list_of_teams_1:
            assert expected_team in received_list_of_teams_1
        for expected_id in expected_list_of_id_1:
            assert expected_id in received_list_of_id_1

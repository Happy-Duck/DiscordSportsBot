# api_test.py
import os
import pytest
import aiohttp
import sys
import json
from pathlib import Path

PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)  # getting the root cause the tests are in /tests - painful to figure out this issue by the way
sys.path.insert(0, str(PROJECT_ROOT))

from src.SportsAPIClient import SportsAPIClient

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

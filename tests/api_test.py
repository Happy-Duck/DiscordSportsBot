# api_test.py
import os
import pytest
import aiohttp
import sys
import json
from pathlib import Path
from src.SportsAPIClient import SportsAPIClient
from src.IntegrationLayer import IntegrationLayer

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


@pytest.mark.asyncio
async def test_string_match_algorithm():
    async with aiohttp.ClientSession() as session:
        client = IntegrationLayer(session)

        # single macth
        list_of_potential_player = [
            {
                "player": {
                    "id": 249239,
                    "name": "Lionel Messi Nyamsi",
                    "firstname": "Lionel Messi",
                    "lastname": "Nyamsi",
                    "age": 30,
                    "birth": {
                        "date": "1995-03-30",
                        "place": None,
                        "country": "Cameroon",
                    },
                    "nationality": "Cameroon",
                    "height": None,
                    "weight": None,
                    "number": None,
                    "position": "Attacker",
                    "photo": "https://media.api-sports.io/football/players/249239.png",
                }
            },
            {
                "player": {
                    "id": 154,
                    "name": "L. Messi",
                    "firstname": "Lionel Andrés",
                    "lastname": "Messi Cuccittini",
                    "age": 38,
                    "birth": {
                        "date": "1987-06-24",
                        "place": "Rosario",
                        "country": "Argentina",
                    },
                    "nationality": "Argentina",
                    "height": "170",
                    "weight": "67",
                    "number": 10,
                    "position": "Attacker",
                    "photo": "https://media.api-sports.io/football/players/154.png",
                }
            },
        ]
        first_name = "Lionel"
        last_name = "Messi"
        result = await client.string_match_algorithm(
            list_of_potential_player=list_of_potential_player,
            first_name=first_name,
            last_name=last_name,
        )

        assert len(result) == 1
        assert result[0]["player"]["id"] == 154
        assert result[0]["player"]["name"] == "L. Messi"

@pytest.mark.asyncio
async def test_get_player_profile():
    async with aiohttp.ClientSession() as session:
        # this function should "only" return "Lionel Messi"
        client = IntegrationLayer(session)
        result = await client.get_player_profile(first_name="Lionel", last_name="Messi", season=2023)
        assert result["status"] == "success"
        assert len(result["data"]) == 1
        assert result["data"][0]["player"]["id"] == 154

@pytest.mark.asyncio
async def test_get_player_stats():
    async with aiohttp.ClientSession() as session:
        client = IntegrationLayer(session)
        result = await client.get_player_stats(first_name="Lionel", last_name="Messi", season=2023)
        result = result["data"]
        result[0]["team"]["id"] == 9568
        result[0]["team"]["name"] == "Inter Miami"
        result[0]["league"]["id"] == 253
        result[0]["league"]["name"] == "Major League Soccer"
        result[0]["games"]["appearences"] == 6
        result[0]["shots"]["total"] == 11


@pytest.mark.asyncio
async def test_get_player_stats():
    async with aiohttp.ClientSession() as session:
        client = IntegrationLayer(session)
        potential_team = [
            {
                "team": {
                    "id": 33,
                    "name": "Manchester United",
                    "code": "MUN",
                    "country": "England",
                    "founded": 1878,
                    "national": False,
                    "logo": "https://media.api-sports.io/football/teams/33.png",
                },
                "venue": {
                    "id": 556,
                    "name": "Old Trafford",
                    "address": "Sir Matt Busby Way",
                    "city": "Manchester",
                    "capacity": 76212,
                    "surface": "grass",
                    "image": "https://media.api-sports.io/football/venues/556.png",
                },
            },
            {
                "team": {
                    "id": 4898,
                    "name": "Manchester United W",
                    "code": "MUN",
                    "country": "England",
                    "founded": None,
                    "national": False,
                    "logo": "https://media.api-sports.io/football/teams/4898.png",
                },
                "venue": {
                    "id": 10726,
                    "name": "Leigh Sports Village Stadium",
                    "address": "Sale Way",
                    "city": "Leigh, Greater Manchester",
                    "capacity": 11000,
                    "surface": "grass",
                    "image": "https://media.api-sports.io/football/venues/10726.png",
                },
            },
            {
                "team": {
                    "id": 7198,
                    "name": "Manchester United U21",
                    "code": "MUN",
                    "country": "England",
                    "founded": None,
                    "national": False,
                    "logo": "https://media.api-sports.io/football/teams/7198.png",
                },
                "venue": {
                    "id": 556,
                    "name": "Old Trafford",
                    "address": "Sir Matt Busby Way",
                    "city": "Manchester",
                    "capacity": 76212,
                    "surface": "grass",
                    "image": "https://media.api-sports.io/football/venues/556.png",
                },
            },
        ]
        result = await client.get_exact_team(
            list_of_potential_team= potential_team,
            team_name="Manchester United",
        )
        result = result["data"]
        assert result["team"]["id"] == 33
        assert result["team"]["name"] == "Manchester United"

@pytest.mark.asyncio
async def test_get_team_profile():
    async with aiohttp.ClientSession() as session:
        client = IntegrationLayer(session)
        result = await client.get_team_profile(
            team_name="Manchester United",
        )
        result = result["data"]
        assert result["team"]["id"] == 33
        assert result["team"]["name"] == "Manchester United"

@pytest.mark.asyncio
async def test_get_team_stat():
    async with aiohttp.ClientSession() as session:
        client = IntegrationLayer(session)
        result = await client.get_team_stats(
            team_name="Manchester United",
        )
        result = result["data"]
        assert result["league"]["id"] == 39
        assert result["team"]["id"] == 33
        assert result["fixtures"]["played"]["total"] == 38
        assert result["fixtures"]["wins"]["total"] == 18
        assert result["fixtures"]["draws"]["total"] == 6
        assert result["fixtures"]["loses"]["total"] == 14
        

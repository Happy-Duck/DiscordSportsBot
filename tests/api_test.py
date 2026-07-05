# api_test.py
#
# Offline tests (matching algorithms) always run.
# TheSportsDB tests only need network access (free public key).
# API-Football tests are skipped unless API_FOOTBALL_KEY is set.

import json
import os

import aiohttp
import pytest

from src.SportsAPIClient import SportsAPIClient
from src.IntegrationLayer import IntegrationLayer

requires_af_key = pytest.mark.skipif(
    not os.getenv("API_FOOTBALL_KEY"),
    reason="API_FOOTBALL_KEY not found. Go to .env and set API_FOOTBALL_KEY locally.",
)


# ------------------------- offline tests -------------------------


@pytest.mark.asyncio
async def test_string_match_algorithm():
    async with aiohttp.ClientSession() as session:
        client = IntegrationLayer(session)

        list_of_potential_player = [
            {
                "player": {
                    "id": 249239,
                    "name": "Lionel Messi Nyamsi",
                    "firstname": "Lionel Messi",
                    "lastname": "Nyamsi",
                    "nationality": "Cameroon",
                    "position": "Attacker",
                }
            },
            {
                "player": {
                    "id": 154,
                    "name": "L. Messi",
                    "firstname": "Lionel Andrés",
                    "lastname": "Messi Cuccittini",
                    "nationality": "Argentina",
                    "position": "Attacker",
                }
            },
        ]
        result = await client.string_match_algorithm(
            list_of_potential_player=list_of_potential_player,
            first_name="Lionel",
            last_name="Messi",
        )

        assert len(result) == 1
        assert result[0]["player"]["id"] == 154
        assert result[0]["player"]["name"] == "L. Messi"


@pytest.mark.asyncio
async def test_string_match_is_accent_insensitive():
    async with aiohttp.ClientSession() as session:
        client = IntegrationLayer(session)
        players = [
            {
                "player": {
                    "id": 278,
                    "name": "K. Mbappé",
                    "firstname": "Kylian",
                    "lastname": "Mbappé Lottin",
                }
            }
        ]
        # plain-ascii search should match the accented API name
        result = await client.string_match_algorithm(
            players, first_name="Kylian", last_name="Mbappe"
        )
        assert len(result) == 1
        assert result[0]["player"]["id"] == 278


@pytest.mark.asyncio
async def test_string_match_skips_null_names():
    async with aiohttp.ClientSession() as session:
        client = IntegrationLayer(session)
        players = [{"player": {"id": 1, "firstname": None, "lastname": "Messi"}}]
        result = await client.string_match_algorithm(
            players, first_name="Lionel", last_name="Messi"
        )
        assert result == []


@pytest.mark.asyncio
async def test_get_exact_team():
    async with aiohttp.ClientSession() as session:
        client = IntegrationLayer(session)
        potential_team = [
            {
                "team": {"id": 33, "name": "Manchester United", "country": "England"},
                "venue": {"id": 556, "name": "Old Trafford", "city": "Manchester"},
            },
            {
                "team": {"id": 4898, "name": "Manchester United W", "country": "England"},
                "venue": {"id": 10726, "name": "Leigh Sports Village Stadium"},
            },
            {
                "team": {"id": 7198, "name": "Manchester United U21", "country": "England"},
                "venue": {"id": 556, "name": "Old Trafford"},
            },
        ]
        result = await client.get_exact_team(
            list_of_potential_team=potential_team,
            team_name="Manchester United",
        )
        result = result["data"]
        assert result["team"]["id"] == 33
        assert result["team"]["name"] == "Manchester United"


@pytest.mark.asyncio
async def test_short_last_name_is_rejected():
    async with aiohttp.ClientSession() as session:
        client = IntegrationLayer(session)
        result = await client.get_player_profile(first_name="Bo", last_name="Li")
        assert result["status"] != "success"
        assert result["data"] is None


# ------------------------- TheSportsDB (live, no key needed) -------------------------


@pytest.mark.asyncio
async def test_real_get_team_request():
    async with aiohttp.ClientSession() as sess:
        url = "https://www.thesportsdb.com/api/v1/json/3/searchteams.php"
        async with sess.get(url, params={"t": "arsenal"}) as resp:
            raw = await resp.json()
        assert "Arsenal" in json.dumps(raw)


@pytest.mark.asyncio
async def test_get_player_via_sportsdb():
    async with aiohttp.ClientSession() as session:
        client = SportsAPIClient(session)
        players = await client.get_player("Lionel Messi")
        assert isinstance(players, list) and players
        assert any("Messi" in (p.name or "") for p in players)


@pytest.mark.asyncio
async def test_get_player_no_results_returns_empty_list():
    async with aiohttp.ClientSession() as session:
        client = SportsAPIClient(session)
        players = await client.get_player("zzzz-no-such-player-zzzz")
        assert players == []


@pytest.mark.asyncio
async def test_get_team_via_sportsdb():
    async with aiohttp.ClientSession() as session:
        client = SportsAPIClient(session)
        teams = await client.get_team("Arsenal")
        assert isinstance(teams, list) and teams
        assert teams[0].name
        assert teams[0].country
        assert teams[0].id  # needed for fixture/result lookups
        assert teams[0].badge  # used as embed thumbnail


@pytest.mark.asyncio
async def test_get_last_events_via_sportsdb():
    async with aiohttp.ClientSession() as session:
        client = SportsAPIClient(session)
        teams = await client.get_team("Real Madrid")
        events = await client.get_last_events(teams[0].id)
        assert isinstance(events, list) and events
        e = events[0]
        assert e.id and e.home and e.away
        assert e.finished  # last events should have final scores


@pytest.mark.asyncio
async def test_get_next_events_via_sportsdb():
    async with aiohttp.ClientSession() as session:
        client = SportsAPIClient(session)
        teams = await client.get_team("Real Madrid")
        events = await client.get_next_events(teams[0].id)
        # upcoming fixtures can legitimately be empty deep in the off-season;
        # when present they must parse into named, unfinished events
        assert isinstance(events, list)
        for e in events:
            assert e.id and e.home and e.away
            assert not e.finished


# ------------------------- API-Football (live, key required) -------------------------


@requires_af_key
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


@requires_af_key
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


@requires_af_key
@pytest.mark.asyncio
async def test_af_get_team_profile():
    async with aiohttp.ClientSession() as session:
        client = SportsAPIClient(session)
        result1 = await client.af_get_team_profile(team_name="manchester united")
        team = result1["data"][0]

        assert team["team"]["id"] == 33
        assert team["team"]["name"] == "Manchester United"
        assert team["team"]["founded"] == 1878
        assert team["venue"]["id"] == 556
        assert team["venue"]["name"] == "Old Trafford"
        assert team["venue"]["city"] == "Manchester"


@requires_af_key
@pytest.mark.asyncio
async def test_af_get_team_league_id():
    async with aiohttp.ClientSession() as session:
        client = SportsAPIClient(session)
        result1 = await client.af_get_team_league_id(team_id=33, season=2023)
        leagues = [row["league"] for row in result1["data"]]
        premier_league = next(lg for lg in leagues if lg["id"] == 39)
        assert premier_league["name"] == "Premier League"
        assert premier_league["type"] == "League"


@requires_af_key
@pytest.mark.asyncio
async def test_af_get_team_stat():
    async with aiohttp.ClientSession() as session:
        client = SportsAPIClient(session)
        result1 = await client.af_get_team_stat(team_id=33, league_id=39, season=2023)
        stat1 = result1["data"]

        assert stat1["league"]["id"] == 39
        assert stat1["team"]["id"] == 33
        assert stat1["fixtures"]["played"]["total"] == 38
        assert stat1["fixtures"]["wins"]["total"] == 18
        assert stat1["fixtures"]["draws"]["total"] == 6
        assert stat1["fixtures"]["loses"]["total"] == 14


@requires_af_key
@pytest.mark.asyncio
async def test_get_player_profile():
    async with aiohttp.ClientSession() as session:
        # this function should "only" return "Lionel Messi"
        client = IntegrationLayer(session)
        result = await client.get_player_profile(
            first_name="Lionel", last_name="Messi", season=2023
        )
        assert result["status"] == "success"
        assert len(result["data"]) == 1
        assert result["data"][0]["player"]["id"] == 154


@requires_af_key
@pytest.mark.asyncio
async def test_get_player_stats():
    async with aiohttp.ClientSession() as session:
        client = IntegrationLayer(session)
        result = await client.get_player_stats(first_name="Lionel", last_name="Messi", season=2023)
        assert result["status"] == "success"
        stats = result["data"]
        assert stats[0]["team"]["name"] == "Inter Miami"
        assert stats[0]["league"]["name"] == "Major League Soccer"


@requires_af_key
@pytest.mark.asyncio
async def test_get_team_profile():
    async with aiohttp.ClientSession() as session:
        client = IntegrationLayer(session)
        result = await client.get_team_profile(team_name="Manchester United")
        result = result["data"]
        assert result["team"]["id"] == 33
        assert result["team"]["name"] == "Manchester United"

# SportsAPIClient.py

import os
from dotenv import load_dotenv
from .DataClass import MatchEvent, Player, Team

load_dotenv()

# TheSportsDB: free/public test key "3" works for basic search endpoints.
SPORTS_DB_KEY = os.getenv("SPORTS_DB_KEY", "3")
SPORTS_DB_URL = f"https://www.thesportsdb.com/api/v1/json/{SPORTS_DB_KEY}"

# API-Football: optional, required only for the detailed /stats command.
AF_BASE_URL = "https://v3.football.api-sports.io"


def _af_headers():
    """Build API-Football headers at call time so late-set env vars are honored."""
    key = os.getenv("API_FOOTBALL_KEY")
    if not key:
        return None
    return {"x-apisports-key": key}


# The class SportsAPIClient is responsible for giving back player/team info.
class SportsAPIClient:
    # Maintain a single session per server to avoid creating many sessions
    def __init__(self, session):
        self.session = session

    # ------------------------- TheSportsDB -------------------------

    async def get_player(self, player):
        """Search players on TheSportsDB. Returns a list of Player objects,
        an empty list when nothing matched, or "Server Down" on HTTP errors."""
        async with self.session.get(
            f"{SPORTS_DB_URL}/searchplayers.php", params={"p": player}
        ) as response:
            if not 200 <= response.status < 300:
                return "Server Down"

            response_object = await response.json()

        player_list = response_object.get("player") or []
        return [Player().from_api_json(p) for p in player_list if p]

    async def get_team(self, team):
        """Search teams on TheSportsDB. Returns a list of Team objects,
        an empty list when nothing matched, or "Server Down" on HTTP errors."""
        async with self.session.get(
            f"{SPORTS_DB_URL}/searchteams.php", params={"t": team}
        ) as response:
            if not 200 <= response.status < 300:
                return "Server Down"

            response_object = await response.json()

        team_list = response_object.get("teams") or []
        return [Team().from_api_json(t) for t in team_list if t]

    async def get_next_events(self, team_id):
        """Upcoming fixtures for a TheSportsDB team id. Returns a list of
        MatchEvent (possibly empty) or "Server Down" on HTTP errors."""
        async with self.session.get(
            f"{SPORTS_DB_URL}/eventsnext.php", params={"id": team_id}
        ) as response:
            if not 200 <= response.status < 300:
                return "Server Down"
            body = await response.json()

        events = body.get("events") or []
        return [MatchEvent().from_api_json(e) for e in events if e]

    async def get_last_events(self, team_id):
        """Most recent results for a TheSportsDB team id. Returns a list of
        MatchEvent (possibly empty) or "Server Down" on HTTP errors."""
        async with self.session.get(
            f"{SPORTS_DB_URL}/eventslast.php", params={"id": team_id}
        ) as response:
            if not 200 <= response.status < 300:
                return "Server Down"
            body = await response.json()

        events = body.get("results") or []
        return [MatchEvent().from_api_json(e) for e in events if e]

    # ------------------------- API-Football -------------------------

    async def _af_get(self, path, params, not_found_status):
        """Shared GET wrapper for API-Football endpoints.

        Always returns {"status": ..., "data": ...} where status is "success"
        only when usable data came back."""
        headers = _af_headers()
        if headers is None:
            return {
                "status": "API-Football is not configured. Set API_FOOTBALL_KEY in .env.",
                "data": None,
            }

        async with self.session.get(
            f"{AF_BASE_URL}{path}", headers=headers, params=params
        ) as response:
            if response.status == 204:
                return {"status": not_found_status, "data": None}
            if response.status >= 400:
                return {"status": "server down", "data": None}
            body = await response.json()

        # API-Football reports problems (bad key, rate limit, bad params) inside
        # a 200 body under "errors" — as a dict or list depending on the case.
        errors = body.get("errors")
        if errors:
            if isinstance(errors, dict):
                detail = "; ".join(f"{k}: {v}" for k, v in errors.items())
            else:
                detail = "; ".join(str(e) for e in errors)
            return {"status": f"API-Football error — {detail}", "data": None}

        data = body.get("response") or []
        if not data:
            return {"status": not_found_status, "data": None}
        return {"status": "success", "data": data}

    async def af_get_player_profile(self, last_name):
        return await self._af_get(
            "/players/profiles",
            {"search": last_name},
            "player profile not found",
        )

    async def af_get_player_stat(self, id, season=2023):
        return await self._af_get(
            "/players",
            {"id": id, "season": season},
            "player statistics not found",
        )

    async def af_get_team_profile(self, team_name):
        return await self._af_get(
            "/teams",
            {"name": team_name},
            "team profile not found",
        )

    async def af_get_team_league_id(self, team_id, season=2023):
        return await self._af_get(
            "/leagues",
            {"season": season, "team": team_id},
            "team league not found",
        )

    async def af_get_team_stat(self, team_id, league_id, season=2023):
        return await self._af_get(
            "/teams/statistics",
            {"league": league_id, "season": season, "team": team_id},
            "team stat not found",
        )

    # Backwards-compatible aliases for the old mixed-case method names.
    AF_get_team_profile = af_get_team_profile
    AF_get_team_league_id = af_get_team_league_id
    AF_get_team_stat = af_get_team_stat

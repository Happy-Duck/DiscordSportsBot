# IntegrationLayer.py

import unicodedata

from .SportsAPIClient import SportsAPIClient


def _fold(text):
    """Lowercase and strip accents so 'Mbappé' matches 'mbappe'."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


class IntegrationLayer:
    # Uses the shared aiohttp session provided by the bot.
    def __init__(self, session):
        self.session = session
        self.sports_api_client = SportsAPIClient(self.session)

    async def string_match_algorithm(self, list_of_potential_player, first_name, last_name):
        """Filter API-Football search results down to players whose first and
        last names contain the requested names (case- and accent-insensitive)."""
        first_name = _fold(first_name)
        last_name = _fold(last_name)

        trickled_list = []
        for player in list_of_potential_player:
            info = player.get("player") or {}
            candidate_first = _fold(info.get("firstname"))
            candidate_last = _fold(info.get("lastname"))
            if not candidate_first or not candidate_last:
                continue
            if first_name in candidate_first and last_name in candidate_last:
                trickled_list.append(player)
        return trickled_list

    async def get_player_profile(self, first_name, last_name, season=2023):
        # API-Football requires search terms of at least 3 characters.
        if len(last_name) < 3:
            return {
                "status": "Last name must be at least 3 characters to search.",
                "data": None,
            }

        result = await self.sports_api_client.af_get_player_profile(last_name)
        if result["status"] != "success":
            return result

        best_match = await self.string_match_algorithm(
            result["data"], first_name=first_name, last_name=last_name
        )

        if len(best_match) == 1:
            return {"status": "success", "data": best_match}
        if len(best_match) == 0:
            return {
                "status": f"No player found matching '{first_name} {last_name}'. "
                "Check the spelling and try again.",
                "data": None,
            }

        names = ", ".join(
            f"{p['player'].get('firstname', '?')} {p['player'].get('lastname', '?')}"
            for p in best_match[:10]
        )
        return {
            "status": f"{len(best_match)} players match '{first_name} {last_name}': "
            f"{names}. Please be more specific.",
            "data": None,
        }

    async def get_player_stats(self, first_name, last_name, season=2023):
        # get ID of player
        player_profile = await self.get_player_profile(first_name, last_name, season=season)
        if player_profile["status"] != "success":
            return player_profile

        player_id = player_profile["data"][0]["player"]["id"]

        # fetch that player's stats for the season
        player_stat = await self.sports_api_client.af_get_player_stat(id=player_id, season=season)
        if player_stat["status"] != "success":
            return player_stat

        statistics = player_stat["data"][0].get("statistics") or []
        if not statistics:
            return {
                "status": f"No {season} season statistics found for " f"{first_name} {last_name}.",
                "data": None,
            }
        return {"status": "success", "data": statistics}

    async def get_exact_team(self, list_of_potential_team, team_name):
        for team in list_of_potential_team:
            if _fold(team.get("team", {}).get("name")) == _fold(team_name):
                return {"status": "success", "data": team}
        return {"status": "could not find team with exact name given", "data": None}

    async def get_team_profile(self, team_name, season=2023):
        list_of_team = await self.sports_api_client.af_get_team_profile(team_name=team_name)
        if list_of_team["status"] != "success":
            return list_of_team
        return await self.get_exact_team(
            list_of_potential_team=list_of_team["data"], team_name=team_name
        )

    async def get_team_stats(self, team_name, season=2023):
        # get teamID
        team_profile = await self.get_team_profile(team_name=team_name)
        if team_profile["status"] != "success":
            return team_profile
        team_id = team_profile["data"]["team"]["id"]

        # get leagueID based on teamID
        league_info = await self.sports_api_client.af_get_team_league_id(
            team_id=team_id, season=season
        )
        if league_info["status"] != "success":
            return league_info

        # find league id with type="league"
        league_id = None
        for league in league_info["data"]:
            if league["league"]["type"].strip().lower() == "league":
                league_id = league["league"]["id"]
                break
        if league_id is None:
            return {
                "status": f"The team has no regular league in the {season} season.",
                "data": None,
            }

        # get stat based on teamID and leagueID
        return await self.sports_api_client.af_get_team_stat(
            team_id=team_id, league_id=league_id, season=season
        )

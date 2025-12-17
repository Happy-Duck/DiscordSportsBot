# integrationLayer.py
from .SportsAPIClient import SportsAPIClient
import aiohttp
import asyncio
import unicodedata


class IntegrationLayer:
    # Use the session provided by the
    def __init__(self, session):
        self.session = session
        self.sports_api_client = SportsAPIClient(self.session)

    async def string_match_algorithm(
        self, list_of_potential_player, first_name, last_name
    ):
        first_name = first_name.lower()
        last_name = last_name.lower()

        trickled_list = []
        # Then do exact search to see if the desired name is present
        for player in list_of_potential_player:
            if (
                player["player"]["firstname"] is None
                or player["player"]["lastname"] is None
            ):
                continue
            # normalize first and last name first
            normalized_first_name = unicodedata.normalize(
                "NFD", player["player"]["firstname"]
            ).lower()
            normalized_last_name = unicodedata.normalize(
                "NFD", player["player"]["lastname"]
            ).lower()

            if (
                first_name in normalized_first_name
                and last_name in normalized_last_name
            ):
                trickled_list.append(player)
        return trickled_list

    async def get_player_profile(self, first_name, last_name, season=2023):
        result = await self.sports_api_client.af_get_player_profile(last_name)
        # if status != 200 just throw the status back
        if result["status"] != "success":
            return result

        list_of_potential_player = result["data"]
        best_match = await self.string_match_algorithm(
            list_of_potential_player, first_name=first_name, last_name=last_name
        )

        if len(best_match) == 1:
            return {"status": "success", "data": best_match}
        else:
            first_names = []
            for player in best_match:
                first_names.append(player["player"]["firstname"])
            list_of_players = ", ".join(first_names)
            return {
                "status": f"more than one player with first name exists including{list_of_players}",
                "data": None,
            }

    async def get_player_stats(self, first_name, last_name, season=2023):
        # get ID of player
        player_profile = await self.get_player_profile(
            first_name, last_name, season=season
        )
        if player_profile["status"] != "success":
            return player_profile

        player_id = player_profile["data"][0]["player"]["id"]

        # call stat of player
        player_stat = await self.sports_api_client.af_get_player_stat(
            id=player_id, season=season
        )
        if player_stat["status"] != "success":
            return player_stat

        # return player_profile, player_statistics
        return {"status": "success", "data": player_stat["data"][0]["statistics"]}

    async def get_exact_team(self, list_of_potential_team, team_name):
        for team in list_of_potential_team:
            if team["team"]["name"].lower() == team_name.lower():
                return {"status": "success", "data": team}
        return {"status": "could not find team with exact name given", "data": None}

    async def get_team_profile(self, team_name, season=2023):
        # need teamID
        list_of_team = await self.sports_api_client.AF_get_team_profile(
            team_name=team_name
        )
        if list_of_team["status"] != "success":
            return list_of_team
        team = await self.get_exact_team(
            list_of_potential_team=list_of_team["data"], team_name=team_name
        )
        if team["status"] != "success":
            return team
        return {"status": "success", "data": team["data"]}

    async def get_team_stats(self, team_name, season=2023):
        # get teamID
        team_profile = await self.get_team_profile(team_name=team_name)
        if team_profile["status"] != "success":
            return team_profile
        team_id = team_profile["data"]["team"]["id"]

        # get leagueID based on teamID
        league_info = await self.sports_api_client.AF_get_team_league_id(
            team_id=team_id, season=season
        )
        if league_info["status"] != "success":
            return league_info

        # find league id with type="league"
        league_id = None
        for league in league_info["data"]:
            if league["league"]["type"] == "League":
                league_id = league["league"]["id"]
                break
        if league_id is None:
            return {
                "status": f"The team have a regular league in {season} season",
                "data": None,
            }

        # get stat based on teamID and leagueID
        team_stat = await self.sports_api_client.AF_get_team_stat(
            team_id=team_id, league_id=league_id, season=season
        )
        if team_stat["status"] != "success":
            return team_stat
        return team_stat

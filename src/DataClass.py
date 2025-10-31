# the code will contain bunch of dictionary that will be useful around the codes to use/convert # These are the things we only need
# better way to do this is to initalize everything to None instead and handle error? but for now i think empty string will be fine for safe initialization


class Player:

    def __init__(
        self,
        id="",
        name="",
        team_id="",
        position="",
        age="",
        nationality="",
        team="",
        stats="",
    ):
        self.id = id
        self.name = name
        self.team_id = team_id
        self.position = position
        self.age = age
        self.nationality = nationality
        self.team = team
        self.stats = stats

    def from_api_json(self, data: dict):
        if not data:
            return self

        # id
        self.id = data.get("idPlayer") or data.get("id") or self.id

        # name
        self.name = data.get("strPlayer") or data.get("name") or self.name

        # position
        self.position = data.get("strPosition") or data.get("position") or self.position

        # nationality
        self.nationality = (
            data.get("strNationality") or data.get("nationality") or self.nationality
        )

        # team info
        self.team = data.get("strTeam") or data.get("team") or self.team
        self.team_id = data.get("idTeam") or data.get("team_id") or self.team_id


# same as above, I should initalize them to none but for now before tests, this shall be fine.
class Team:

    def __init__(
        self,
        id="",
        name="",
        league="",
        country="",
        players=[],
        home_matches="",
        away_matches="",
    ):
        self.id = id
        self.name = name
        self.league = league
        self.country = country
        self.players = players
        self.home_matches = home_matches
        self.away_matches = away_matches

    def from_api_json(self, dictionary):
        # TODO
        return self

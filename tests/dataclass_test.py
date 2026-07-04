# dataclass_test.py

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

from src.DataClass import Player
from src.DataClass import Team


def test_player_from_api_json():
    example_player = Player()
    assert example_player.name is None
    assert example_player.id is None

    example_data_1 = {
        "idPlayer": "34146370",
        "idTeam": "137699",
        "strPlayer": "Lionel Messi",
        "strTeam": "Inter Miami",
        "strSport": "Soccer",
        "strThumb": "https://r2.thesportsdb.com/images/media/player/thumb/kpfsvp1725295651.jpg",
        "strCutout": "https://r2.thesportsdb.com/images/media/player/cutout/e0i2051750317027.png",
        "strNationality": "Argentina",
        "dateBorn": "1987-06-24",
        "strStatus": "Active",
        "strGender": "Male",
        "strPosition": "Right Winger",
        "relevance": "26.152610778808594",
    }

    example_player.from_api_json(example_data_1)
    assert example_player.name == "Lionel Messi"
    assert example_player.id == "34146370"

    example_player_2 = Player()
    example_data_2 = {
        "idPlayer": "34162098",
        "idTeam": "133738",
        "strPlayer": "Kylian Mbappé",
        "strTeam": "Real Madrid",
        "strSport": "Soccer",
        "strThumb": "https://r2.thesportsdb.com/images/media/player/thumb/buf4j51723707431.jpg",
        "strCutout": "https://r2.thesportsdb.com/images/media/player/cutout/h9u9vz1733653583.png",
        "strNationality": "France",
        "dateBorn": "1998-12-20",
        "strStatus": "Active",
        "strGender": "Male",
        "strPosition": "Centre-Forward",
        "relevance": "45.058837890625",
    }

    example_player_2.from_api_json(example_data_2)
    assert example_player_2.position == "Centre-Forward"
    assert example_player_2.nationality == "France"
    assert example_player_2.team == "Real Madrid"
    assert example_player_2.team_id == "133738"


def test_team_from_api_json():
    example_team = Team()
    assert example_team.name is None
    assert example_team.id is None

    example_data_1 = {
        "idTeam": "133604",
        "idESPN": "359",
        "idAPIfootball": "42",
        "intLoved": "9",
        "strTeam": "Arsenal",
        "strTeamAlternate": "Arsenal Football Club, AFC, Arsenal FC",
        "strTeamShort": "ARS",
        "intFormedYear": "1892",
        "strSport": "Soccer",
        "strLeague": "English Premier League",
        "idLeague": "4328",
        "strLeague2": "FA Cup",
        "idLeague2": "4482",
        "strLeague3": "EFL Cup",
        "idLeague3": "4570",
        "strLeague4": "UEFA Champions League",
        "idLeague4": "4480",
        "strLeague5": "Emirates Cup",
        "idLeague5": "5648",
        "strLeague6": "",
        "idLeague6": None,
        "strLeague7": "",
        "idLeague7": None,
        "strDivision": None,
        "idVenue": "15528",
        "strStadium": "Emirates Stadium",
        "strKeywords": "Gunners, Gooners",
        "strRSS": "",
        "strLocation": "Holloway, London, England",
        "intStadiumCapacity": "60338",
        "strWebsite": "www.arsenal.com",
        "strFacebook": "www.facebook.com/Arsenal",
        "strTwitter": "twitter.com/arsenal",
        "strInstagram": "instagram.com/arsenal",
        "strDescriptionEN": (
            "Arsenal Football Club is a professional football club based in Islington, "
            "London, England, that plays in the Premier League..."
        ),
        "strColour1": "#EF0107",
        "strColour2": "#fbffff",
        "strColour3": "#013373",
        "strGender": "Male",
        "strCountry": "England",
        "strBadge": "https://r2.thesportsdb.com/images/media/team/badge/uyhbfe1612467038.png",
        "strLogo": "https://r2.thesportsdb.com/images/media/team/logo/q2mxlz1512644512.png",
        "strYoutube": "www.youtube.com/user/ArsenalTour",
        "strLocked": "unlocked",
    }
    example_team.from_api_json(example_data_1)
    assert example_team.id == "133604"
    assert example_team.name == "Arsenal"
    assert example_team.country == "England"
    assert example_team.league == "English Premier League"
    assert example_team.stadium == "Emirates Stadium"
    assert example_team.founded == "1892"


def test_team_from_api_json_handles_missing_fields():
    # Regression test: a team object with no league/country/stadium keys
    # used to crash with AttributeError (self.league_id was never defined).
    team = Team()
    team.from_api_json({"idTeam": "1", "strTeam": "Tiny FC"})
    assert team.id == "1"
    assert team.name == "Tiny FC"
    assert team.league is None
    assert team.country is None


def test_player_age_computed_from_date_born():
    player = Player()
    player.from_api_json({"idPlayer": "2", "strPlayer": "Young Talent", "dateBorn": "2000-01-15"})
    assert isinstance(player.age, int)
    assert player.age >= 26  # born in 2000, so at least 26 by 2026

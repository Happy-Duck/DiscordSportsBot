# match_event_test.py
#
# Offline tests for MatchEvent parsing and the bot's match-embed helpers.

from datetime import datetime, timezone

from src.DataClass import MatchEvent
from src.bot import (
    GREEN,
    GREY,
    RED,
    _event_when,
    _filter_choices,
    _fixture_embed,
    _result_embed,
)

FINISHED_EVENT = {
    "idEvent": "2279771",
    "strEvent": "Real Madrid vs Athletic Bilbao",
    "strLeague": "Spanish La Liga",
    "strSeason": "2025-2026",
    "intRound": "38",
    "strVenue": "Estadio Santiago Bernabéu",
    "strHomeTeam": "Real Madrid",
    "strAwayTeam": "Athletic Bilbao",
    "intHomeScore": "4",
    "intAwayScore": "2",
    "strHomeTeamBadge": "https://example.com/rm.png",
    "strAwayTeamBadge": "https://example.com/ab.png",
    "strTimestamp": "2026-05-23T19:00:00",
    "dateEvent": "2026-05-23",
}

UPCOMING_EVENT = {
    "idEvent": "2506175",
    "strEvent": "Real Madrid vs Real Sociedad",
    "strLeague": "Spanish La Liga",
    "intRound": "1",
    "strHomeTeam": "Real Madrid",
    "strAwayTeam": "Real Sociedad",
    "intHomeScore": None,
    "intAwayScore": None,
    "strTimestamp": "2026-08-16T15:00:00",
    "dateEvent": "2026-08-16",
}


def test_finished_event_parsing():
    e = MatchEvent().from_api_json(FINISHED_EVENT)
    assert e.id == "2279771"
    assert e.home == "Real Madrid"
    assert e.away == "Athletic Bilbao"
    assert e.home_score == 4
    assert e.away_score == 2
    assert e.finished
    assert e.timestamp == datetime(2026, 5, 23, 19, 0, tzinfo=timezone.utc)
    assert e.league == "Spanish La Liga"
    assert e.venue == "Estadio Santiago Bernabéu"


def test_upcoming_event_parsing():
    e = MatchEvent().from_api_json(UPCOMING_EVENT)
    assert e.id == "2506175"
    assert not e.finished
    assert e.home_score is None
    assert e.timestamp.year == 2026


def test_event_when_falls_back_to_date():
    e = MatchEvent().from_api_json({"idEvent": "1", "dateEvent": "2026-01-02"})
    when = _event_when(e)
    assert when is not None
    assert when.date().isoformat() == "2026-01-02"


def test_result_embed_color_reflects_followed_team():
    e = MatchEvent().from_api_json(FINISHED_EVENT)
    assert _result_embed(e, followed_team="Real Madrid").color.value == GREEN
    assert _result_embed(e, followed_team="Athletic Bilbao").color.value == RED

    draw = dict(FINISHED_EVENT, intHomeScore="1", intAwayScore="1")
    e2 = MatchEvent().from_api_json(draw)
    assert _result_embed(e2, followed_team="Real Madrid").color.value == GREY


def test_result_embed_contents():
    e = MatchEvent().from_api_json(FINISHED_EVENT)
    embed = _result_embed(e, followed_team="Real Madrid")
    assert embed.title == "FT: Real Madrid 4 – 2 Athletic Bilbao"
    assert any("Spanish La Liga" in (f.value or "") for f in embed.fields)
    assert embed.thumbnail.url == "https://example.com/rm.png"


def test_fixture_embed_uses_discord_timestamp():
    e = MatchEvent().from_api_json(UPCOMING_EVENT)
    embed = _fixture_embed(e)
    assert embed.title == "Upcoming: Real Madrid vs Real Sociedad"
    kickoff = next(f for f in embed.fields if f.name == "Kickoff")
    unix = int(e.timestamp.timestamp())
    assert f"<t:{unix}:F>" in kickoff.value


def test_filter_choices():
    names = ["Lionel Messi", "Kylian Mbappé", "Lamine Yamal"]
    assert [c.value for c in _filter_choices(names, "")] == names
    assert [c.value for c in _filter_choices(names, "mess")] == ["Lionel Messi"]
    assert [c.value for c in _filter_choices(names, "LAMINE")] == ["Lamine Yamal"]
    # capped at 25 for Discord's autocomplete limit
    many = [f"Player {i}" for i in range(40)]
    assert len(_filter_choices(many, "player")) == 25

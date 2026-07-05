# DataClass.py

# Utility data containers used across the codebase.

from datetime import date, datetime, timezone


def _age_from_date_born(date_born):
    """Compute an age in years from a 'YYYY-MM-DD' string, or None."""
    if not date_born:
        return None
    try:
        born = datetime.strptime(date_born, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


class Player:
    def __init__(
        self,
        id=None,
        name=None,
        team_id=None,
        position=None,
        age=None,
        nationality=None,
        team=None,
        stats=None,
        thumb=None,
    ):
        self.id = id
        self.name = name
        self.team_id = team_id
        self.position = position
        self.age = age
        self.nationality = nationality
        self.team = team
        self.stats = stats
        self.thumb = thumb

    def from_api_json(self, data: dict):
        """Populate fields from a TheSportsDB player object (or a generic dict)."""
        if not data:
            return self

        self.id = data.get("idPlayer") or data.get("id") or self.id
        self.name = data.get("strPlayer") or data.get("name") or self.name
        self.position = data.get("strPosition") or data.get("position") or self.position
        self.nationality = data.get("strNationality") or data.get("nationality") or self.nationality
        self.age = _age_from_date_born(data.get("dateBorn")) or data.get("age") or self.age
        self.team = data.get("strTeam") or data.get("team") or self.team
        self.team_id = data.get("idTeam") or data.get("team_id") or self.team_id
        self.thumb = data.get("strCutout") or data.get("strThumb") or self.thumb

        return self


class Team:
    def __init__(
        self,
        id=None,
        name=None,
        league=None,
        country=None,
        players=None,
        stadium=None,
        founded=None,
        badge=None,
    ):
        self.id = id
        self.name = name
        self.league = league
        self.country = country
        self.players = players if players is not None else []
        self.stadium = stadium
        self.founded = founded
        self.badge = badge

    def from_api_json(self, data: dict):
        """Populate fields from a TheSportsDB team object (or a generic dict)."""
        if not data:
            return self

        self.id = data.get("idTeam") or data.get("id") or self.id
        self.name = (
            data.get("strTeam") or data.get("strTeamAlternate") or data.get("name") or self.name
        )
        self.league = data.get("strLeague") or data.get("league") or self.league
        self.country = data.get("strCountry") or data.get("country") or self.country
        self.stadium = data.get("strStadium") or data.get("stadium") or self.stadium
        self.founded = data.get("intFormedYear") or data.get("founded") or self.founded
        self.badge = data.get("strBadge") or data.get("badge") or self.badge

        return self


class MatchEvent:
    """One fixture/result from TheSportsDB's eventsnext/eventslast endpoints."""

    def __init__(self):
        self.id = None
        self.name = None
        self.league = None
        self.season = None
        self.round = None
        self.venue = None
        self.home = None
        self.away = None
        self.home_score = None
        self.away_score = None
        self.home_badge = None
        self.away_badge = None
        self.timestamp = None  # aware datetime (UTC) of kickoff, when known
        self.date = None  # 'YYYY-MM-DD' string fallback

    @property
    def finished(self):
        return self.home_score is not None and self.away_score is not None

    def from_api_json(self, data: dict):
        if not data:
            return self

        def to_int(val):
            try:
                return int(val)
            except (TypeError, ValueError):
                return None

        self.id = data.get("idEvent")
        self.name = data.get("strEvent")
        self.league = data.get("strLeague")
        self.season = data.get("strSeason")
        self.round = data.get("intRound")
        self.venue = data.get("strVenue")
        self.home = data.get("strHomeTeam")
        self.away = data.get("strAwayTeam")
        self.home_score = to_int(data.get("intHomeScore"))
        self.away_score = to_int(data.get("intAwayScore"))
        self.home_badge = data.get("strHomeTeamBadge")
        self.away_badge = data.get("strAwayTeamBadge")
        self.date = data.get("dateEvent")

        # strTimestamp is UTC, e.g. "2026-08-16T15:00:00"
        raw = data.get("strTimestamp")
        if raw:
            try:
                self.timestamp = datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
            except ValueError:
                self.timestamp = None

        return self

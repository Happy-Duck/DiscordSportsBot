from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession  # pyright: ignore
from sqlalchemy.orm import sessionmaker, declarative_base, relationship  # pyright: ignore
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Date,
    UniqueConstraint,
)  # pyright: ignore

# Use SQLite for local testing, the same DB the bot will connect to
DATABASE_URL = "sqlite+aiosqlite:///./sportsbot.db"


# Create the async engine and session factory
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Base class for SQLAlchemy
# SQLAlchemy is somewhat new to me. If I slip up and put a VARCHAR somewhere
# I shouldn't, you're allowed to yell at me (but be nice about it, please).
Base = declarative_base()


# call this function in setup_database to create sportsbot.DB
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class Team(Base):
    __tablename__ = "teams"
    id = Column(
        Integer, primary_key=True
    )  # APIs we are pulling from presumably have each team mapped to a unique ID.
    # If this is hard to verify, might want to change how we do this
    name = Column(String(100), nullable=False)
    league = Column(String(100))
    country = Column(
        String(50)
    )  # League and Country being here is quite expansive; could be removed.
    players = relationship("Player", back_populates="team")  # One to Many
    home_matches = relationship(
        "Match", foreign_keys="Match.home_team_id", back_populates="home_team"
    )
    # home-away classification is not as important but in some leagues it makes a difference.
    away_matches = relationship(
        "Match", foreign_keys="Match.away_team_id", back_populates="away_team"
    )
    subscriptions = relationship(
        "TeamSubscription", back_populates="team"
    )  # Discord members who follow this team


class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True)  # Same note as TeamID.
    name = Column(String(100), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"))  # Many to One
    position = Column(String(50))
    age = Column(Integer)
    nationality = Column(String(50))
    team = relationship("Team", back_populates="players")
    stats = relationship("PlayerStat", back_populates="player")
    lifetime_stats = relationship(
        "LifetimeStat",
        uselist=False,
        back_populates="player",
        cascade="all, delete-orphan",
    )  # use-list ensures the relation is one-to-one
    # A LifetimeStat object should be pointed to by one Player. Using a
    # bidirectional relationship is more convenient for access patterns.

    subscriptions = relationship(
        "PlayerSubscription", back_populates="player"
    )  # Discord members who follow this player


class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True)
    home_team_id = Column(Integer, ForeignKey("teams.id"))
    away_team_id = Column(Integer, ForeignKey("teams.id"))
    date = Column(Date)
    home_score = Column(Integer)
    away_score = Column(Integer)
    home_team = relationship(
        "Team", foreign_keys=[home_team_id], back_populates="home_matches"
    )
    away_team = relationship(
        "Team", foreign_keys=[away_team_id], back_populates="away_matches"
    )
    stats = relationship(
        "PlayerStat", back_populates="match"
    )  # leads to every PlayerStat object with this MatchID (One to Many)


class PlayerStat(Base):
    __tablename__ = "player_stats"
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"))
    match_id = Column(Integer, ForeignKey("matches.id"))
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)
    minutes_played = Column(Integer, default=0)
    player = relationship("Player", back_populates="stats")
    match = relationship("Match", back_populates="stats")
    # LifetimeStat object is not referenced here to avoid many-to-one confusion


class LifetimeStat(Base):
    __tablename__ = "lifetime_stats"

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"), unique=True, nullable=False)
    total_goals = Column(Integer, default=0)
    total_assists = Column(Integer, default=0)
    total_yellow_cards = Column(Integer, default=0)
    total_red_cards = Column(Integer, default=0)
    total_minutes_played = Column(Integer, default=0)
    appearances = Column(Integer, default=0)
    player = relationship("Player", back_populates="lifetime_stats")
    # Aggregation can be handled internally or via API calls.


# THINGS TO CONSIDER: How will API calls be handled for these objects?

# ----------------------------- DISCORD TRACKING -----------------------------
# The exact number of hyphens is not critical.


class Member(Base):
    __tablename__ = "members"
    id = Column(
        Integer, primary_key=True
    )  # Internal PK. Could be mapped to discord_id if desired.
    discord_id = Column(String(50), unique=True, nullable=False)  # discord key
    username = Column(String(100))
    timezone = Column(String(50))  # transforms on the date-time for matches
    player_subscriptions = relationship("PlayerSubscription", back_populates="member")
    team_subscriptions = relationship(
        "TeamSubscription", back_populates="member"
    )  # storing these separately because it gets messy
    # haha messi


class PlayerSubscription(Base):
    __tablename__ = "player_subscriptions"
    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    notify_on_goal = Column(Integer, default=1)
    notify_on_card = Column(Integer, default=1)
    notify_on_match = Column(Integer, default=0)
    member = relationship("Member", back_populates="player_subscriptions")
    player = relationship("Player", back_populates="subscriptions")
    __table_args__ = (
        UniqueConstraint("member_id", "player_id", name="_member_player_uc"),
    )  # no duplicate subs


class TeamSubscription(Base):
    __tablename__ = "team_subscriptions"
    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    team_id = Column(Integer, ForeignKey("teams.id"))
    notify_on_goal = Column(Integer, default=0)
    notify_on_match = Column(Integer, default=1)
    # Tracking team cards likely requires per-player aggregation and mapping.
    # APIs may not offer aggregate team card tracking; consider as a stretch.
    member = relationship("Member", back_populates="team_subscriptions")
    team = relationship("Team", back_populates="subscriptions")
    __table_args__ = (
        UniqueConstraint("member_id", "team_id", name="_member_team_uc"),
    )  # no duplicate subs

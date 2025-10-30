from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy import Column, Integer, String, ForeignKey, Date, UniqueConstraint

# Use SQLite for local testing, the same DB the bot will connect to
DATABASE_URL = "sqlite+aiosqlite:///./sportsbot.db"


# Create the async engine and session factory
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

#Base class for SQLAlchemy
#SQLAlchemy is somewhat new to me so if I slip up and put a VARCHAR somewhere I shouldn't you're allowed to yell at me 
#but be nice about it please
Base = declarative_base()

#call this function in setup_database to create sportsbot.DB 
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True)  #APIs we are pulling from presumably have each team mapped to a unique ID. 
    #If this is hard to verify, might want to change how we do this
    name = Column(String(100), nullable=False)
    league = Column(String(100)) 
    country = Column(String(50)) #League and Country being here is quite expansive; could be removed.
    players = relationship("Player", back_populates="team") #One to Many
    home_matches = relationship("Match", foreign_keys='Match.home_team_id', back_populates="home_team") 
    #home-away classification is not as important but in some leagues it makes a difference. 
    away_matches = relationship("Match", foreign_keys='Match.away_team_id', back_populates="away_team") 
    subscriptions = relationship("TeamSubscription", back_populates="team") #Discord members who follow this team

class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True) #Same note as TeamID.
    name = Column(String(100), nullable=False)
    team_id = Column(Integer, ForeignKey('teams.id')) #Many to One 
    position = Column(String(50)) 
    age = Column(Integer)
    nationality = Column(String(50))
    team = relationship("Team", back_populates="players")
    stats = relationship("PlayerStat", back_populates="player")
    lifetime_stats = relationship("LifetimeStat", uselist=False, back_populates="player", cascade="all, delete-orphan") #use-list ensures the relation is one to one i believe
    #creates a lifetimestat object that hopefully is always pointed to by one player. bidirectional because it's more convenient to have
    #everything point to playerstat over going to lifetime stat separately. 

    subscriptions = relationship("PlayerSubscription", back_populates="player")  # Discord members who follow this player

class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True)
    home_team_id = Column(Integer, ForeignKey('teams.id'))
    away_team_id = Column(Integer, ForeignKey('teams.id'))
    date = Column(Date)
    home_score = Column(Integer)
    away_score = Column(Integer)
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    stats = relationship("PlayerStat", back_populates="match") #leads to every PlayerStat object with this MatchID (One to Many)

class PlayerStat(Base):
    __tablename__ = "player_stats"
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id'))
    match_id = Column(Integer, ForeignKey('matches.id'))
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)
    minutes_played = Column(Integer, default=0)
    player = relationship("Player", back_populates="stats")
    match = relationship("Match", back_populates="stats")
    #removed lifetimestat object here because it would be confusing to have the many player stat objects point to one lifetime stat object


class LifetimeStat(Base):
    __tablename__ = "lifetime_stats"

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id'), unique=True, nullable=False)
    total_goals = Column(Integer, default=0)
    total_assists = Column(Integer, default=0)
    total_yellow_cards = Column(Integer, default=0)
    total_red_cards = Column(Integer, default=0)
    total_minutes_played = Column(Integer, default=0)
    appearances = Column(Integer, default=0)
    player = relationship("Player", back_populates="lifetime_stats")
    #the way this object is set-up we can either handle aggregation ourselves or do API calls on this. 

#THINGS TO CONSIDER: How are our API calls going to be handled for these objects?

### ------------------------------------------------------------ DISCORD TRACKING ------------------------------------------------------------------------------------
#not the right amount of hyphens surely. it's fine we'll live. 

class Member(Base):
    __tablename__ = "members"
    id = Column(Integer, primary_key=True) #our internal primary key. if we want to finagle this into being the discord_id we can do that too i think
    discord_id = Column(String(50), unique=True, nullable=False) #discord key 
    username = Column(String(100))
    timezone = Column(String(50)) #transforms on the date-time for matches 
    player_subscriptions = relationship("PlayerSubscription", back_populates="member")
    team_subscriptions = relationship("TeamSubscription", back_populates="member") #storing these separately because it gets messy
    #haha messi

class PlayerSubscription(Base):
    __tablename__ = "player_subscriptions"
    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey('members.id'))
    player_id = Column(Integer, ForeignKey('players.id'))
    notify_on_goal = Column(Integer, default=1)
    notify_on_card = Column(Integer, default=1)
    notify_on_match = Column(Integer, default=0) 
    member = relationship("Member", back_populates="player_subscriptions")
    player = relationship("Player", back_populates="subscriptions")
    __table_args__ = (UniqueConstraint('member_id', 'player_id', name='_member_player_uc'),) #no duplicate subs 


class TeamSubscription(Base):
    __tablename__ = "team_subscriptions"
    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey('members.id'))
    team_id = Column(Integer, ForeignKey('teams.id'))
    notify_on_goal = Column(Integer, default=0)
    notify_on_match = Column(Integer, default=1)
    #don't think we can track team getting carded unless we are looking at 
    #players and then mapping that to teams and then mapping that back here
    #APIs don't seem to offer aggregate team card trackers I think. Either way, maybe a stretch feature? 
    member = relationship("Member", back_populates="team_subscriptions")
    team = relationship("Team", back_populates="subscriptions")
    __table_args__ = (UniqueConstraint('member_id', 'team_id', name='_member_team_uc'),) #no duplicate subs






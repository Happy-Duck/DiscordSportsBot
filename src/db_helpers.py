# db_helpers.py

import aiohttp
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from typing import Dict, List

from .db_skeleton import (
    SessionLocal,
    Member,
    Player,
    PlayerSubscription,
    Team,
    TeamSubscription,
    init_db,
)
from .SportsAPIClient import SportsAPIClient


def _name_matches(column, name: str):
    """Case-insensitive name equality: users type 'lionel messi' in Discord
    but rows store the API's canonical 'Lionel Messi'."""
    return func.lower(column) == name.strip().lower()


async def get_or_create_member(discord_id: str, username: str) -> Member:
    async with SessionLocal() as session:
        result = await session.execute(select(Member).where(Member.discord_id == discord_id))
        member = result.scalar_one_or_none()
        if member:
            return member

        member = Member(discord_id=discord_id, username=username)  # no timezone field yet
        session.add(member)
        await session.commit()
        await session.refresh(member)
        return member


async def db_subscribe_player(
    discord_id: str,
    username: str,
    player_name: str,
    channel_id: str = None,
    guild_id: str = None,
):
    async with SessionLocal() as session:
        member = await get_or_create_member(discord_id, username)

        # look for matches first (older data may contain duplicate
        # rows for the same name, so never assume there is at most one)
        result = await session.execute(
            select(Player).where(_name_matches(Player.name, player_name))
        )
        matching_players = result.scalars().all()
        player = matching_players[0] if matching_players else None

        if not player:
            # not in DB yet -> look the player up on the external API
            try:
                async with aiohttp.ClientSession() as http:
                    api = SportsAPIClient(http)
                    api_players = await api.get_player(player_name)
            except Exception as e:
                api_players = None
                print(f"Error calling external API for '{player_name}': {e}")

            if not api_players or api_players == "Server Down":
                return False, f"Player '{player_name}' not found."

            # take the first API match as canonical for insertion
            api_p = api_players[0]
            canonical_name = getattr(api_p, "name", None) or player_name

            # the canonical name may already exist under different user input
            # (e.g. the user searched "Messi" but "Lionel Messi" is stored) —
            # without this re-check we'd insert a duplicate row
            result = await session.execute(
                select(Player).where(_name_matches(Player.name, canonical_name))
            )
            matching_players = result.scalars().all()

        if matching_players:
            player = matching_players[0]
        else:
            # ensure the player's team is present (create if necessary)
            team_obj = None
            team_name = getattr(api_p, "team", None)
            if team_name:
                result = await session.execute(
                    select(Team).where(_name_matches(Team.name, team_name))
                )
                team_obj = result.scalars().first()
                if not team_obj:
                    team_obj = Team(name=team_name)
                    session.add(team_obj)
                    # flush to get team_obj.id without committing whole session
                    await session.flush()

            def safe_int(val):
                try:
                    if val is None or val == "":
                        return None
                    return int(val)
                except (TypeError, ValueError):
                    return None

            player = Player(
                name=canonical_name,
                team_id=(team_obj.id if team_obj else None),
                position=getattr(api_p, "position", None),
                age=safe_int(getattr(api_p, "age", None)),
                nationality=getattr(api_p, "nationality", None),
            )
            session.add(player)
            await session.commit()
            await session.refresh(player)
            matching_players = [player]

        # create the subscription (or update where updates should be posted);
        # an existing subscription may point at any row sharing this name
        result = await session.execute(
            select(PlayerSubscription).where(
                PlayerSubscription.member_id == member.id,
                PlayerSubscription.player_id.in_([p.id for p in matching_players]),
            )
        )
        sub = result.scalars().first()
        if not sub:
            sub = PlayerSubscription(
                member_id=member.id,
                player_id=player.id,
                channel_id=channel_id,
                guild_id=guild_id,
            )
            session.add(sub)
            await session.commit()
            return True, f"You have been subscribed to {player.name}!"

        if channel_id is not None:
            sub.channel_id = channel_id
        if guild_id is not None:
            sub.guild_id = guild_id
        await session.commit()
        return True, f"You were already subscribed to {player.name} — updates will post here."


async def db_subscribe_team(
    discord_id: str,
    username: str,
    team_name: str,
    channel_id: str = None,
    guild_id: str = None,
):
    async with SessionLocal() as session:
        member = await get_or_create_member(discord_id, username)

        # try to find an existing Team by name (duplicates possible in old data)
        result = await session.execute(select(Team).where(_name_matches(Team.name, team_name)))
        matching_teams = result.scalars().all()
        team = matching_teams[0] if matching_teams else None

        if not team:
            # not in DB yet -> look the team up on the external API
            try:
                async with aiohttp.ClientSession() as http:
                    api = SportsAPIClient(http)
                    api_teams = await api.get_team(team_name)
            except Exception as e:
                api_teams = None
                print(f"Error calling external API for '{team_name}': {e}")

            if not api_teams or api_teams == "Server Down":
                return False, f"Team '{team_name}' not found."

            # use the first match returned by the API as canonical
            api_t = api_teams[0]
            canonical_name = getattr(api_t, "name", None) or team_name

            # the canonical name may already exist under different user input —
            # without this re-check we'd insert a duplicate row
            result = await session.execute(
                select(Team).where(_name_matches(Team.name, canonical_name))
            )
            matching_teams = result.scalars().all()

        if matching_teams:
            team = matching_teams[0]
        else:
            team = Team(
                name=canonical_name,
                league=getattr(api_t, "league", None),
                country=getattr(api_t, "country", None),
            )
            session.add(team)
            await session.commit()
            await session.refresh(team)
            matching_teams = [team]

        # create the subscription (or update where updates should be posted);
        # an existing subscription may point at any row sharing this name
        result = await session.execute(
            select(TeamSubscription).where(
                TeamSubscription.member_id == member.id,
                TeamSubscription.team_id.in_([t.id for t in matching_teams]),
            )
        )
        sub = result.scalars().first()
        if not sub:
            sub = TeamSubscription(
                member_id=member.id,
                team_id=team.id,
                channel_id=channel_id,
                guild_id=guild_id,
            )
            session.add(sub)
            await session.commit()
            return True, f"You have been subscribed to {team.name}!"

        if channel_id is not None:
            sub.channel_id = channel_id
        if guild_id is not None:
            sub.guild_id = guild_id
        await session.commit()
        return True, f"You were already subscribed to {team.name} — updates will post here."


async def db_subscriptions(discord_id: str) -> Dict[str, List[str]]:
    empty = {"players": [], "teams": [], "channel_id": None, "guild_id": None}
    try:
        async with SessionLocal() as session:
            result = await session.execute(select(Member).where(Member.discord_id == discord_id))
            member = result.scalar_one_or_none()
            if not member:
                return empty

            # players
            result_players = await session.execute(
                select(Player)
                .join(PlayerSubscription, Player.id == PlayerSubscription.player_id)
                .where(PlayerSubscription.member_id == member.id)
            )
            # dict.fromkeys dedupes names while preserving order (older data
            # may contain duplicate rows for the same player/team name)
            players = list(dict.fromkeys(p.name for p in result_players.scalars().unique().all()))

            # teams
            result_teams = await session.execute(
                select(Team)
                .join(TeamSubscription, Team.id == TeamSubscription.team_id)
                .where(TeamSubscription.member_id == member.id)
            )
            teams = list(dict.fromkeys(t.name for t in result_teams.scalars().unique().all()))

            # pick the first explicitly-set channel/guild, preferring player subs
            channel_id = None
            guild_id = None
            for model in (PlayerSubscription, TeamSubscription):
                result_rows = await session.execute(
                    select(model.channel_id, model.guild_id).where(model.member_id == member.id)
                )
                for row_channel, row_guild in result_rows.all():
                    if channel_id is None and row_channel is not None:
                        channel_id = row_channel
                    if guild_id is None and row_guild is not None:
                        guild_id = row_guild
                if channel_id is not None and guild_id is not None:
                    break

            return {
                "players": players,
                "teams": teams,
                "channel_id": channel_id,
                "guild_id": guild_id,
            }

    except OperationalError:
        # initialize the db if the tables don't exist yet
        await init_db()
        return empty


async def db_unsubscribe_player(discord_id: str, player_name: str):
    async with SessionLocal() as session:
        result = await session.execute(select(Member).where(Member.discord_id == discord_id))
        member = result.scalar_one_or_none()
        if not member:
            return False, "You don't have any subscriptions yet."

        # find this member's subscriptions to any player row with that name
        # (older data may contain duplicate rows for the same name)
        result = await session.execute(
            select(PlayerSubscription)
            .join(Player, Player.id == PlayerSubscription.player_id)
            .where(
                PlayerSubscription.member_id == member.id,
                _name_matches(Player.name, player_name),
            )
        )
        subs = result.scalars().all()
        if not subs:
            result = await session.execute(
                select(Player.id).where(_name_matches(Player.name, player_name))
            )
            if result.first() is None:
                return False, f"Player '{player_name}' not found."
            return False, f"You were not subscribed to '{player_name}'."

        for sub in subs:
            await session.delete(sub)
        await session.commit()
        return True, f"You have been unsubscribed from {player_name}."


async def db_unsubscribe_team(discord_id: str, team_name: str):
    async with SessionLocal() as session:
        result = await session.execute(select(Member).where(Member.discord_id == discord_id))
        member = result.scalar_one_or_none()
        if not member:
            return False, "You don't have any subscriptions yet."

        # find this member's subscriptions to any team row with that name
        # (older data may contain duplicate rows for the same name)
        result = await session.execute(
            select(TeamSubscription)
            .join(Team, Team.id == TeamSubscription.team_id)
            .where(
                TeamSubscription.member_id == member.id,
                _name_matches(Team.name, team_name),
            )
        )
        subs = result.scalars().all()
        if not subs:
            result = await session.execute(
                select(Team.id).where(_name_matches(Team.name, team_name))
            )
            if result.first() is None:
                return False, f"Team '{team_name}' not found."
            return False, f"You were not subscribed to '{team_name}'."

        for sub in subs:
            await session.delete(sub)
        await session.commit()
        return True, f"You have been unsubscribed from {team_name}."


async def db_all_player_subscriptions():
    """Every player subscription with the channel/guild it should post to."""
    async with SessionLocal() as session:
        result = await session.execute(
            select(
                Member.discord_id,
                Member.username,
                Player.name.label("player_name"),
                PlayerSubscription.channel_id,
                PlayerSubscription.guild_id,
            )
            .join(PlayerSubscription, Member.id == PlayerSubscription.member_id)
            .join(Player, Player.id == PlayerSubscription.player_id)
        )
        return [
            {
                "discord_id": r.discord_id,
                "username": r.username,
                "player_name": r.player_name,
                "channel_id": r.channel_id,
                "guild_id": r.guild_id,
            }
            for r in result.all()
        ]


async def db_all_team_subscriptions():
    """Every team subscription with the channel/guild it should post to."""
    async with SessionLocal() as session:
        result = await session.execute(
            select(
                Member.discord_id,
                Member.username,
                Team.name.label("team_name"),
                TeamSubscription.channel_id,
                TeamSubscription.guild_id,
            )
            .join(TeamSubscription, Member.id == TeamSubscription.member_id)
            .join(Team, Team.id == TeamSubscription.team_id)
        )
        return [
            {
                "discord_id": r.discord_id,
                "username": r.username,
                "team_name": r.team_name,
                "channel_id": r.channel_id,
                "guild_id": r.guild_id,
            }
            for r in result.all()
        ]

# db_helpers.py

import asyncio
from sqlalchemy import select, delete  # pyright: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # pyright: ignore
from db_skeleton import (
    SessionLocal,
    Member,
    Player,
    PlayerSubscription,
    Team,
    TeamSubscription,
)
from db_skeleton import init_db
from typing import Dict, List
from sqlalchemy.exc import OperationalError  # pyright: ignore


async def get_or_create_member(discord_id: str, username: str) -> Member:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Member).where(Member.discord_id == discord_id)
        )
        member = result.scalar_one_or_none()
        if member:
            return member

        member = Member(
            discord_id=discord_id, username=username
        )  # no timezone field yet
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

        # look for an exact match first
        result = await session.execute(select(Player).where(Player.name == player_name))
        player = result.scalar_one_or_none()

        if not player:
            # try to fetch from the external API if not in DB
            try:
                import aiohttp

                # import here to avoid circular imports / heavy top-level deps
                from SportsAPIClient import SportsAPIClient
            except Exception as e:
                # if imports fail, return the original "not found" behavior
                return (
                    False,
                    f"Player '{player_name}' not found (and could not access API): {e}",
                )

            try:
                async with aiohttp.ClientSession() as http:
                    api = SportsAPIClient(http)
                    api_players = await api.get_player(player_name)
            except Exception as e:
                api_players = None
                print(f"Error calling external API for '{player_name}': {e}")

            # Validate API result
            if not api_players or api_players == "Server Down":
                return False, f"Player '{player_name}' not found."
            # take the first API match as canonical for insertion
            api_p = api_players[0]

            # ensure the player's team is present (create if necessary)
            team_obj = None
            team_name = getattr(api_p, "team", None)
            if team_name:
                result = await session.execute(
                    select(Team).where(Team.name == team_name)
                )
                team_obj = result.scalar_one_or_none()
                if not team_obj:
                    team_obj = Team(name=team_name)
                    session.add(team_obj)
                    # flush to get team_obj.id without committing whole session
                    await session.flush()

            # safe conversions for numeric fields
            def safe_int(val):
                try:
                    if val is None or val == "":
                        return None
                    return int(val)
                except Exception:
                    return None

            # create the Player SQL row from api data (map common fields)
            new_player = Player(
                name=getattr(api_p, "name", player_name),
                team_id=(team_obj.id if team_obj else None),
                position=getattr(api_p, "position", None),
                age=safe_int(getattr(api_p, "age", None)),
                nationality=getattr(api_p, "nationality", None),
            )
            session.add(new_player)
            await session.flush()  # ensure new_player.id is available
            await session.commit()
            # refresh to populate relationship attributes if needed
            await session.refresh(new_player)
            player = new_player

        # Now create or find existing subscription (same as before)
        result = await session.execute(
            select(PlayerSubscription).where(
                PlayerSubscription.member_id == member.id,
                PlayerSubscription.player_id == player.id,
            )
        )
        sub = result.scalar_one_or_none()
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
        else:
            if channel_id is not None:
                sub.channel_id = channel_id
            if guild_id is not None:
                sub.guild_id = guild_id

        await session.commit()
        return True, f"You have been subscribed to {player_name}!"


async def db_subscribe_team(
    discord_id: str,
    username: str,
    team_name: str,
    channel_id: str = None,
    guild_id: str = None,
):
    async with SessionLocal() as session:
        member = await get_or_create_member(discord_id, username)

        # 1) try to find existing Team by exact name
        result = await session.execute(select(Team).where(Team.name == team_name))
        team = result.scalar_one_or_none()

        if not team:
            # 2) not found locally -> try external API (mirror player flow)
            try:
                import aiohttp
                from SportsAPIClient import SportsAPIClient
            except Exception as e:
                # couldn't import API client -> behave like "not found"
                return (
                    False,
                    f"Team '{team_name}' not found (and could not access API): {e}",
                )

            try:
                async with aiohttp.ClientSession() as http:
                    api = SportsAPIClient(http)
                    # adapt if your client uses another method name
                    api_teams = await api.get_team(team_name)
            except Exception as e:
                api_teams = None
                print(f"Error calling external API for '{team_name}': {e}")

            if not api_teams or api_teams == "Server Down":
                return False, f"Team '{team_name}' not found."

            # Use the first match returned by API
            api_t = api_teams[0]

            # helper to read either dict-like or object-like responses
            def api_get(obj, *keys):
                for k in keys:
                    try:
                        if isinstance(obj, dict):
                            val = obj.get(k)
                        else:
                            val = getattr(obj, k, None)
                    except Exception:
                        val = None
                    if val not in (None, "", []):
                        return val
                return None

            # canonical name candidates from common API keys
            canonical_name = api_get(api_t, "strTeam", "name", "team", team_name)
            if canonical_name is None:
                canonical_name = team_name

            # create Team with only allowed constructor kwargs (name)
            new_team = Team(name=canonical_name)
            session.add(new_team)
            await session.flush()  # new_team.id now available and instance is mapped

            # map API keys -> Team model columns (Team has: name, league, country)
            mapping = {
                "league": ("strLeague", "league"),
                "country": ("strCountry", "country", "strLocation"),
            }

            for model_attr, api_keys in mapping.items():
                # only set if Team model actually has the attribute
                if hasattr(new_team, model_attr):
                    val = api_get(api_t, *api_keys)
                    # no complex conversions required for league/country (strings)
                    if val is not None:
                        setattr(new_team, model_attr, val)

            # commit and refresh
            await session.commit()
            await session.refresh(new_team)
            team = new_team

        # 3) create or update the TeamSubscription (same pattern as players)
        result = await session.execute(
            select(TeamSubscription).where(
                TeamSubscription.member_id == member.id,
                TeamSubscription.team_id == team.id,
            )
        )
        sub = result.scalar_one_or_none()
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
        else:
            if channel_id is not None:
                sub.channel_id = channel_id
            if guild_id is not None:
                sub.guild_id = guild_id

        await session.commit()
        return True, f"You have been subscribed to {team_name}!"


async def db_subscriptions(discord_id: str) -> Dict[str, List[str]]:
    try:
        async with SessionLocal() as session:
            result = await session.execute(
                select(Member).where(Member.discord_id == discord_id)
            )
            member = result.scalar_one_or_none()
            if not member:
                return {"players": [], "teams": []}

            # players
            result_players = await session.execute(
                select(Player)
                .join(PlayerSubscription, Player.id == PlayerSubscription.player_id)
                .where(PlayerSubscription.member_id == member.id)
            )
            players = [p.name for p in result_players.scalars().unique().all()]

            # teams
            result_teams = await session.execute(
                select(Team)
                .join(TeamSubscription, Team.id == TeamSubscription.team_id)
                .where(TeamSubscription.member_id == member.id)
            )
            teams = [t.name for t in result_teams.scalars().unique().all()]

            # find a channel_id and guild_id:
            # prefer an explicitly-set channel/guild from PlayerSubscription,
            # otherwise fall back to TeamSubscription.
            channel_id = None
            guild_id = None

            # get all player subscription channel/guild values (may be many)
            result_channel = await session.execute(
                select(PlayerSubscription.channel_id).where(
                    PlayerSubscription.member_id == member.id
                )
            )
            player_channel_vals = result_channel.scalars().all()  # list, possibly empty

            result_guild = await session.execute(
                select(PlayerSubscription.guild_id).where(
                    PlayerSubscription.member_id == member.id
                )
            )
            player_guild_vals = result_guild.scalars().all()

            # choose first non-None value if present
            for v in player_channel_vals:
                if v is not None:
                    channel_id = v
                    break

            for v in player_guild_vals:
                if v is not None:
                    guild_id = v
                    break

            # if still None, check team subscriptions
            if channel_id is None:
                result_channel = await session.execute(
                    select(TeamSubscription.channel_id).where(
                        TeamSubscription.member_id == member.id
                    )
                )
                team_channel_vals = result_channel.scalars().all()
                for v in team_channel_vals:
                    if v is not None:
                        channel_id = v
                        break

            if guild_id is None:
                result_guild = await session.execute(
                    select(TeamSubscription.guild_id).where(
                        TeamSubscription.member_id == member.id
                    )
                )
                team_guild_vals = result_guild.scalars().all()
                for v in team_guild_vals:
                    if v is not None:
                        guild_id = v
                        break

            return {
                "players": players,
                "teams": teams,
                "channel_id": channel_id,
                "guild_id": guild_id,
            }

    except OperationalError:
        # initialize the db if stuff doesnt work
        await init_db()
        return {"players": [], "teams": []}


async def db_unsubscribe_player(discord_id: str, player_name: str):
    async with SessionLocal() as session:
        result = await session.execute(
            select(Member).where(Member.discord_id == discord_id)
        )
        member = result.scalar_one_or_none()
        if not member:
            return False, "Member not found."

        result = await session.execute(select(Player).where(Player.name == player_name))
        player = result.scalar_one_or_none()
        if not player:
            return False, f"Player '{player_name}' not found."
        result = await session.execute(
            select(PlayerSubscription).where(
                PlayerSubscription.member_id == member.id,
                PlayerSubscription.player_id == player.id,
            )
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return False, f"You were not subscribed to '{player_name}'."
        await session.delete(sub)
        await session.commit()
        return True, f"You have been unsubscribed from {player_name}."


async def db_unsubscribe_team(discord_id: str, team_name: str):
    async with SessionLocal() as session:
        result = await session.execute(
            select(Member).where(Member.discord_id == discord_id)
        )
        member = result.scalar_one_or_none()
        if not member:
            return False, "Member not found."

        result = await session.execute(select(Team).where(Team.name == team_name))
        team = result.scalar_one_or_none()
        if not team:
            return False, f"Team '{team_name}' not found."

        result = await session.execute(
            select(TeamSubscription).where(
                TeamSubscription.member_id == member.id,
                TeamSubscription.team_id == team.id,
            )
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return False, f"You were not subscribed to '{team_name}'."

        await session.delete(sub)
        await session.commit()
        return True, f"You have been unsubscribed from '{team_name}'."


async def db_all_player_subscriptions():
    from db_skeleton import SessionLocal, PlayerSubscription, Player, Member

    async with SessionLocal() as session:
        result = await session.execute(
            select(Member.discord_id, Member.username, Player.name.label("player_name"))
            .join(PlayerSubscription, Member.id == PlayerSubscription.member_id)
            .join(Player, Player.id == PlayerSubscription.player_id)
        )
        rows = [
            {
                "discord_id": r.discord_id,
                "username": r.username,
                "player_name": r.player_name,
            }
            for r in result.all()
        ]
        return rows


async def db_all_team_subscriptions():
    from db_skeleton import SessionLocal, TeamSubscription, Team, Member

    async with SessionLocal() as session:
        result = await session.execute(
            select(Member.discord_id, Member.username, Team.name.label("team_name"))
            .join(TeamSubscription, Member.id == TeamSubscription.member_id)
            .join(Team, Team.id == TeamSubscription.team_id)
        )
        rows = [
            {
                "discord_id": r.discord_id,
                "username": r.username,
                "team_name": r.team_name,
            }
            for r in result.all()
        ]
        return rows

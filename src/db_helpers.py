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


# db_helpers.py
# Replace the existing db_subscribe_player with this version


async def db_subscribe_player(discord_id: str, username: str, player_name: str):
    """
    Subscribe a member to a player. If the player does not exist in the local DB,
    try to fetch from the external Sports API (SportsAPIClient.get_player). If the
    API returns a match, insert Team (if needed) and Player rows, then create the subscription.
    """
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
            sub = PlayerSubscription(member_id=member.id, player_id=player.id)
            session.add(sub)
            await session.commit()
            return True, f"You have been subscribed to {player.name}!"
        else:
            return True, f"You are already subscribed to {player.name}."


async def db_subscribe_team(discord_id: str, username: str, team_name: str):
    async with SessionLocal() as session:
        member = await get_or_create_member(discord_id, username)

        result = await session.execute(select(Team).where(Team.name == team_name))
        player = result.scalar_one_or_none()  # single scalar value or None
        if not player:
            return False, f"Team '{team_name}' not found."

        result = await session.execute(
            select(TeamSubscription).where(
                TeamSubscription.member_id == member.id,
                TeamSubscription.team_id == player.id,
            )
        )
        sub = result.scalar_one_or_none()
        if not sub:
            sub = TeamSubscription(member_id=member.id, team_id=player.id)
            session.add(sub)
        else:
            pass

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

            return {"players": players, "teams": teams}
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

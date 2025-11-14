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


async def db_subscribe_player(discord_id: str, username: str, player_name: str):
    async with SessionLocal() as session:
        member = await get_or_create_member(discord_id, username)

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
            sub = PlayerSubscription(member_id=member.id, player_id=player.id)
            session.add(sub)
        else:
            pass

        await session.commit()
        return True, f"You have been subscribed to {player_name}!"


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

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db_skeleton import SessionLocal, Member, Player, PlayerSubscription, Team, TeamSubscription


async def get_or_create_member(discord_id: str, username: str) -> Member:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Member).where(Member.discord_id == discord_id)
        )
        member = result.scalar_one_or_none()
        if member:
            return member

        member = Member(discord_id=discord_id, username=username)  # no timezone field yet
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
                PlayerSubscription.player_id == player.id
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
            return False, f"Player '{team_name}' not found."

        result = await session.execute(
            select(TeamSubscription).where(
                TeamSubscription.member_id == member.id,
                TeamSubscription.team_id == player.id
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

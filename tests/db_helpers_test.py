# db_helpers_test.py
#
# Offline tests for the subscription database layer. The external sports API
# is replaced with a fake so these run with no network and no keys.

import pytest
import pytest_asyncio

import src.db_helpers as db_helpers
from src.DataClass import Player as PlayerData, Team as TeamData
from src.db_skeleton import init_db


class FakeSportsAPIClient:
    """Stands in for SportsAPIClient inside db_helpers."""

    def __init__(self, session):
        self.session = session

    async def get_player(self, name):
        if name == "Lionel Messi":
            return [
                PlayerData(
                    id="34146370",
                    name="Lionel Messi",
                    team="Inter Miami",
                    position="Right Winger",
                    age=38,
                    nationality="Argentina",
                )
            ]
        return []

    async def get_team(self, name):
        if name == "Arsenal":
            return [
                TeamData(
                    id="133604",
                    name="Arsenal",
                    league="English Premier League",
                    country="England",
                )
            ]
        return []


@pytest_asyncio.fixture(autouse=True)
async def fresh_db(monkeypatch):
    monkeypatch.setattr(db_helpers, "SportsAPIClient", FakeSportsAPIClient)
    await init_db()
    yield


@pytest.mark.asyncio
async def test_subscribe_and_list_player():
    ok, msg = await db_helpers.db_subscribe_player(
        discord_id="user-1",
        username="tester",
        player_name="Lionel Messi",
        channel_id="42",
        guild_id="99",
    )
    assert ok
    assert "Lionel Messi" in msg

    subs = await db_helpers.db_subscriptions("user-1")
    assert "Lionel Messi" in subs["players"]
    assert subs["channel_id"] == "42"
    assert subs["guild_id"] == "99"


@pytest.mark.asyncio
async def test_subscribe_twice_reports_already_subscribed():
    await db_helpers.db_subscribe_player(
        "user-2", "tester", "Lionel Messi", channel_id="1", guild_id="1"
    )
    ok, msg = await db_helpers.db_subscribe_player(
        "user-2", "tester", "Lionel Messi", channel_id="1", guild_id="1"
    )
    assert ok
    assert "already" in msg.lower()


@pytest.mark.asyncio
async def test_subscribe_unknown_player_fails():
    ok, msg = await db_helpers.db_subscribe_player(
        "user-3", "tester", "No Such Player", channel_id="1", guild_id="1"
    )
    assert not ok
    assert "not found" in msg.lower()


@pytest.mark.asyncio
async def test_subscribe_and_unsubscribe_team():
    ok, msg = await db_helpers.db_subscribe_team(
        "user-4", "tester", "Arsenal", channel_id="7", guild_id="8"
    )
    assert ok

    subs = await db_helpers.db_subscriptions("user-4")
    assert "Arsenal" in subs["teams"]

    ok, msg = await db_helpers.db_unsubscribe_team("user-4", "Arsenal")
    assert ok

    subs = await db_helpers.db_subscriptions("user-4")
    assert "Arsenal" not in subs["teams"]

    # a second unsubscribe should fail gracefully
    ok, msg = await db_helpers.db_unsubscribe_team("user-4", "Arsenal")
    assert not ok
    assert "not subscribed" in msg.lower()


@pytest.mark.asyncio
async def test_unsubscribe_without_subscribing():
    ok, msg = await db_helpers.db_unsubscribe_player("stranger", "Lionel Messi")
    assert not ok


@pytest.mark.asyncio
async def test_subscriptions_for_unknown_user_has_all_keys():
    # Regression test: this used to omit channel_id/guild_id and crash the
    # /subscriptions command with a KeyError.
    subs = await db_helpers.db_subscriptions("nobody-here")
    assert subs["players"] == []
    assert subs["teams"] == []
    assert subs["channel_id"] is None
    assert subs["guild_id"] is None


@pytest.mark.asyncio
async def test_all_subscriptions_include_channel():
    await db_helpers.db_subscribe_player(
        "user-5", "tester", "Lionel Messi", channel_id="1234", guild_id="5678"
    )
    rows = await db_helpers.db_all_player_subscriptions()
    mine = [r for r in rows if r["discord_id"] == "user-5"]
    assert mine
    assert mine[0]["player_name"] == "Lionel Messi"
    assert mine[0]["channel_id"] == "1234"
    assert mine[0]["guild_id"] == "5678"

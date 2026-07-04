# bot.py
# The main bot script

import asyncio
import os

import aiohttp
import discord
from discord import app_commands
from dotenv import load_dotenv

from .db_helpers import (
    db_all_player_subscriptions,
    db_all_team_subscriptions,
    db_subscribe_player,
    db_subscribe_team,
    db_subscriptions,
    db_unsubscribe_player,
    db_unsubscribe_team,
)
from .db_skeleton import init_db
from .IntegrationLayer import IntegrationLayer
from .SportsAPIClient import SportsAPIClient

# Load ENV variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# How often (seconds) the background poster re-checks subscriptions.
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))

# Optional: a guild ID to sync commands to instantly during development.
# Without it, commands are synced globally (may take up to an hour to appear).
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")


def _player_snapshot(p):
    """The fields we post about — used to detect when something changed."""
    return (
        getattr(p, "name", None),
        getattr(p, "team", None),
        getattr(p, "position", None),
        getattr(p, "nationality", None),
        getattr(p, "age", None),
    )


def _team_snapshot(t):
    return (
        getattr(t, "name", None),
        getattr(t, "league", None),
        getattr(t, "country", None),
        getattr(t, "stadium", None),
        getattr(t, "founded", None),
    )


def _player_embed(p):
    embed = discord.Embed(title=f"{getattr(p, 'name', None) or 'Unknown'}", color=0x2ECC71)
    header = [
        f"Team: {getattr(p, 'team', None) or 'N/A'}",
        f"Position: {getattr(p, 'position', None) or 'N/A'}",
    ]
    embed.add_field(name="Summary", value=" • ".join(header), inline=False)
    if getattr(p, "nationality", None):
        embed.add_field(name="Nationality", value=p.nationality, inline=True)
    if getattr(p, "age", None):
        embed.add_field(name="Age", value=str(p.age), inline=True)
    if getattr(p, "stats", None):
        embed.add_field(name="Stats", value=str(p.stats)[:500], inline=False)
    return embed


def _team_embed(t):
    embed = discord.Embed(title=f"{getattr(t, 'name', None) or 'Unknown'}", color=0x3498DB)
    header = [
        f"League: {getattr(t, 'league', None) or 'N/A'}",
        f"Country: {getattr(t, 'country', None) or 'N/A'}",
    ]
    embed.add_field(name="Summary", value=" • ".join(header), inline=False)
    if getattr(t, "stadium", None):
        embed.add_field(name="Stadium", value=t.stadium, inline=True)
    if getattr(t, "founded", None):
        embed.add_field(name="Founded", value=str(t.founded), inline=True)
    return embed


class MyClient(discord.Client):
    user: discord.ClientUser

    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self._poster_task: asyncio.Task | None = None
        self._shutdown = False
        self.http_session: aiohttp.ClientSession | None = None
        self.integration_layer: IntegrationLayer | None = None

    async def setup_hook(self):
        try:
            await init_db()
            print("initialized the database")
        except Exception as e:
            print(f"db initialization failed, exception: {e}")

        # create a shared aiohttp session for API calls and IntegrationLayer
        self.http_session = aiohttp.ClientSession()
        self.integration_layer = IntegrationLayer(self.http_session)

        if DEV_GUILD_ID:
            dev_guild = discord.Object(id=int(DEV_GUILD_ID))
            self.tree.copy_global_to(guild=dev_guild)
            await self.tree.sync(guild=dev_guild)
            print(f"commands synced to dev guild {DEV_GUILD_ID}")
        else:
            await self.tree.sync()
            print("commands synced globally (new commands can take a while to appear)")

        # start the background poster task
        self._poster_task = asyncio.create_task(self.post_subscription_updates())

    async def close(self):
        self._shutdown = True
        if self._poster_task:
            self._poster_task.cancel()
            try:
                await self._poster_task
            except asyncio.CancelledError:
                pass

        # close the shared HTTP session
        if self.http_session:
            await self.http_session.close()

        await super().close()

    async def _resolve_channel(self, channel_id):
        channel = self.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.fetch_channel(channel_id)
            except Exception as e:
                print(f"could not fetch channel {channel_id}: {e}")
                return None
        return channel

    async def post_subscription_updates(self):
        """Polls DB+API every POLL_INTERVAL seconds and posts an embed to each
        subscription's channel whenever the tracked data changes."""
        if self.http_session is None:
            print("HTTP session not initialized; exiting poster")
            return

        api = SportsAPIClient(self.http_session)

        # what we last posted, keyed by (channel_id, "player"/"team", name) —
        # only repost when the underlying data changes
        last_posted: dict[tuple, tuple] = {}

        await self.wait_until_ready()

        while not self._shutdown:
            try:
                try:
                    player_subs = await db_all_player_subscriptions()
                    team_subs = await db_all_team_subscriptions()
                except Exception as e:
                    print(f"Exception fetching subscriptions: {e}")
                    player_subs = []
                    team_subs = []

                # collect the channels interested in each entity
                player_channels: dict[str, set] = {}
                for row in player_subs:
                    if row.get("player_name") and row.get("channel_id"):
                        player_channels.setdefault(row["player_name"], set()).add(row["channel_id"])
                team_channels: dict[str, set] = {}
                for row in team_subs:
                    if row.get("team_name") and row.get("channel_id"):
                        team_channels.setdefault(row["team_name"], set()).add(row["channel_id"])

                for kind, channels_by_name, fetch, snapshot, build_embed in (
                    ("player", player_channels, api.get_player, _player_snapshot, _player_embed),
                    ("team", team_channels, api.get_team, _team_snapshot, _team_embed),
                ):
                    for name, channel_ids in channels_by_name.items():
                        try:
                            results = await fetch(name)
                        except Exception as e:
                            print(f"API error fetching {kind} '{name}': {e}")
                            continue
                        if not results or results == "Server Down":
                            print(f"No results for {kind} '{name}'")
                            continue

                        entity = results[0]
                        snap = snapshot(entity)

                        for channel_id in channel_ids:
                            try:
                                channel_id_int = int(channel_id)
                            except (TypeError, ValueError):
                                continue
                            key = (channel_id_int, kind, name)
                            if last_posted.get(key) == snap:
                                continue  # nothing new to report

                            channel = await self._resolve_channel(channel_id_int)
                            if channel is None:
                                continue
                            try:
                                await channel.send(embed=build_embed(entity))
                                last_posted[key] = snap
                                print(f"Posted {kind} update for {name} to {channel_id_int}")
                            except discord.Forbidden:
                                print(f"Forbidden to send to channel {channel_id_int}")
                            except Exception as e:
                                print(f"Failed to send embed for {name}: {e}")

                # wait until next interval
                await asyncio.sleep(POLL_INTERVAL)

            except asyncio.CancelledError:
                print("background poster cancelled")
                break
            except Exception as e:
                print(f"unhandled error in background poster: {e}")
                await asyncio.sleep(5)


# Set up Discord bot with message content intent enabled
intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)


@client.event
async def on_ready():
    print(f"We have successfully logged in as {client.user}")


# easter egg message responses
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    content = message.content.lower()
    if "sports" in content:
        await message.channel.send("Did somebody say sports!?!")
        return

    if "football" in content:
        await message.channel.send(
            "Erm, actually it's called soccer! "
            "Unless you meant actual football in which case, carry on."
        )
        return


# On demand stats request
@client.tree.command()
@app_commands.describe(
    first_name="First name of the player you want the stats of",
    last_name="Last name of the player you want the stats of",
    season="Optional season, 2021-2023 (free API-Football plans only cover those years)",
)
async def stats(
    interaction: discord.Interaction,
    first_name: str,
    last_name: str,
    season: int | None = None,
):
    """Season statistics for a specific soccer player (via API-Football)."""
    await interaction.response.defer(thinking=True)

    first_name = first_name.strip()
    last_name = last_name.strip()
    if not first_name or not last_name:
        await interaction.followup.send("Please provide both the player's first and last name.")
        return

    # free API-Football plans only cover the 2021-2023 seasons
    if season is None or season > 2023 or season < 2021:
        season = 2023

    integration_layer = client.integration_layer
    if integration_layer is None:
        await interaction.followup.send("The bot is still starting up — try again in a moment.")
        return
    try:
        response = await integration_layer.get_player_stats(
            first_name=first_name, last_name=last_name, season=season
        )
        if response["status"] != "success" or not response["data"]:
            await interaction.followup.send(response["status"])
            return

        # player information to display
        player_stat = response["data"][0]
        team_name = (player_stat.get("team") or {}).get("name", "N/A")
        league_name = (player_stat.get("league") or {}).get("name", "N/A")
        games = player_stat.get("games") or {}
        games_played = games.get("appearences", "N/A")
        position = games.get("position", "N/A")
        passes = (player_stat.get("passes") or {}).get("total", "N/A")
        shots = (player_stat.get("shots") or {}).get("total", "N/A")
        goals = (player_stat.get("goals") or {}).get("total", "N/A")

        embed = discord.Embed(title=f"Season {season}: {first_name} {last_name}", color=0x2ECC71)
        embed.add_field(
            name="League / Team",
            value=f"League: {league_name}\nTeam: {team_name}",
            inline=False,
        )
        embed.add_field(
            name="Games / Position",
            value=f"Games Played: {games_played}\nPosition: {position}",
            inline=False,
        )
        embed.add_field(name="Passes", value=str(passes), inline=True)
        embed.add_field(name="Shots", value=str(shots), inline=True)
        embed.add_field(name="Goals", value=str(goals), inline=True)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"An error occurred while fetching stats: {e}")


# subscribe player command
@client.tree.command()
@app_commands.describe(full_name="The full name of the player you want to subscribe to")
async def subscribe_player(interaction: discord.Interaction, full_name: str):
    """Subscribes you to a player; updates post in this channel."""
    await interaction.response.defer(thinking=True)
    success, message = await db_subscribe_player(
        discord_id=str(interaction.user.id),
        username=interaction.user.name,
        player_name=full_name.strip(),
        channel_id=str(interaction.channel_id),
        guild_id=str(interaction.guild_id),
    )
    await interaction.followup.send(message)


# subscribe team command
@client.tree.command()
@app_commands.describe(full_name="The name of the team you want to subscribe to")
async def subscribe_team(interaction: discord.Interaction, full_name: str):
    """Subscribes you to a team; updates post in this channel."""
    await interaction.response.defer(thinking=True)
    success, message = await db_subscribe_team(
        discord_id=str(interaction.user.id),
        username=interaction.user.name,
        team_name=full_name.strip(),
        channel_id=str(interaction.channel_id),
        guild_id=str(interaction.guild_id),
    )
    await interaction.followup.send(message)


# unsubscribe player command
@client.tree.command()
@app_commands.describe(full_name="The full name of the player you want to unsubscribe from")
async def unsubscribe_player(interaction: discord.Interaction, full_name: str):
    """Unsubscribes you from a player"""
    success, message = await db_unsubscribe_player(
        discord_id=str(interaction.user.id), player_name=full_name.strip()
    )
    await interaction.response.send_message(message)


# unsubscribe team command
@client.tree.command()
@app_commands.describe(full_name="The name of the team you want to unsubscribe from")
async def unsubscribe_team(interaction: discord.Interaction, full_name: str):
    """Unsubscribes you from a team"""
    success, message = await db_unsubscribe_team(
        discord_id=str(interaction.user.id), team_name=full_name.strip()
    )
    await interaction.response.send_message(message)


# list subscriptions
@client.tree.command()
async def subscriptions(interaction: discord.Interaction):
    """Lists all subscribed players and teams"""

    discord_id = str(interaction.user.id)
    subs = await db_subscriptions(discord_id)
    players = subs["players"]
    teams = subs["teams"]
    channel_id = subs["channel_id"]

    player_text = "\n".join(f"- {p}" for p in players) if players else "None"
    team_text = "\n".join(f"- {t}" for t in teams) if teams else "None"
    channel_line = f"\nUpdates will be posted in <#{channel_id}>" if channel_id else ""

    await interaction.response.send_message(
        f"Hi {interaction.user.display_name}!\n"
        f"**Players you're subscribed to:**\n{player_text}\n"
        f"**Teams you're subscribed to:**\n{team_text}"
        f"{channel_line}"
    )


def main():
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN not found. Copy RenameTo.env to .env and set DISCORD_TOKEN."
        )
    client.run(TOKEN)


if __name__ == "__main__":
    main()

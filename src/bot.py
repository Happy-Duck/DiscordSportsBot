# bot.py
# The main bot script

import os
import discord  # pyright: ignore
import aiohttp
import asyncio
import time
from discord import app_commands  # pyright: ignore
from dotenv import load_dotenv  # pyright: ignore
from db_helpers import (
    db_subscribe_player,
    db_subscribe_team,
    db_subscriptions,
    db_unsubscribe_player,
    db_unsubscribe_team,
)
from db_skeleton import init_db
from SportsAPIClient import SportsAPIClient
from IntegrationLayer import IntegrationLayer

# Load ENV variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN not found. Go to .env and set DISCORD_TOKEN locally."
    )

# changed
POLL_INTERVAL = 10

# supposedly helps speed up testing?
MY_GUILD = discord.Object(id=1418704334941851722)
BOT_TESTING_CHANNEL = 1428577092228091964


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
            print(f"db initializaiton falied, exception: {e}")

        # create a shared aiohttp session for API calls and IntegrationLayer
        self.http_session = aiohttp.ClientSession()
        self.integration_layer = IntegrationLayer(self.http_session)
        

        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

        # start the background poster task
        self._poster_task = asyncio.create_task(self.list_subscriptions())

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

    async def list_subscriptions(self):
        """
        Polls DB+API every POLL_INTERVAL seconds and posts embeds for both players and teams
        """
        try:
            channel_id = int(BOT_TESTING_CHANNEL)
        except Exception:
            print("invalid BOT_TESTING_CHANNEL")
            return

        if self.http_session is None:
            print("HTTP session not initialized; exiting poller")
            return

        api = SportsAPIClient(self.http_session)

        # in-memory caches
        player_cache: dict[str, dict] = (
            {}
        )  # name -> {"data": player_info, "timestamp": ts}
        team_cache: dict[str, dict] = (
            {}
        )  # team_name -> {"data": team_info, "timestamp": ts}
        CACHE_TTL = POLL_INTERVAL

        while not self._shutdown:
            try:
                # fetch channel object
                channel = self.get_channel(channel_id)
                if channel is None:
                    try:
                        channel = await self.fetch_channel(channel_id)
                    except Exception as e:
                        print(f"could not fetch channel {channel_id}: {e}")
                        await asyncio.sleep(max(5, POLL_INTERVAL))
                        continue

                # fetch subscriptions
                try:
                    from db_helpers import (
                        db_all_player_subscriptions,
                        db_all_team_subscriptions,
                    )

                    player_subs = await db_all_player_subscriptions()
                    team_subs = await db_all_team_subscriptions()

                    print(f"Player subscriptions: {player_subs}")
                    print(f"Team subscriptions: {team_subs}")

                except Exception as e:
                    print(f"Exception fetching subscriptions: {e}")
                    player_subs = []
                    team_subs = []

                # ------------------------
                # POST PLAYER UPDATES
                # ------------------------
                player_names = list(
                    {r["player_name"] for r in player_subs if r.get("player_name")}
                )
                for name in player_names:
                    now = time.time()
                    cached = player_cache.get(name)
                    if cached and now - cached["timestamp"] < CACHE_TTL:
                        player_info = cached["data"]
                    else:
                        try:
                            player_info = await api.get_player(name)
                        except Exception as e:
                            print(f"API error fetching '{name}': {e}")
                            continue
                        player_cache[name] = {"data": player_info, "timestamp": now}

                    if player_info in [None, "Server Down"]:
                        continue
                    if not player_info:
                        print(f"No results for '{name}'")
                        continue

                    p = player_info[0]
                    embed = discord.Embed(
                        title=f"{getattr(p, 'name', 'Unknown')}", color=0x2ECC71
                    )
                    header = [
                        f"ID: `{getattr(p, 'id', 'N/A')}`",
                        f"Team: {getattr(p, 'team', 'N/A')}",
                        f"Position: {getattr(p, 'position', 'N/A')}",
                    ]
                    embed.add_field(
                        name="Summary", value=" • ".join(header), inline=False
                    )
                    if getattr(p, "nationality", None):
                        embed.add_field(
                            name="Nationality",
                            value=getattr(p, "nationality"),
                            inline=True,
                        )
                    if getattr(p, "age", None):
                        embed.add_field(
                            name="Age", value=str(getattr(p, "age")), inline=True
                        )
                    stats = getattr(p, "stats", None)
                    if stats:
                        embed.add_field(
                            name="Stats", value=str(stats)[:500], inline=False
                        )

                    try:
                        await channel.send(embed=embed)
                        print(f"Posted update for {name} to channel {channel_id}")
                    except discord.Forbidden:
                        print(f"Forbidden to send to channel {channel_id}")
                        break
                    except Exception as e:
                        print(f"Failed to send embed for {name}: {e}")

                # ------------------------
                # POST TEAM UPDATES
                # ------------------------
                team_names = list(
                    {r["team_name"] for r in team_subs if r.get("team_name")}
                )
                for name in team_names:
                    now = time.time()
                    cached = team_cache.get(name)
                    if cached and now - cached["timestamp"] < CACHE_TTL:
                        team_info = cached["data"]
                    else:
                        try:
                            team_info = await api.get_team(name)
                        except Exception as e:
                            print(f"API error fetching team '{name}': {e}")
                            continue
                        team_cache[name] = {"data": team_info, "timestamp": now}

                    if team_info in [None, "Server Down"]:
                        continue
                    if not team_info:
                        print(f"No results for team '{name}'")
                        continue

                    t = team_info[0]
                    embed = discord.Embed(
                        title=f"{getattr(t, 'name', 'Unknown')}", color=0x3498DB
                    )
                    header = [
                        f"ID: `{getattr(t, 'id', 'N/A')}`",
                        f"League: {getattr(t, 'league', 'N/A')}",
                        f"Country: {getattr(t, 'country', 'N/A')}",
                    ]
                    embed.add_field(
                        name="Summary", value=" • ".join(header), inline=False
                    )
                    if getattr(t, "stadium", None):
                        embed.add_field(
                            name="Stadium", value=getattr(t, "stadium"), inline=True
                        )
                    if getattr(t, "founded", None):
                        embed.add_field(
                            name="Founded",
                            value=str(getattr(t, "founded")),
                            inline=True,
                        )

                    try:
                        await channel.send(embed=embed)
                        print(f"Posted update for team {name} to channel {channel_id}")
                    except discord.Forbidden:
                        print(f"Forbidden to send to channel {channel_id}")
                        break
                    except Exception as e:
                        print(f"Failed to send embed for team {name}: {e}")

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
    print("We have successfully loggged in as {0.user}".format(client))


# easter egg message responses
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if "sports" in message.content.lower():
        await message.channel.send("Did somebody say sports!?!")
        return

    if "football" in message.content.lower():
        await message.channel.send(
            (
                "Erm, actually it's called soccer! "
                "Unless you meant actual football in which case, carry on."
            )
        )
        return


# On demand stats request
@client.tree.command()
@app_commands.describe(
    first_name="First name of the player you want the stats of",
    last_name="Last name of the player you want the stats of",
    season="Optional season (YYYY)",
)
async def stats(
    interaction: discord.Interaction, first_name: str, last_name: str, season: int | None = None
):
    """Current season statistics for a specific soccer player (uses APIFootball when available)."""
    await interaction.response.defer(thinking=True)

    if len(first_name) == 0 or len(last_name) == 0:
        await interaction.followup.send("Please provide both player's first and last name.")
        return

    # cant go past 2023 or before 2021
    if season is None or season > 2023 or season < 2021:
        season = 2023

    integration_layer = client.integration_layer
    if integration_layer is None:
        await interaction.followup.send("The Integration Layer was never initialized")
        return 
    try:
        response = await integration_layer.get_player_stats(first_name=first_name, last_name=last_name, season=season)
        if response["status"] != "success":
            await interaction.followup.send(response["status"])
            return
        
        # player information to display
        player_stat = response["data"][0]
        team_name = player_stat["team"].get("name", "N/A")
        league_name = player_stat["league"].get("name", "N/A")
        games_played = player_stat["games"].get("appearences", "N/A")
        position = player_stat["games"].get("position", "N/A")
        passes = player_stat["passes"].get("total", "N/A")
        shots =player_stat["shots"].get("total", "N/A")
        goals = player_stat["goals"].get("total", "N/A")


        embed = discord.Embed(title=f"Season {season}: {first_name} {last_name}", color=0x2ECC71)
        
        embed.add_field(
            name="League / Team",
            value=f"League: {league_name}\nTeam: {team_name}",
            inline=False
        )

        embed.add_field(
            name="Games / Position",
            value=f"Games Played: {games_played}\nPosition: {position}",
            inline=False
        )
        
        embed.add_field(name="Passes", value=passes, inline=True)
        embed.add_field(name="Shots", value=shots, inline=True)
        embed.add_field(name="Goals", value=goals, inline=True)
        
        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"An error occurred while fetching stats: {e}")


# subscribe player command
@client.tree.command()
# @app_commands.rename(full_name='full name')
@app_commands.describe(full_name="The full name of the player you want to subscribe to")
async def subscribe_player(interaction: discord.Interaction, full_name: str):
    success, message = await db_subscribe_player(
        discord_id=str(interaction.user.id),
        username=interaction.user.name,
        player_name=full_name,
        channel_id=str(interaction.channel_id),
        guild_id=str(interaction.guild_id),
    )
    await interaction.response.send_message(message)


# subscribe team command
@client.tree.command()
# @app_commands.rename(full_name='team name')
@app_commands.describe(full_name="The name of the team you want to subscribe to")
async def subscribe_team(interaction: discord.Interaction, full_name: str):
    success, message = await db_subscribe_team(
        discord_id=str(interaction.user.id),
        username=interaction.user.name,
        team_name=full_name,
        channel_id=str(interaction.channel_id),
        guild_id=str(interaction.guild_id),
    )
    await interaction.response.send_message(message)


# unsubscribe player command
@client.tree.command()
# @app_commands.rename(full_name='full name')
@app_commands.describe(
    full_name="The full name of the player you want to unsubscribe from"
)
async def unsubscribe_player(interaction: discord.Interaction, full_name: str):
    """Unsubscribes you from a player"""
    success, message = await db_unsubscribe_player(
        discord_id=str(interaction.user.id), player_name=full_name
    )
    await interaction.response.send_message(
        "You have been unsubscribed from " + full_name
    )


# unsubscribe team command
@client.tree.command()
# @app_commands.rename(full_name='team name')
@app_commands.describe(full_name="The name of the team you want to unsubscribe from")
async def unsubscribe_team(interaction: discord.Interaction, full_name: str):
    """Unsubscribes you from a team"""
    success, message = await db_unsubscribe_team(
        discord_id=str(interaction.user.id), team_name=full_name
    )
    await interaction.response.send_message(
        "You have been unsubscribed from " + full_name
    )


# list subscriptions
@client.tree.command()
async def subscriptions(interaction: discord.Interaction):
    """Lists all subscribed players and teams"""

    discord_id = str(interaction.user.id)
    subs = await db_subscriptions(discord_id)
    players = subs["players"]
    teams = subs["teams"]
    channel_id = subs["channel_id"]
    guild_id = subs["guild_id"]

    player_text = "\n".join(f"- {p}" for p in players) if players else "None"
    team_text = "\n".join(f"- {t}" for t in teams) if teams else "None"
    channel_line = f"Updates will be posted in <#{channel_id}>\n" if channel_id else ""
    guild_line = f"Guild ID: {guild_id}\n" if guild_id else ""

    await interaction.response.send_message(
        f"""Hi {interaction.user.display_name}!
        Players you're subscribed to:\n{player_text}
        Teams you're subscribed to:\n{team_text}
        {channel_line}{guild_line}"""
    )


client.run(TOKEN)

# bot.py
# The main bot script

import asyncio
import os
import traceback
from datetime import datetime, timedelta, timezone

import aiohttp
import discord
from discord import app_commands
from dotenv import load_dotenv

from .db_helpers import (
    db_all_player_subscriptions,
    db_all_team_subscriptions,
    db_get_posted_fingerprint,
    db_set_posted_fingerprint,
    db_set_team_sportsdb_id,
    db_subscribe_player,
    db_subscribe_team,
    db_subscriptions,
    db_unsubscribe_player,
    db_unsubscribe_team,
)
from .db_skeleton import init_db
from .IntegrationLayer import IntegrationLayer, _fold
from .SportsAPIClient import SportsAPIClient

# Load ENV variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# How often (seconds) the background poster re-checks subscriptions.
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))

# Fixture reminders are posted when kickoff is within this window.
REMINDER_HOURS = int(os.getenv("REMINDER_HOURS", "48"))

# Optional: a guild ID to sync commands to instantly during development.
# Without it, commands are synced globally (may take up to an hour to appear).
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")

GREEN = 0x2ECC71
BLUE = 0x3498DB
RED = 0xE74C3C
GREY = 0x95A5A6
GOLD = 0xF1C40F


# ------------------------- snapshots (change detection) -------------------------


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


# ------------------------- embed builders -------------------------


def _player_embed(p):
    embed = discord.Embed(title=f"{getattr(p, 'name', None) or 'Unknown'}", color=GREEN)
    header = [
        f"Team: {getattr(p, 'team', None) or 'N/A'}",
        f"Position: {getattr(p, 'position', None) or 'N/A'}",
    ]
    embed.add_field(name="Summary", value=" • ".join(header), inline=False)
    if getattr(p, "nationality", None):
        embed.add_field(name="Nationality", value=p.nationality, inline=True)
    if getattr(p, "age", None):
        embed.add_field(name="Age", value=str(p.age), inline=True)
    if getattr(p, "thumb", None):
        embed.set_thumbnail(url=p.thumb)
    embed.set_footer(text="via TheSportsDB")
    return embed


def _team_embed(t):
    embed = discord.Embed(title=f"{getattr(t, 'name', None) or 'Unknown'}", color=BLUE)
    header = [
        f"League: {getattr(t, 'league', None) or 'N/A'}",
        f"Country: {getattr(t, 'country', None) or 'N/A'}",
    ]
    embed.add_field(name="Summary", value=" • ".join(header), inline=False)
    if getattr(t, "stadium", None):
        embed.add_field(name="Stadium", value=t.stadium, inline=True)
    if getattr(t, "founded", None):
        embed.add_field(name="Founded", value=str(t.founded), inline=True)
    if getattr(t, "badge", None):
        embed.set_thumbnail(url=t.badge)
    embed.set_footer(text="via TheSportsDB")
    return embed


def _result_embed(event, followed_team=None):
    """Full-time score embed. Colored by the followed team's result if given."""
    color = GOLD
    if followed_team and event.finished:
        we_are_home = _fold(event.home) == _fold(followed_team)
        our_score = event.home_score if we_are_home else event.away_score
        their_score = event.away_score if we_are_home else event.home_score
        if our_score > their_score:
            color = GREEN
        elif our_score < their_score:
            color = RED
        else:
            color = GREY

    embed = discord.Embed(
        title=f"FT: {event.home} {event.home_score} – {event.away_score} {event.away}",
        color=color,
    )
    details = [d for d in [event.league, f"Round {event.round}" if event.round else None] if d]
    if details:
        embed.add_field(name="Competition", value=" • ".join(details), inline=False)
    if event.venue:
        embed.add_field(name="Venue", value=event.venue, inline=True)
    if event.timestamp:
        embed.add_field(
            name="Played", value=f"<t:{int(event.timestamp.timestamp())}:D>", inline=True
        )
    elif event.date:
        embed.add_field(name="Played", value=event.date, inline=True)
    if event.home_badge:
        embed.set_thumbnail(url=event.home_badge)
    embed.set_footer(text="via TheSportsDB")
    return embed


def _fixture_embed(event):
    """Upcoming match embed with Discord-native kickoff timestamps."""
    embed = discord.Embed(title=f"Upcoming: {event.home} vs {event.away}", color=BLUE)
    if event.timestamp:
        unix = int(event.timestamp.timestamp())
        embed.add_field(name="Kickoff", value=f"<t:{unix}:F> (<t:{unix}:R>)", inline=False)
    elif event.date:
        embed.add_field(name="Kickoff", value=event.date, inline=False)
    details = [d for d in [event.league, f"Round {event.round}" if event.round else None] if d]
    if details:
        embed.add_field(name="Competition", value=" • ".join(details), inline=True)
    if event.venue:
        embed.add_field(name="Venue", value=event.venue, inline=True)
    if event.home_badge:
        embed.set_thumbnail(url=event.home_badge)
    embed.set_footer(text="via TheSportsDB")
    return embed


def _event_when(event):
    """Best-effort aware datetime for sorting/recency checks, or None."""
    if event.timestamp:
        return event.timestamp
    if event.date:
        try:
            return datetime.strptime(event.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _filter_choices(names, current):
    """Autocomplete helper: case-insensitive substring filter, max 25 choices."""
    current = (current or "").strip().lower()
    filtered = [n for n in names if current in n.lower()] if current else list(names)
    return [app_commands.Choice(name=n, value=n) for n in filtered[:25]]


class MyClient(discord.Client):
    user: discord.ClientUser

    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self._poster_task: asyncio.Task | None = None
        self._shutdown = False
        self.http_session: aiohttp.ClientSession | None = None
        self.integration_layer: IntegrationLayer | None = None
        self.sports_api: SportsAPIClient | None = None

    async def setup_hook(self):
        try:
            await init_db()
            print("initialized the database")
        except Exception as e:
            print(f"db initialization failed, exception: {e}")

        # create a shared aiohttp session for API calls and IntegrationLayer
        self.http_session = aiohttp.ClientSession()
        self.integration_layer = IntegrationLayer(self.http_session)
        self.sports_api = SportsAPIClient(self.http_session)

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

    async def _post_once(self, channel_id, kind, key, fingerprint, embed):
        """Send `embed` to `channel_id` unless the same fingerprint was already
        posted for (kind, key). Returns True when a message was sent."""
        try:
            channel_id_int = int(channel_id)
        except (TypeError, ValueError):
            return False

        already = await db_get_posted_fingerprint(channel_id, kind, key)
        if already == fingerprint:
            return False

        channel = await self._resolve_channel(channel_id_int)
        if channel is None:
            return False
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            print(f"Forbidden to send to channel {channel_id}")
            return False
        except Exception as e:
            print(f"Failed to send embed to {channel_id}: {e}")
            return False

        await db_set_posted_fingerprint(channel_id, kind, key, fingerprint)
        print(f"Posted {kind} update '{key}' to channel {channel_id}")
        return True

    async def _post_team_matches(self, api, team_name, sportsdb_id, channel_ids):
        """Post new final scores and upcoming-kickoff reminders for one team."""
        # ---- results ----
        try:
            last_events = await api.get_last_events(sportsdb_id)
        except Exception as e:
            print(f"API error fetching last events for '{team_name}': {e}")
            last_events = None
        if isinstance(last_events, list):
            finished = sorted(
                (e for e in last_events if e.finished and e.id and _event_when(e)),
                key=_event_when,
            )
            for channel_id in channel_ids:
                marker = await db_get_posted_fingerprint(channel_id, "lastresult", team_name)
                if marker is None:
                    # first time: announce only the most recent result
                    to_post = finished[-1:]
                else:
                    to_post = [e for e in finished if _event_when(e).isoformat() > marker]
                for event in to_post:
                    sent = await self._post_once(
                        channel_id,
                        "result",
                        event.id,
                        f"{event.home_score}-{event.away_score}",
                        _result_embed(event, followed_team=team_name),
                    )
                    if sent:
                        await db_set_posted_fingerprint(
                            channel_id,
                            "lastresult",
                            team_name,
                            _event_when(event).isoformat(),
                        )

        # ---- kickoff reminders ----
        try:
            next_events = await api.get_next_events(sportsdb_id)
        except Exception as e:
            print(f"API error fetching next events for '{team_name}': {e}")
            next_events = None
        if isinstance(next_events, list):
            now = datetime.now(timezone.utc)
            window = now + timedelta(hours=REMINDER_HOURS)
            for event in next_events:
                when = _event_when(event)
                if not (event.id and when and now <= when <= window):
                    continue
                for channel_id in channel_ids:
                    await self._post_once(
                        channel_id, "reminder", event.id, "sent", _fixture_embed(event)
                    )

    async def post_subscription_updates(self):
        """Polls DB+API every POLL_INTERVAL seconds. Posts to each subscription's
        channel: profile changes, new final scores, and kickoff reminders."""
        if self.http_session is None:
            print("HTTP session not initialized; exiting poster")
            return

        api = SportsAPIClient(self.http_session)
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
                team_info: dict[str, dict] = {}
                for row in team_subs:
                    if row.get("team_name") and row.get("channel_id"):
                        info = team_info.setdefault(
                            row["team_name"], {"channels": set(), "sportsdb_id": None}
                        )
                        info["channels"].add(row["channel_id"])
                        if row.get("sportsdb_id"):
                            info["sportsdb_id"] = row["sportsdb_id"]

                # ---- player profile updates ----
                for name, channel_ids in player_channels.items():
                    try:
                        results = await api.get_player(name)
                    except Exception as e:
                        print(f"API error fetching player '{name}': {e}")
                        continue
                    if not results or results == "Server Down":
                        continue
                    p = results[0]
                    snap = repr(_player_snapshot(p))
                    for channel_id in channel_ids:
                        await self._post_once(channel_id, "player", name, snap, _player_embed(p))

                # ---- team profile updates + matches ----
                for name, info in team_info.items():
                    try:
                        results = await api.get_team(name)
                    except Exception as e:
                        print(f"API error fetching team '{name}': {e}")
                        results = None
                    if isinstance(results, list) and results:
                        t = results[0]
                        snap = repr(_team_snapshot(t))
                        for channel_id in info["channels"]:
                            await self._post_once(channel_id, "team", name, snap, _team_embed(t))
                        # backfill TheSportsDB id on rows created before the column existed
                        if not info["sportsdb_id"] and getattr(t, "id", None):
                            try:
                                await db_set_team_sportsdb_id(name, str(t.id))
                                info["sportsdb_id"] = str(t.id)
                            except Exception as e:
                                print(f"could not backfill sportsdb_id for '{name}': {e}")

                    if info["sportsdb_id"]:
                        await self._post_team_matches(
                            api, name, info["sportsdb_id"], info["channels"]
                        )

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


# friendly error handling: users should never see a silent
# "The application did not respond"
@client.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: Exception):
    command = interaction.command.name if interaction.command else "unknown"
    print(f"Error in command '{command}':")
    traceback.print_exception(type(error), error, error.__traceback__)
    message = "Something went wrong running that command — please try again."
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except Exception:
        pass


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


# ------------------------- autocomplete callbacks -------------------------


async def _subscribed_player_autocomplete(interaction: discord.Interaction, current: str):
    subs = await db_subscriptions(str(interaction.user.id))
    return _filter_choices(subs["players"], current)


async def _subscribed_team_autocomplete(interaction: discord.Interaction, current: str):
    subs = await db_subscriptions(str(interaction.user.id))
    return _filter_choices(subs["teams"], current)


# ------------------------- commands -------------------------


# On demand stats request
@client.tree.command()
@app_commands.describe(
    first_name="First name of the player you want the stats of",
    last_name="Last name of the player you want the stats of",
    season="Season year, 2021-2023 (free API-Football plans only cover those)",
)
async def stats(
    interaction: discord.Interaction,
    first_name: str,
    last_name: str,
    season: app_commands.Range[int, 2021, 2023] | None = None,
):
    """Season statistics for a specific soccer player (via API-Football)."""
    await interaction.response.defer(thinking=True)

    first_name = first_name.strip()
    last_name = last_name.strip()
    if not first_name or not last_name:
        await interaction.followup.send("Please provide both the player's first and last name.")
        return

    if season is None:
        season = 2023

    integration_layer = client.integration_layer
    if integration_layer is None:
        await interaction.followup.send("The bot is still starting up — try again in a moment.")
        return

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
    rating = games.get("rating")
    passes = (player_stat.get("passes") or {}).get("total", "N/A")
    shots = (player_stat.get("shots") or {}).get("total", "N/A")
    goals = (player_stat.get("goals") or {}).get("total", "N/A")
    assists = (player_stat.get("goals") or {}).get("assists", "N/A")
    cards = player_stat.get("cards") or {}

    embed = discord.Embed(title=f"Season {season}: {first_name} {last_name}", color=GREEN)
    embed.add_field(
        name="League / Team",
        value=f"League: {league_name}\nTeam: {team_name}",
        inline=False,
    )
    games_value = f"Games Played: {games_played}\nPosition: {position}"
    if rating:
        try:
            games_value += f"\nAvg Rating: {float(rating):.2f}"
        except (TypeError, ValueError):
            pass
    embed.add_field(name="Games / Position", value=games_value, inline=False)
    embed.add_field(name="Goals", value=str(goals), inline=True)
    embed.add_field(
        name="Assists", value=str(assists if assists is not None else "N/A"), inline=True
    )
    embed.add_field(name="Shots", value=str(shots), inline=True)
    embed.add_field(name="Passes", value=str(passes), inline=True)
    embed.add_field(
        name="Cards",
        value=f"🟨 {cards.get('yellow') or 0} 🟥 {cards.get('red') or 0}",
        inline=True,
    )
    embed.set_footer(text="via API-Football")

    await interaction.followup.send(embed=embed)


@client.tree.command()
@app_commands.describe(full_name="The player's name")
async def player(interaction: discord.Interaction, full_name: str):
    """Look up a player's profile (photo, team, position, nationality)."""
    await interaction.response.defer(thinking=True)
    api = client.sports_api
    if api is None:
        await interaction.followup.send("The bot is still starting up — try again in a moment.")
        return

    players = await api.get_player(full_name.strip())
    if players == "Server Down":
        await interaction.followup.send("The sports data service is unavailable right now.")
        return
    if not players:
        await interaction.followup.send(f"No player found matching '{full_name}'.")
        return
    await interaction.followup.send(embed=_player_embed(players[0]))


async def _lookup_team(interaction, team_name):
    """Shared team lookup for the match commands. Returns a Team or None
    (after replying with the reason)."""
    api = client.sports_api
    if api is None:
        await interaction.followup.send("The bot is still starting up — try again in a moment.")
        return None
    teams = await api.get_team(team_name.strip())
    if teams == "Server Down":
        await interaction.followup.send("The sports data service is unavailable right now.")
        return None
    if not teams:
        await interaction.followup.send(f"No team found matching '{team_name}'.")
        return None
    return teams[0]


@client.tree.command()
@app_commands.describe(team_name="The team to look up")
async def next_match(interaction: discord.Interaction, team_name: str):
    """Upcoming fixtures for a team."""
    await interaction.response.defer(thinking=True)
    team = await _lookup_team(interaction, team_name)
    if team is None:
        return

    events = await client.sports_api.get_next_events(team.id)
    if events == "Server Down":
        await interaction.followup.send("The sports data service is unavailable right now.")
        return
    if not events:
        await interaction.followup.send(f"No upcoming fixtures found for {team.name}.")
        return
    await interaction.followup.send(embeds=[_fixture_embed(e) for e in events[:3]])


@client.tree.command()
@app_commands.describe(team_name="The team to look up")
async def last_match(interaction: discord.Interaction, team_name: str):
    """The most recent result for a team."""
    await interaction.response.defer(thinking=True)
    team = await _lookup_team(interaction, team_name)
    if team is None:
        return

    events = await client.sports_api.get_last_events(team.id)
    if events == "Server Down":
        await interaction.followup.send("The sports data service is unavailable right now.")
        return
    finished = sorted((e for e in (events or []) if e.finished and _event_when(e)), key=_event_when)
    if not finished:
        await interaction.followup.send(f"No recent results found for {team.name}.")
        return
    await interaction.followup.send(embed=_result_embed(finished[-1], followed_team=team.name))


@client.tree.command()
@app_commands.describe(
    team_name="The team to look up",
    season="Season year, 2021-2023 (free API-Football plans only cover those)",
)
async def team_stats(
    interaction: discord.Interaction,
    team_name: str,
    season: app_commands.Range[int, 2021, 2023] | None = None,
):
    """A team's league record for a season (via API-Football)."""
    await interaction.response.defer(thinking=True)
    if season is None:
        season = 2023

    integration_layer = client.integration_layer
    if integration_layer is None:
        await interaction.followup.send("The bot is still starting up — try again in a moment.")
        return

    response = await integration_layer.get_team_stats(team_name=team_name.strip(), season=season)
    if response["status"] != "success" or not response["data"]:
        await interaction.followup.send(response["status"])
        return

    data = response["data"]
    team = (data.get("team") or {}).get("name", team_name)
    league = (data.get("league") or {}).get("name", "N/A")
    fixtures = data.get("fixtures") or {}
    played = (fixtures.get("played") or {}).get("total", "N/A")
    wins = (fixtures.get("wins") or {}).get("total", "N/A")
    draws = (fixtures.get("draws") or {}).get("total", "N/A")
    loses = (fixtures.get("loses") or {}).get("total", "N/A")
    goals = data.get("goals") or {}
    goals_for = ((goals.get("for") or {}).get("total") or {}).get("total", "N/A")
    goals_against = ((goals.get("against") or {}).get("total") or {}).get("total", "N/A")
    clean_sheets = (data.get("clean_sheet") or {}).get("total", "N/A")
    form = data.get("form")

    embed = discord.Embed(title=f"Season {season}: {team}", color=BLUE)
    embed.add_field(name="League", value=league, inline=False)
    embed.add_field(
        name="Record", value=f"{wins}W • {draws}D • {loses}L ({played} played)", inline=False
    )
    embed.add_field(name="Goals For", value=str(goals_for), inline=True)
    embed.add_field(name="Goals Against", value=str(goals_against), inline=True)
    embed.add_field(name="Clean Sheets", value=str(clean_sheets), inline=True)
    if form:
        embed.add_field(name="Form", value=str(form)[-20:], inline=False)
    badge = (data.get("team") or {}).get("logo")
    if badge:
        embed.set_thumbnail(url=badge)
    embed.set_footer(text="via API-Football")

    await interaction.followup.send(embed=embed)


# subscribe player command
@client.tree.command()
@app_commands.describe(full_name="The full name of the player you want to subscribe to")
async def subscribe_player(interaction: discord.Interaction, full_name: str):
    """Subscribes you to a player; updates post in this channel."""
    await interaction.response.defer(thinking=True, ephemeral=True)
    success, message = await db_subscribe_player(
        discord_id=str(interaction.user.id),
        username=interaction.user.name,
        player_name=full_name.strip(),
        channel_id=str(interaction.channel_id),
        guild_id=str(interaction.guild_id),
    )
    await interaction.followup.send(message, ephemeral=True)


# subscribe team command
@client.tree.command()
@app_commands.describe(full_name="The name of the team you want to subscribe to")
async def subscribe_team(interaction: discord.Interaction, full_name: str):
    """Subscribes you to a team; match updates post in this channel."""
    await interaction.response.defer(thinking=True, ephemeral=True)
    success, message = await db_subscribe_team(
        discord_id=str(interaction.user.id),
        username=interaction.user.name,
        team_name=full_name.strip(),
        channel_id=str(interaction.channel_id),
        guild_id=str(interaction.guild_id),
    )
    await interaction.followup.send(message, ephemeral=True)


# unsubscribe player command
@client.tree.command()
@app_commands.describe(full_name="The player you want to unsubscribe from")
@app_commands.autocomplete(full_name=_subscribed_player_autocomplete)
async def unsubscribe_player(interaction: discord.Interaction, full_name: str):
    """Unsubscribes you from a player"""
    success, message = await db_unsubscribe_player(
        discord_id=str(interaction.user.id), player_name=full_name.strip()
    )
    await interaction.response.send_message(message, ephemeral=True)


# unsubscribe team command
@client.tree.command()
@app_commands.describe(full_name="The team you want to unsubscribe from")
@app_commands.autocomplete(full_name=_subscribed_team_autocomplete)
async def unsubscribe_team(interaction: discord.Interaction, full_name: str):
    """Unsubscribes you from a team"""
    success, message = await db_unsubscribe_team(
        discord_id=str(interaction.user.id), team_name=full_name.strip()
    )
    await interaction.response.send_message(message, ephemeral=True)


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
        f"{channel_line}",
        ephemeral=True,
    )


def main():
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN not found. Copy RenameTo.env to .env and set DISCORD_TOKEN."
        )
    client.run(TOKEN)


if __name__ == "__main__":
    main()

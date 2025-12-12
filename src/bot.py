# bot.py
# The main bot script

import os
import discord  # pyright: ignore
import aiohttp
import asyncio
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

# Load ENV variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN not found. Go to .env and set DISCORD_TOKEN locally."
    )

POLL_INTERVAL = 10

# supposedly helps speed up testing?
MY_GUILD = discord.Object(id=1418704334941851722)
BOT_TESTING_CHANNEL = 1428577092228091964

BOT_TESTING_CHANNEL = 1428577092228091964
POLL_INTERVAL = 10


class MyClient(discord.Client):
    user: discord.ClientUser

    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self._poster_task: asyncio.Task
        self._shutdown = False

    async def setup_hook(self):
        try:
            await init_db()
            print("initialized the database")
        except Exception as e:
            print(f"db initializaiton falied, exception: {e}")

        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

        self._poster_task = asyncio.create_task(self.list_subscriptions())

    async def close(self):
        self._shutdown = True
        if self._poster_task:
            self._poster_task.cancel()
            try:
                await self._poster_task
            except asyncio.CancelledError:
                pass
        await super().close()

    async def list_subscriptions(self):
        """
        Subscriptions, posts updates in x second interval
        """
        try:
            channel_id = int(BOT_TESTING_CHANNEL)
        except Exception:
            print("invalid BOT_TESTING_CHANNEL")
            return

        while not self._shutdown:
            try:
                channel = self.get_channel(channel_id)
                if channel is None:
                    try:
                        channel = await self.fetch_channel(channel_id)
                    except Exception as e:
                        print(f"could not fetch channel {channel_id}: {e}")
                        # wait and retry later
                        continue
                try:
                    await channel.send(
                        "Here is information about your subscriptions! DUMMY"
                    )
                except discord.Forbidden:
                    print(f"bot cannot send messages to channel {channel_id}")
                except Exception as e:
                    print(f"failed to send to channel {channel_id}: {e}")

                # wait for next interval
                await asyncio.sleep(POLL_INTERVAL)

            except asyncio.CancelledError:
                print("background poster cancelled")
                break
            except Exception as e:
                print(f"unhandled error in background poster: {e}")


# Set up Discord bot with message content intent enabled
intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)


@client.event
async def on_ready():
    print("We have successfully loggged in as {0.user}".format(client))


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
@app_commands.describe(full_name="The full name of the player you want the stats of")
async def stats(interaction: discord.Interaction, full_name: str):
    """Current season statistics for a specific soccer player"""
    await interaction.response.defer(thinking=True)

    try:
        async with aiohttp.ClientSession() as session:
            api = SportsAPIClient(session)
            player_info = await api.get_player(full_name)

        if player_info == "Server Down":
            await interaction.followup.send("The server is currently down")
            return
        if not player_info:
            await interaction.followup.send(f"No player found for '{full_name}'.")
            return

        p = player_info[0]
        await interaction.followup.send(
            f"""Here are the current stats of {p.name}:\nTeam: {p.team}\n"""
            f"""Position: {p.position}\nNationality: {p.nationality}"""  # \nStats: {p.stats}"""
        )

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}")


# subscribe player command
@client.tree.command()
# @app_commands.rename(full_name='full name')
@app_commands.describe(full_name="The full name of the player you want to subscribe to")
async def subscribe_player(interaction: discord.Interaction, full_name: str):
    success, message = await db_subscribe_player(
        discord_id=str(interaction.user.id),
        username=interaction.user.name,
        player_name=full_name,
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

    player_text = "\n".join(f"- {p}" for p in players) if players else "None"
    team_text = "\n".join(f"- {t}" for t in teams) if teams else "None"

    await interaction.response.send_message(
        f"""Hi {interaction.user.display_name}!
        Players you're subscribed to:\n{player_text}
        Teams you're subscribed to:\n{team_text}"""
    )


client.run(TOKEN)

# The main bot script

# We definitely need these at the very least
import os
import discord                      # pyright: ignore
from discord import app_commands    # pyright: ignore
from dotenv import load_dotenv      # pyright: ignore

# TODO: Need to add env folder

# Load ENV variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN not found. Copy .env.example -> .env and set DISCORD_TOKEN locally."
    )


class MyClient(discord.Client):
    user: discord.ClientUser

    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)


# Set up Discord bot with message content intent enabled
intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)

# supposedly helps speed up testing?
MY_GUILD = discord.Object(id=1418704334941851722)


# This is temporary (borrowed) for testing if im doing any of this right - Rishi
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
            "Erm, actually it's called soccer! "
            + "Unless you meant actual football in which case, carry on."
        )
        return


# On demand stats request
@client.tree.command()
# @app_commands.rename(full_name='full name')
@app_commands.describe(full_name="The full name of the player you want the stats of")
async def stats(interaction: discord.Interaction, full_name: str):
    """Current season statistics for a specific soccer player"""
    await interaction.response.send_message(
        "Here are the current stats of " + full_name + ": \n"
    )


# subscribe player command
@client.tree.command()
# @app_commands.rename(full_name='full name')
@app_commands.describe(full_name="The full name of the player you want to subscribe to")
async def subscribe_player(interaction: discord.Interaction, full_name: str):
    """Subscribes you to a player"""
    await interaction.response.send_message(
        "You have been subscribed to " + full_name + "!"
    )


# subscribe team command
@client.tree.command()
# @app_commands.rename(full_name='team name')
@app_commands.describe(full_name="The name of the team you want to subscribe to")
async def subscribe_team(interaction: discord.Interaction, full_name: str):
    """Subscribes you to a team"""
    await interaction.response.send_message(
        "You have been subscribed to " + full_name + "!"
    )


# unsubscribe player command
@client.tree.command()
# @app_commands.rename(full_name='full name')
@app_commands.describe(
    full_name="The full name of the player you want to unsubscribe from"
)
async def unsubscribe_player(interaction: discord.Interaction, full_name: str):
    """Unsubscribes you from a player"""
    await interaction.response.send_message(
        "You have been unsubscribed from " + full_name
    )


# unsubscribe team command
@client.tree.command()
# @app_commands.rename(full_name='team name')
@app_commands.describe(full_name="The name of the team you want to unsubscribe from")
async def unsubscribe_team(interaction: discord.Interaction, full_name: str):
    """Unsubscribes you from a team"""
    await interaction.response.send_message(
        "You have been unsubscribed from " + full_name
    )


# list subscriptions
@client.tree.command()
async def subscriptions(interaction: discord.Interaction):
    """Lists all subscribed players and teams"""
    await interaction.response.send_message(
        "Hi "
        + interaction.user.display_name
        + "!\n"
        + "Here are all of the players you are subscribed to: \n \n "
        + "Here are all of the teams you are subscribed to: \n "
    )


client.run(TOKEN)

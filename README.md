# Discord Sports Bot (Team 86)

## Introduction
The Discord Sports Bot is a comprehensive tool designed for sports enthusiasts on Discord, created for CS 222 (Fall 2025). It allows users to subscribe to their favorite players and teams, receiving real-time updates and statistics directly in their server. The bot aims to centralize sports information, making it easy to track performance and news without leaving the Discord platform.

Key Features:
- **Player & Team Subscriptions**: Users can follow specific entities to get tailored updates.
- **Statistics Retrieval**: Fetch current stats for players and teams on command.
- **Notifications**: Automated updates based on subscriptions.

[View Project Proposal](https://docs.google.com/document/d/1j0bAS2HjeMlY9QebZ3tDX2xjbtOkhRvqG1ifpu8Gssg/edit?tab=t.0)

## Technical Architecture
The application is built using specific layers to ensure modularity and maintainability:

1.  **Interface Layer (Discord):**
    -   Built with **`discord.py`**, this layer handles Slash Commands (e.g., `/stats`, `/subscribe`) and user interactions.
    -   Entry point: `src/bot.py`.

2.  **Application Logic & Integration:**
    -   The **Integration Layer** (`src/IntegrationLayer.py`) acts as a bridge, coordinating requests between the bot interface and the backend data services.
    -   This separates the Discord-specific logic from the core business logic.

3.  **Data Access & External APIs:**
    -   **Sports Data**: `src/SportsAPIClient.py` wraps external APIs (like TheSportsDB) to fetch real-time player and team data.
    -   **Persistence**: User subscriptions and settings are stored in a local **SQLite** database.
    -   **ORM**: We use **`SQLAlchemy`** with **`aiosqlite`** for asynchronous database interactions (`src/database.py`, `src/db_skeleton.py`).

4.  **Deployment:**
    -   The application is containerized using **Docker** to ensure a reproducible environment (`Dockerfile`, `compose.yaml`).

## Setup

You need three things: a Discord bot identity (free, ~5 minutes), this code, and
a way to run it (Docker **or** Python 3.10+). Follow the steps in order.

### Step 1 — Create your Discord bot (one time)

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
   and click **New Application**. Name it anything (e.g. "SportsBot").
2. In the left sidebar open **Bot**, click **Reset Token**, and copy the token
   somewhere safe. This is your `DISCORD_TOKEN`. Treat it like a password —
   anyone who has it controls your bot.
3. Still on the **Bot** page, under **Privileged Gateway Intents**, enable
   **Message Content Intent** and save. *The bot refuses to start without this.*
4. Invite the bot to your server: open **OAuth2 → URL Generator**, check the
   scopes **`bot`** and **`applications.commands`**, then under Bot Permissions
   check **View Channels**, **Send Messages**, **Embed Links**, and
   **Read Message History**. Open the generated URL in your browser and pick
   your server.

### Step 2 — Gather your config values

| Value | Required? | Where to get it |
|-------|-----------|-----------------|
| `DISCORD_TOKEN` | **Yes** | Step 1.2 above |
| `DEV_GUILD_ID` | Recommended | In Discord: User Settings → Advanced → enable **Developer Mode**, then right-click your server's name → **Copy Server ID**. With this set, slash commands appear in that server instantly; without it they sync globally, which can take up to an hour. |
| `API_FOOTBALL_KEY` | No | Free key from [api-football.com](https://www.api-football.com/). Only needed for `/stats` and `/team_stats`; everything else works without it. |

### Step 3 — Get the code and configure it

```bash
git clone https://github.com/Happy-Duck/DiscordSportsBot.git
cd DiscordSportsBot
cp RenameTo.env .env        # copy it — don't rename it
```

Open `.env` in any editor and fill in the values from Step 2:

```env
DISCORD_TOKEN=paste_your_token_here
DEV_GUILD_ID=paste_your_server_id_here
API_FOOTBALL_KEY=            # fine to leave empty
POLL_INTERVAL=300
REMINDER_HOURS=48
```

### Step 4 — Run it

**Option A: Docker (no Python needed)**

```bash
docker compose up --build
```

**Option B: Python 3.10+**

macOS/Linux:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.bot
```

Windows (PowerShell — use `py` if `python` isn't found):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.bot
```

Always run `python -m src.bot` **from the project root** (the folder containing
`src/`), not from inside `src/`. The SQLite database (`src/sportsbot.db`) is
created automatically on first startup — no separate setup step needed.

### Step 5 — Check that it worked

The console should print, in order:

```
initialized the database
commands synced to dev guild <your id>
We have successfully logged in as <YourBot>#1234
```

Then in Discord: the bot shows as **Online**; type `/about` and it should reply
with its status. If commands don't appear, see Troubleshooting below.

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `RuntimeError: DISCORD_TOKEN not found` | No `.env` file next to `README.md`, or the token line is empty. Copy `RenameTo.env` to `.env` and paste your token. |
| `PrivilegedIntentsRequired` on startup | Message Content Intent isn't enabled — Step 1.3. |
| `LoginFailure: Improper token` | The token was copied wrong or reset since. Reset it in the Developer Portal and paste the new one. |
| Slash commands don't show up in Discord | Set `DEV_GUILD_ID` to your server's ID (Step 2) and restart — global sync without it can take up to an hour. Also confirm the invite used the `applications.commands` scope (Step 1.4). |
| `ModuleNotFoundError: No module named 'src'` | You ran the bot from inside `src/`. Run `python -m src.bot` from the project root. |
| `Python was not found` (Windows) | Install Python from [python.org](https://www.python.org/downloads/) or the `winget install Python.Python.3.12` command, then reopen the terminal. Try `py` instead of `python`. |
| Bot is online but never posts updates | Subscribe to something first (`/subscribe_team`), then wait one poll cycle (`POLL_INTERVAL`, default 5 minutes). Updates only post when something new happens — no repeat spam. |
| `/stats` or `/team_stats` says API-Football is not configured | Those two commands need `API_FOOTBALL_KEY` in `.env` (Step 2). |

## Bot Commands

| Command | Description |
|---------|-------------|
| `/subscribe_player <full_name>` | Follow a player; updates post in the channel you ran the command in |
| `/subscribe_team <full_name>` | Follow a team; match results and kickoff reminders post in that channel |
| `/unsubscribe_player <full_name>` | Stop following a player (autocompletes from your subscriptions) |
| `/unsubscribe_team <full_name>` | Stop following a team (autocompletes from your subscriptions) |
| `/subscriptions` | List everything you follow (only you see the reply) |
| `/player <full_name>` | A player's profile card — photo, team, position, nationality, age |
| `/next_match <team_name>` | A team's upcoming fixtures with kickoff times in your local timezone |
| `/last_match <team_name>` | A team's most recent result |
| `/standings <team_name>` | The league table for that team's league (free key shows the top 5) |
| `/stats <first_name> <last_name> [season]` | Season stats for a player (needs `API_FOOTBALL_KEY`; free plans cover 2021–2023) |
| `/team_stats <team_name> [season]` | A team's league record for a season (needs `API_FOOTBALL_KEY`) |
| `/about` | Bot status: uptime, latency, subscription counts |

When a subscribe search matches several players or teams (try "Ronaldo"), the
bot shows a dropdown so you pick the right one instead of guessing.

### Notifications

The background poster re-checks your subscriptions every `POLL_INTERVAL` seconds
(default 300) and posts to each subscription's channel:

- **Final scores** when a followed team's match finishes (green/red/grey embed
  for win/loss/draw)
- **Kickoff reminders** when a followed team plays within `REMINDER_HOURS`
  (default 48), plus a **kickoff alert** when the match starts
- **Profile updates** when a followed player/team's info changes (transfer,
  new stadium, ...)

Following a **player** also gets you their club's match notifications — no
separate team subscription needed.

Everything posted is remembered in the database, so restarts never repost old
updates.

## Running Tests

With the virtual environment from Step 4 active, run from the project root:

```bash
pytest tests/
```

Offline and TheSportsDB tests always run; API-Football tests are skipped unless
`API_FOOTBALL_KEY` is set in your environment. Tests use a throwaway database —
they never touch your real subscriptions.

## Group Members

| Name | Role |
|------|------|
| **Ayana** | API Integration & Data Handling |
| **Rishi Garhyan** | Discord Integration |
| **Hyunho Kim** | Discord Integration |
| **Zeeshan Khan** | API Integration, documentation, and bug handling |

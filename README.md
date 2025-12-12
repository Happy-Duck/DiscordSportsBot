# Discord Sports Bot (Team 86) · FA25

Made for CS 222 Fall 2025 by Ayana, Hyunho Kim, Rishi Garhyan, and Zeeshan Khan

A Discord bot that provides sports-related functionality (player/team subscriptions, stats, and notifications). This repository contains the bot code, an async SQLite schema, database initialization utilities, tests, Docker configuration, and CI configuration used by the team.

---

## Table of contents

- Project overview
- How to run (local)
- How to run (Docker)
- Database initialization (create .db)
- Run tests
- Code quality rules (formatter & flake8)
- Usage
- Project status & known limitations
- Environment & security
- Contact / team

---

## Project overview

Main pieces in this repo:
- Bot entrypoint: `src/bot.py` — Discord commands and interaction handlers.
- Database schema and async engine: `src/db_skeleton.py`, `src/setup_database.py`, `src/database.py`, `src/db_helpers.py`.
- API client: `src/SportsAPIClient.py` (wraps external sports APIs).
- Utilities & tests: `tests/database_tests.py`, `tests/api_test.py`, and other helpers.
- Docker compose file: `compose.yaml` (service named `server`).
- `.env` template: `RenameTo.env` (rename to `.env` and set tokens).

Goal: let users subscribe to players/teams and receive updates; store subscriptions and stats in a local SQLite DB during development.

---

## How to run — Local

Requirements:
- Python 3.10+ (use a virtual environment)
- Git

1. Clone repo
   ```
   git clone https://github.com/CS222-UIUC/fa25-team86-discordsportsbot.git
   cd fa25-team86-discordsportsbot
   ```

2. Create and activate a virtual environment
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. Install dependencies
   ```
   pip install -r requirements.txt
   ```

4. Create the local SQLite database
   ```
   python src/setup_database.py
   ```
   This creates `src/sportsbot.db` (default defined in `src/db_skeleton.py`).

5. Add environment variables
   - Copy/rename the template:
     ```
     cp RenameTo.env .env
     ```
     Edit `.env` and set:
     - `DISCORD_TOKEN=your_discord_bot_token`
     - `API_FOOTBALL_KEY=your_api_key` (optional; required for some tests and future API integration)

   Important: never commit `.env` or any tokens.

6. Run the bot locally
   ```
   python src/bot.py
   ```

Note: For single-guild command testing, update `MY_GUILD` in `src/bot.py`.

---

## How to run — Docker

The repo includes `compose.yaml` (service `server`) and a Dockerfile.

1. Ensure `.env` is present.
2. Build and run:
   ```
   docker compose up --build
   ```
   To run detached:
   ```
   docker compose up --build -d
   ```

3. The compose file maps port `8000:8000` by default.

Notes:
- On Apple Silicon or different architectures:
  ```
  docker build --platform=linux/amd64 -t discord-sports-bot .
  ```
- If tests fail in the container due to path issues, run tests locally for debugging.

---

## Database initialization

- Primary initializer: `src/setup_database.py` — creates tables via `src/db_skeleton.init_db()`:
  ```
  python src/setup_database.py
  ```
- Helper functions in `src/database.py`.
- Default DB URL in `src/db_skeleton.py`:
  ```
  DATABASE_URL = "sqlite+aiosqlite:///./src/sportsbot.db"
  ```

---

## Run tests

This project uses `pytest` and `pytest-asyncio`.

- Run all tests:
  ```
  pytest
  ```
- Integration tests that call external APIs (e.g., `tests/api_test.py`) are skipped unless `API_FOOTBALL_KEY` is set.

---

## Code quality rules

CI runs an auto-formatter and tests.

1. Formatting
   - Run Black:
     ```
     black .
     ```

2. Linting
   - Run flake8:
     ```
     flake8
     ```

Suggested quick local check before PR:
```
black . && flake8 && pytest
```

---

## Usage

Invite: use your bot's OAuth2 URL.

**Slash Commands:**
- `/stats [full_name]` — Fetch current season stats for a soccer player (uses TheSportsDB).
- `/subscribe_player [full_name]` — Subscribe to player updates.
- `/subscribe_team [full_name]` — Subscribe to team updates.
- `/unsubscribe_player [full_name]` — Unsubscribe from a player.
- `/unsubscribe_team [full_name]` — Unsubscribe from a team.
- `/subscriptions` — List your active subscriptions.

**Chat Triggers:**
- "sports" — The bot responds with enthusiasm.
- "football" — The bot attempts to correct you to "soccer".

---

## Project status & known limitations

**Current Status:**
- Functional Discord bot with subscription management and player statistics retrieval.
- Database: Local SQLite for storing user subscriptions.
- API: Currently relies on `TheSportsDB` for player and team data in the active commands. `API-Football` implementation is in progress.

**Known Limitations:**
- **Data Source**: The free tier of some sports APIs has constraints. We are currently using `TheSportsDB` which works well for basic info but might have different coverage than `API-Football`.
- **API Limits**: Rate limits apply.
- **Disambiguation**: Use full player names for best results.

---

## Environment variables & security

Do not commit secrets.

Common environment variables:
- `DISCORD_TOKEN` — Discord bot token (required)
- `API_FOOTBALL_KEY` — API-Football key (optional for now)
- `DATABASE_URL` — optional override for the DB connection string

Use `.env` for local development.

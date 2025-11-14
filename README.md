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
- Bot entrypoint: `bot.py` — Discord commands and interaction handlers.
- Database schema and async engine: `db_skeleton.py`, `setup_database.py`, `database.py`, `db_helpers.py`.
- API client: `SportsAPIClient.py` (wraps external sports APIs).
- Utilities & tests: `database_tests.py`, `api_test.py`, and other helpers.
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

4. Create the local SQLite database (Ayana’s initializer)
   ```
   python setup_database.py
   ```
   This creates `sportsbot.db` in the project root (default defined in `db_skeleton.py`).

   If another initializer exists (e.g., `scripts/init_db.py`), run that instead.

5. Add environment variables
   - Copy/rename the template:
     ```
     cp RenameTo.env .env
     ```
     Edit `.env` and set:
     - `DISCORD_TOKEN=your_discord_bot_token`
     - `API_FOOTBALL_KEY=your_api_key` (optional; API tests/requests may be skipped without it)

   Important: never commit `.env` or any tokens.

6. Run the bot locally
   - Example:
     ```
     export DISCORD_TOKEN="..."    # macOS / Linux
     python bot.py
     ```
   - If the project layout differs, use the correct module entrypoint (e.g., `python -m src.bot`).

Note: For single-guild command testing, update `MY_GUILD` in `bot.py`.

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

3. The compose file maps port `8000:8000` by default; adjust if needed.

Notes:
- On Apple Silicon or different architectures:
  ```
  docker build --platform=linux/amd64 -t discord-sports-bot .
  ```
- If tests fail in the container due to path issues, run tests locally for debugging (Ayana and Rishi used that workflow).

---

## Database initialization

- Primary initializer: `setup_database.py` — creates tables via `db_skeleton.init_db()`:
  ```
  python setup_database.py
  ```
- Helper functions in `database.py`:
  - `initialize_database()`, `ensure_tables(...)`, `test_database()`, `clear_dummy_data()`
- Default DB URL in `db_skeleton.py`:
  ```
  DATABASE_URL = "sqlite+aiosqlite:///./sportsbot.db"
  ```
  For CI or containerized runs, override via `DATABASE_URL` env var if needed.

---

## Run tests

This project uses `pytest` and `pytest-asyncio`.

- Run all tests:
  ```
  pytest
  ```
- Integration tests that call external APIs (e.g., `api_test.py`) are skipped unless `API_FOOTBALL_KEY` is set.
- If tests fail due to DB path mismatches in Docker, ensure the container DB path matches test expectations (e.g., `database_tests.py` uses `/app/src/sportsbot.db`), or run tests locally.

---

## Code quality rules

CI runs an auto-formatter and tests. Hyunho temporarily disabled `flake8` in CI due to preexisting lint errors; please help re-enable it by following these steps before opening a PR.

1. Formatting
   - Run Black:
     ```
     black .
     ```

2. Imports
   - If present, run isort:
     ```
     isort .
     ```

3. Linting (critical)
   - Run flake8 and fix issues:
     ```
     flake8
     ```
   - Typical fixes: remove unused imports/variables, fix line lengths and comment formatting, spacing/indentation.
   - If an import is required for side effects and flake8 flags it as unused, add:
     ```
     from some.module import plugin  # noqa: F401  # required for plugin registration
     ```

4. Pre-commit (optional but recommended)
   - If `.pre-commit-config.yaml` exists:
     ```
     pip install pre-commit
     pre-commit install
     pre-commit run --all-files
     ```

5. Commit & PR guidance
   - Keep commits small and focused.
   - For formatting-only changes, use a single commit with a clear title: `style: run formatter`.
   - In PR description, state whether the PR is formatting-only or contains logic changes.

Suggested quick local check before PR:
```
black . && isort . && flake8 && pytest
```

---

## Usage

Invite (example):
```
https://discord.com/oauth2/authorize?client_id=1427527753154171020
```
(Replace `client_id` if you use a different application.)

Slash commands available (server):
- `/subscribe_player [player name]` — subscribe to a player
- `/subscribe_team [team name]` — subscribe to a team
- `/unsubscribe_player [player name]` — unsubscribe from a player
- `/unsubscribe_team [team name]` — unsubscribe from a team
- `/stats [player name]` — current season stats for a player
- `/subscriptions` — list your subscriptions

---

## Project status & known limitations

Current status:
- Core bot scaffolding, DB schema, and DB initializer exist.
- Team can create a local `.db` and run basic tests.
- CI runs tests and the auto-formatter; `flake8` is disabled in CI pending cleanup.

Known blockers / limitations:
- External sports APIs:
  - Free API tiers often have low rate limits (e.g., APIFootball ~100 requests/day) or stale data (some free tiers return last data from 2023).
  - Some endpoints return multiple "similar" player matches instead of a single canonical player, requiring user disambiguation.
  - Due to these limits, the team is evaluating switching to targeted web scraping (e.g., ESPN) to obtain up-to-date real-time stats (goals, assists). Coordinate with the team before major API-client changes.

Short guidance for API work:
- Keep API keys out of source control.
- Implement caching and rate-limit handling.
- Add a disambiguation flow when API returns multiple player candidates.

---

## Environment variables & security

Do not commit secrets.

Common environment variables (local / dev):
- `DISCORD_TOKEN` — Discord bot token (required)
- `API_FOOTBALL_KEY` — external API key (optional; enables integration tests)
- `DATABASE_URL` — optional override for the DB connection string

Use `.env` for local development and ensure `.gitignore` excludes it.

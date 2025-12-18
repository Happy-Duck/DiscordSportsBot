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

## Installation Instructions

### Prerequisites
-   **Git**
-   **Docker** (Recommended for easiest run)
-   **Python 3.10+** (If running locally without Docker)
-   A **Discord Bot Token** (Get one from the [Discord Developer Portal](https://discord.com/developers/applications))
-   An **API-Football Key** (Optional, for advanced stats)

### Method 1: Running with Docker (Recommended)
This method ensures all dependencies are isolated and correct.

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/CS222-UIUC/fa25-team86-discordsportsbot.git
    cd fa25-team86-discordsportsbot
    ```

2.  **Configure Environment Variables**
    - Copy the template file:
      ```bash
      cp RenameTo.env .env
      ```
    - Open `.env` and add your keys:
      ```env
      DISCORD_TOKEN=your_discord_bot_token_here
      API_FOOTBALL_KEY=your_api_key_here
      ```

3.  **Build and Run**
    ```bash
    docker compose up --build
    ```
    The bot should now be online in your Discord server.

### Method 2: Running Locally (Python)

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/CS222-UIUC/fa25-team86-discordsportsbot.git
    cd fa25-team86-discordsportsbot
    ```

2.  **Set Up Virtual Environment**
    -   **macOS/Linux**:
        ```bash
        python -m venv .venv
        source .venv/bin/activate
        ```
    -   **Windows**:
        ```powershell
        python -m venv .venv
        .\.venv\Scripts\Activate.ps1
        ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Initialize Database**
    ```bash
    python src/setup_database.py
    ```
    This creates the local `src/sportsbot.db`.

5.  **Configure Environment Variables**
    -   Create a `.env` file (copy `RenameTo.env`) and add your `DISCORD_TOKEN`.

6.  **Run the Bot**
    ```bash
    python src/bot.py
    ```

## Group Members

| Name | Role |
|------|------|
| **Ayana** | API Integration & Data Handling |
| **Rishi Garhyan** | Discord Integration |
| **Hyunho Kim** | Discord Integration |
| **Zeeshan Khan** | API Integration, documentation, and bug handling |

# Copilot Instructions for Sahasrahbot

## Project Overview
Sahasrahbot is a Python project for managing tournaments, bots, and integrations related to ALTTPR (A Link to the Past: Randomizer) and SpeedGaming events. It uses Tortoise ORM for database access and Aerich for migrations. The bot integrates with Discord, Racetime.gg, and other platforms for event management and automation.

## Architecture & Key Components
- **sahasrahbot.py**: Main entry point for the bot.
- **config.py**: Configuration settings and environment variable management.
- **alttprbot/**: Core bot logic, including tournament management, SpeedGaming integration, and utility modules.
- **alttprbot_api/**: API and authentication logic.
- **alttprbot_audit/**: Audit logging and event tracking.
- **alttprbot_discord/**: Discord bot integration and cogs.
- **alttprbot_racetime/**: Racetime.gg bot integration and handlers.
- **migrations/**: Database migration scripts and Tortoise config (`tortoise_config.py`).
- **presets/**, **helpers/**, **utils/**: Game presets, helper scripts, and utilities.
- **docs/**: Documentation for users and developers.

## Developer Workflows
- **Install dependencies:** `poetry install`
- **Run the bot:** `poetry run python sahasrahbot.py`
- **Database migrations:** Use Aerich (`poetry run aerich migrate`, `poetry run aerich upgrade`). Config in `pyproject.toml` and `migrations/tortoise_config.py`.
- **Configuration:** Set environment variables as needed (see `config.py` and `migrations/tortoise_config.py`).

## Patterns & Conventions
- **Async/await:** Used for DB and bot actions.
- **Tortoise ORM:** For models and DB access.
- **Aerich:** For migrations.
- **Modular structure:** Each bot/integration in its own folder.
- **Presets and helpers:** For game logic and migration scripts.
- **Discord integration:** Managed via Discord.py and custom cogs.
- **Audit logging:** Use modules in `alttprbot_audit/` for event tracking.

## Integration Points
- **Discord:** OAuth login, user info, and messaging (see `alttprbot_discord/`).
- **Racetime.gg:** Race management and event tracking (see `alttprbot_racetime/`).
- **Database:** MySQL via Tortoise ORM; config in `.env` and `migrations/tortoise_config.py`.

## Examples
- To add a new bot feature: create a module in `alttprbot/` or a cog in `alttprbot_discord/cogs/`.
- To add a migration: define a Tortoise `Model` in the appropriate folder, run Aerich migrations.
- To add audit logging: use helpers in `alttprbot_audit/`.
- To add a preset: update files in `presets/`.

## References
- See `README.md` for more details.
- See `pyproject.toml` for dependencies and Aerich config.

---
If any section is unclear or missing, please provide feedback for further refinement.

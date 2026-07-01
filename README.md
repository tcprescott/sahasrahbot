# SahasrahBot

This really wasn't meant to be publically viewable, but since people asked for the code here it is.

This is mostly here for transparency purposes, as this bot is responsible for rolling games for racing.  However, I cannot provide any support with setting this bot up locally or getting a local dev environment going.

If there's any feature within this bot that you'd like to use for your own project, feel free to use it within the terms of the license agreement attached.

Thanks,

Thomas Prescott, aka Synack

## Development setup

```bash
# Install dependencies
poetry install

# Door-randomizer presets need the utils/ submodules + enemizer binaries
git submodule update --init
(cd utils/enemizer && ./install.sh)

# Configure environment — copy and fill in required values
cp .env.example .env

# Validate config before running
poetry run python helpers/validate_runtime_config.py

# Apply database migrations
poetry run aerich upgrade

# Run the application
poetry run python sahasrahbot.py
```

Full documentation lives under [`docs/`](docs/MASTER_INDEX.md); developer guidelines are in [`CLAUDE.md`](CLAUDE.md).

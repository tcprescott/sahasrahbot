## Summary

<!-- What changed, and why. One or two sentences is usually enough. -->

## Testing

<!-- How you verified this: `./scripts/check.sh`, commands run, what you tried in Discord or racetime.gg by hand. -->

## Checklist

- [ ] `./scripts/check.sh` passes (ruff, guardrails, pytest)
- [ ] No privileged intents requested, and no reliance on the member cache (use `alttprbot/util/discord_members.py`)
- [ ] New `config.X` settings added to `config.example.py` with a placeholder, and called out below for production
- [ ] Model change: migration generated with `poetry run aerich migrate` and committed
- [ ] User-facing command or preset change: `docs/` (the public site) updated

# testdata: anonymized, production-shaped fixtures

Small, connected slices of SahasrahBot's production data with every personal and
secret value replaced. Used by `tests/test_testdata.py` and seeded by the dev server
(`./scripts/dev.sh`) after its hand-made rows.

| File | What's in it |
|---|---|
| `users.json` | The fake users every feature refers to, plus the fake Discord world (guilds, channels, roles, members) the dev server builds from them |
| `asynctournament.json` | 4 async tournaments: an active one, a two-runs-per-pool one, and runner samples from two large qualifiers; pools, seeds, live races, permissions, races |
| `ranked_choice.json` | 6 elections: open and role-gated, one with an authorized-voter list, active and finished, multi-seat; sampled ballots and recomputed results |
| `presets.json` | 12 preset namespaces, including every one with collaborators. The dump had no `presets` table, so their presets are copies of this repo's `presets/` files |

Fixture primary keys start at 1001, so they sit beside the dev server's hand-made rows.

## What was replaced

- Discord user, guild, channel, role, message and thread ids: fake snowflakes,
  `91…` users, `92…` guilds, `93…` channels, `94…` roles, `95…` messages, `96…` threads.
  The same real id always maps to the same fake one, across every file.
- Usernames, display names, Twitch names, namespace names: fake handles (`AmberLynx001`).
- racetime ids: fake (`fk0001…`); racetime access tokens: removed.
- Candidate names in elections between people: fake names. Option names (rules,
  game modes) are kept. Election descriptions are replaced; results are recounted
  from the kept ballots with the same algorithm the bot uses.
- Runner notes, reviewer notes and reattempt reasons: picked from a fixed list.
- VOD links, seed permalinks, racetime room slugs, SpeedGaming episode ids: fake.
- Kept as is: tournament, pool and election titles, statuses, scores, par times,
  timestamps. `updated` columns are reset to the load time by the ORM.

## Regenerating

Unzip the dump **outside the repo** and run:

```bash
poetry run python -I scripts/scrub_prod_dump.py /path/to/Dump20261123
```

The script only parses the SQL text; it never runs it. Before writing, it searches the
output for every real Discord-sized id, username and racetime id/token in the dump,
and for any big number outside the fake ranges, and refuses to write if it finds one.
Which tournaments, elections and namespaces are sliced is set at the top of the script.

Never commit the raw dump or anything derived from it that didn't go through the script.

## Dropping a feature

Delete its JSON file. The loader, the dev server and the tests only use the files
that exist; to stop regenerating it, remove its `slice_*` call from `build()` in the script.

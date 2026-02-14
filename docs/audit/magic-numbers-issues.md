# Codebase Audit: Magic Numbers & Unexplained Logic — GitHub Issues

Generated 2026-02-14 from a comprehensive codebase audit.

---

## Issue 1: Fix known-broken ranked choice validation

**Labels:** `bug`, `priority: critical`

### Description

`alttprbot_api/blueprints/ranked_choice.py:87-88` contains code that is self-acknowledged as broken:

```python
if dupcheck([v for v in payload.values() if not v == '']):  # this is broken and we're not sure why
    return await abort(400, "Each candidate must have a unique rank.")
```

The comment `this is broken and we're not sure why` indicates a known defect shipped to production with no remediation plan, no issue ticket, and no follow-up.

### Action items

- [ ] Investigate `dupcheck()` logic and determine what is broken
- [ ] Fix or remove the broken check
- [ ] Add tests for the ranked choice validation path

---

## Issue 2: Replace bare `except:` clauses with specific exception handling

**Labels:** `bug`, `code quality`

### Description

Two bare `except:` clauses silently swallow all exceptions, including `SystemExit` and `KeyboardInterrupt`:

1. **`alttprbot/alttprgen/randomizer/smdash.py:25-36`** — catches everything and returns hardcoded defaults without logging:
   ```python
   except:
       return ['classic', 'recall', '2017_mm', 'chozo_bozo', 'sgl23', 'surprise_surprise']
   ```

2. **`alttprbot/alttprgen/generator.py:304-314`** — bare except with commented-out audit code:
   ```python
   except:
       # await models.AuditGeneratedGames.create(...)
       logging.exception("Failed to generate game, retrying...")
       raise
   ```

### Action items

- [ ] Replace bare `except:` with `except Exception:` (at minimum)
- [ ] Add logging to the smdash fallback so API failures are visible
- [ ] Decide whether the commented-out audit code in generator.py should be restored or deleted

---

## Issue 3: Extract hardcoded Discord IDs into a constants/config module

**Labels:** `enhancement`, `code quality`, `tech debt`

### Description

60+ hardcoded Discord guild, channel, role, and user IDs are scattered across the codebase with no documentation mapping them to human-readable names. Examples:

| File | IDs | Purpose |
|------|-----|---------|
| `tournament/alttpr.py:136-154` | `334795604918272012`, `647966639266201620`, 6 role IDs | Guild, audit channel, roles |
| `tournament/alttprleague.py:50-65` | Multiple guild/channel/role IDs | League config |
| `tournament/smrl.py:156-166` | SMRL-specific IDs | Tournament config |
| `alttprbot_discord/cogs/tournament.py:22-23` | Role IDs with debug/prod split | Admin roles |
| `alttprbot_discord/cogs/bontamw.py:65-66` | `507932829527703554`, `482266765137805333` | French community roles |
| `alttprbot_discord/cogs/misc.py:92` | `543572578787393556` | Channel in help text |
| `alttprbot_audit/cogs/audit.py:64,126` | `606873327839215616`, `694710452478803968`, `694710286455930911` | Channels ignored "for reasons" |
| `alttprbot_discord/bot.py:122` | `508335685044928540` | Debug guild |
| `alttprbot/alttprgen/generator.py:492` | `185198185990324225` | Privilege escalation for specific user |

If any Discord entity is renamed, deleted, or migrated, there is no way to find all references without grepping.

### Action items

- [ ] Create a `discord_ids.py` constants module (or move to config/env)
- [ ] Document each ID with the entity name it refers to
- [ ] Replace all inline IDs with named constants
- [ ] Consider moving tournament-specific IDs to tournament YAML configs

---

## Issue 4: Document and extract timing/delay magic numbers

**Labels:** `enhancement`, `code quality`

### Description

Numerous timing constants are hardcoded inline with no rationale documented:

**Race timing parameters:**
- `start_delay=15` (8 tournament files) vs `start_delay=30` (2 files) — why different?
- `time_limit=24` — hours? No unit documented
- `stream_delay=10` vs `15` vs `0` — varies by tournament, no explanation
- `studytime = 25 * 60` in `smz3.py:106` — why 25 minutes?

**Background loop intervals:**
- `5 min` — daily announcement check
- `15 min` — weekly race check
- `240 min` (4h) — find races with bad Discord info
- `1440 min` (24h) — racer reverification

**Sleep workarounds:**
- `asyncio.sleep(2)` in `sglive.py:111` — "workaround for tournament branch seeds not being available immediately"
- `asyncio.sleep(random.random() * 5)` in `misc.py:71` — unexplained random delay before reactions
- 600-second subtraction in `core.py:157-160` — cryptic reauth timer adjustment

**Retry config duplicated 4 times:**
- `stop_after_attempt(5), wait_exponential(min=4, max=10)` — should be shared

### Action items

- [ ] Extract timing constants with documented rationale (e.g. `RACE_START_DELAY_SECONDS = 15  # allow participants to ready up`)
- [ ] Document why different tournaments use different delays
- [ ] Add comments explaining the sleep workarounds or fix the underlying issues
- [ ] Centralize retry configuration

---

## Issue 5: Document and unify seed range constants

**Labels:** `enhancement`, `code quality`

### Description

Each randomizer uses different, undocumented seed bounds with no explanation of why:

| Randomizer | Range | File |
|-----------|-------|------|
| AOSR | `-2147483648` to `2147483647` (INT32) | `randomizer/aosr.py:5` |
| Z1R | `0` to `8999999999999999999` | `randomizer/z1r.py:5` |
| Z2R | `0` to `1000000000` | `randomizer/z2r.py:32` |
| SMB3R | `0` to `999999999999` | `randomizer/smb3r.py:5` |
| FFR | `0` to `16^8` (~4.3B) | `randomizer/ffr.py:6` |
| SMZ3/SMR | `0` to `2147483647` (INT32_MAX, duplicated) | `handlers/smz3.py`, `handlers/smr.py` |
| Bingosync | `0` to `899999` | Multiple files |

The value `2147483647` appears in multiple files and should be a shared constant.

### Action items

- [ ] Add comments explaining each randomizer's seed range (determined by upstream API? game limitation?)
- [ ] Extract shared values like `INT32_MAX = 2147483647` into a constants module
- [ ] Document why bingosync uses `899999` specifically

---

## Issue 6: Add documentation to SNES ROM address conversion and URL regex

**Labels:** `enhancement`, `documentation`

### Description

Two utility functions contain complex logic with zero documentation:

1. **`alttprbot/util/rom.py:1-7`** — SNES LoROM address conversion:
   ```python
   def snes_to_pc_lorom(snes_address):
       return (snes_address & 0x7F0000) >> 1 | (snes_address & 0x7FFF)
   ```
   Uses bit masks `0x7F0000`, `0x7FFF`, `0x8000` related to the SNES LoROM memory model. No docstring, no explanation of the memory mapping, no test cases.

2. **`alttprbot_audit/cogs/moderation.py:137-139`** — URL detection regex:
   ```python
   re_equ = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»""'']))"
   ```
   5 capture groups, nested parentheses handling, unicode quote exclusions — completely opaque. Variable name `re_equ` is cryptic.

### Action items

- [ ] Add docstrings to ROM conversion functions explaining the LoROM memory model
- [ ] Name the magic bit masks as constants (e.g., `LOROM_BANK_MASK = 0x7F0000`)
- [ ] Document the URL regex with inline comments or use `re.VERBOSE` mode
- [ ] Rename `re_equ` to `URL_PATTERN` or similar
- [ ] Consider replacing the regex with a URL parsing library

---

## Issue 7: Standardize Discord message length handling

**Labels:** `enhancement`, `code quality`

### Description

Three different thresholds are used for the same concept (Discord's 2000-character message limit):

| File | Threshold | Effective buffer |
|------|-----------|-----------------|
| `alttprbot_audit/bot.py:67` | `1990` | 10 chars |
| `alttprbot_discord/cogs/racer_verification.py:90` | `1800` | 200 chars |
| `alttprbot_audit/cogs/audit.py:311` | `1000` / `1020` | varies |

### Action items

- [ ] Define a single constant (e.g., `DISCORD_MAX_MESSAGE_LENGTH = 2000`) in a shared utils module
- [ ] Create a helper function for message truncation/splitting
- [ ] Replace all inline length checks with the shared constant

---

## Issue 8: Fix unsafe feature flag defaults and inconsistent config patterns

**Labels:** `bug`, `code quality`

### Description

Feature flags default to unsafe values when config keys are missing:

**`alttprbot_discord/bot.py:46`:**
```python
if getattr(config, 'DISCORD_ROLE_ASSIGNMENT_ENABLED', True):
```
If the config key is missing, role assignment is **enabled** by default. Should default to `False` (fail-safe).

**`alttprbot_racetime/config.py:15-21`:**
```python
return getattr(config, f"RACETIME_CLIENT_ID_{self.category_slug.upper().replace('-', '')}")
```
Dynamic attribute resolution without validation. If the attribute doesn't exist, `getattr()` returns `None` silently, leading to cryptic downstream errors.

### Action items

- [ ] Change feature flag defaults to `False` (fail-safe)
- [ ] Add validation for dynamically resolved config attributes
- [ ] Raise clear errors when required config keys are missing

---

## Issue 9: Clean up mystery doors generator: variable mutation, infinite loop, ambiguous logic

**Labels:** `code quality`, `tech debt`

### Description

`alttprbot/alttprgen/randomizer/mysterydoors.py` contains several obscure patterns:

1. **Variable semantic mutation (lines 266-279):** `doors` is computed as a boolean, then unconditionally overwritten to `True` 13 lines later — the original value is discarded.

2. **Infinite loop with buried termination (lines 243-255):** `while True` loop with break condition 7 lines deep, dependent on the return contract of `get_random_option()`.

3. **Dictionary surgery:** `weights = {**weights, **subweights}` with a confusing deep update pattern.

### Action items

- [ ] Rename variables to clarify semantic intent (e.g., `has_door_shuffle` vs `force_doors`)
- [ ] Document the loop's termination condition
- [ ] Add comments explaining the weight merging strategy

---

## Issue 10: Fix typo and anti-patterns in racetime core

**Labels:** `bug`, `code quality`

### Description

**`alttprbot_racetime/core.py:261`:**
```python
if not race_name.split('/')[0] == self.category_slug:
    raise Exception('Race is not for the bot\'s category category.')
```

Issues:
- `not x == y` should be `x != y` (PEP8 / Pythonic style)
- Typo in error message: "category category" (duplicated word)
- Raises bare `Exception` instead of a specific exception type

### Action items

- [ ] Change `not x == y` to `x != y`
- [ ] Fix the "category category" typo
- [ ] Use a specific exception type

---

## Issue 11: Inconsistent hash/slug length constants

**Labels:** `code quality`

### Description

Various truncation lengths are used across the codebase with no documented rationale:

| Usage | Length | File |
|-------|--------|------|
| Spoiler log keys | `20` | Multiple |
| Door hash | `12` | `alttprdoor.py` |
| Filename suffix | `4` | Various |
| Bingo passphrase | `8` | `bingo.py` |
| Slugify max length | `19` | `smmulti.py:171` |
| Slugify max length | `20` | `asynctournament.py:291` |
| `auto_archive_duration` | `1440` | Multiple (means 24 hours) |

The slugify lengths of 19 and 20 are inconsistent and may cause bugs.

### Action items

- [ ] Investigate if `19` vs `20` slugify lengths is intentional
- [ ] Extract `auto_archive_duration=1440` to a named constant (e.g., `ARCHIVE_AFTER_24H = 1440`)
- [ ] Document truncation length rationale where relevant

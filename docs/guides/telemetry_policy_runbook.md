# Telemetry Policy & Operator Runbook

> **Last updated:** 2026-02-12  
> **Status:** MVP deployed

## Overview

SahasrahBot implements privacy-preserving anonymous telemetry to understand feature usage and reliability across Discord, RaceTime, and Web/API surfaces.

## Privacy Policy

### Data Minimization

Telemetry is designed to be **anonymous by design** and **aggregate-safe**:

- **No user identity:** No Discord user IDs, usernames, discriminators, or OAuth identifiers
- **No personal content:** No message text, seed payloads, request bodies, or spoiler content
- **No behavior profiling:** Cannot track individuals across sessions
- **Guild anonymization:** Guild IDs are hashed with a salt (one-way, not reversible)
- **Short retention:** Default 30-day retention with automated purge

### Allowed Fields

The telemetry system stores **only** the following fields:

| Field | Description | Example Values |
|-------|-------------|----------------|
| `event_name` | Namespaced event identifier | `discord.generator.preset.invoke` |
| `surface` | Execution surface | `discord`, `racetime`, `api` |
| `feature` | Feature/module name | `generator`, `daily`, `asynctournament` |
| `action` | Event lifecycle stage | `invoke`, `success`, `failure` |
| `status` | Outcome status | `ok`, `error`, `timeout`, `denied` |
| `provider` | External service name (optional) | `alttpr`, `sm.samus.link` |
| `guild_hash` | Salted one-way hash of guild ID (optional) | SHA-256 hash |
| `day_bucket` | UTC date only | `2026-02-12` |
| `duration_ms` | Execution time in milliseconds (optional) | `1234` |
| `error_type` | Normalized error category (optional) | `invalid_preset`, `provider_timeout` |
| `sample_rate` | Sampling rate for this event | `1.0` |

### Prohibited Fields

The following fields are **strictly prohibited** in telemetry storage:

- ❌ Raw Discord user IDs
- ❌ Usernames or display names
- ❌ Discriminators
- ❌ OAuth user identifiers or session tokens
- ❌ Raw guild/channel IDs (must be hashed)
- ❌ Raw command arguments when they can contain custom text
- ❌ Request IP addresses
- ❌ User-agent strings
- ❌ Full exception stack traces

## Configuration

Telemetry is configured via environment variables in `config.py`:

```python
# Enable/disable telemetry (default: false)
TELEMETRY_ENABLED = false

# Sampling rate: 0.0 to 1.0 (default: 1.0 = 100%)
TELEMETRY_SAMPLE_RATE = 1.0

# Retention period in days (default: 30)
TELEMETRY_RETENTION_DAYS = 30

# Salt for hashing guild IDs (required if telemetry enabled)
TELEMETRY_HASH_SALT = "random-secret-salt-value"

# Max queue size before dropping events (default: 1000)
TELEMETRY_QUEUE_SIZE = 1000
```

### Enabling Telemetry

1. Set `TELEMETRY_ENABLED=true` in environment
2. Set `TELEMETRY_HASH_SALT` to a secure random value
3. Restart bot services
4. Verify telemetry is recording: `poetry run python helpers/telemetry_report.py 1`

### Disabling Telemetry

1. Set `TELEMETRY_ENABLED=false` in environment
2. Restart bot services
3. Optionally purge existing data: `poetry run python helpers/purge_old_telemetry.py`

## Architecture

### Components

- **`alttprbot.util.telemetry`**: Core telemetry service
  - `TelemetryEvent`: Validated event dataclass
  - `NoOpTelemetryService`: Silent no-op when disabled
  - `DatabaseTelemetryService`: Async buffered writes with fail-open behavior
  - `record_event()`: Convenience function for instrumentation

- **`alttprbot.models.models.TelemetryEvent`**: ORM model for storage

- **`helpers/purge_old_telemetry.py`**: Retention enforcement script

- **`helpers/telemetry_report.py`**: Usage report generator

### Fail-Open Design

Telemetry is designed to **never impact user-facing flows**:

- All telemetry operations are wrapped in try/except
- Exceptions are logged but never propagated
- Bounded queue prevents unbounded memory growth
- When queue is full, oldest events are dropped

### Data Flow

1. Instrumentation code calls `record_event()`
2. Event is validated and queued in memory
3. Background flush writes batched events to database
4. Retention purge runs daily to delete old events

## Operations

### Viewing Usage Reports

Generate a usage report for the last 7 days:

```bash
poetry run python helpers/telemetry_report.py
```

Generate a report for a custom time period:

```bash
poetry run python helpers/telemetry_report.py 30  # Last 30 days
```

The report includes:
- Total event counts
- Top features by usage
- Success/failure rates by feature
- Approximate active guild count
- Daily breakdowns

### Retention Purge

The retention purge script should run as a scheduled task (e.g., daily cron):

```bash
# Run purge manually
poetry run python helpers/purge_old_telemetry.py

# Example cron (daily at 2am UTC)
0 2 * * * cd /path/to/sahasrahbot && poetry run python helpers/purge_old_telemetry.py >> logs/telemetry_purge.log 2>&1
```

The script:
- Deletes events older than `TELEMETRY_RETENTION_DAYS`
- Logs statistics before and after purge
- Exits with non-zero code on failure

### Monitoring

Monitor telemetry health with:

```bash
# Check queue depth (if exposed)
# Check for "queue full" warnings in logs
grep "Telemetry queue full" logs/*.log

# Verify data is being written
poetry run python helpers/telemetry_report.py 1
```

### Troubleshooting

**No telemetry data appearing:**
- Verify `TELEMETRY_ENABLED=true` in config
- Check bot startup logs for "Telemetry enabled" message
- Verify `TELEMETRY_HASH_SALT` is set

**Queue overflow warnings:**
- Increase `TELEMETRY_QUEUE_SIZE` in config
- Reduce `TELEMETRY_SAMPLE_RATE` to sample fewer events
- Check for database write failures preventing flush

**Database write failures:**
- Check database connection and permissions
- Verify migration 98 has been applied
- Check disk space

## Instrumented Surfaces (MVP)

### Discord

- `discord.generator.preset.invoke` - Generator preset command invoked
- `discord.generator.preset.success` - Generator preset succeeded
- `discord.generator.preset.failure` - Generator preset failed

### RaceTime

*(Not yet instrumented in MVP)*

### API

*(Not yet instrumented in MVP)*

## Future Expansion

Additional instrumentation targets (Phase 2):

- Discord daily announcement cog
- Discord async tournament flows
- RaceTime room commands
- RaceTime seed generation
- API authentication flows
- API seed generation endpoints

## Security Considerations

- **Hash salt rotation:** If `TELEMETRY_HASH_SALT` is ever compromised, rotate immediately and purge all existing data
- **Database access:** Limit telemetry table access to read-only for reporting queries
- **Data export:** Never export telemetry data in a way that could correlate hashes back to guilds
- **Sampling:** Use sampling (`TELEMETRY_SAMPLE_RATE < 1.0`) to reduce storage if volumes grow

## Compliance

This telemetry implementation is designed to be GDPR-compliant due to:

- No personal data collection
- No user profiling capabilities
- Short retention period
- Fail-open behavior (not required for service operation)
- Transparent documentation

If you have compliance concerns, consult with legal counsel.

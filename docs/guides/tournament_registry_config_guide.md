# Tournament Registry Configuration Guide

> Last updated: 2026-02-12  
> Status: Phase 0/1 Complete (Dual-path runtime available)

## Overview

The tournament registry configuration system provides a validated, config-driven approach to managing which tournament handlers are active. This replaces the previous pattern of commenting/uncommenting handlers in source code.

## Architecture

### Dual-Path Runtime

The system supports two operational modes:

1. **Hardcoded Fallback** (default): Uses the original `TOURNAMENT_DATA` dictionary defined in code
2. **Config-Backed**: Loads active handlers from `config/tournaments.yaml`

The active mode is controlled by the `TOURNAMENT_CONFIG_ENABLED` flag in `config.py`.

### Key Components

#### 1. AVAILABLE_TOURNAMENT_HANDLERS

Static capability catalog in `alttprbot/tournaments.py`:

```python
AVAILABLE_TOURNAMENT_HANDLERS = {
    'test': test.TestTournament,
    'alttpr': alttpr_quals.ALTTPRQualifierRace,
    'alttprdaily': dailies.AlttprSGDailyRace,
    # ... all available handlers
}
```

**Purpose:** Defines what handlers exist in the codebase (capability).

#### 2. config/tournaments.yaml

Runtime configuration file that controls which handlers are active (policy).

**Purpose:** Seasonal activation/deactivation without code changes.

#### 3. registry_loader.py

Loader module in `alttprbot/tournament/registry_loader.py`:

- Parses YAML configuration
- Validates schema and handler references
- Builds active registry from enabled events
- Provides startup logging

**Purpose:** Fail-fast validation before operational loops begin.

## Configuration Schema

### File Structure

```yaml
version: 1

profiles:
  debug:
    events:
      - event_slug: test
        handler: test
        enabled: true
        notes: "Optional description"

  production:
    events:
      - event_slug: alttpr
        handler: alttpr
        enabled: true
        notes: "Main qualifier"
```

### Required Fields

- `version` (integer): Schema version (currently 1)
- `profiles` (object): Profile configurations
  - `debug` (object): Debug profile (when `config.DEBUG = True`)
  - `production` (object): Production profile (when `config.DEBUG = False`)

### Profile Fields

- `events` (list): List of event configurations

### Event Fields

- `event_slug` (string, required): Unique event identifier
- `handler` (string, required): Handler key from `AVAILABLE_TOURNAMENT_HANDLERS`
- `enabled` (boolean, required): Whether this event is active
- `notes` (string, optional): Description or notes

### Validation Rules

1. `event_slug` must be non-empty and unique per profile
2. `handler` must reference a key in `AVAILABLE_TOURNAMENT_HANDLERS`
3. `enabled` must be a boolean
4. Duplicate `event_slug` values are rejected
5. Unknown handler references are rejected

## Operational Usage

### Enabling Config-Backed Mode

In your `config.py`:

```python
TOURNAMENT_CONFIG_ENABLED = True  # Enable config-backed registry
```

**Default:** `False` (uses hardcoded fallback)

### Seasonal Activation Changes

To enable a seasonal tournament in `config/tournaments.yaml`:

```yaml
- event_slug: boots
  handler: boots
  enabled: true  # Changed from false
  notes: "ALTTPR CAS Boots Tournament - Season 2026"
```

To disable:

```yaml
- event_slug: boots
  handler: boots
  enabled: false  # Changed from true
  notes: "ALTTPR CAS Boots Tournament - disabled off-season"
```

**No code changes required** - just edit YAML and restart.

### Startup Logs

When the bot starts, you'll see registry initialization logs:

**Hardcoded mode:**
```
INFO: Tournament Registry: source=hardcoded, profile=production, 
      enabled_events_count=5, enabled_event_slugs=['alttpr', 'alttprdaily', ...]
```

**Config-backed mode:**
```
INFO: Tournament Registry: source=config, profile=production, 
      enabled_events_count=5, disabled_events_count=7,
      enabled_event_slugs=['alttpr', 'alttprdaily', ...]
```

### Validation Failure Behavior

If config validation fails, the bot will:

1. Log a FATAL error message
2. Raise `TournamentConfigError`
3. **Prevent tournament loops from starting**

Example:
```
ERROR: FATAL: Tournament config validation failed: 
       Profile 'production': event 'invalid_event': unknown handler 'nonexistent'
ERROR: Tournament loops will not start. Fix config and restart.
```

## Validation Tools

### Manual Validation

```bash
python3 helpers/validate_tournament_config.py
```

This validates:
- YAML syntax
- Schema compliance
- Handler references
- Profile completeness

### Demonstration

```bash
# Test hardcoded fallback path
python3 helpers/demo_tournament_registry.py hardcoded

# Test config-backed path
python3 helpers/demo_tournament_registry.py config
```

## Rollback Strategy

If config-backed mode causes issues:

1. Set `TOURNAMENT_CONFIG_ENABLED = False` in `config.py`
2. Restart the bot
3. System reverts to hardcoded `TOURNAMENT_DATA`

**Rollback window:** Hardcoded registry remains available until Phase 3 cleanup.

## Migration Path

### Current State (Phase 0/1)

- Dual-path runtime available
- Hardcoded registry preserved as default
- Config-backed mode available for testing

### Future Phases

- **Phase 2:** Enable config-backed mode in production
- **Phase 3:** Remove hardcoded registry after validation period

## Best Practices

### When to Use Config vs Hardcoded

**Use config-backed mode when:**
- Seasonal tournaments change frequently
- Multiple operators need to manage activation
- You want fail-fast validation before loops start

**Use hardcoded fallback when:**
- Emergency rollback is needed
- Config validation is failing
- Testing minimal tournament set

### Configuration Management

1. **Always validate** before deploying config changes
2. **Document seasonal changes** in the `notes` field
3. **Review startup logs** to confirm active handler set
4. **Keep disabled events** in config for documentation

### Adding New Handlers

1. Add handler class to codebase
2. Register in `AVAILABLE_TOURNAMENT_HANDLERS`
3. Add entry to `config/tournaments.yaml` (disabled by default)
4. Enable when ready for seasonal activation

## Troubleshooting

### Config validation fails on startup

**Check:**
1. YAML syntax (use validation script)
2. Handler references match `AVAILABLE_TOURNAMENT_HANDLERS`
3. No duplicate `event_slug` values
4. All required fields present

### Tournament loops not creating races

**Check:**
1. Startup logs show correct active events
2. Event is marked `enabled: true` in config
3. Handler reference is correct
4. `TOURNAMENT_CONFIG_ENABLED` is set correctly

### Rollback not working

**Verify:**
1. `TOURNAMENT_CONFIG_ENABLED = False` in `config.py`
2. Bot has been restarted
3. Startup logs show `source=hardcoded`

## References

- [Tournament Registry Config Design](../design/tournament_registry_config_design.md)
- [Tournament Registry Config Rollout Plan](../plans/tournament_registry_config_rollout_plan.md)
- [Modernization Compatibility Gate Validation Runbook](../plans/modernization_compatibility_gate_validation_runbook.md)

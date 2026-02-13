# Discord OAuth Behavior Contract

> **Status:** Phase 0 Discovery  
> **Last updated:** 2026-02-12  
> **Related plan:** [Authlib Discord OAuth Migration Plan](../plans/authlib_discord_oauth_migration_plan.md)

## Purpose

Documents the expected behavior contract for Discord OAuth authentication to ensure parity between Quart-Discord (legacy) and Authlib (target) implementations.

## OAuth Flow Behavior Matrix

| Operation | Current Behavior (Quart-Discord) | Required Parity (Authlib) | Notes |
|-----------|----------------------------------|---------------------------|-------|
| **Login Initiation** | `discord.create_session(scope=['identify'], data={...})` returns redirect response to Discord OAuth authorize URL | Must return equivalent redirect response | Preserve `scope` and `data` passthrough for redirect tracking |
| **OAuth Callback** | `discord.callback()` exchanges code for token, stores in session, returns data dict with redirect target | Must exchange code, store token in session, return equivalent data | Session storage mechanism must be compatible |
| **Fetch User** | `discord.fetch_user()` retrieves Discord user object from API using stored token | Must retrieve user object with same fields | User object shape must match or be adapted |
| **Authorization Check** | `@requires_authorization` decorator redirects to login if no valid token in session | Must provide equivalent decorator behavior | Redirect logic and session check must match |
| **Token Revocation** | `discord.revoke()` clears token from session (does not call Discord API) | Must clear session token equivalently | Session clearing behavior must match |
| **Unauthorized Error** | Raises `Unauthorized` exception when token missing/invalid | Must raise compatible exception | Error handler contract must be preserved |
| **Access Denied Error** | Raises `AccessDenied` exception on OAuth denial | Must raise compatible exception | Error handler contract must be preserved |

## Session Contract

### Token Storage
- **Key:** Quart-Discord stores token under session key (implementation detail)
- **Scope:** Session-scoped, server-side session store
- **Lifetime:** Session lifetime controlled by `app.secret_key` and Quart session config

### Required Session Fields
- OAuth access token (for API calls to Discord)
- Token type (Bearer)
- User identification data (cached or token-derived)

## API Endpoints Affected

### Direct OAuth Endpoints
- `GET /login/` - Initiates OAuth flow
- `GET /callback/discord/` - Handles OAuth callback
- `GET /logout/` - Revokes/clears session
- `GET /` - Displays user if authenticated (optional)
- `GET /me/` - Requires authentication

### Protected Blueprint Routes
Routes using `@requires_authorization` decorator:
- **asynctournament**: 6 human-facing routes
- **presets**: 4 routes
- **racetime**: 2 routes  
- **ranked_choice**: 2 routes
- **schedule**: 4 routes (DEBUG only)
- **sglive**: Uses `fetch_user()` but no decorator (optional auth)
- **tournament**: 2 routes
- **triforcetexts**: 4 routes
- **user**: Routes (DEBUG only)

## Security Requirements

### Current State (Quart-Discord)
- ❌ `OAUTHLIB_INSECURE_TRANSPORT=1` forced globally
- ⚠️ `APP_SECRET_KEY` defaults to empty string
- ✅ CSRF state validation (built into Quart-Discord)
- ✅ Redirect URI validation (configured)

### Target State (Authlib)
- ✅ Must support HTTPS in production (conditional insecure transport)
- ✅ Must enforce non-empty session secret
- ✅ CSRF state validation (built into Authlib)
- ✅ Redirect URI validation (configured)
- ✅ Token storage in secure session cookies

## Error Handling

### Expected Error Scenarios
1. **No token in session** → Redirect to `/login/` with original path stored
2. **Token expired** → Redirect to `/login/` (Quart-Discord does not auto-refresh)
3. **OAuth denial** → Render error page with access denied message
4. **Invalid grant** → Redirect to `/login/`

### Observability Requirements
Structured logging for:
- Auth success (user ID, timestamp)
- Auth failure (reason, original path)
- Token expiry (user ID, timestamp)
- OAuth callback errors (error code, description)

## Rollback Strategy

### Feature Flag: `USE_AUTHLIB_OAUTH`
- **Default:** `False` (Quart-Discord active)
- **Type:** Boolean configuration in `config.py`
- **Scope:** Global runtime selector

### Dual-Path Selection Points
1. OAuth client initialization (`alttprbot_api/api.py`)
2. Authorization decorator registration
3. Error handler registration

## Non-Goals (Out of Scope)

- User-facing OAuth flow redesign
- Multi-provider OAuth support
- Token refresh/renewal (neither implementation supports this currently)
- Session storage backend changes
- Authorization key system (`alttprbot_api/auth.py` - separate auth path)

## Success Criteria

- [ ] All protected routes function identically under both implementations
- [ ] Session lifecycle (login → callback → fetch_user → logout) preserves same behavior
- [ ] Error handling produces equivalent user experience
- [ ] No change in security posture (and ideally improvement)
- [ ] Feature flag allows instant rollback

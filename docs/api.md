---
layout: default
title:  API and AI clients
---
# The SahasrahBot API and AI clients

SahasrahBot's website has a REST API for your own scripts, and an MCP server so AI
clients like Claude can use SahasrahBot as you. Both act as your Discord account and
can do what you can do on the website: read and save presets, roll seeds, look up a
seed by its hash, vote in and run elections in servers you administer, submit and
moderate triforce texts, and submit tournament race settings.

Make tokens and see your connected clients on the website, under **Me**, then
**API access** (`/me/api`).

## Connect Claude (or another AI client)

The MCP address is the website's address followed by `/mcp`. The API access page shows
it with a copy button.

- **Claude on the web or desktop:** Settings, then Connectors, then *Add custom
  connector*. Paste the MCP address, then sign in with Discord when asked.
- **Claude Code:** `claude mcp add --transport http sahasrahbot <MCP address>`, then
  run `/mcp` in Claude Code to sign in.

SahasrahBot then asks you to approve the client. It can always read. Tick **Also let it
make changes as you** if you want it to save presets, vote and so on; otherwise it only
sees the tools that read (rolling a seed counts as reading). You can disconnect a client
at any time on the API access page.

## Personal access tokens (REST API)

Press **New token** on the API access page, name it, choose *Read only* or *Read and make
changes*, and pick when it expires. The token is shown once: copy it then.

Send it in the `Authorization` header:

```
curl -H "Authorization: Bearer sb_pat_…" https://<website>/api/v1/me
```

Every endpoint is described at `/api/v1/docs` on the website. A read-only token gets
`403` from anything that changes data, except rolling a seed (`POST /api/v1/seeds`).
Making tokens, approving AI clients and deleting your data only work on the website.
Errors come back as `{"error": "…"}`.

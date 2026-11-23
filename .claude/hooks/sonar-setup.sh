#!/usr/bin/env bash
# sonar-setup.sh — SessionStart hook: give cloud sessions the SonarQube CLI and,
# where possible, the SonarQube MCP server, so agents can read SonarCloud
# results (project tcprescott_sahasrahbot, organization tcprescott).
#
# Runs only in cloud sessions that have a SONAR_TOKEN (set it as a secret or
# environment variable on the cloud environment; never commit it). Everything
# fails open: a failed step prints a note and the session carries on.
#
# Without a token the project is still public, so the web API works anonymously:
#   curl "https://sonarcloud.io/api/issues/search?componentKeys=tcprescott_sahasrahbot&pullRequest=<N>&resolved=false"
set -uo pipefail

if [[ "${CLAUDE_CODE_REMOTE:-}" != "true" || -z "${SONAR_TOKEN:-}" ]]; then
  exit 0
fi

SONAR_ORG=tcprescott
SONAR_SERVER=https://sonarcloud.io
SONAR_BIN_DIR="$HOME/.local/share/sonarqube-cli/bin"
LOG=/tmp/sonar-setup.log
export PATH="$SONAR_BIN_DIR:$PATH"

# 1. Install the CLI (SonarSource's script downloads one binary into $SONAR_BIN_DIR).
if ! command -v sonar >/dev/null 2>&1; then
  script=$(mktemp)
  if curl -fsSL --proto '=https' --tlsv1.2 -o "$script" \
      https://raw.githubusercontent.com/SonarSource/sonarqube-cli/refs/heads/master/user-scripts/install.sh; then
    PROFILE=/dev/null bash "$script" >>"$LOG" 2>&1 || true
  fi
  rm -f "$script"
fi
if ! command -v sonar >/dev/null 2>&1; then
  echo "SonarQube: CLI install failed (see $LOG). Use the public web API instead."
  exit 0
fi

# 2. The CLI authenticates from these variables; there is no keychain in the
#    container. CLAUDE_ENV_FILE carries them into the session's Bash commands.
export SONARQUBE_CLI_TOKEN="$SONAR_TOKEN"
export SONARQUBE_CLI_ORG="$SONAR_ORG"
export SONARQUBE_CLI_SERVER="$SONAR_SERVER"
if [[ -n "${CLAUDE_ENV_FILE:-}" ]]; then
  {
    echo "export PATH=\"$SONAR_BIN_DIR:\$PATH\""
    echo 'export SONARQUBE_CLI_TOKEN="$SONAR_TOKEN"'
    echo "export SONARQUBE_CLI_ORG=$SONAR_ORG"
    echo "export SONARQUBE_CLI_SERVER=$SONAR_SERVER"
  } >>"$CLAUDE_ENV_FILE"
fi

if ! sonar auth status >>"$LOG" 2>&1; then
  echo "SonarQube: CLI installed but SONAR_TOKEN was rejected (see $LOG). Use the public web API instead."
  exit 0
fi

# 3. The MCP server runs in a container. Cloud containers ship Docker with the
#    daemon stopped; start it if we can.
if command -v docker >/dev/null 2>&1 && ! docker ps >/dev/null 2>&1 && command -v dockerd >/dev/null 2>&1; then
  (dockerd >/tmp/dockerd.log 2>&1 &)
  for _ in $(seq 1 20); do docker ps >/dev/null 2>&1 && break; sleep 1; done
fi

# 4. Wire the MCP server and secrets-scanning hooks into the user-level Claude
#    config (~/.claude), not the repo. Run from $HOME so no repo file changes.
( cd "$HOME" && sonar integrate claude --non-interactive >>"$LOG" 2>&1 ) || true

echo "SonarQube CLI ready (org $SONAR_ORG, project tcprescott_sahasrahbot): e.g." \
  "'sonar list issues -p tcprescott_sahasrahbot --pull-request <N>', 'sonar qg status -p tcprescott_sahasrahbot'." \
  "If no mcp__sonarqube__* tools appear, the MCP server is wired for the next session; the CLI works now."
exit 0

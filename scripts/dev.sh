#!/usr/bin/env bash
# dev.sh — run the web app standalone, with fake Discord, racetime.gg and
# SpeedGaming, against a seeded local MariaDB. See CLAUDE.md, "Running the web
# app standalone".
#
#   ./scripts/dev.sh             start (seeds the database the first time, builds web/)
#   ./scripts/dev.sh --reset     drop every table and reseed, then start
#   ./scripts/dev.sh --port 5002 any other flag goes to `python -m devserver`
#   ./scripts/dev.sh db-down     stop the database container (keeps its data)
#   ./scripts/dev.sh db-destroy  delete the database container and its data
#
# Set DEV_DB_URL=mysql://user:pass@host:port/db to use a MariaDB/MySQL you run
# yourself; the script then leaves Docker alone. Never point it at production:
# --reset drops every table.
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE=(docker compose -f docker-compose.dev.yml)

# The dev database's password: generated once, kept in a gitignored file.
PASSWORD_FILE=.devdb-password
if [[ ! -s "$PASSWORD_FILE" ]]; then
  python3 -c 'import secrets; print(secrets.token_hex(16))' > "$PASSWORD_FILE"
  chmod 600 "$PASSWORD_FILE"
fi
export DEV_DB_PASSWORD="$(cat "$PASSWORD_FILE")"

case "${1:-}" in
  db-down) exec "${COMPOSE[@]}" down ;;
  db-destroy) exec "${COMPOSE[@]}" down -v ;;
  *) ;;  # anything else starts the app below
esac

if [[ -z "${DEV_DB_URL:-}" ]]; then
  export DEV_DB_URL="mysql://sahasrahbot:${DEV_DB_PASSWORD}@127.0.0.1:3307/sahasrahbot_dev"
  if ! command -v docker >/dev/null 2>&1; then
    echo "dev.sh: Docker is not installed. Install it, or set DEV_DB_URL to a MariaDB/MySQL database." >&2
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    # Cloud sessions ship the Docker engine without a running daemon.
    if [[ "${CLAUDE_CODE_REMOTE:-}" == "true" ]] && command -v dockerd >/dev/null 2>&1; then
      echo "dev.sh: starting the Docker daemon"
      (dockerd >/tmp/dockerd.log 2>&1 &)
      for _ in $(seq 1 30); do docker info >/dev/null 2>&1 && break; sleep 1; done
    fi
    docker info >/dev/null 2>&1 || { echo "dev.sh: the Docker daemon is not running. Start Docker and retry." >&2; exit 1; }
  fi
  echo "dev.sh: starting MariaDB (docker-compose.dev.yml)"
  "${COMPOSE[@]}" up -d --wait db
fi

# The pages are the React app in web/, which the Quart app serves from web/dist.
# Build it when it's missing or older than its sources. For live reload while
# working on it, also run `npm run dev` in web/ and open http://localhost:5173.
if [[ -n "$(find web/src web/index.html web/package.json -newer web/dist/index.html 2>/dev/null | head -1)" || ! -f web/dist/index.html ]]; then
  if command -v npm >/dev/null 2>&1; then
    echo "dev.sh: building the web app (web/)"
    (cd web && { [[ -d node_modules ]] || npm ci --ignore-scripts --no-audit --no-fund; } && npm run gen:api && npm run build)
  else
    echo "dev.sh: Node.js isn't installed, so the web app (web/) can't be built; pages will say so." >&2
  fi
fi

exec poetry run python -m devserver "$@"

#!/usr/bin/env bash
# Build the website (web/) into web/dist, which the Quart app serves.
#
# Production deploys with `git pull`; run this after each pull, then restart
# SahasrahBot. It needs Node.js 22 and nothing from Python: the API types that
# `npm run gen:api` generates are only for type checking, which CI already does.
set -euo pipefail
cd "$(dirname "$0")/../web"

if ! command -v npm >/dev/null 2>&1; then
  echo "build_web.sh: Node.js 22 (npm) isn't installed" >&2
  exit 1
fi
major="$(node -p 'process.versions.node.split(".")[0]')"
if (( major < 22 )); then
  echo "build_web.sh: Node.js 22 or later is needed (this is $(node -v))" >&2
  exit 1
fi

npm ci --ignore-scripts --no-audit --no-fund
npm run build:site
echo "build_web.sh: built web/dist"

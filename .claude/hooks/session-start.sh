#!/usr/bin/env bash
# SessionStart hook: layering reminder + export-gap / model-import burn-down audit.
REPO="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0

cat <<'EOF'
ARCHITECTURE: SahasrahBot is a strict three-tier app inside a single alttprbot/ package.
  alttprbot/presentation/{discord,audit,racetime,api,web}  ->  alttprbot/services/  ->  alttprbot/repositories/  ->  alttprbot/models/
  - Presentation: thin; calls services, renders results, catches errors. No business logic; no ORM access.
  - Service: business rules/validation/authz/audit/notify. Raises ValueError/PermissionError. No discord/racetime_bot/quart/presentation imports.
  - Repository: pure Tortoise CRUD; returns models. No business logic/notify.
  Full rules: docs/architecture-layers.md
EOF

for tier_dir in "$REPO/alttprbot/services" "$REPO/alttprbot/repositories"; do
  [[ -d "$tier_dir" ]] || continue
  while IFS= read -r src; do
    init_file="$(dirname "$src")/__init__.py"
    stem="$(basename "$src" .py)"
    if [[ -f "$init_file" ]] && ! grep -q "$stem" "$init_file" 2>/dev/null; then
      echo "EXPORT GAP: $src — not exported from $(dirname "$src")/__init__.py"
    fi
  done < <(find "$tier_dir" -type f \( -name '*_service.py' -o -name '*_repository.py' \) 2>/dev/null)
done

PRES="$REPO/alttprbot/presentation"
if [[ -d "$PRES" ]]; then
  COUNT=$(grep -rEl '^[[:space:]]*(from[[:space:]]+alttprbot[[:space:]]+import[[:space:]]+.*\bmodels\b|from[[:space:]]+alttprbot\.models|import[[:space:]]+alttprbot\.models)' "$PRES" 2>/dev/null | wc -l | tr -d ' ')
  echo "BURN-DOWN: $COUNT presentation file(s) still import alttprbot.models directly (target: 0)."
fi

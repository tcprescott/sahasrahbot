#!/usr/bin/env bash
# _repo.sh — repo-root resolution for the shell hooks. Source it, then use $REPO.
#
# Hooks inherit the session's shell cwd, which moves whenever a Bash tool call
# cd's elsewhere. `git rev-parse --show-toplevel` therefore resolves against the
# wrong tree (or fails outright, so the hook exits 0 and silently stops
# checking). Anchor to the project dir Claude Code hands us, falling back to this
# file's own location — both are independent of cwd.

resolve_repo() {
  local candidate

  if [[ -n "${CLAUDE_PROJECT_DIR:-}" && -d "$CLAUDE_PROJECT_DIR/.claude/scripts" ]]; then
    ( cd "$CLAUDE_PROJECT_DIR" && pwd )
    return 0
  fi

  # <root>/.claude/hooks/_repo.sh → <root>
  candidate="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." 2>/dev/null && pwd )"
  if [[ -n "$candidate" && -d "$candidate/.claude/scripts" ]]; then
    echo "$candidate"
    return 0
  fi

  git rev-parse --show-toplevel 2>/dev/null
}

REPO="$(resolve_repo)"
[[ -n "$REPO" ]] || exit 0
cd "$REPO" || exit 0

#!/usr/bin/env python3
"""
PostToolUse hook: reject code that asks Discord for privileged intents, or that
depends on the member cache only those intents fill.

SahasrahBot's Discord applications are not approved for the privileged gateway
intents (members, presences, message_content). A client that requests one is
disconnected at login (close code 4014) and never comes online, so this is a
whole-bot outage, not a degraded feature. See docs/privileged_intents.md.

Flags, in any .py file outside the vendored utils/ tree:
  discord.Intents.all() / Intents.privileged()
  intents.members|presences|message_content = True
  Intents(members=True, …) and friends
  chunk_guilds_at_startup=True
  guild.chunk(…)                       → needs the members intent

Use alttprbot/util/discord_members.py (get_member / get_member_named) for member
lookups instead of the cache.

A line can opt out with a trailing ``# intents: ok`` comment when it only
*reads* an intent flag or the code is guarded for a bot that has the intent.

Exit 0 = clean / not applicable; exit 2 = violation (details on stderr).
"""

import json
import re
import sys
from pathlib import Path

from _hook_paths import anchor

ROOT = anchor()

PATTERNS = [
    (re.compile(r"\bIntents\.(?:all|privileged)\s*\("), "Intents.all()/privileged() requests privileged intents"),
    (
        re.compile(r"\.(?:members|presences|message_content)\s*=\s*True\b"),
        "turning on a privileged intent flag",
    ),
    (
        re.compile(r"\bIntents\s*\([^)]*\b(?:members|presences|message_content)\s*=\s*True"),
        "Intents(...) with a privileged flag",
    ),
    (re.compile(r"\bchunk_guilds_at_startup\s*=\s*True\b"), "chunk_guilds_at_startup=True needs the members intent"),
    (re.compile(r"\bguild\w*\.chunk\s*\("), "guild.chunk() needs the members intent"),
]

OPT_OUT = re.compile(r"#\s*intents:\s*ok\b")


def scan(text: str) -> list[tuple[int, str, str]]:
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        code = line.split("#", 1)[0] if not OPT_OUT.search(line) else ""
        if not code.strip():
            continue
        for pattern, why in PATTERNS:
            if pattern.search(code):
                hits.append((lineno, why, line.strip()))
    return hits


def applies(path: str) -> bool:
    if not path.endswith(".py"):
        return False
    try:
        rel = Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        rel = path
    # Vendored code, and the guardrail's own files, which have to name the hazard.
    return not (
        rel.startswith("utils/")
        or rel.startswith(".claude/")
        or rel.startswith("tests/test_guardrails")
    )


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path or not applies(file_path):
        sys.exit(0)
    try:
        text = Path(file_path).read_text(encoding="utf-8")
    except OSError:
        sys.exit(0)

    hits = scan(text)
    if not hits:
        sys.exit(0)

    print(f"PRIVILEGED INTENTS in '{file_path}':", file=sys.stderr)
    for lineno, why, line in hits:
        print(f"  line {lineno}: {why}\n    {line}", file=sys.stderr)
    print(
        "  SahasrahBot is not approved for privileged intents; requesting one stops the bot\n"
        "  from logging in at all (close 4014). Use alttprbot/util/discord_members.py for\n"
        "  member lookups. See docs/privileged_intents.md. If this line only reads a flag,\n"
        "  append `# intents: ok`.",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()

"""Shared helpers for the architecture-enforcement hooks.

Mode is controlled by the ``SAHASRAHBOT_HOOKS_ENFORCE`` environment variable:

- unset / "0" / "false"  → **notification-only**: print violations, exit 0 (non-blocking).
- "1" / "true" / "yes"   → **blocking**: print violations, exit 2 (blocks the Write/Edit).

The migration starts in notification-only mode so the agent is made aware of the
layering rules without being blocked while the codebase still contains the
pre-migration violations. It flips to blocking in the final phase.
"""

import os
import sys


def enforcing() -> bool:
    return os.environ.get("SAHASRAHBOT_HOOKS_ENFORCE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def finish(violations) -> None:
    """Emit any violations and exit. Blocks (exit 2) only when enforcement is on."""
    if not violations:
        sys.exit(0)
    prefix = "" if enforcing() else "[architecture notice — not blocking] "
    for v in violations:
        print(prefix + v, file=sys.stderr)
    sys.exit(2 if enforcing() else 0)

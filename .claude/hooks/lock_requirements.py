#!/usr/bin/env python3
"""Print poetry.lock as a pip requirements list (name==version ; markers).

Used by install-deps.sh when `poetry install` can't finish in a cloud session:
the egress proxy refuses racetime-bot's GitHub archive URL, and Poetry then
aborts the whole install, leaving other packages missing or stale. Packages
with a url/git source are skipped here; the hook installs racetime-bot from git
separately. Stdlib only.
"""

import sys
import tomllib
from pathlib import Path

lock = tomllib.loads((Path(__file__).resolve().parents[2] / "poetry.lock").read_text())
for pkg in lock["package"]:
    if pkg.get("source"):
        continue
    markers = pkg.get("markers")
    if isinstance(markers, dict):
        # Per-group markers. A group with no entry installs the package
        # unconditionally; otherwise it's needed if any group's marker holds.
        if any(group not in markers for group in pkg.get("groups", [])):
            markers = None
        else:
            markers = " or ".join(f"({m})" for m in markers.values())
    line = f"{pkg['name']}=={pkg['version']}"
    print(f"{line} ; {markers}" if markers else line)
sys.exit(0)

"""Regenerate the static config-constant usage table for
docs/guides/config_constants_inventory.md.

Scans application code (sahasrahbot.py, alttprbot/, helpers/, migrations/) for
`config.<CONSTANT>` attribute reads in modules that import the root `config`
module, and prints the inventory as a Markdown table.

Usage: poetry run python helpers/scan_config_constants.py
"""

import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_TARGETS = ['sahasrahbot.py', 'alttprbot', 'helpers', 'migrations']
IMPORT_RE = re.compile(r'^\s*import config\b', re.MULTILINE)
READ_RE = re.compile(r'(?<![\w.])config\.([A-Z][A-Z0-9_]+)\b')
SELF_NAME = Path(__file__).name


def iter_files():
    for target in SCAN_TARGETS:
        path = ROOT / target
        if path.is_file():
            yield path
        else:
            yield from sorted(p for p in path.rglob('*.py')
                              if '__pycache__' not in p.parts and p.name != SELF_NAME)


def main():
    usage = defaultdict(set)
    files_with_reads = set()
    for path in iter_files():
        text = path.read_text(encoding='utf-8')
        if not IMPORT_RE.search(text):
            continue
        rel = path.relative_to(ROOT).as_posix()
        for match in READ_RE.finditer(text):
            usage[match.group(1)].add(rel)
            files_with_reads.add(rel)

    print(f'<!-- {len(files_with_reads)} files with config constant reads, '
          f'{len(usage)} unique constants -->')
    print('| Constant | References | Consuming files |')
    print('|---|---:|---|')
    for constant in sorted(usage):
        files = sorted(usage[constant])
        joined = ', '.join(f'`{f}`' for f in files)
        print(f'| `{constant}` | {len(files)} | {joined} |')


if __name__ == '__main__':
    main()

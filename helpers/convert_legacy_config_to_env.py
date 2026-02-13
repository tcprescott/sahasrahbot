#!/usr/bin/env python3
"""Convert legacy Python config assignments into a dotenv file for pydantic-settings."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any


class ConfigConversionError(RuntimeError):
    """Raised when a legacy config file cannot be converted safely."""


def parse_legacy_config(path: Path) -> list[tuple[str, Any]]:
    source = path.read_text(encoding='utf-8')
    tree = ast.parse(source, filename=str(path))

    assignments: list[tuple[str, Any]] = []
    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        if len(statement.targets) != 1:
            continue

        target = statement.targets[0]
        if not isinstance(target, ast.Name):
            continue

        key = target.id
        if not key.isupper():
            continue

        try:
            value = ast.literal_eval(statement.value)
        except Exception as error:  # noqa: BLE001
            raise ConfigConversionError(
                f'Unable to parse value for {key!r} in {path}. '
                'Only literal assignments are supported.'
            ) from error

        assignments.append((key, value))

    if not assignments:
        raise ConfigConversionError(
            f'No uppercase literal assignments found in {path}.'
        )

    return assignments


def encode_string_for_env(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def value_to_env(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return encode_string_for_env(value)
    if isinstance(value, (dict, list, tuple)):
        return encode_string_for_env(json.dumps(value, ensure_ascii=False))

    return encode_string_for_env(str(value))


def convert_file(input_path: Path, output_path: Path, force: bool) -> int:
    if not input_path.exists():
        raise ConfigConversionError(f'Input file not found: {input_path}')

    if output_path.exists() and not force:
        raise ConfigConversionError(
            f'Output file already exists: {output_path}. Use --force to overwrite.'
        )

    assignments = parse_legacy_config(input_path)

    lines = [
        '# Generated from legacy config file',
        f'# Source: {input_path}',
        '',
    ]

    for key, value in assignments:
        lines.append(f'{key}={value_to_env(value)}')

    output_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return len(assignments)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Convert a legacy Python config.py file to dotenv format.'
    )
    parser.add_argument(
        'input',
        type=Path,
        help='Path to legacy Python config file (e.g. config.backup.py)',
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('.env.converted'),
        help='Output dotenv file path (default: .env.converted)',
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite output file if it already exists.',
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        count = convert_file(args.input, args.output, args.force)
    except ConfigConversionError as error:
        print(f'Conversion failed: {error}')
        return 1

    print(f'Wrote {count} keys to {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

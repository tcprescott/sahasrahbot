#!/usr/bin/env python3
import sys
from pathlib import Path

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from alttprbot.util.config_contract import ConfigValidationError, validate_config_contract


def main() -> int:
    try:
        validate_config_contract()
    except ConfigValidationError as error:
        print(f'Configuration validation failed: {error}')
        return 1

    print('Configuration validation passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

import config


class ConfigValidationError(RuntimeError):
    pass


def _is_blank(value):
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ''
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


def expected_racetime_category_slugs(debug: bool) -> list[str]:
    if debug:
        return ['test']

    return [
        'alttpr',
        'contra',
        'ct-jets',
        'ff1r',
        'sgl',
        'smb3r',
        'smr',
        'smw-hacks',
        'smz3',
        'twwr',
        'z1r',
        'z2r',
    ]


def required_keys(debug: bool) -> list[str]:
    keys = [
        'DB_HOST',
        'DB_PORT',
        'DB_USER',
        'DB_PASS',
        'DB_NAME',
        'DISCORD_TOKEN',
        'AUDIT_DISCORD_TOKEN',
        'RACETIME_HOST',
        'RACETIME_PORT',
        'RACETIME_URL',
        'RACETIME_COMMAND_PREFIX',
    ]
    if not debug:
        keys.append('APP_SECRET_KEY')
    return keys


def validate_config_contract() -> None:
    debug = bool(getattr(config, 'DEBUG', False))
    missing = []

    for key in required_keys(debug):
        if not hasattr(config, key):
            missing.append(key)
            continue

        value = getattr(config, key)
        if _is_blank(value):
            missing.append(key)

    for slug in expected_racetime_category_slugs(debug):
        category_key = slug.upper().replace('-', '')
        client_id_key = f'RACETIME_CLIENT_ID_{category_key}'
        client_secret_key = f'RACETIME_CLIENT_SECRET_{category_key}'

        for dynamic_key in (client_id_key, client_secret_key):
            if not hasattr(config, dynamic_key):
                missing.append(dynamic_key)
                continue

            value = getattr(config, dynamic_key)
            if _is_blank(value):
                missing.append(dynamic_key)

    if missing:
        missing_sorted = sorted(set(missing))
        raise ConfigValidationError(
            'missing required configuration keys: ' + ', '.join(missing_sorted)
        )

"""Application runtime configuration loaded via pydantic-settings."""

from __future__ import annotations

from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='allow',
    )

    DEBUG: bool = False

    APP_URL: str = 'http://localhost:5001'
    APP_SECRET_KEY: str = ''

    DB_HOST: str = 'localhost'
    DB_PORT: int = 3306
    DB_NAME: str = 'sahasrahbot'
    DB_USER: str = 'sahasrahbot'
    DB_PASS: str = ''

    DISCORD_TOKEN: str = ''
    AUDIT_DISCORD_TOKEN: str = ''
    DISCORD_CLIENT_ID: str = ''
    DISCORD_CLIENT_SECRET: str = ''

    ALTTPR_BASEURL: str = 'https://alttpr.com'
    ALTTPR_SEED_BASEURL: str = 'https://s3.us-east-2.amazonaws.com/alttpr-patches'
    ALTTPR_USERNAME: str = ''
    ALTTPR_PASSWORD: str = ''

    SPOILERLOGURLBASE: str = ''
    AWS_SPOILER_BUCKET_NAME: str = ''
    SAHASRAHBOT_BUCKET: str = ''

    SG_API_ENDPOINT: str = 'https://speedgaming.org/api'
    SG_DISCORD_WEBHOOK: str = ''
    BINGO_COLLAB_DISCORD_WEBHOOK: str = ''

    MULTIWORLDROMBASE: str = 'http://localhost'
    MULTIWORLDHOSTBASE: str = 'localhost'

    RACETIME_GAMES: str = ''
    RACETIME_HOST: str = 'localhost'
    RACETIME_PORT: int = 8000
    RACETIME_SECURE: bool = False
    RACETIME_URL: str = 'http://localhost:8000'
    RACETIME_COMMAND_PREFIX: str = '!'

    RACETIME_CLIENT_ID_OAUTH: str = ''
    RACETIME_CLIENT_SECRET_OAUTH: str = ''
    RACETIME_CLIENT_ID_TEST: str = ''
    RACETIME_CLIENT_SECRET_TEST: str = ''
    RACETIME_CLIENT_ID_ALTTPR: str = ''
    RACETIME_CLIENT_SECRET_ALTTPR: str = ''
    RACETIME_CLIENT_ID_CONTRA: str = ''
    RACETIME_CLIENT_SECRET_CONTRA: str = ''
    RACETIME_CLIENT_ID_CTJETS: str = ''
    RACETIME_CLIENT_SECRET_CTJETS: str = ''
    RACETIME_CLIENT_ID_FF1R: str = ''
    RACETIME_CLIENT_SECRET_FF1R: str = ''
    RACETIME_CLIENT_ID_SGL: str = ''
    RACETIME_CLIENT_SECRET_SGL: str = ''
    RACETIME_CLIENT_ID_SMB3R: str = ''
    RACETIME_CLIENT_SECRET_SMB3R: str = ''
    RACETIME_CLIENT_ID_SMR: str = ''
    RACETIME_CLIENT_SECRET_SMR: str = ''
    RACETIME_CLIENT_ID_SMWHACKS: str = ''
    RACETIME_CLIENT_SECRET_SMWHACKS: str = ''
    RACETIME_CLIENT_ID_SMZ3: str = ''
    RACETIME_CLIENT_SECRET_SMZ3: str = ''
    RACETIME_CLIENT_ID_TWWR: str = ''
    RACETIME_CLIENT_SECRET_TWWR: str = ''
    RACETIME_CLIENT_ID_Z1R: str = ''
    RACETIME_CLIENT_SECRET_Z1R: str = ''
    RACETIME_CLIENT_ID_Z2R: str = ''
    RACETIME_CLIENT_SECRET_Z2R: str = ''

    OOTR_API_KEY: str = ''

    ALTTP_ROM: str = '/opt/data/alttp_jp10.sfc'
    SM_ROM: str = '/opt/data/super_metroid.sfc'
    ENEMIZER_HOME: str = '/opt/enemizer'
    DOOR_RANDO_HOME: str = '/opt/ALttPDoorRandomizer'

    ALTTP_RANDOMIZER_SERVERS: str = ''
    MAIN_TOURNAMENT_SERVERS: str = ''
    CC_TOURNAMENT_SERVERS: str = ''
    CC_TOURNAMENT_AUDIT_CHANNELS: str = ''

    SENTRY_URL: str = ''

    DISCORD_ROLE_ASSIGNMENT_ENABLED: bool = True
    TOURNAMENT_CONFIG_ENABLED: bool = False

    TELEMETRY_ENABLED: bool = False
    TELEMETRY_SAMPLE_RATE: float = 1.0
    TELEMETRY_RETENTION_DAYS: int = 30
    TELEMETRY_HASH_SALT: str = ''
    TELEMETRY_QUEUE_SIZE: int = 1000


settings = Settings()

for key in Settings.model_fields:
    globals()[key] = getattr(settings, key)

for key, extra_value in (settings.model_extra or {}).items():
    if key.isupper() and key not in globals():
        globals()[key] = extra_value


def __getattr__(name: str) -> Any:
    if name in globals():
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

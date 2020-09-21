# coding: utf-8
from sqlalchemy import Column, DateTime, Index, JSON, MetaData, String, TIMESTAMP, Table, text
from sqlalchemy.dialects.mysql import BIGINT, BIT, INTEGER, TINYINT, VARCHAR

metadata = MetaData()


t_audit_generated_games = Table(
    'audit_generated_games', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('randomizer', String(45)),
    Column('hash_id', String(50), index=True),
    Column('permalink', String(2000)),
    Column('settings', JSON),
    Column('gentype', String(45)),
    Column('genoption', String(45)),
    Column('timestamp', DateTime, server_default=text(
        "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")),
    Column('customizer', INTEGER(11))
)


t_audit_messages = Table(
    'audit_messages', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('guild_id', BIGINT(20)),
    Column('message_id', BIGINT(20), index=True),
    Column('user_id', BIGINT(20)),
    Column('channel_id', BIGINT(20)),
    Column('message_date', DateTime),
    Column('content', String(4000, 'utf8mb4_bin')),
    Column('attachment', String(2000, 'utf8mb4_bin')),
    Column('deleted', INTEGER(11), server_default=text("'0'"))
)


t_config = Table(
    'config', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('guild_id', BIGINT(20), nullable=False),
    Column('parameter', String(45, 'utf8mb4_unicode_ci'), nullable=False),
    Column('value', String(45, 'utf8mb4_unicode_ci'))
)


t_daily = Table(
    'daily', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('hash', String(45, 'utf8_bin'), nullable=False)
)

t_discord_server_list = Table(
    'discord_server_lists', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('server_description', String(200), nullable=False),
    Column('invite_id', String(45), nullable=False),
    Column('category_id', INTEGER(11))
)

t_discord_server_categories = Table(
    'discord_server_categories', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('order', INTEGER(11), nullable=False, server_default=text("'0'")),
    Column('guild_id', BIGINT(20), nullable=False),
    Column('channel_id', BIGINT(20), nullable=False),
    Column('category_title', String(200), nullable=False),
    Column('category_description', String(200)),
)

t_gtbk_games = Table(
    'gtbk_games', metadata,
    Column('game_id', INTEGER(11), primary_key=True),
    Column('channel', String(200)),
    Column('status', String(45)),
    Column('timestamp', DateTime, server_default=text(
        "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
)


t_gtbk_guesses = Table(
    'gtbk_guesses', metadata,
    Column('guess_id', INTEGER(11), primary_key=True),
    Column('game_id', INTEGER(11)),
    Column('twitch_user', String(200)),
    Column('guess', INTEGER(11)),
    Column('score', INTEGER(11), server_default=text("'0'")),
    Column('timestamp', TIMESTAMP, nullable=False,
           server_default=text("CURRENT_TIMESTAMP")),
    Index('guess_UNIQUE', 'game_id', 'twitch_user', unique=True)
)


t_gtbk_whitelist = Table(
    'gtbk_whitelist', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('channel', String(200, 'utf8_bin')),
    Column('twitch_user', String(200, 'utf8_bin'))
)


t_mention_counters = Table(
    'mention_counters', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('guild_id', BIGINT(20), nullable=False),
    Column('role_id', BIGINT(20), nullable=False, unique=True),
    Column('counter', INTEGER(11), nullable=False, server_default=text("'1'")),
    Column('last_used', DateTime, nullable=False, server_default=text(
        "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
)


t_permissions = Table(
    'permissions', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('guild_id', BIGINT(20), nullable=False),
    Column('role_id', BIGINT(20), nullable=False),
    Column('permission', String(45, 'utf8mb4_unicode_ci'))
)


t_reaction_group = Table(
    'reaction_group', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('guild_id', BIGINT(20), nullable=False),
    Column('channel_id', BIGINT(20), nullable=False),
    Column('message_id', BIGINT(20), nullable=False, unique=True),
    Column('name', String(400, 'utf8mb4_unicode_ci')),
    Column('description', VARCHAR(1000)),
    Column('bot_managed', INTEGER(11))
)


t_reaction_role = Table(
    'reaction_role', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('guild_id', BIGINT(20), nullable=False),
    Column('reaction_group_id', BIGINT(20)),
    Column('role_id', BIGINT(20)),
    Column('name', String(45, 'utf8mb4_unicode_ci'), nullable=False),
    Column('emoji', VARCHAR(200), nullable=False),
    Column('description', String(400, 'utf8mb4_unicode_ci')),
    Column('protect_mentions', TINYINT(1))
)


t_seed_presets = Table(
    'seed_presets', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('name', VARCHAR(45), nullable=False, unique=True),
    Column('randomizer', VARCHAR(45)),
    Column('customizer', TINYINT(4)),
    Column('settings', JSON, nullable=False)
)


t_smz3_multiworld = Table(
    'smz3_multiworld', metadata,
    Column('message_id', BIGINT(20), primary_key=True),
    Column('owner_id', BIGINT(20), nullable=False),
    Column('randomizer', VARCHAR(45), nullable=False),
    Column('preset', VARCHAR(45), nullable=False),
    Column('status', VARCHAR(20), nullable=False)
)


t_spoiler_races = Table(
    'spoiler_races', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('srl_id', String(45, 'utf8_bin'), nullable=False, unique=True),
    Column('spoiler_url', String(255, 'utf8_bin'), nullable=False),
    Column('studytime', INTEGER(11)),
    Column('date', DateTime, server_default=text("CURRENT_TIMESTAMP"))
)


t_srl_nick_verification = Table(
    'srl_nick_verification', metadata,
    Column('srl_nick', String(45, 'utf8_bin'), primary_key=True, unique=True),
    Column('key', BIGINT(20), unique=True),
    Column('discord_user_id', BIGINT(20)),
    Column('timestamp', DateTime, server_default=text(
        "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
)


t_srl_races = Table(
    'srl_races', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('srl_id', String(45), nullable=False, unique=True),
    Column('goal', String(200), nullable=False),
    Column('timestamp', DateTime, server_default=text(
        "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")),
    Column('message', String(200))
)


t_srlnick = Table(
    'srlnick', metadata,
    Column('discord_user_id', BIGINT(20), primary_key=True),
    Column('srl_nick', String(200), index=True),
    Column('twitch_name', String(200), index=True),
    Column('srl_verified', BIT(1))
)


t_tournament_results = Table(
    'tournament_results', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('srl_id', String(45, 'utf8_bin')),
    Column('episode_id', String(45, 'utf8_bin')),
    Column('permalink', String(200, 'utf8_bin')),
    Column('spoiler', String(200, 'utf8_bin')),
    Column('event', String(45, 'utf8_bin')),
    Column('status', String(45, 'utf8_bin')),
    Column('results_json', JSON),
    Column('week', String(45, 'utf8_bin')),
    Column('written_to_gsheet', TINYINT(4))
)


t_twitch_channels = Table(
    'twitch_channels', metadata,
    Column('channel', String(200), primary_key=True),
    Column('group', String(45), nullable=False)
)


t_twitch_command_text = Table(
    'twitch_command_text', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('channel', String(200, 'utf8_bin')),
    Column('command', String(45, 'utf8_bin')),
    Column('content', String(200, 'utf8_bin')),
    Index('idx_twitch_command_text_channel_command',
          'channel', 'command', unique=True)
)


t_voice_role = Table(
    'voice_role', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('guild_id', BIGINT(20), nullable=False),
    Column('voice_channel_id', BIGINT(20), nullable=False),
    Column('role_id', BIGINT(20), nullable=False)
)

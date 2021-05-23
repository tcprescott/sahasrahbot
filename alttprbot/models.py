import datetime

from tortoise.models import Model
from tortoise import fields

class AuditGeneratedGames(Model):
    class Meta:
        table="audit_generated_games"

    id = fields.IntField(pk=True)
    randomizer = fields.CharField(45)
    hash_id = fields.CharField(50, index=True)
    permalink = fields.CharField(2000, index=True)
    settings = fields.JSONField()
    gentype = fields.CharField(45, index=True)
    genoption = fields.CharField(45, index=True)
    timestamp = fields.DateField(auto_now=True)
    id = fields.IntField()

class AuditMessages(Model):
    class Meta:
        table="audit_messages"

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField()
    message_id = fields.BigIntField()
    user_id = fields.BigIntField()
    message_date = fields.DateField(auto_now_add=True)
    content = fields.CharField(4000)
    attachment = fields.CharField(2000)
    deleted = fields.IntField(default=0)

class Config(Model):
    class Meta:
        table="config"

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField(null=False)
    parameter = fields.CharField(45, null=False)
    value = fields.CharField(45)

class Daily(Model):
    class Meta:
        table="daily"

    id = fields.IntField(pk=True)
    hash = fields.CharField(45)

class DiscordServerLists(Model):
    class Meta:
        table='discord_server_list'

    id = fields.IntField(pk=True)
    server_description = fields.CharField(200, null=False)
    invite_id = fields.CharField(45, null=False)
    category_id = fields.IntField()

class DiscordServerCategories(Model):
    class Meta:
        table='discord_server_categories'

    id = fields.IntField(pk=True)
    order = fields.IntField(null=False, default=0)
    guild_id = fields.BigIntField(null=False)
    channel_id = fields.BigIntField(null=False)
    category_title = fields.CharField(200, null=False)
    category_description = fields.CharField(200)

class LeaguePlayoffs(Model):
    class Meta:
        table='league_playoffs'

    episode_id = fields.IntField(pk=True, generated=False)
    playoff_round = fields.CharField(45)
    game_number = fields.IntField()
    type = fields.CharField(45)
    preset = fields.CharField(45)
    settings = fields.JSONField()
    submitted = fields.BooleanField()
    created = fields.DateField(auto_now_add=True)
    modified = fields.DateField(auto_now=True)

class MentionCounters(Model):
    class Meta:
        table='mention_counters'

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField(null=False)
    role_id = fields.BigIntField(null=False, unique=True)
    counter = fields.IntField(null=False, default=1)
    last_used = fields.DateField(auto_now=True)

class PatchDistribution(Model):
    class Meta:
        table='patch_distribution'

    id = fields.IntField(pk=True)
    patch_id = fields.CharField(45)
    game = fields.CharField(45)
    used = fields.BooleanField()

class ReactionGroup(Model):
    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField(null=False)
    channel_id = fields.BigIntField(null=False)
    message_id = fields.BigIntField(null=False)
    name = fields.CharField(400)
    description = fields.CharField(1000)
    bot_managed = fields.IntField()

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
    Column('date', DateTime, server_default=text("CURRENT_TIMESTAMP")),
    Column('started', DateTime)
)


t_nick_verification = Table(
    'nick_verification', metadata,
    Column('key', BIGINT(20), primary_key=True, unique=True, autoincrement=False),
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
    Column('rtgg_id', String(200), index=True),
    Column('srl_verified', BIT(1))
)

t_tournament_games = Table(
    'tournament_games', metadata,
    Column('episode_id', INTEGER(11), primary_key=True, autoincrement=False),
    Column('event', String(45, 'utf8_bin')),
    Column('game_number', INTEGER(11)),
    Column('settings', JSON),
    Column('submitted', TINYINT(1)),
    Column('created', DateTime, server_default=text(
        "CURRENT_TIMESTAMP")),
    Column('updated', DateTime, server_default=text(
        "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")),
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

t_tournaments = Table(
    'tournaments', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('schedule_type', String(45)),
    Column('slug', String(45)),
    Column('guild_id', BIGINT(20), nullable=False),
    Column('helper_roles', String(4000)),
    Column('audit_channel_id', BIGINT(20)),
    Column('commentary_channel_id', BIGINT(20)),
    Column('scheduling_needs_channel_id', BIGINT(20)),
    Column('scheduling_needs_tracker', TINYINT(1)),
    Column('mod_channel_id', BIGINT(20)),
    Column('tracker_roles', String(4000)),
    Column('commentator_roles', String(4000)),
    Column('mod_roles', String(4000)),
    Column('admin_roles', String(4000)),
    Column('category', String(200)),
    Column('goal', String(200)),
    Column('active', TINYINT(1)),
    Column('lang', String(20)),
    Index('idx_tournaments_type_slug', 'schedule_type', 'slug', unique=True)
)

t_sgdailies = Table(
    'sgdailies', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('slug', String(45)),
    Column('guild_id', BIGINT(20), nullable=False),
    Column('announce_channel', BIGINT(20), nullable=False),
    Column('announce_message', VARCHAR(2000), nullable=False),
    Column('racetime_category', String(45)),
    Column('racetime_goal', String(45)),
    Column('race_info', VARCHAR(2000), nullable=False),
    Column('active', TINYINT(1))
)

t_sgl2020_tournament = Table(
    'sgl2020_tournament', metadata,
    Column('episode_id', INTEGER(11), primary_key=True, autoincrement=False),
    Column('room_name', String(100, 'utf8_bin'), unique=True),
    Column('event', String(45, 'utf8_bin')),
    Column('platform', String(45, 'utf8_bin')),
    Column('permalink', String(200, 'utf8_bin')),
    Column('seed', String(200, 'utf8_bin')),
    Column('password', String(200, 'utf8_bin')),
    Column('status', String(45, 'utf8_bin')),
    Column('created', DateTime, server_default=text(
        "CURRENT_TIMESTAMP")),
    Column('updated', DateTime, server_default=text(
        "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")),
)

t_sgl2020_tournament_bo3 = Table(
    'sgl2020_tournament_bo3', metadata,
    Column('id', INTEGER(11), primary_key=True),
    Column('episode_id', INTEGER(11)),
    Column('room_name', String(100, 'utf8_bin'), unique=True),
    Column('event', String(45, 'utf8_bin')),
    Column('platform', String(45, 'utf8_bin')),
    Column('permalink', String(200, 'utf8_bin')),
    Column('seed', String(200, 'utf8_bin')),
    Column('password', String(200, 'utf8_bin')),
    Column('status', String(45, 'utf8_bin')),
    Column('created', DateTime, server_default=text(
        "CURRENT_TIMESTAMP")),
    Column('updated', DateTime, server_default=text(
        "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
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
    Column('content', String(4000, 'utf8_bin')),
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

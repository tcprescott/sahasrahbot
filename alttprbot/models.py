from tortoise.models import Model
from tortoise import fields


class AuditGeneratedGames(Model):
    class Meta:
        table = "audit_generated_games"

    id = fields.IntField(pk=True)
    randomizer = fields.CharField(45, null=True)
    hash_id = fields.CharField(50, index=True, null=True)
    permalink = fields.CharField(2000, null=True)
    settings = fields.JSONField(null=True)
    gentype = fields.CharField(45, index=True, null=True)
    genoption = fields.CharField(45, index=True, null=True)
    timestamp = fields.DatetimeField(auto_now=True, null=True)
    customizer = fields.IntField(null=True)


class AuditMessages(Model):
    class Meta:
        table = "audit_messages"

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField(null=True)
    message_id = fields.BigIntField(null=True)
    user_id = fields.BigIntField(null=True)
    channel_id = fields.BigIntField(null=True)
    message_date = fields.DatetimeField(null=True)
    content = fields.CharField(4000, null=True)
    attachment = fields.CharField(1000, null=True)
    deleted = fields.IntField(default=0)


class Config(Model):
    class Meta:
        table = "config"

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField(null=False)
    parameter = fields.CharField(45, null=False)
    value = fields.CharField(45, null=True)


class Daily(Model):
    class Meta:
        table = "daily"

    id = fields.IntField(pk=True)
    hash = fields.CharField(45, index=True)


class DiscordServerLists(Model):
    class Meta:
        table = 'discord_server_lists'

    id = fields.IntField(pk=True)
    server_description = fields.CharField(200, null=False)
    invite_id = fields.CharField(45, null=False)
    category = fields.ForeignKeyField('models.DiscordServerCategories', related_name='discord_server_lists')


class DiscordServerCategories(Model):
    class Meta:
        table = 'discord_server_categories'

    id = fields.IntField(pk=True)
    order = fields.IntField(null=False, default=0)
    guild_id = fields.BigIntField(null=False)
    channel_id = fields.BigIntField(null=False)
    category_title = fields.CharField(200, null=False)
    category_description = fields.CharField(200, null=True)


class LeaguePlayoffs(Model):
    class Meta:
        table = 'league_playoffs'

    episode_id = fields.IntField(pk=True, generated=False)
    playoff_round = fields.CharField(45, null=True)
    game_number = fields.IntField(null=True)
    type = fields.CharField(45, null=True)
    preset = fields.CharField(45, null=True)
    settings = fields.JSONField(null=True)
    submitted = fields.SmallIntField(null=True)
    created = fields.DatetimeField(auto_now_add=True)
    modified = fields.DatetimeField(auto_now=True)


class PatchDistribution(Model):
    class Meta:
        table = 'patch_distribution'

    id = fields.IntField(pk=True)
    patch_id = fields.CharField(45, null=True)
    game = fields.CharField(45, null=True)
    used = fields.SmallIntField(index=True)


class RacetimeKONOTGame(Model):
    id = fields.IntField(pk=True)
    category_slug = fields.CharField(50, null=False)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)


class RaceTimeKONOTSegment(Model):
    id = fields.IntField(pk=True)
    racetime_room = fields.CharField(200, null=False)
    game_id = fields.IntField(null=False)
    segment_number = fields.IntField(null=False)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)


class ReactionGroup(Model):
    class Meta:
        table = 'reaction_group'

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField(null=False)
    channel_id = fields.BigIntField(null=False)
    message_id = fields.BigIntField(null=False)
    name = fields.CharField(400, null=True)
    description = fields.CharField(1000, null=True)
    bot_managed = fields.IntField(null=True)


class ReactionRole(Model):
    class Meta:
        table = 'reaction_role'

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField(null=False)
    reaction_group = fields.ForeignKeyField('models.ReactionGroup', related_name='reaction_roles')
    role_id = fields.BigIntField(null=True)
    name = fields.CharField(45, null=True)
    emoji = fields.CharField(200, null=True)
    protect_mentions = fields.SmallIntField(null=True)


class SMZ3Multiworld(Model):
    class Meta:
        table = 'smz3_multiworld'

    message_id = fields.BigIntField(pk=True, generated=False)
    owner_id = fields.BigIntField(null=True)
    randomizer = fields.CharField(45, null=True)
    preset = fields.CharField(45, null=True)
    status = fields.CharField(20, null=True)


class Multiworld(Model):
    message_id = fields.BigIntField(pk=True, generated=False)
    owner_id = fields.BigIntField(null=True)
    randomizer = fields.CharField(45, null=True)
    preset = fields.CharField(45, null=True)
    status = fields.CharField(20, null=True)


class MultiworldEntrant(Model):
    id = fields.IntField(pk=True)
    discord_user_id = fields.BigIntField(null=True)
    multiworld = fields.ForeignKeyField('models.Multiworld', related_name='entrant')


class SpoilerRaces(Model):
    class Meta:
        table = 'spoiler_races'

    id = fields.IntField(pk=True)
    srl_id = fields.CharField(45, null=True)
    spoiler_url = fields.CharField(255, null=True)
    studytime = fields.IntField(null=True)
    date = fields.DatetimeField(auto_now_add=True)
    started = fields.DatetimeField(null=True)


class NickVerification(Model):
    class Meta:
        table = 'nick_verification'

    key = fields.BigIntField(pk=True, generated=False)
    discord_user_id = fields.BigIntField(null=True)
    timestamp = fields.DatetimeField(auto_now=True, null=True)


class PresetNamespaces(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(50, null=False, unique=True)
    discord_user_id = fields.BigIntField(null=False, unique=True)


class Presets(Model):
    class Meta:
        unique_together = ('randomizer', 'preset_name', 'namespace')

    id = fields.IntField(pk=True)
    randomizer = fields.CharField(50)
    preset_name = fields.CharField(50)
    namespace = fields.ForeignKeyField('models.PresetNamespaces', related_name='presets')
    content = fields.TextField()
    modified = fields.DatetimeField(auto_now=True)
    generated_count = fields.IntField(default=0)


class RTGGUnlistedRooms(Model):
    id = fields.IntField(pk=True)
    room_name = fields.CharField(200, null=False)
    category = fields.CharField(50, null=False)


class RTGGWatcher(Model):
    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField(null=False)
    channel_id = fields.BigIntField(null=False)
    notify_on_new_player = fields.BooleanField(default=False)  # NYI
    category = fields.CharField(50, null=False)


class RTGGWatcherPlayer(Model):
    id = fields.IntField(pk=True)
    rtgg_watcher = fields.ForeignKeyField('models.RTGGWatcher', related_name='watched_player')
    racetime_id = fields.CharField(50, null=False)


class RTGGAnnouncers(Model):
    id = fields.IntField(pk=True)
    category = fields.CharField(50, null=False)
    guild_id = fields.BigIntField(null=False)
    channel_id = fields.BigIntField(null=False)


class RTGGAnnouncerMessages(Model):
    id = fields.IntField(pk=True)
    announcer = fields.ForeignKeyField('models.RTGGAnnouncers', related_name='announcer_messages')
    message_id = fields.BigIntField(null=False)
    room_name = fields.CharField(50)


class SrlRaces(Model):
    class Meta:
        table = 'srl_races'

    id = fields.IntField(pk=True)
    srl_id = fields.CharField(45, null=True)
    goal = fields.CharField(200, null=True)
    timestamp = fields.DatetimeField(auto_now=True)
    message = fields.CharField(200, null=True)


class SRLNick(Model):
    class Meta:
        table = 'srlnick'

    discord_user_id = fields.BigIntField(pk=True, generated=False)
    srl_nick = fields.CharField(200, index=True)
    twitch_name = fields.CharField(200, index=True)
    rtgg_id = fields.CharField(200, index=True)
    srl_verified = fields.SmallIntField(null=True)


class TournamentGames(Model):
    class Meta:
        table = 'tournament_games'

    episode_id = fields.IntField(pk=True, generated=False)
    event = fields.CharField(45, null=True)
    game_number = fields.IntField(null=True)
    settings = fields.JSONField(null=True)
    preset = fields.CharField(100, null=True)
    notes = fields.TextField(null=True)
    submitted = fields.SmallIntField(null=True)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)


class TournamentResults(Model):
    class Meta:
        table = 'tournament_results'

    id = fields.IntField(pk=True)
    srl_id = fields.CharField(45, null=True)
    episode_id = fields.CharField(45, null=True)
    permalink = fields.CharField(1000, null=True)
    bingosync_room = fields.CharField(200, null=True)
    bingosync_password = fields.CharField(40, null=True)
    spoiler = fields.CharField(200, null=True)
    event = fields.CharField(45, null=True)
    status = fields.CharField(45, null=True)
    results_json = fields.JSONField(null=True)
    week = fields.CharField(45, null=True)
    written_to_gsheet = fields.SmallIntField(null=True)


class Tournaments(Model):
    class Meta:
        table = 'tournaments'
        unique_together = ('schedule_type', 'slug')

    id = fields.IntField(pk=True)
    schedule_type = fields.CharField(45, null=True)
    slug = fields.CharField(45, null=True)
    guild_id = fields.BigIntField(null=True)
    helper_roles = fields.CharField(2000, null=True)
    audit_channel_id = fields.BigIntField(null=True)
    commentary_channel_id = fields.BigIntField(null=True)
    scheduling_needs_channel_id = fields.BigIntField(null=True)
    scheduling_needs_tracker = fields.SmallIntField(null=True)
    mod_channel_id = fields.BigIntField(null=True)
    tracker_roles = fields.CharField(2000, null=True)
    commentator_roles = fields.CharField(2000, null=True)
    mod_roles = fields.CharField(2000, null=True)
    admin_roles = fields.CharField(2000, null=True)
    category = fields.CharField(200, null=True)
    goal = fields.CharField(200, null=True)
    active = fields.SmallIntField(null=True)
    has_submission = fields.BooleanField(null=True)
    lang = fields.CharField(20, null=True)
    coop = fields.BooleanField(null=True)


class TriforceTexts(Model):
    id = fields.IntField(pk=True)
    pool_name = fields.CharField(45, null=False)
    text = fields.CharField(200, null=False)
    author = fields.CharField(200, null=True)
    author_credit = fields.CharField(200, null=True)
    broadcasted = fields.BooleanField(null=False, default=False)


class SpeedGamingDailies(Model):
    class Meta:
        table = 'sgdailies'

    id = fields.IntField(pk=True)
    slug = fields.CharField(45, null=True)
    guild_id = fields.BigIntField(null=False)
    announce_channel = fields.BigIntField(null=False)
    announce_message = fields.BigIntField(null=False)
    racetime_category = fields.CharField(45, null=True)
    racetime_goal = fields.CharField(45, null=True)
    race_info = fields.CharField(2000, null=False)
    active = fields.SmallIntField(null=True)


class SGL2020Tournament(Model):
    class Meta:
        table = 'sgl2020_tournament'

    episode_id = fields.IntField(pk=True, generated=False)
    room_name = fields.CharField(100, null=True)
    event = fields.CharField(45, null=True)
    platform = fields.CharField(45, null=True)
    permalink = fields.CharField(200, null=True)
    seed = fields.CharField(200, null=True)
    password = fields.CharField(200, null=True)
    status = fields.CharField(45, null=True)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)


class SGL2020TournamentBO3(Model):
    class Meta:
        table = 'sgl2020_tournament_bo3'

    id = fields.IntField(pk=True)
    episode_id = fields.IntField(null=True)
    room_name = fields.CharField(100, null=True)
    event = fields.CharField(45, null=True)
    platform = fields.CharField(45, null=True)
    permalink = fields.CharField(200, null=True)
    seed = fields.CharField(200, null=True)
    password = fields.CharField(200, null=True)
    status = fields.CharField(45, null=True)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)


class TwitchChannels(Model):
    class Meta:
        table = 'twitch_channels'

    channel = fields.CharField(200, pk=True)
    status = fields.CharField(45, null=False)


class TwitchCommandText(Model):
    class Meta:
        table = 'twitch_command_text'
        unique_together = ('channel', 'command')

    id = fields.IntField(pk=True)
    channel = fields.CharField(200, null=True)
    command = fields.CharField(45, null=True)
    content = fields.CharField(4000, null=True)


class VoiceRole(Model):
    class Meta:
        table = 'voice_role'

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField(null=False)
    voice_channel_id = fields.BigIntField(null=False)
    role_id = fields.BigIntField(null=False)

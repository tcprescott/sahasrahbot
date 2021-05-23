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
    timestamp = fields.DatetimeField(auto_now=True)
    customizer = fields.IntField()

class AuditMessages(Model):
    class Meta:
        table="audit_messages"

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField()
    message_id = fields.BigIntField()
    user_id = fields.BigIntField()
    message_date = fields.DatetimeField(auto_now_add=True)
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
    submitted = fields.SmallIntField()
    created = fields.DatetimeField(auto_now_add=True)
    modified = fields.DatetimeField(auto_now=True)

class MentionCounters(Model):
    class Meta:
        table='mention_counters'

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField(null=False)
    role_id = fields.BigIntField(null=False, unique=True)
    counter = fields.IntField(null=False, default=1)
    last_used = fields.DatetimeField(auto_now=True)

class PatchDistribution(Model):
    class Meta:
        table='patch_distribution'

    id = fields.IntField(pk=True)
    patch_id = fields.CharField(45)
    game = fields.CharField(45)
    used = fields.SmallIntField(index=True)

class ReactionGroup(Model):
    class Meta:
        table='reaction_group'

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField(null=False)
    channel_id = fields.BigIntField(null=False)
    message_id = fields.BigIntField(null=False)
    name = fields.CharField(400)
    description = fields.CharField(1000)
    bot_managed = fields.IntField()

class ReactionRole(Model):
    class Meta:
        table='reaction_role'

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField(null=False)
    reaction_group_id = fields.BigIntField()
    role_id = fields.BigIntField()
    name = fields.CharField(45)
    emoji = fields.CharField(200)
    protect_mentions = fields.SmallIntField()


class SMZ3Multiworld(Model):
    class Meta:
        table='smz3_multiworld'

    message_id = fields.BigIntField(pk=True, generated=False)
    owner_id = fields.BigIntField()
    randomizer = fields.CharField(45)
    preset = fields.CharField(45)
    status = fields.CharField(20)

class SpoilerRaces(Model):
    class Meta:
        table='spoiler_races'

    id = fields.IntField(pk=True)
    srl_id = fields.CharField(45)
    spoiler_url = fields.CharField(255)
    studytime = fields.IntField()
    date = fields.DatetimeField(auto_now_add=True)
    started = fields.DatetimeField()

class NickVerification(Model):
    class Meta:
        table='nick_verification'

    key = fields.BigIntField(pk=True, generated=False)
    discord_user_id = fields.BigIntField()
    timestamp = fields.DatetimeField(auto_now=True)

class SrlRaces(Model):
    class Meta:
        table='srl_races'

    id = fields.IntField(pk=True)
    srl_id = fields.CharField(45)
    goal = fields.CharField(200)
    timestamp = fields.DatetimeField(auto_now=True)
    message = fields.CharField(200)

class SRLNick(Model):
    class Meta:
        table='srlnick'

    discord_user_id = fields.BigIntField(pk=True, generated=False)
    srl_nick = fields.CharField(200, index=True)
    twitch_name = fields.CharField(200, index=True)
    rtgg_id = fields.CharField(200, index=True)
    srl_verified = fields.SmallIntField()

class TournamentGames(Model):
    class Meta:
        table='tournament_games'

    episode_id = fields.IntField(pk=True, generated=False)
    event = fields.CharField(45)
    game_number = fields.IntField()
    settings = fields.JSONField()
    submitted = fields.SmallIntField()
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)

class TournamentResults(Model):
    class Meta:
        table='tournament_results'

    id = fields.IntField(pk=True)
    srl_id = fields.CharField(45)
    episode_id = fields.CharField(45)
    permalink = fields.CharField(200)
    spoiler = fields.CharField(200)
    event = fields.CharField(45)
    status = fields.CharField(45)
    results_json = fields.JSONField()
    week = fields.CharField(45)
    written_to_gsheet = fields.SmallIntField()

class Tournaments(Model):
    class Meta:
        table='tournaments'
        unique_together=('schedule_type', 'slug')

    id = fields.IntField(pk=True)
    schedule_type = fields.CharField(45)
    slug = fields.CharField(45)
    guild_id = fields.BigIntField()
    helper_roles = fields.CharField(4000)
    audit_channel_id = fields.BigIntField()
    commentary_channel_id = fields.BigIntField()
    scheduling_needs_channel_id = fields.BigIntField()
    scheduling_needs_tracker = fields.SmallIntField()
    mod_channel_id = fields.BigIntField()
    tracker_roles = fields.CharField(4000)
    commentator_roles = fields.CharField(4000)
    mod_roles = fields.CharField(4000)
    admin_roles = fields.CharField(4000)
    category = fields.CharField(200)
    goal = fields.CharField(200)
    active = fields.SmallIntField()
    lang = fields.CharField(20)

class SpeedGamingDailies(Model):
    class Meta:
        table = 'sgdailies'

    id = fields.IntField(pk=True)
    slug = fields.CharField(45)
    guild_id = fields.BigIntField(null=False)
    announce_channel = fields.BigIntField(null=False)
    announce_message = fields.BigIntField(null=False)
    racetime_category = fields.CharField(45)
    racetime_goal = fields.CharField(45)
    race_info = fields.CharField(2000, null=False)
    active = fields.SmallIntField()

class SGL2020Tournament(Model):
    class Meta:
        table='sgl2020_tournament'

    episode_id = fields.IntField(pk=True, generated=False)
    room_name = fields.CharField(100)
    event = fields.CharField(45)
    platform = fields.CharField(45)
    permalink = fields.CharField(200)
    seed = fields.CharField(200)
    password = fields.CharField(200)
    status = fields.CharField(45)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)

class SGL2020TournamentBO3(Model):
    class Meta:
        table='sgl2020_tournament_bo3'

    id = fields.IntField(pk=True)
    episode_id = fields.IntField()
    room_name = fields.CharField(100)
    event = fields.CharField(45)
    platform = fields.CharField(45)
    permalink = fields.CharField(200)
    seed = fields.CharField(200)
    password = fields.CharField(200)
    status = fields.CharField(45)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)

class TwitchChannels(Model):
    class Meta:
        table='twitch_channels'

    channel = fields.CharField(200, pk=True)
    status = fields.CharField(45, null=False)

class TwitchCommandText(Model):
    class Meta:
        table='twitch_command_text'
        unique_together=('channel', 'command')

    id = fields.IntField(pk=True)
    channel = fields.CharField(200)
    command = fields.CharField(45)
    content = fields.CharField(4000)

class VoiceRole(Model):
    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField(null=False)
    voice_channel_id = fields.BigIntField(null=False)
    role_id = fields.BigIntField(null=False)

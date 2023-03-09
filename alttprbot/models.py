from tortoise.models import Model
from tortoise import fields

from alttprbot import enums


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
    doors = fields.BooleanField(default=False, null=False)


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
    category = fields.ForeignKeyField('models.DiscordServerCategories', related_name='server_list')


class DiscordServerCategories(Model):
    class Meta:
        table = 'discord_server_categories'

    id = fields.IntField(pk=True)
    order = fields.IntField(null=False, default=0)
    guild_id = fields.BigIntField(null=False)
    channel_id = fields.BigIntField(null=False)
    category_title = fields.CharField(200, null=False)
    category_description = fields.CharField(200, null=True)


class InquiryMessageConfig(Model):
    message_id = fields.BigIntField(pk=True, generated=False)
    role_id = fields.BigIntField(null=False)


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


class PresetNamespaceCollaborators(Model):
    class Meta:
        unique_together = ('namespace', 'discord_user_id')
    id = fields.IntField(pk=True)
    namespace = fields.ForeignKeyField('models.PresetNamespaces', related_name='collaborators')
    discord_user_id = fields.BigIntField(null=False)


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


class AuthorizationKeys(Model):
    id = fields.IntField(pk=True)
    key = fields.CharField(200, null=False, unique=True)
    name = fields.CharField(200, null=False)


class AuthorizationKeyPermissions(Model):
    id = fields.IntField(pk=True)
    auth_key = fields.ForeignKeyField('models.AuthorizationKeys', related_name='permissions')
    type = fields.CharField(45, null=False)
    subtype = fields.TextField(null=True)


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
    twitch_name = fields.CharField(200, index=True, null=True)
    rtgg_id = fields.CharField(200, index=True, null=True)
    display_name = fields.CharField(200, index=True, null=True)


class Users(Model):
    id = fields.IntField(pk=True)
    discord_user_id = fields.BigIntField(null=True, unique=True)
    twitch_name = fields.CharField(200, null=True)
    rtgg_id = fields.CharField(200, null=True, unique=True)
    display_name = fields.CharField(200, index=True, null=True)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)


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


class TournamentPresetHistory(Model):
    id = fields.IntField(pk=True)
    preset = fields.CharField(max_length=255)
    discord_user_id = fields.BigIntField()
    episode_id = fields.IntField(null=True)
    event_slug = fields.CharField(max_length=255)
    timestamp = fields.DatetimeField(auto_now_add=True)


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
    discord_user_id = fields.BigIntField(null=True)
    author = fields.CharField(200, null=True)
    approved = fields.BooleanField(default=False)
    broadcasted = fields.BooleanField(null=False, default=False)
    timestamp = fields.DatetimeField(auto_now=True)


class TriforceTextsConfig(Model):
    id = fields.IntField(pk=True)
    pool_name = fields.CharField(45, null=False)
    key_name = fields.CharField(2000, null=False)
    value = fields.CharField(2000, null=False)


class ScheduledEvents(Model):
    scheduled_event_id = fields.BigIntField(pk=True, generated=False)
    event_slug = fields.CharField(40, null=False)
    episode_id = fields.IntField(null=False, unique=True)


class SpeedGamingDailies(Model):
    class Meta:
        table = 'sgdailies'

    id = fields.IntField(pk=True)
    slug = fields.CharField(45, null=True)
    guild_id = fields.BigIntField(null=False)
    announce_channel = fields.BigIntField(null=False)
    announce_message = fields.CharField(2000, null=False)
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


class VoiceRole(Model):
    class Meta:
        table = 'voice_role'

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField(null=False)
    voice_channel_id = fields.BigIntField(null=False)
    role_id = fields.BigIntField(null=False)


class RankedChoiceElection(Model):
    class Meta:
        table = 'ranked_choice_election'

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField(null=True)
    channel_id = fields.BigIntField(null=True)
    message_id = fields.BigIntField(null=True)
    owner_id = fields.BigIntField(null=False)
    title = fields.CharField(200, null=False)
    description = fields.CharField(2000, null=True)
    show_vote_count = fields.BooleanField(null=False, default=True)
    active = fields.BooleanField(null=False, default=True)
    private = fields.BooleanField(null=False, default=False)
    seats = fields.SmallIntField(null=False, default=1)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)
    results = fields.TextField(null=True)


class RankedChoiceAuthorizedVoters(Model):
    class Meta:
        table = 'ranked_choice_authorized_voters'

    id = fields.IntField(pk=True)
    election = fields.ForeignKeyField('models.RankedChoiceElection', related_name='authorized_voters')
    user_id = fields.BigIntField(null=False)


class RankedChoiceCandidate(Model):
    class Meta:
        table = 'ranked_choice_candidate'

    id = fields.IntField(pk=True)
    election = fields.ForeignKeyField('models.RankedChoiceElection', related_name='candidates')
    name = fields.CharField(200, null=False)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)
    winner = fields.BooleanField(null=True)


class RankedChoiceVotes(Model):
    class Meta:
        table = 'ranked_choice_votes'

    id = fields.IntField(pk=True)
    election = fields.ForeignKeyField('models.RankedChoiceElection', related_name='votes')
    user_id = fields.BigIntField(null=False)
    candidate = fields.ForeignKeyField('models.RankedChoiceCandidate', related_name='votes')
    rank = fields.IntField(null=True)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)


class AsyncTournament(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(45, null=False)
    guild_id = fields.BigIntField(null=False)
    channel_id = fields.BigIntField(null=False, unique=True)
    report_channel_id = fields.BigIntField(null=True)
    owner_id = fields.BigIntField(null=False)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)
    active = fields.BooleanField(null=False, default=True)
    allowed_reattempts = fields.SmallIntField(null=False, default=0)


class AsyncTournamentWhitelist(Model):
    id = fields.IntField(pk=True)
    tournament = fields.ForeignKeyField('models.AsyncTournament', related_name='whitelist')
    user = fields.ForeignKeyField('models.Users', related_name='async_tournament_whitelist')
    discord_user_id = fields.BigIntField(null=False)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)


class AsyncTournamentPermalink(Model):
    id = fields.IntField(pk=True)
    pool = fields.ForeignKeyField('models.AsyncTournamentPermalinkPool', related_name='permalinks')
    permalink = fields.CharField(200, null=False)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)
    live_race = fields.BooleanField(null=False, default=False)
    racetime_slug = fields.CharField(200, null=True)


class AsyncTournamentPermalinkPool(Model):
    id = fields.IntField(pk=True)
    tournament = fields.ForeignKeyField('models.AsyncTournament', related_name='permalink_pools')
    name = fields.CharField(45, null=False)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)


class AsyncTournamentRace(Model):
    id = fields.IntField(pk=True)
    tournament = fields.ForeignKeyField('models.AsyncTournament', related_name='races')
    permalink = fields.ForeignKeyField('models.AsyncTournamentPermalink', related_name='races')
    discord_user_id = fields.BigIntField(null=False)
    user = fields.ForeignKeyField('models.Users', related_name='async_tournament_races', null=True)
    thread_id = fields.BigIntField(null=True)  # only set if run async in discord
    thread_open_time = fields.DatetimeField(null=True)  # only set if run async in discord
    thread_timeout_time = fields.DatetimeField(null=True)
    start_time = fields.DatetimeField(null=True)
    end_time = fields.DatetimeField(null=True)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)
    status = fields.CharField(45, null=False, default='pending')  # pending, in_progress, finished, forfeit
    racetime_slug = fields.CharField(200, null=True)  # only set if race was performed on racetime.gg
    reattempted = fields.BooleanField(null=False, default=False)
    runner_notes = fields.TextField(null=True)
    runner_vod_url = fields.CharField(400, null=True)
    review_status = fields.CharEnumField(enums.AsyncReviewStatus, null=False, default="pending")  # pending, approved, rejected
    reviewed_by = fields.BigIntField(null=True)
    reviewed_at = fields.DatetimeField(null=True)
    reviewer_notes = fields.TextField(null=True)


class AsyncTournamentAuditLog(Model):
    id = fields.IntField(pk=True)
    tournament = fields.ForeignKeyField('models.AsyncTournament', related_name='audit_log')
    discord_user_id = fields.BigIntField(null=True)
    user = fields.ForeignKeyField('models.Users', related_name='async_tournament_audit_log', null=True)
    action = fields.CharField(45, null=False)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)
    details = fields.TextField(null=True)

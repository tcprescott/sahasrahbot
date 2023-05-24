import os

from datetime import timedelta
from typing import Optional
from bs4 import BeautifulSoup
import markdown

import discord.utils
from tortoise import fields
from tortoise.models import Model

RACETIME_URL = os.environ.get('RACETIME_URL', 'https://racetime.gg')


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
    rtgg_access_token = fields.CharField(200, null=True)
    display_name = fields.CharField(200, index=True, null=True)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)
    test_user = fields.BooleanField(default=False)

    async_tournament_permissions = fields.ReverseRelation['AsyncTournamentPermissions']
    async_tournament_whitelist = fields.ReverseRelation['AsyncTournamentWhitelist']
    async_tournament_races = fields.ReverseRelation['AsyncTournamentRace']
    async_tournament_reviews = fields.ReverseRelation['AsyncTournamentRace']
    async_tournament_audit_log = fields.ReverseRelation['AsyncTournamentAuditLog']

    @property
    def racetime_profile(self):
        if self.rtgg_id is None:
            return None
        return f'{RACETIME_URL}/user/{self.rtgg_id}/'

    class PydanticMeta:
        exclude = [
            'rtgg_access_token',
            'test_user',
            'created',
            'updated',
            'async_tournament_permissions',
            'async_tournament_whitelist',
            'async_tournament_races',
            'async_tournament_reviews',
            'async_tournament_audit_log'
        ]
        backward_relations = False
    #     computed = ['racetime_profile']


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
    episode_id = fields.BigIntField(null=True)
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

    customization = fields.CharField(45, null=False, default='default')

    races: fields.ReverseRelation["AsyncTournamentRace"]
    whitelist: fields.ReverseRelation["AsyncTournamentWhitelist"]
    permissions: fields.ReverseRelation["AsyncTournamentPermissions"]
    permalink_pools: fields.ReverseRelation["AsyncTournamentPermalinkPool"]
    live_races: fields.ReverseRelation["AsyncTournamentLiveRace"]

    class PydanticMeta:
        backward_relations = False
        exclude = ['permissions', 'whitelist']


class AsyncTournamentWhitelist(Model):
    id = fields.IntField(pk=True)
    tournament = fields.ForeignKeyField('models.AsyncTournament', related_name='whitelist')
    user = fields.ForeignKeyField('models.Users', related_name='async_tournament_whitelist', on_delete="RESTRICT")
    discord_user_id = fields.BigIntField(null=True)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)

    class PydanticMeta:
        backward_relations = False
        exclude = ['discord_user_id', 'tournament']


class AsyncTournamentPermissions(Model):
    id = fields.IntField(pk=True)
    tournament = fields.ForeignKeyField('models.AsyncTournament', related_name='permissions')
    user = fields.ForeignKeyField('models.Users', related_name='async_tournament_permissions', on_delete="RESTRICT", null=True)
    discord_role_id = fields.BigIntField(null=True)
    role = fields.CharField(45, null=False)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)


class AsyncTournamentPermalink(Model):
    id = fields.IntField(pk=True)
    pool = fields.ForeignKeyField('models.AsyncTournamentPermalinkPool', related_name='permalinks')
    url = fields.CharField(200, null=False)
    notes = fields.CharField(200, null=True)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)
    live_race = fields.BooleanField(null=False, default=False)
    par_time = fields.FloatField(null=True)
    par_updated_at = fields.DatetimeField(null=True)

    races: fields.ReverseRelation["AsyncTournamentRace"]
    live_races: fields.ReverseRelation["AsyncTournamentLiveRace"]

    @property
    def par_time_timedelta(self):
        if self.par_time is None:
            return None
        return timedelta(seconds=self.par_time)

    @property
    def par_time_formatted(self):
        hours, remainder = divmod(self.par_time_timedelta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    class PydanticMeta:
        # computed = ['par_time_formatted']
        backward_relations = False
        exclude = ['created', 'updated']


class AsyncTournamentPermalinkPool(Model):
    class Meta:
        unique_together = ('tournament', 'name')

    id = fields.IntField(pk=True)
    tournament = fields.ForeignKeyField('models.AsyncTournament', related_name='permalink_pools')
    name = fields.CharField(45, null=False)
    preset = fields.CharField(45, null=True)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)

    permalinks: fields.ReverseRelation["AsyncTournamentPermalink"]
    live_races: fields.ReverseRelation["AsyncTournamentLiveRace"]

    class PydanticMeta:
        max_recursion = 1
        exclude = ['created', 'updated', 'tournament']


class AsyncTournamentLiveRace(Model):
    id = fields.IntField(pk=True)
    tournament = fields.ForeignKeyField('models.AsyncTournament', related_name='live_races')
    pool = fields.ForeignKeyField('models.AsyncTournamentPermalinkPool', related_name='live_races')
    permalink = fields.ForeignKeyField('models.AsyncTournamentPermalink', related_name='live_races', null=True)
    racetime_slug = fields.CharField(200, null=True, unique=True)
    episode_id = fields.IntField(null=True, unique=True)
    match_title = fields.CharField(200, null=True)
    status = fields.CharField(45, null=False, default='scheduled')  # scheduled, pending, in_progress, finished
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)

    races: fields.ReverseRelation["AsyncTournamentRace"]

    @property
    def racetime_url(self):
        if self.racetime_slug is None:
            return None
        return f"{RACETIME_URL}/{self.racetime_slug}"

    class PydanticMeta:
        # computed = ['racetime_url']
        backward_relations = False
        exclude = ['created', 'updated', 'races']


class AsyncTournamentReviewNotes(Model):
    id = fields.IntField(pk=True)
    race = fields.ForeignKeyField('models.AsyncTournamentRace', related_name='review_notes')
    author = fields.ForeignKeyField('models.Users', related_name='async_tournament_review_notes', on_delete="RESTRICT")
    created = fields.DatetimeField(auto_now_add=True)
    note = fields.TextField(null=False)


class AsyncTournamentRace(Model):
    id = fields.IntField(pk=True)
    tournament = fields.ForeignKeyField('models.AsyncTournament', related_name='races')
    permalink = fields.ForeignKeyField('models.AsyncTournamentPermalink', related_name='races')
    user = fields.ForeignKeyField('models.Users', related_name='async_tournament_races', null=False)
    thread_id = fields.BigIntField(null=True)  # only set if run async in discord
    thread_open_time = fields.DatetimeField(null=True)  # only set if run async in discord
    thread_timeout_time = fields.DatetimeField(null=True)
    start_time = fields.DatetimeField(null=True)
    end_time = fields.DatetimeField(null=True)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)
    status = fields.CharField(45, null=False, default='pending')  # pending, in_progress, finished, forfeit, disqualified
    live_race = fields.ForeignKeyField('models.AsyncTournamentLiveRace', null=True)  # only set if run was raced live
    reattempted = fields.BooleanField(null=False, default=False)
    runner_notes = fields.TextField(null=True)
    runner_vod_url = fields.CharField(400, null=True)
    run_collection_rate = fields.CharField(100, null=True)
    run_igt = fields.CharField(100, null=True)
    review_status = fields.CharField(20, null=False, default="pending")  # pending, approved, rejected
    reviewed_by = fields.ForeignKeyField('models.Users', related_name='async_tournament_reviews', null=True)
    reviewed_at = fields.DatetimeField(null=True)
    reviewer_notes = fields.TextField(null=True)
    score = fields.FloatField(null=True)
    score_updated_at = fields.DatetimeField(null=True)

    review_notes: fields.ReverseRelation["AsyncTournamentReviewNotes"]

    @property
    def elapsed_time(self) -> Optional[timedelta]:
        if self.start_time is None:
            return None

        if self.status == 'finished':
            return self.end_time - self.start_time
        elif self.status == 'in_progress':
            return discord.utils.utcnow() - self.start_time

        return None

    @property
    def elapsed_time_formatted(self) -> Optional[str]:
        if self.elapsed_time is None:
            return "N/A"

        hours, remainder = divmod(self.elapsed_time.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    @property
    def score_formatted(self) -> Optional[str]:
        if self.score is None:
            if self.status in ['pending', 'in_progress']:
                return "N/A"

            return "not calculated"

        return f"{self.score:.3f}"

    @property
    def status_formatted(self) -> str:
        if self.status == 'pending':
            return "Pending"
        elif self.status == 'in_progress':
            return "In Progress"
        elif self.status == 'finished':
            return "Finished"
        elif self.status == 'forfeit':
            return "Forfeit"
        elif self.status == 'disqualified':
            return "Disqualified"

        return "Unknown"

    @property
    def review_status_formatted(self) -> str:
        if self.live_race:
            return "N/A"
        if self.reattempted:
            return "N/A"
        if self.status != 'finished':
            return "N/A"

        if self.review_status == 'pending':
            return "Pending"
        elif self.review_status == 'accepted':
            return "Accepted"
        elif self.review_status == 'rejected':
            return "Rejected"

        return "Unknown"

    @property
    def thread_url(self) -> Optional[str]:
        if self.thread_id is None:
            return None

        return f"https://discord.com/channels/{self.tournament.guild_id}/{self.thread_id}"

    @property
    def url(self) -> Optional[str]:
        if self.live_race:
            return self.live_race.racetime_url

        return self.thread_url

    def is_closed(self):
        return self.status in ['finished', 'forfeit', 'disqualified']

    @property
    def runner_notes_html(self):
        if self.runner_notes is None:
            return None

        soup = BeautifulSoup(self.runner_notes, 'html.parser')
        text = soup.get_text()
        text = text.replace("\n", "<br/>")
        return markdown.markdown(text)

    class PydanticMeta:
        # computed = ['elapsed_time']
        backward_relations = False
        exclude = ['created', 'updated', 'tournament']


class AsyncTournamentAuditLog(Model):
    id = fields.IntField(pk=True)
    tournament = fields.ForeignKeyField('models.AsyncTournament', related_name='audit_log')
    user = fields.ForeignKeyField('models.Users', related_name='async_tournament_audit_log', null=True, on_delete="RESTRICT")
    action = fields.CharField(45, null=False)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)
    details = fields.TextField(null=True)

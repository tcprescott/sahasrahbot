from datetime import datetime, timedelta, timezone
from typing import Optional

import markdown
import pytz
from bs4 import BeautifulSoup
from tortoise import fields
from tortoise.models import Model

import config

RACETIME_URL = config.RACETIME_URL


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
    runs_per_pool = fields.SmallIntField(null=False, default=1)

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
    user = fields.ForeignKeyField('models.Users', related_name='async_tournament_permissions', on_delete="RESTRICT",
                                  null=True)
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
    status = fields.CharField(45, null=False,
                              default='pending')  # pending, in_progress, finished, forfeit, disqualified
    live_race = fields.ForeignKeyField('models.AsyncTournamentLiveRace', null=True)  # only set if run was raced live
    reattempted = fields.BooleanField(null=False, default=False)
    reattempt_reason = fields.TextField(null=True)
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
            return datetime.now(timezone.utc) - self.start_time

        return None

    @property
    def elapsed_time_formatted(self) -> Optional[str]:
        if self.elapsed_time is None:
            return "N/A"

        hours, remainder = divmod(self.elapsed_time.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    @property
    def thread_open_time_formatted(self) -> Optional[str]:
        if self.thread_open_time is None:
            return "N/A"

        return self.thread_open_time.astimezone(tz=pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S')

    @property
    def reviewed_at_formatted(self) -> Optional[str]:
        if self.reviewed_at is None:
            return ""

        return self.reviewed_at.astimezone(tz=pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S')

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
            return "Pending Second Review"

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
    user = fields.ForeignKeyField('models.Users', related_name='async_tournament_audit_log', null=True,
                                  on_delete="RESTRICT")
    action = fields.CharField(45, null=False)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)
    details = fields.TextField(null=True)

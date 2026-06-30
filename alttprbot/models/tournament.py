from tortoise import fields
from tortoise.models import Model


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


class ScheduledEvents(Model):
    scheduled_event_id = fields.BigIntField(pk=True, generated=False)
    event_slug = fields.CharField(40, null=False)
    episode_id = fields.IntField(null=False, unique=True)

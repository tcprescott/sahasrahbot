from tortoise import fields
from tortoise.models import Model


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


class SpoilerRaces(Model):
    class Meta:
        table = 'spoiler_races'

    id = fields.IntField(pk=True)
    srl_id = fields.CharField(45, null=True)
    spoiler_url = fields.CharField(255, null=True)
    studytime = fields.IntField(null=True)
    date = fields.DatetimeField(auto_now_add=True)
    started = fields.DatetimeField(null=True)


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


class RTGGOverrideWhitelist(Model):
    id = fields.IntField(pk=True)
    racetime_id = fields.CharField(50, null=False)
    category = fields.CharField(50, null=False)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)
    reason = fields.CharField(200, null=True)
    expires = fields.DatetimeField(null=True)


class SrlRaces(Model):
    class Meta:
        table = 'srl_races'

    id = fields.IntField(pk=True)
    srl_id = fields.CharField(45, null=True)
    goal = fields.CharField(200, null=True)
    timestamp = fields.DatetimeField(auto_now=True)
    message = fields.CharField(200, null=True)

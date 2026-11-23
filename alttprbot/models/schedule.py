from tortoise import fields
from tortoise.models import Model

class ScheduleEvent(Model):
    id = fields.IntField(pk=True)
    event_slug = fields.CharField(50, unique=True)
    name = fields.TextField()
    description = fields.TextField()
    stream_delay = fields.IntField(default=0) # in seconds

    # allow anyone to sign up for this event to run or crew
    open_player_signup = fields.BooleanField(default=True)
    open_restreamer_signup = fields.BooleanField(default=True)
    open_commentator_signup = fields.BooleanField(default=True)
    open_tracker_signup = fields.BooleanField(default=True)

    max_players = fields.IntField(default=2)
    max_commentators = fields.IntField(default=2)
    max_trackers = fields.IntField(default=1)
    max_restreamers = fields.IntField(default=1)

class ScheduleRole(Model):
    id = fields.IntField(pk=True)
    event = fields.ForeignKeyField('models.ScheduleEvent', related_name='roles')
    name = fields.CharField(50) # admin, mod, player, commentator, tracker, restreamer

class ScheduleRoleMember(Model):
    id = fields.IntField(pk=True)
    role = fields.ForeignKeyField('models.ScheduleRole', related_name='members')
    user = fields.ForeignKeyField('models.Users', related_name='schedule_event_roles')

class ScheduleEpisode(Model):
    id = fields.IntField(pk=True)
    event = fields.ForeignKeyField('models.ScheduleEvent', related_name='episodes')
    scheduled_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    when_countdown = fields.DatetimeField(null=False)
    runner_notes = fields.TextField(null=True) # notes from the runner
    private_notes = fields.TextField(null=True) # notes from the event organizer(s)
    channel = fields.ForeignKeyField('models.ScheduleBroadcastChannels', related_name='episodes', null=True)

    approved = fields.BooleanField(default=False)
    approved_at = fields.DatetimeField(null=True)
    approved_by = fields.ForeignKeyField('models.Users', related_name='schedule_episode_approvals', on_delete="RESTRICT", null=True)

    players: fields.ReverseRelation['ScheduleEpisodePlayer']
    commentators: fields.ReverseRelation['ScheduleEpisodeCommentator']
    trackers: fields.ReverseRelation['ScheduleEpisodeTracker']
    restreamers: fields.ReverseRelation['ScheduleEpisodeRestreamer']

class ScheduleEpisodePlayer(Model):
    id = fields.IntField(pk=True)
    episode = fields.ForeignKeyField('models.ScheduleEpisode', related_name='players')
    user = fields.ForeignKeyField('models.Users', related_name='schedule_events', on_delete="RESTRICT")

class ScheduleEpisodeCommentator(Model):
    id = fields.IntField(pk=True)
    episode = fields.ForeignKeyField('models.ScheduleEpisode', related_name='commentators')
    user = fields.ForeignKeyField('models.Users', related_name='schedule_commentators', on_delete="RESTRICT")
    approved = fields.BooleanField(default=False)
    approved_at = fields.DatetimeField(null=True)
    approved_by = fields.ForeignKeyField('models.Users', related_name='schedule_commentator_approvals', on_delete="RESTRICT", null=True)
    submitted_at = fields.DatetimeField(auto_now_add=True)
    submitter_notes = fields.TextField(null=True)

    preferred_partner: fields.ReverseRelation['ScheduleEpisodeCommentatorPreferredPartner']

class ScheduleEpisodeCommentatorPreferredPartner(Model):
    id = fields.IntField(pk=True)
    episode = fields.ForeignKeyField('models.ScheduleEpisode', related_name='preferred_commentator_partners')
    user = fields.ForeignKeyField('models.Users', related_name='schedule_preferred_commentator_partners', on_delete="RESTRICT")

class ScheduleEpisodeTracker(Model):
    id = fields.IntField(pk=True)
    episode = fields.ForeignKeyField('models.ScheduleEpisode', related_name='trackers')
    user = fields.ForeignKeyField('models.Users', related_name='schedule_trackers', on_delete="RESTRICT")
    approved = fields.BooleanField(default=False)
    approved_at = fields.DatetimeField(null=True)
    approved_by = fields.ForeignKeyField('models.Users', related_name='schedule_tracker_approvals', on_delete="RESTRICT", null=True)
    submitted_at = fields.DatetimeField(auto_now_add=True)
    submitter_notes = fields.TextField(null=True)

class ScheduleEpisodeRestreamer(Model):
    id = fields.IntField(pk=True)
    episode = fields.ForeignKeyField('models.ScheduleEpisode', related_name='restreamers')
    user = fields.ForeignKeyField('models.Users', related_name='schedule_restreamers', on_delete="RESTRICT")
    approved = fields.BooleanField(default=False)
    approved_at = fields.DatetimeField(null=True)
    approved_by = fields.ForeignKeyField('models.Users', related_name='schedule_restreamer_approvals', on_delete="RESTRICT", null=True)
    submitted_at = fields.DatetimeField(auto_now_add=True)
    submitter_notes = fields.TextField(null=True)


class ScheduleBroadcastChannels(Model):
    id = fields.IntField(pk=True)
    event = fields.ForeignKeyField('models.ScheduleEvent', related_name='broadcast_channels')
    channel_type = fields.CharField(200, default="twitch", null=False) # only twitch supported for now
    channel_name = fields.CharField(200)
    display_name = fields.CharField(200)

    @property
    def url(self):
        return f"https://twitch.tv/{self.channel_name}"

class ScheduleAudit(Model):
    id = fields.IntField(pk=True)
    event = fields.ForeignKeyField('models.ScheduleEvent', related_name='audits')
    episode = fields.ForeignKeyField('models.ScheduleEpisode', related_name='audits', null=True)
    user = fields.ForeignKeyField('models.Users', related_name='schedule_audits', on_delete="RESTRICT")
    action = fields.TextField()
    timestamp = fields.DatetimeField(auto_now_add=True)

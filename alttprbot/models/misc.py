from tortoise import fields
from tortoise.models import Model


class Daily(Model):
    class Meta:
        table = "daily"

    id = fields.IntField(pk=True)
    hash = fields.CharField(45, index=True)


class PatchDistribution(Model):
    class Meta:
        table = 'patch_distribution'

    id = fields.IntField(pk=True)
    patch_id = fields.CharField(45, null=True)
    game = fields.CharField(45, null=True)
    used = fields.SmallIntField(index=True)


class AuthorizationKeys(Model):
    id = fields.IntField(pk=True)
    key = fields.CharField(200, null=False, unique=True)
    name = fields.CharField(200, null=False)


class AuthorizationKeyPermissions(Model):
    id = fields.IntField(pk=True)
    auth_key = fields.ForeignKeyField('models.AuthorizationKeys', related_name='permissions')
    type = fields.CharField(45, null=False)
    subtype = fields.TextField(null=True)


class TriforceTexts(Model):
    id = fields.IntField(pk=True)
    pool_name = fields.CharField(45, null=False)
    text = fields.CharField(200, null=False)
    discord_user_id = fields.BigIntField(null=True)
    author = fields.CharField(200, null=True)
    approved = fields.BooleanField(null=True)
    broadcasted = fields.BooleanField(null=False, default=False)
    timestamp = fields.DatetimeField(auto_now=True)


class TriforceTextsConfig(Model):
    id = fields.IntField(pk=True)
    pool_name = fields.CharField(45, null=False)
    key_name = fields.CharField(2000, null=False)
    value = fields.CharField(2000, null=False)


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


class SGL2023OnsiteHistory(Model):
    id = fields.IntField(pk=True)
    date = fields.DatetimeField(auto_now_add=True)
    tournament = fields.CharField(45, null=False)
    url = fields.CharField(300, null=False)
    ip_address = fields.CharField(200, null=False) # will store X-Forwarded-For header


class TelemetryEvent(Model):
    """
    Anonymous telemetry event storage.
    Stores privacy-preserving usage and reliability metrics.

    Privacy Policy:
    - No raw user IDs, usernames, or identifiable information
    - guild_hash is a salted one-way hash (not reversible)
    - Short retention period (default 30 days)
    """
    class Meta:
        table = "telemetry_events"
        indexes = [
            ("day_bucket", "surface", "feature"),
            ("day_bucket", "event_name"),
            ("day_bucket", "status"),
        ]

    id = fields.IntField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    day_bucket = fields.DateField(index=True)
    event_name = fields.CharField(100, index=True)
    surface = fields.CharField(20, index=True)  # discord, racetime, api
    feature = fields.CharField(50, index=True)  # generator, daily, asynctournament, etc.
    action = fields.CharField(20)  # invoke, success, failure
    status = fields.CharField(20, index=True)  # ok, error, timeout, denied
    provider = fields.CharField(50, null=True)  # optional: randomizer provider/API name
    guild_hash = fields.CharField(64, index=True, null=True)  # salted hash, not raw ID
    duration_ms = fields.IntField(null=True)
    error_type = fields.CharField(50, null=True)  # normalized domain error
    sample_rate = fields.FloatField(default=1.0)

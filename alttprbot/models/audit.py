from tortoise import fields
from tortoise.models import Model


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
    avianart = fields.BooleanField(default=False, null=False)


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

from tortoise import fields
from tortoise.models import Model


class Config(Model):
    class Meta:
        table = "config"

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField(null=False)
    parameter = fields.CharField(45, null=False)
    value = fields.CharField(45, null=True)


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
    description = fields.CharField(1000, null=True)
    protect_mentions = fields.SmallIntField(null=True)


class VoiceRole(Model):
    class Meta:
        table = 'voice_role'

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField(null=False)
    voice_channel_id = fields.BigIntField(null=False)
    role_id = fields.BigIntField(null=False)

from tortoise import fields
from tortoise.models import Model


class PresetNamespaces(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(50, null=False, unique=True)
    discord_user_id = fields.BigIntField(null=False, unique=True)

    presets = fields.ReverseRelation['Presets']


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

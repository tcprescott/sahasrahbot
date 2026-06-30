from tortoise import fields
from tortoise.models import Model

import config

RACETIME_URL = config.RACETIME_URL


class NickVerification(Model):
    class Meta:
        table = 'nick_verification'

    key = fields.BigIntField(pk=True, generated=False)
    discord_user_id = fields.BigIntField(null=True)
    timestamp = fields.DatetimeField(auto_now=True, null=True)


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
    display_name = fields.CharField(200, index=True, null=True, unique=True)
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


class RacerVerification(Model):
    id = fields.IntField(pk=True)
    message_id = fields.BigIntField(null=True)
    channel_id = fields.BigIntField(null=True)
    guild_id = fields.BigIntField(null=False)
    role_id = fields.BigIntField(null=False)
    racetime_categories = fields.CharField(2000, null=True)  # comma separated list of racetime categories to query
    use_alttpr_ladder = fields.BooleanField(null=False, default=False)  # use alttpr ladder to verify
    minimum_races = fields.IntField(null=False)
    time_period_days = fields.IntField(null=False, default=365)
    reverify_period_days = fields.IntField(null=True, default=None) # if set, will reverify every X days
    revoke_ineligible = fields.BooleanField(null=False, default=False) # if set, will revoke role if ineligible
    audit_channel_id = fields.BigIntField(null=True, default=None) # if set, will notify this channel if reverify fails
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)

    verified_racers: fields.ReverseRelation['VerifiedRacer']


class VerifiedRacer(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField('models.Users', related_name='verified_racer', on_delete="RESTRICT")
    racer_verification = fields.ForeignKeyField('models.RacerVerification', related_name='verified_racer', on_delete="CASCADE")
    estimated_count = fields.IntField(null=True)
    created = fields.DatetimeField(auto_now_add=True)
    last_verified = fields.DatetimeField(null=True)

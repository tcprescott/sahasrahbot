from tortoise import fields
from tortoise.models import Model


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
    voter_role_id = fields.BigIntField(null=True)
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

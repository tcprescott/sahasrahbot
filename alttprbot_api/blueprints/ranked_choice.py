import logging

import tortoise.exceptions
from discord.errors import NotFound
from quart import Blueprint, request, abort, jsonify
from alttprbot_api.oauth_client import requires_authorization

from alttprbot import models
from alttprbot.util import rankedchoice
from alttprbot_api.api import discord
from alttprbot_discord.bot import discordbot

# TODO: add a way to resubmit votes (low priority)
# TODO: client-side verification that ranked choices are unique
# TODO: the entire Discord-side of this need to be written
# TODO: deduplicate code between presentation and submission

ranked_choice_blueprint = Blueprint('ranked_choice', __name__)


@ranked_choice_blueprint.route('/ranked_choice/<int:election_id>/api', methods=['GET'])
@requires_authorization
async def get_ballot_json(election_id: int):
    user = await discord.fetch_user()

    try:
        election = await models.RankedChoiceElection.get(id=election_id)
    except tortoise.exceptions.DoesNotExist:
        return jsonify({'error': 'Election not found.'}), 404

    if not election.active:
        return jsonify({'error': 'Election is inactive.'}), 404

    if election.private:
        guild = await discordbot.fetch_guild(election.guild_id)
        voter_role = guild.get_role(election.voter_role_id)
        try:
            member = await guild.fetch_member(user.id)
        except NotFound:
            logging.exception(f"Unable to find user {user.id} in guild.")
            return jsonify({'error': 'Unable to find you in the server.'}), 403

        if voter_role not in member.roles:
            return jsonify({'error': 'You are not authorized to vote in this election.'}), 403

    await election.fetch_related('candidates')
    existing_votes = await election.votes.filter(user_id=user.id)

    return jsonify({
        'election': {
            'id': election.id,
            'name': election.title,
            'description': election.description,
            'candidates': [
                {'id': c.id, 'name': c.name}
                for c in election.candidates
            ],
        },
        'existing_votes': [
            {'candidate_id': v.candidate_id, 'rank': v.rank}
            for v in existing_votes
        ] if existing_votes else None,
        'already_voted': bool(existing_votes),
    })


@ranked_choice_blueprint.route('/ranked_choice/<int:election_id>/api', methods=['POST'])
@requires_authorization
async def submit_ballot_json(election_id: int):
    user = await discord.fetch_user()

    try:
        election = await models.RankedChoiceElection.get(id=election_id)
    except tortoise.exceptions.DoesNotExist:
        return jsonify({'error': 'Election not found.'}), 404

    if not election.active:
        return jsonify({'error': 'Election is inactive.'}), 404

    if election.private:
        guild = await discordbot.fetch_guild(election.guild_id)
        voter_role = guild.get_role(election.voter_role_id)
        try:
            member = await guild.fetch_member(user.id)
        except NotFound:
            return jsonify({'error': 'Unable to find you in the server.'}), 403
        if voter_role not in member.roles:
            return jsonify({'error': 'You are not authorized to vote in this election.'}), 403

    await election.fetch_related('candidates')
    existing_votes = await election.votes.filter(user_id=user.id)
    if existing_votes:
        return jsonify({'error': 'You have already voted in this election.'}), 403

    payload = await request.get_json(force=True) or {}
    # payload: {"votes": [{"candidate_id": 1, "rank": 1}, ...]}
    votes_data = payload.get('votes', [])

    ranks = [v['rank'] for v in votes_data if v.get('rank')]
    if len(ranks) != len(set(ranks)):
        return jsonify({'error': 'Each rank must be unique.'}), 400

    votes = []
    for vote in votes_data:
        if not vote.get('rank'):
            continue
        candidate = next((c for c in election.candidates if c.id == vote['candidate_id']), None)
        if not candidate:
            return jsonify({'error': f"Invalid candidate {vote['candidate_id']}"}), 400
        votes.append(models.RankedChoiceVotes(
            election=election, candidate=candidate, user_id=user.id, rank=vote['rank']
        ))

    votes.sort(key=lambda v: v.rank)
    await models.RankedChoiceVotes.bulk_create(votes)
    await rankedchoice.refresh_election_post(election, discordbot)

    return jsonify({'success': True})

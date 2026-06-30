import logging

from discord.errors import NotFound
from quart import Blueprint, request, jsonify
from alttprbot.presentation.web.oauth_client import requires_authorization

from alttprbot.services import AuthorizationService, AuthSubject, RankedChoiceService
from alttprbot.presentation.discord.util import ranked_choice as ranked_choice_embeds
from alttprbot.presentation.web.web import discord
from alttprbot.presentation.discord.bot import discordbot

# TODO: add a way to resubmit votes (low priority)
# TODO: client-side verification that ranked choices are unique
# TODO: the entire Discord-side of this need to be written
# TODO: deduplicate code between presentation and submission

ranked_choice_blueprint = Blueprint('ranked_choice', __name__)


async def _voter_role_denial(election, user_id):
    """Return an error response tuple if the user may not vote, else None.

    Discord membership/role resolution stays in the presentation layer; the
    voter-role decision is made by AuthorizationService.
    """
    if not election.private:
        return None

    guild = await discordbot.fetch_guild(election.guild_id)
    try:
        member = await guild.fetch_member(user_id)
    except NotFound:
        logging.exception(f"Unable to find user {user_id} in guild.")
        return jsonify({'error': 'Unable to find you in the server.'}), 403

    subject = AuthSubject(
        discord_user_id=user_id,
        discord_role_ids=frozenset(role.id for role in member.roles),
    )
    if not AuthorizationService().can_vote_ranked_choice(subject, election):
        return jsonify({'error': 'You are not authorized to vote in this election.'}), 403
    return None


@ranked_choice_blueprint.route('/ranked_choice/<int:election_id>/api', methods=['GET'])
@requires_authorization
async def get_ballot_json(election_id: int):
    user = await discord.fetch_user()
    service = RankedChoiceService()

    election = await service.get_election_with_candidates(election_id)
    if election is None:
        return jsonify({'error': 'Election not found.'}), 404
    if not election.active:
        return jsonify({'error': 'Election is inactive.'}), 404

    denial = await _voter_role_denial(election, user.id)
    if denial is not None:
        return denial

    existing_votes = await service.get_user_votes(election, user.id)

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
    service = RankedChoiceService()

    election = await service.get_election_with_candidates(election_id)
    if election is None:
        return jsonify({'error': 'Election not found.'}), 404
    if not election.active:
        return jsonify({'error': 'Election is inactive.'}), 404

    denial = await _voter_role_denial(election, user.id)
    if denial is not None:
        return denial

    if await service.get_user_votes(election, user.id):
        return jsonify({'error': 'You have already voted in this election.'}), 403

    payload = await request.get_json(force=True) or {}
    # payload: {"votes": [{"candidate_id": 1, "rank": 1}, ...]}
    votes_data = payload.get('votes', [])

    try:
        await service.submit_ballot(election, user.id, votes_data)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    await ranked_choice_embeds.refresh_election_post(election, discordbot)

    return jsonify({'success': True})

from quart import Blueprint, jsonify, render_template, request, url_for, abort
from quart_discord import requires_authorization

from alttprbot import models
from alttprbot.tournaments import TOURNAMENT_DATA, fetch_tournament_handler

from alttprbot_api.api import discord

tournament_blueprint = Blueprint('tournament', __name__)


@tournament_blueprint.route('/api/tournament/games', methods=['GET'])
async def get_tournament_games():
    terms = request.args
    data = await models.TournamentGames.filter(**terms).values()
    return jsonify(data)


@tournament_blueprint.route("/submit/<string:event>", methods=['GET'])
@requires_authorization
async def submission_form(event):
    user = await discord.fetch_user()
    episode_id = request.args.get("episode_id", "")

    event_config = await TOURNAMENT_DATA[event].get_config()
    form_data = event_config.submission_form
    if form_data is None:
        raise Exception("There is no form submission data for this event.")

    if isinstance(form_data, str):
        return await render_template(
            form_data,
            logged_in=True,
            user=user,
            event=event,
            endpoint=url_for("tournament.submit"),
            episode_id=episode_id
        )
    else:
        return await render_template(
            'submission.html',
            logged_in=True,
            user=user,
            event=event,
            endpoint=url_for("tournament.submit"),
            settings_list=form_data,
            episode_id=episode_id
        )


@tournament_blueprint.route("/submit", methods=['POST'])
@requires_authorization
async def submit():
    user = await discord.fetch_user()
    payload = await request.form
    try:
        tournament_race = await fetch_tournament_handler(payload['event'], int(payload['episodeid']))
        await tournament_race.process_submission_form(payload, submitted_by=f"{user.name}#{user.discriminator}")
        return await render_template(
            "submission_done.html",
            logged_in=True,
            user=user,
            tournament_race=tournament_race
        )
    except Exception as e:
        abort(400, description=f"Error processing submission: {e}")

import re

from quart import Blueprint, render_template, request, url_for, redirect, session, abort
from quart_discord import requires_authorization, Unauthorized

from alttprbot import models
from alttprbot_api.api import discord

schedule_blueprint = Blueprint('schedule', __name__)

@schedule_blueprint.route("/<string:slug>")
async def schedule(slug):
    try:
        user = await discord.fetch_user()
        logged_in = True
    except Unauthorized:
        user = None
        logged_in = False

    event = await models.ScheduleEvent.get_or_none(event_slug=slug)
    if event is None:
        return abort(404)

    await event.fetch_related('episodes', 'episodes__channel', 'episodes__players') # TODO: add filters and pagination

    return await render_template('schedule/main.html', logged_in=logged_in, user=user, event=event)

@schedule_blueprint.route("/<string:slug>/<int:episode_id>")
async def schedule_episode(slug, episode_id):
    try:
        user = await discord.fetch_user()
        logged_in = True
    except Unauthorized:
        user = None
        logged_in = False

    event = await models.ScheduleEvent.get_or_none(event_slug=slug)
    if event is None:
        return abort(404)

    episode = await models.ScheduleEpisode.get_or_none(id=episode_id, event__event_slug=slug)
    if episode is None:
        return abort(404)

    await episode.fetch_related('players', 'commentators', 'trackers', 'restreamers')

    return await render_template('schedule/episode.html', logged_in=logged_in, user=user, event=event, episode=episode)

@schedule_blueprint.route("/<string:slug>/submit")
@requires_authorization
async def schedule_submit(slug):
    user = await discord.fetch_user()
    event = await models.ScheduleEvent.get_or_none(event_slug=slug)
    if event is None:
        return abort(404)

    return await render_template('schedule/submit.html', user=user, event=event)

@schedule_blueprint.route("/<string:slug>/submit", methods=['POST'])
@requires_authorization
async def schedule_submit_post(slug):
    user = await discord.fetch_user()
    event = await models.ScheduleEvent.get_or_none(event_slug=slug)
    if event is None:
        return abort(404)

    episode = await models.ScheduleEpisode.create(
        event=event,
        runner_notes=request.form.get('runner_notes', None),
        private_notes=request.form.get('private_notes', None),
        when_countdown=request.form.get('when_countdown', None)
    )
    await models.ScheduleEpisodePlayer.create(
        episode=episode,
        user=user
    )
    await models.ScheduleEpisodePlayer.create(
        episode=episode,
        user=user
    )

    return redirect(url_for('schedule.schedule_episode', slug=slug, episode_id=episode.id))

@schedule_blueprint.route("/<string:slug>/<int:episode_id>/signup")
@requires_authorization
async def schedule_episode_signup(slug, episode_id):
    pass

@schedule_blueprint.route("/<string:slug>/<int:episode_id>/signup", methods=['POST'])
@requires_authorization
async def schedule_episode_signup_post(slug, episode_id):
    pass


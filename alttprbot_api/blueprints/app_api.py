"""The JSON API the React app in ``web/`` uses: ``/api/v1/...``.

Routes are thin: they find out who's signed in (the Discord OAuth session cookie),
call a service in ``alttprbot/services/``, and return a model from ``schemas.py``.
Services raise ``NotFoundError`` / ``PermissionDeniedError`` / ``InvalidInputError``,
which ``api.py`` turns into 404 / 403 / 400 with ``{"error": "..."}``.

Requests that change something must carry ``X-Requested-With: SahasrahBot``. A
cross-site form can't set that header, which keeps the session cookie from being
used against the user (CSRF).
"""

from quart import Blueprint, abort, request
from quart_discord import Unauthorized
from quart_schema import tag, validate_querystring, validate_request, validate_response

from alttprbot.services import accounts, presets, ranked_choice, tournament_submissions, triforce_texts
from alttprbot_api import schemas
from alttprbot_api.api import discord

app_api_blueprint = Blueprint('app_api', __name__, url_prefix='/api/v1')

CSRF_HEADER = 'X-Requested-With'
CSRF_VALUE = 'SahasrahBot'


@app_api_blueprint.before_request
async def require_csrf_header():
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and request.headers.get(CSRF_HEADER) != CSRF_VALUE:
        abort(403, description=f"Missing the {CSRF_HEADER} header.")


async def signed_in_user():
    """The signed-in Discord user, or None."""
    if not await discord.authorized:
        return None
    try:
        return await discord.fetch_user()
    except Unauthorized:
        return None


async def require_user():
    user = await signed_in_user()
    if user is None:
        raise Unauthorized()
    return user


def _session_user(user) -> schemas.SessionUser:
    return schemas.SessionUser(id=str(user.id), name=user.name, avatar_url=getattr(user, 'avatar_url', None) or None)


def _author(user) -> str:
    return f"{user.name}#{user.discriminator}"


# --- Session and profile -----------------------------------------------------


@app_api_blueprint.get('/session')
@tag(['session'])
@validate_response(schemas.SessionInfo)
async def get_session():
    """Who is signed in. Never 401: ``user`` is null when nobody is."""
    user = await signed_in_user()
    return schemas.SessionInfo(user=_session_user(user) if user else None)


@app_api_blueprint.get('/me')
@tag(['session'])
@validate_response(schemas.Profile)
async def get_me():
    user = await require_user()
    return schemas.Profile(user=_session_user(user), **await accounts.profile(user.id))


@app_api_blueprint.post('/me/purge')
@tag(['session'])
async def purge_me():
    """Delete what SahasrahBot keeps about the user, then sign them out."""
    user = await require_user()
    await accounts.purge(user.id)
    discord.revoke()
    return '', 204


# --- Presets -----------------------------------------------------------------


@app_api_blueprint.get('/presets/randomizers')
@tag(['presets'])
@validate_response(schemas.Randomizers)
async def get_randomizers():
    return schemas.Randomizers(randomizers=presets.randomizers())


@app_api_blueprint.get('/presets/namespaces')
@tag(['presets'])
@validate_response(schemas.NamespaceList)
async def list_namespaces():
    return schemas.NamespaceList(namespaces=await presets.list_namespaces())


@app_api_blueprint.get('/presets/mine')
@tag(['presets'])
@validate_response(schemas.MyNamespace)
async def my_namespace():
    """The signed-in user's namespace, created on first use."""
    user = await require_user()
    return schemas.MyNamespace(namespace=await presets.my_namespace(user.id, user.name))


@app_api_blueprint.get('/presets/namespaces/<namespace>')
@tag(['presets'])
@validate_response(schemas.Namespace)
async def get_namespace(namespace: str):
    user = await signed_in_user()
    return schemas.Namespace(**await presets.get_namespace(namespace, presets.Viewer(user.id if user else None)))


@app_api_blueprint.get('/presets/namespaces/<namespace>/<randomizer>/<preset>')
@tag(['presets'])
@validate_response(schemas.Preset)
async def get_preset(namespace: str, randomizer: str, preset: str):
    user = await signed_in_user()
    viewer = presets.Viewer(user.id if user else None)
    return schemas.Preset(**await presets.get_preset(namespace, randomizer, preset, viewer))


@app_api_blueprint.put('/presets/namespaces/<namespace>/<randomizer>/<preset>')
@tag(['presets'])
@validate_request(schemas.PresetContent)
@validate_response(schemas.Preset)
async def save_preset(namespace: str, randomizer: str, preset: str, data: schemas.PresetContent):
    """Create the preset, or replace its YAML."""
    user = await require_user()
    saved = await presets.save_preset(namespace, randomizer, preset, data.content, presets.Viewer(user.id))
    return schemas.Preset(**saved)


@app_api_blueprint.delete('/presets/namespaces/<namespace>/<randomizer>/<preset>')
@tag(['presets'])
async def delete_preset(namespace: str, randomizer: str, preset: str):
    user = await require_user()
    await presets.delete_preset(namespace, randomizer, preset, presets.Viewer(user.id))
    return '', 204


# --- Ranked-choice voting ----------------------------------------------------


@app_api_blueprint.get('/ranked-choice/<int:election_id>')
@tag(['ranked choice'])
@validate_response(schemas.Election)
async def get_election(election_id: int):
    user = await require_user()
    return schemas.Election(**await ranked_choice.get_ballot(election_id, user.id))


@app_api_blueprint.post('/ranked-choice/<int:election_id>/ballot')
@tag(['ranked choice'])
@validate_request(schemas.BallotIn)
@validate_response(schemas.Election)
async def cast_ballot(election_id: int, data: schemas.BallotIn):
    user = await require_user()
    return schemas.Election(**await ranked_choice.cast_ballot(election_id, user.id, data.ranking))


# --- Triforce texts ----------------------------------------------------------


@app_api_blueprint.get('/triforce-texts/<string:pool>')
@tag(['triforce texts'])
@validate_response(schemas.TriforcePool)
async def get_triforce_pool(pool: str):
    user = await require_user()
    return schemas.TriforcePool(**await triforce_texts.pool(pool, user.id))


@app_api_blueprint.post('/triforce-texts/<string:pool>/submissions')
@tag(['triforce texts'])
@validate_request(schemas.TriforceTextIn)
@validate_response(schemas.TriforceText, 201)
async def submit_triforce_text(pool: str, data: schemas.TriforceTextIn):
    user = await require_user()
    return schemas.TriforceText(**await triforce_texts.submit(pool, user.id, _author(user), data.lines)), 201


@app_api_blueprint.get('/triforce-texts/<string:pool>/moderation')
@tag(['triforce texts'])
@validate_querystring(schemas.ModerationQuery)
@validate_response(schemas.TriforceModerationList)
async def list_triforce_moderation(pool: str, query_args: schemas.ModerationQuery):
    user = await require_user()
    texts = await triforce_texts.list_for_moderation(pool, user.id, query_args.status)
    return schemas.TriforceModerationList(pool=pool, status=query_args.status, texts=texts)


@app_api_blueprint.post('/triforce-texts/<string:pool>/moderation/<int:text_id>')
@tag(['triforce texts'])
@validate_request(schemas.ModerationIn)
@validate_response(schemas.TriforceText)
async def moderate_triforce_text(pool: str, text_id: int, data: schemas.ModerationIn):
    user = await require_user()
    return schemas.TriforceText(**await triforce_texts.moderate(pool, text_id, user.id, data.approved))


# --- Tournament settings submission -----------------------------------------


@app_api_blueprint.get('/tournaments/<event>/submission-form')
@tag(['tournaments'])
@validate_response(schemas.SubmissionForm)
async def get_submission_form(event: str):
    await require_user()
    return schemas.SubmissionForm(**await tournament_submissions.get_form(event))


@app_api_blueprint.post('/tournaments/<event>/submissions')
@tag(['tournaments'])
@validate_request(schemas.SubmissionIn)
@validate_response(schemas.SubmissionDone)
async def submit_settings(event: str, data: schemas.SubmissionIn):
    user = await require_user()
    done = await tournament_submissions.submit(event, data.episode_id, data.settings, _author(user))
    return schemas.SubmissionDone(**done)

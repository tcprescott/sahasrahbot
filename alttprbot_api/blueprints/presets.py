import re
from io import BytesIO

from quart import Blueprint, redirect, render_template, request, send_file, url_for, jsonify
from quart_discord import Unauthorized, requires_authorization
from tortoise.query_utils import Prefetch

from alttprbot import models
from alttprbot.alttprgen import generator
from alttprbot_api.api import discord

presets_blueprint = Blueprint('presets', __name__)


@presets_blueprint.route('/presets', methods=['GET'])
async def all_presets():
    try:
        user = await discord.fetch_user()
        logged_in = True
    except Unauthorized:
        user = None
        logged_in = False

    namespaces = await models.PresetNamespaces.all()

    return await render_template('preset_namespaces_all.html', logged_in=logged_in, user=user, namespaces=namespaces)


@presets_blueprint.route('/presets/me', methods=['GET'])
@requires_authorization
async def my_presets():
    user = await discord.fetch_user()
    ns_current_user = await generator.create_or_retrieve_namespace(user.id, user.name)

    return redirect(url_for('presets.presets_for_namespace', namespace=ns_current_user.name))


@presets_blueprint.route('/presets/<string:namespace>/create', methods=['GET'])
@requires_authorization
async def new_preset(namespace):
    user = await discord.fetch_user()
    ns_current_user = await generator.create_or_retrieve_namespace(user.id, user.name)
    ns_data = await models.PresetNamespaces.get(name=namespace)
    await ns_data.fetch_related('collaborators')

    if not generator.is_namespace_owner(user, ns_data):
        return await render_template('error.html', logged_in=True, user=user, title="Unauthorized",
                                     message="You are not authorized to create presets in this namespace.")

    return await render_template('preset_new.html', logged_in=True, user=user, ns_data=ns_data,
                                 ns_current_user=ns_current_user, randomizers=generator.PRESET_CLASS_MAPPING.keys())


@presets_blueprint.route('/presets/<string:namespace>/create', methods=['POST'])
@requires_authorization
async def new_preset_submit(namespace):
    user = await discord.fetch_user()
    payload = await request.form
    request_files = await request.files
    ns_data = await models.PresetNamespaces.get(name=namespace)
    await ns_data.fetch_related('collaborators')

    if not generator.is_namespace_owner(user, ns_data):
        return await render_template('error.html', logged_in=True, user=user, title="Unauthorized",
                                     message="You are not authorized to create presets in this namespace.")

    if not re.match("^[a-zA-Z0-9_]*$", payload['preset_name']):
        return await render_template('error.html', logged_in=True, user=user, title="Unauthorized",
                                     message="Invalid preset name provided.")

    preset_data, _ = await models.Presets.update_or_create(
        preset_name=payload['preset_name'],
        randomizer=payload['randomizer'],
        namespace=ns_data,
        defaults={
            'content': request_files['presetfile'].read().decode()
        }
    )

    return redirect(
        url_for('presets.presets_for_namespace_randomizer', namespace=ns_data.name, preset=preset_data.preset_name,
                randomizer=preset_data.randomizer))


@presets_blueprint.route('/presets/manage/<string:namespace>', methods=['GET'])
# @requires_authorization
async def presets_for_namespace(namespace):
    ns_data = await models.PresetNamespaces.get(name=namespace)
    await ns_data.fetch_related('collaborators')

    try:
        user = await discord.fetch_user()
        logged_in = True
        is_owner = generator.is_namespace_owner(user, ns_data)
    except Unauthorized:
        user = None
        logged_in = False
        is_owner = False

    presets = await models.Presets.filter(namespace__name=namespace)

    return await render_template('preset_namespace.html', logged_in=logged_in, user=user, is_owner=is_owner,
                                 ns_data=ns_data, presets=presets)


@presets_blueprint.route('/presets/manage/<string:namespace>/<string:randomizer>', methods=['GET'])
# @requires_authorization
async def presets_for_namespace_randomizer(namespace, randomizer):
    ns_data = await models.PresetNamespaces.get(name=namespace)
    await ns_data.fetch_related('collaborators')

    try:
        user = await discord.fetch_user()
        logged_in = True
        is_owner = generator.is_namespace_owner(user, ns_data)
    except Unauthorized:
        user = None
        logged_in = False
        is_owner = False

    presets = await models.Presets.filter(randomizer=randomizer, namespace__name=namespace).only('id', 'preset_name',
                                                                                                 'randomizer')

    return await render_template('preset_namespace.html', logged_in=logged_in, user=user, is_owner=is_owner,
                                 ns_data=ns_data, presets=presets)


@presets_blueprint.route('/presets/manage/<string:namespace>/<string:randomizer>/<string:preset>', methods=['GET'])
async def get_preset(namespace, randomizer, preset):
    ns_data = await models.PresetNamespaces.get(name=namespace)
    await ns_data.fetch_related('collaborators')

    try:
        user = await discord.fetch_user()
        logged_in = True
        is_owner = generator.is_namespace_owner(user, ns_data)
    except Unauthorized:
        user = None
        logged_in = False
        is_owner = False

    preset_data = await models.Presets.get(preset_name=preset, randomizer=randomizer, namespace__name=namespace)

    return await render_template('preset_view.html', logged_in=logged_in, user=user, is_owner=is_owner, ns_data=ns_data,
                                 preset_data=preset_data)


@presets_blueprint.route('/presets/download/<string:namespace>/<string:randomizer>/<string:preset>', methods=['GET'])
async def download_preset(namespace, randomizer, preset):
    preset_data = await models.Presets.get(preset_name=preset, randomizer=randomizer, namespace__name=namespace)

    return await send_file(
        BytesIO(preset_data.content.encode()),
        mimetype="application/octet-stream",
        attachment_filename=f"{namespace}-{preset}.yaml",
        as_attachment=True
    )


@presets_blueprint.route('/presets/manage/<string:namespace>/<string:randomizer>/<string:preset>', methods=['POST'])
@requires_authorization
async def update_preset(namespace, randomizer, preset):
    user = await discord.fetch_user()
    payload = await request.form
    request_files = await request.files
    ns_data = await models.PresetNamespaces.get(name=namespace)
    await ns_data.fetch_related('collaborators')

    is_owner = generator.is_namespace_owner(user, ns_data)

    if not is_owner:
        return await render_template('error.html', logged_in=True, user=user, title="Unauthorized",
                                     message="You are not the owner of this preset.")

    preset_data = await models.Presets.get(preset_name=preset, randomizer=randomizer, namespace__name=namespace)

    if 'delete' in payload:
        await preset_data.delete()
        return redirect(url_for('presets.presets_for_namespace', namespace=namespace))

    preset_data.content = request_files['presetfile'].read().decode()

    if preset_data.content == '':
        return await render_template('error.html', logged_in=True, user=user, title="Oops!",
                                     message="Empty or missing preset file provided.")
    await preset_data.save()

    return redirect(url_for('presets.get_preset', namespace=namespace, randomizer=randomizer, preset=preset))


# @presets_blueprint.route('/presets/<str:namespace>', methods=['POST'])
# @requires_authorization
# async def update_namespace():
#     user = await discord.fetch_user()
#     namespace = await generator.create_or_retrieve_namespace(user.id, user.name)

@presets_blueprint.route('/presets/api/<string:randomizer>/list', methods=['GET'])
async def api_get_presets(randomizer):
    # this is terrible
    generators = {
        'alttpr': generator.ALTTPRPreset,
        'smz3': generator.SMZ3Preset,
        'sm': generator.SMPreset,
        'alttprmystery': generator.ALTTPRMystery,
        'ctjets': generator.CTJetsPreset
    }
    global_presets = await generators[randomizer]().get_presets(namespace=None)
    namespaces = await models.PresetNamespaces.all().prefetch_related(
        Prefetch('presets', queryset=models.Presets.filter(randomizer=randomizer)))

    output = {
        'global': global_presets,
        'namespaces': [
            {
                'name': namespace.name,
                'presets': [
                    n.preset_name for n in namespace.presets
                ]
            } for namespace in namespaces
            if namespace.presets
        ]
    }

    return jsonify(output)


@presets_blueprint.route('/presets/api/<string:randomizer>', methods=['GET'])
async def api_get_preset(randomizer):
    # this is terrible
    preset = request.args.get('preset')
    generators = {
        'alttpr': generator.ALTTPRPreset,
        'smz3': generator.SMZ3Preset,
        'sm': generator.SMPreset,
        'alttprmystery': generator.ALTTPRMystery,
        'ctjets': generator.CTJetsPreset
    }
    try:
        resp = generators[randomizer](preset=preset)
        await resp.fetch()
        return jsonify(
            {
                'preset': preset,
                'randomizer': randomizer,
                'data': resp.raw
            }
        )
    except generator.PresetNotFoundException:
        return jsonify(
            {}
        )

"""Preset namespaces: each Discord user's own folder of uploaded preset YAML files.

A namespace belongs to one Discord user (``discord_user_id``); its collaborators can
edit it too (``generator.is_namespace_owner``). Presets in a namespace are rolled in
Discord as ``<namespace>/<preset>``.
"""

import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Optional

import aiofiles
import yaml
from tortoise.functions import Count
from tortoise.query_utils import Prefetch

from alttprbot import models
from alttprbot.alttprgen import generator
from alttprbot.exceptions import InvalidInputError, NotFoundError, PermissionDeniedError
from alttprbot.services import audit

PRESET_NAME = re.compile(r"^\w+$", re.ASCII)
MAX_PRESET_NAME = 50


@dataclass(frozen=True)
class Viewer:
    """Who is looking: a Discord user id, or nobody signed in."""
    id: Optional[int]


def randomizers() -> list[str]:
    return list(generator.PRESET_CLASS_MAPPING.keys())


MAX_HINT_VALUES = 12
MAX_HINT_DISTINCT_VALUES = 100
_key_hints: dict[str, list[dict]] = {}


async def key_hints(randomizer: str) -> list[dict]:
    """The keys and values the presets that ship with SahasrahBot use, for the editor's autocomplete.

    One entry per key under each parent path (``[]`` is the top level, ``["settings"]``
    is under ``settings:``), with how many shipped presets use it and its most common
    scalar values written as YAML. Items of a list count as values of the list's key,
    and mappings inside a list share that key's path. Keys only one preset uses are left
    out when there are several presets, and so are free text values (descriptions, names),
    so the list stays small. Read once per randomizer, then cached.
    """
    if randomizer not in generator.PRESET_CLASS_MAPPING:
        raise NotFoundError(f"There's no randomizer called {randomizer}.")
    if randomizer not in _key_hints:
        _key_hints[randomizer] = await _read_key_hints(os.path.join("presets", randomizer))
    return _key_hints[randomizer]


async def _read_key_hints(folder: str) -> list[dict]:
    uses: Counter = Counter()
    values: dict[tuple, Counter] = defaultdict(Counter)
    names = sorted(f for f in os.listdir(folder) if f.endswith(".yaml")) if os.path.isdir(folder) else []
    for name in names:
        async with aiofiles.open(os.path.join(folder, name), encoding="utf-8") as f:
            try:
                data = yaml.safe_load(await f.read())
            except yaml.YAMLError:
                continue
        seen: set[tuple] = set()
        _walk(data, (), None, seen, values)
        uses.update(seen)
    least = 2 if len(names) > 2 else 1
    return [
        {
            "path": list(path),
            "key": key,
            "count": count,
            "values": _common_values(values[(path, key)]),
        }
        for (path, key), count in sorted(uses.items(), key=lambda item: (item[0][0], -item[1], item[0][1]))
        if count >= least
    ]


def _common_values(seen: Counter) -> list[str]:
    if len(seen) > MAX_HINT_DISTINCT_VALUES:
        return []
    return [v for v, _ in seen.most_common(MAX_HINT_VALUES) if " " not in v]


def _walk(node, path: tuple, key: Optional[str], seen: set, values: dict) -> None:
    if isinstance(node, dict):
        inner = path if key is None else path + (key,)
        for k, v in node.items():
            k = str(k)
            seen.add((inner, k))
            _walk(v, inner, k, seen, values)
    elif isinstance(node, list):
        for item in node:
            _walk(item, path, key, seen, values)
    elif key is not None and node is not None:
        values[(path, key)][_yaml_scalar(node)] += 1


def _yaml_scalar(value) -> str:
    """A scalar as it would be written in YAML: quoted only when it has to be."""
    return yaml.safe_dump(value, default_flow_style=True, width=1000).strip().removesuffix("...").strip()


async def list_namespaces() -> list[dict]:
    rows = await models.PresetNamespaces.all().annotate(preset_count=Count('presets')).order_by('name')
    return [{'name': ns.name, 'preset_count': ns.preset_count} for ns in rows]


async def _namespace(name: str) -> models.PresetNamespaces:
    namespace = await models.PresetNamespaces.get_or_none(name=name)
    if namespace is None:
        raise NotFoundError(f"There's no preset namespace called {name}.")
    await namespace.fetch_related('collaborators')
    return namespace


def _can_edit(viewer: Viewer, namespace: models.PresetNamespaces) -> bool:
    return viewer.id is not None and generator.is_namespace_owner(viewer, namespace)


async def get_namespace(name: str, viewer: Viewer) -> dict:
    namespace = await _namespace(name)
    presets = await models.Presets.filter(namespace=namespace).order_by('randomizer', 'preset_name')
    return {
        'name': namespace.name,
        'can_edit': _can_edit(viewer, namespace),
        'presets': [_summary(namespace, p) for p in presets],
    }


async def my_namespace(discord_user_id: int, discord_user_name: str) -> str:
    """The signed-in user's namespace, created on first visit."""
    namespace = await generator.create_or_retrieve_namespace(discord_user_id, discord_user_name)
    return namespace.name


async def get_preset(namespace_name: str, randomizer: str, preset_name: str, viewer: Viewer) -> dict:
    namespace = await _namespace(namespace_name)
    preset = await models.Presets.get_or_none(namespace=namespace, randomizer=randomizer, preset_name=preset_name)
    if preset is None:
        raise NotFoundError(f"{namespace_name}/{preset_name} doesn't exist for {randomizer}.")
    return {**_summary(namespace, preset), 'content': preset.content, 'can_edit': _can_edit(viewer, namespace)}


async def save_preset(namespace_name: str, randomizer: str, preset_name: str, content: str, viewer: Viewer) -> dict:
    """Create the preset, or replace its YAML if it already exists."""
    namespace = await _namespace(namespace_name)
    if not _can_edit(viewer, namespace):
        raise PermissionDeniedError("You can't change presets in this namespace.")
    if randomizer not in generator.PRESET_CLASS_MAPPING:
        raise InvalidInputError(f"{randomizer} isn't a randomizer SahasrahBot knows.")
    if not PRESET_NAME.match(preset_name) or len(preset_name) > MAX_PRESET_NAME:
        raise InvalidInputError("Preset names can only use letters, numbers and underscores (up to 50).")
    if not content.strip():
        raise InvalidInputError("The preset file is empty.")
    try:
        parsed = yaml.safe_load(content)
    except yaml.YAMLError as err:
        raise InvalidInputError(f"That isn't valid YAML: {generator.yaml_problem(err)}.") from err
    if not isinstance(parsed, dict):
        raise InvalidInputError("A preset file must be a YAML mapping of settings, like \"settings:\" followed by its options.")

    existing = await models.Presets.get_or_none(namespace=namespace, randomizer=randomizer, preset_name=preset_name)
    preset, created = await models.Presets.update_or_create(
        namespace=namespace, randomizer=randomizer, preset_name=preset_name,
        defaults={'content': content},
    )
    if created or existing is None or existing.content != content:
        await audit.record(audit.PRESET_CREATED if created else audit.PRESET_UPDATED,
                           target=f"{namespace.name}/{preset_name}",
                           details={'randomizer': randomizer, 'namespace': namespace.name, 'preset': preset_name})
    return {**_summary(namespace, preset), 'content': preset.content, 'can_edit': True}


async def delete_preset(namespace_name: str, randomizer: str, preset_name: str, viewer: Viewer) -> None:
    namespace = await _namespace(namespace_name)
    if not _can_edit(viewer, namespace):
        raise PermissionDeniedError("You can't change presets in this namespace.")
    deleted = await models.Presets.filter(
        namespace=namespace, randomizer=randomizer, preset_name=preset_name).delete()
    if not deleted:
        raise NotFoundError(f"{namespace_name}/{preset_name} doesn't exist for {randomizer}.")
    await audit.record(audit.PRESET_DELETED, target=f"{namespace.name}/{preset_name}",
                       details={'randomizer': randomizer, 'namespace': namespace.name, 'preset': preset_name})


def _summary(namespace: models.PresetNamespaces, preset: models.Presets) -> dict:
    return {
        'namespace': namespace.name,
        'randomizer': preset.randomizer,
        'name': preset.preset_name,
        'modified': preset.modified,
        'generated_count': preset.generated_count,
    }


# --- public downloads and JSON (alttprbot_api/blueprints/presets.py) -----------


async def preset_content(namespace_name: str, randomizer: str, preset_name: str) -> Optional[str]:
    """The YAML of a namespaced preset, or None if there's no such preset."""
    preset = await models.Presets.get_or_none(preset_name=preset_name, randomizer=randomizer,
                                              namespace__name=namespace_name)
    return preset.content if preset else None


async def namespace_preset_names(randomizer: str) -> list[dict]:
    """``[{'name': namespace, 'presets': [preset names]}]`` for every namespace that has
    at least one preset for this randomizer."""
    namespaces = await models.PresetNamespaces.all().prefetch_related(
        Prefetch('presets', queryset=models.Presets.filter(randomizer=randomizer)))
    return [
        {'name': namespace.name, 'presets': [p.preset_name for p in namespace.presets]}
        for namespace in namespaces
        if namespace.presets
    ]

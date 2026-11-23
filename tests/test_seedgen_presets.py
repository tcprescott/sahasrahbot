"""Characterization tests for preset loading and seed generation (alttprbot/alttprgen).

No randomizer API is called: ALTTPRDiscord, AlttprDoorDiscord, AVIANARTDiscord,
SMDiscord/SMZ3Discord and ctjets are replaced with fakes that record what they
were asked to generate. The tests pin which settings and endpoint each preset
path sends, and that every shipped preset file still loads and goes through
generation without errors.
"""

import os
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest
import yaml

import config
from alttprbot import models
from alttprbot.alttprgen import generator, preset

ROOT = Path(__file__).resolve().parent.parent
PRESETS = ROOT / "presets"


def preset_names(randomizer):
    return sorted(p.stem for p in (PRESETS / randomizer).glob("*.yaml"))


def fake_seed(**extra):
    return SimpleNamespace(
        url="https://alttpr.test/h/abc123",
        hash="abc123",
        hash_id="abc123",
        slug_id="slug123",
        code=["Bow", "Boomerang", "Hookshot", "Bombs", "Mushroom"],
        data={"guid": "guid-1"},
        baseurl="https://sm.samus.link",
        **extra,
    )


@pytest.fixture
def randomizers(monkeypatch):
    """Replace every randomizer client with an AsyncMock returning a fake seed."""
    fakes = SimpleNamespace(
        alttpr=mock.AsyncMock(return_value=fake_seed()),
        doors=mock.AsyncMock(return_value=fake_seed()),
        avianart=mock.AsyncMock(return_value=fake_seed()),
        sm=mock.AsyncMock(return_value=fake_seed()),
        smz3=mock.AsyncMock(return_value=fake_seed()),
        ctjets=mock.AsyncMock(return_value="https://ctjets.test/seed/1"),
    )
    monkeypatch.setattr(generator.ALTTPRDiscord, "generate", fakes.alttpr)
    monkeypatch.setattr(generator.AlttprDoorDiscord, "create", fakes.doors)
    monkeypatch.setattr(generator.AVIANARTDiscord, "create", fakes.avianart)
    monkeypatch.setattr(generator.SMDiscord, "create", fakes.sm)
    monkeypatch.setattr(generator.SMZ3Discord, "create", fakes.smz3)
    monkeypatch.setattr(generator.ctjets, "roll_ctjets", fakes.ctjets)
    return fakes


# ---------------------------------------------------------------------------
# Shipped preset files
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("randomizer", ["alttpr", "alttprmystery", "sm", "smz3", "ctjets"])
def test_preset_directory_is_not_empty(randomizer):
    assert preset_names(randomizer)


@pytest.mark.parametrize(
    "path",
    sorted(p for p in PRESETS.rglob("*.y*ml")),
    ids=lambda p: str(p.relative_to(PRESETS)),
)
def test_every_preset_file_is_valid_yaml_mapping(path):
    data = yaml.safe_load(path.read_text())
    assert isinstance(data, dict)
    if path.parent.name != "alttprmystery":
        assert isinstance(data.get("settings"), dict), "non-mystery presets need a settings mapping"


@pytest.mark.parametrize("name", preset_names("sm") + preset_names("smz3") + preset_names("ctjets"))
def test_non_alttpr_presets_declare_matching_randomizer(name):
    for randomizer in ("sm", "smz3", "ctjets"):
        path = PRESETS / randomizer / f"{name}.yaml"
        if path.exists():
            assert yaml.safe_load(path.read_text()).get("randomizer") == randomizer


def test_known_issue_yml_extension_presets_are_unreachable():
    """KNOWN ISSUE, pinned not endorsed: presets are looked up as ``<name>.yaml``
    only, so ``presets/alttpr/enemizer_chaos.yml`` can never be used."""
    assert (PRESETS / "alttpr" / "enemizer_chaos.yml").exists()
    assert "enemizer_chaos" not in preset_names("alttpr")


# ---------------------------------------------------------------------------
# SahasrahBotPresetCore: naming, listing, fetching, saving
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, namespace, name",
    [
        ("open", None, "open"),
        ("Open", None, "Open"),  # global names keep their case
        ("Synack/MyPreset", "synack", "mypreset"),  # namespaced names are lower-cased
        (None, None, None),
    ],
)
def test_preset_name_parsing(raw, namespace, name):
    p = generator.ALTTPRPreset(raw)
    assert (p.namespace, p.preset) == (namespace, name)


def test_global_preset_paths():
    assert generator.ALTTPRPreset().global_preset_path == os.path.join("presets", "alttpr")
    assert generator.SMZ3Preset().global_preset_path == os.path.join("presets", "smz3")
    assert generator.ALTTPRMystery().global_preset_path == "presets/alttprmystery"


def test_preset_class_mapping():
    assert generator.PRESET_CLASS_MAPPING == {
        "alttpr": generator.ALTTPRPreset,
        "alttprmystery": generator.ALTTPRMystery,
        "ctjets": generator.CTJetsPreset,
        "smz3": generator.SMZ3Preset,
        "sm": generator.SMPreset,
    }


async def test_get_presets_lists_global_yaml_files():
    names = await generator.ALTTPRPreset().get_presets()
    assert sorted(names) == preset_names("alttpr")


async def test_search_is_prefix_match_sorted_and_capped_at_25():
    results = await generator.ALTTPRPreset().search("CROSS")
    assert results == sorted(results)
    assert results and all(r.startswith("cross") for r in results)
    assert len(await generator.ALTTPRPreset().search("")) == 25


async def test_fetch_global_preset():
    data = await generator.ALTTPRPreset("open").fetch()
    assert data == generator.PresetData(
        randomizer="alttpr",
        preset_name="open",
        preset_data=yaml.safe_load((PRESETS / "alttpr" / "open.yaml").read_text()),
        namespace=None,
    )


async def test_fetch_missing_global_preset_raises_user_facing_error():
    with pytest.raises(generator.PresetNotFoundException, match="Could not find preset nope"):
        await generator.ALTTPRPreset("nope").fetch()


async def test_name_with_a_slash_is_a_namespace_lookup_not_a_path(db):
    p = generator.ALTTPRPreset("../sm/casual_full")
    assert (p.namespace, p.preset) == ("..", "sm")
    with pytest.raises(generator.PresetNotFoundException, match="in namespace"):
        await p.fetch()


async def test_fetch_without_name_raises():
    with pytest.raises(generator.NoPresetSpecified):
        await generator.ALTTPRPreset().fetch()


async def test_namespaced_preset_save_and_fetch_roundtrip(db):
    await models.PresetNamespaces.create(name="synack", discord_user_id=42)

    p = await generator.ALTTPRPreset.custom("settings:\n  mode: open\n", "synack/mine")
    await p.save()
    p.preset_data = {"settings": {"mode": "inverted"}}
    await p.save()  # update_or_create: overwrites, does not duplicate

    assert await models.Presets.filter(preset_name="mine").count() == 1
    fetched = await generator.ALTTPRPreset("synack/mine").fetch()
    assert fetched.preset_data == {"settings": {"mode": "inverted"}}
    assert fetched.namespace == "synack"

    assert await generator.ALTTPRPreset().get_presets(namespace="synack") == ["mine"]
    assert await generator.SMPreset().get_presets(namespace="synack") == []


async def test_namespaced_errors(db):
    with pytest.raises(generator.PresetNotFoundException, match="in namespace ghost"):
        await generator.ALTTPRPreset("ghost/x").fetch()
    with pytest.raises(generator.NamespaceNotFound):
        await generator.ALTTPRPreset().get_presets(namespace="ghost")
    with pytest.raises(generator.AttemptToSaveGlobalPreset):
        await (await generator.ALTTPRPreset.custom_from_dict({}, "global")).save()
    with pytest.raises(generator.NoPresetSpecified):
        await generator.ALTTPRPreset().save()


async def test_create_or_retrieve_namespace_slugifies_username(db):
    ns = await generator.create_or_retrieve_namespace(42, "Some User!")
    assert ns.name == "some-user"
    again = await generator.create_or_retrieve_namespace(42, "Renamed")
    assert again.id == ns.id and again.name == "some-user"


async def test_is_namespace_owner(db):
    ns = await models.PresetNamespaces.create(name="owner", discord_user_id=1)
    await models.PresetNamespaceCollaborators.create(namespace=ns, discord_user_id=2)
    await ns.fetch_related("collaborators")

    def user(i):
        return SimpleNamespace(id=i)

    assert generator.is_namespace_owner(user(1), ns)
    assert generator.is_namespace_owner(user(2), ns)
    assert not generator.is_namespace_owner(user(3), ns)
    # hard-coded override for the bot owner
    assert generator.is_namespace_owner(user(185198185990324225), ns)


# ---------------------------------------------------------------------------
# ALTTPRPreset.generate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "branch, baseurl",
    [
        ("live", "https://alttpr.com"),
        ("beeta", "https://beeta.alttpr.com"),
        ("tournament", "https://tournament.alttpr.com"),
        (None, config.ALTTPR_BASEURL),
    ],
)
async def test_alttpr_branch_selects_base_url(db, randomizers, branch, baseurl):
    await generator.ALTTPRPreset("open").generate(branch=branch)
    assert randomizers.alttpr.call_args.kwargs["baseurl"] == baseurl
    assert randomizers.alttpr.call_args.kwargs["endpoint"] == "/api/randomizer"


async def test_alttpr_generate_sets_flags_and_writes_audit_row(db, randomizers):
    seed = await generator.ALTTPRPreset("open").generate(
        hints=True, spoilers="on", tournament=False, allow_quickswap=True, endpoint_prefix="/festive"
    )
    assert seed is randomizers.alttpr.return_value

    kwargs = randomizers.alttpr.call_args.kwargs
    settings = kwargs["settings"]
    assert settings["hints"] == "on"
    assert settings["tournament"] is False
    assert settings["spoilers"] == "on"
    assert settings["allow_quickswap"] is True
    assert kwargs["endpoint"] == "/festive/api/randomizer"

    audit = await models.AuditGeneratedGames.get()
    assert (audit.randomizer, audit.hash_id, audit.permalink, audit.gentype, audit.genoption) == (
        "alttpr",
        "abc123",
        "https://alttpr.test/h/abc123",
        "preset",
        "open",
    )
    assert audit.customizer == 0


async def test_alttpr_nohints_and_preset_quickswap_wins(db, randomizers):
    p = await generator.ALTTPRPreset.custom_from_dict(
        {"settings": {"allow_quickswap": False}}, preset_name="custom"
    )
    await p.generate(nohints=True, allow_quickswap=True)
    settings = randomizers.alttpr.call_args.kwargs["settings"]
    assert settings["hints"] == "off"
    assert settings["allow_quickswap"] is False  # only defaulted when the preset doesn't say


async def test_alttpr_preset_branch_overrides_argument(db, randomizers):
    p = await generator.ALTTPRPreset.custom_from_dict({"branch": "beeta", "settings": {}}, "x")
    await p.generate(branch="live")
    assert randomizers.alttpr.call_args.kwargs["baseurl"] == "https://beeta.alttpr.com"


async def test_alttpr_customizer_forced_locations(db, randomizers):
    p = await generator.ALTTPRPreset.custom_from_dict(
        {
            "customizer": True,
            "settings": {},
            "forced_locations": [
                {"item": "Bow", "locations": ["loc-a"]},
                {"item": "Hookshot", "locations": ["loc-b", "loc-c"], "chance": 0},
            ],
        },
        "x",
    )
    await p.generate()
    kwargs = randomizers.alttpr.call_args.kwargs
    assert kwargs["endpoint"] == "/api/customizer"
    assert kwargs["settings"]["l"] == {"loc-a": "Bow"}  # chance 0 never places
    assert (await models.AuditGeneratedGames.get()).customizer == 1


async def test_alttpr_doors_preset_goes_to_door_randomizer(db, randomizers):
    p = await generator.ALTTPRPreset.custom_from_dict(
        {"doors": True, "branch": "volatile", "settings": {"door_shuffle": "crossed"}}, "x"
    )
    await p.generate(hints=True, spoilers="on", allow_quickswap=True)
    randomizers.alttpr.assert_not_called()
    kwargs = randomizers.doors.call_args.kwargs
    assert kwargs == {
        "settings": {"door_shuffle": "crossed", "hints": "on", "quickswap": True},
        "spoilers": True,
        "branch": "volatile",
    }
    assert (await models.AuditGeneratedGames.get()).doors is True


async def test_alttpr_avianart_preset(db, randomizers):
    p = await generator.ALTTPRPreset.custom_from_dict({"avianart": True, "settings": {"preset": "foo"}}, "x")
    await p.generate(tournament=False)
    randomizers.avianart.assert_awaited_once_with(preset="foo", race=False)


@pytest.mark.parametrize("name", preset_names("alttpr"))
async def test_every_alttpr_preset_generates_with_fake_randomizer(db, randomizers, name):
    await generator.ALTTPRPreset(name).generate()
    assert randomizers.alttpr.await_count + randomizers.doors.await_count + randomizers.avianart.await_count == 1
    assert await models.AuditGeneratedGames.filter(genoption=name).count() == 1


# ---------------------------------------------------------------------------
# Mystery
# ---------------------------------------------------------------------------


MYSTERY_KNOWN_BROKEN = {
    # KNOWN ISSUE: festive.yaml has no glitches_required, which pyz3r's
    # generate_random_settings requires, so rolling it raises KeyError.
    "festive": pytest.mark.xfail(raises=KeyError, strict=True, reason="festive weightset lacks glitches_required"),
}


@pytest.mark.parametrize(
    "name",
    [pytest.param(n, marks=MYSTERY_KNOWN_BROKEN[n]) if n in MYSTERY_KNOWN_BROKEN else n for n in preset_names("alttprmystery")],
)
async def test_every_mystery_weightset_rolls_settings(name):
    """Rolls each weightset a few times. Rolling is local (pyz3r.mystery); only
    the final seed generation would call a randomizer."""
    import random

    random.seed(name)
    weights = (await generator.ALTTPRMystery(name).fetch()).preset_data
    for _ in range(5):
        mystery = await generator.mystery_generate(weights, spoilers="mystery")
        assert isinstance(mystery.settings, dict)
        assert isinstance(mystery.doors, bool)


async def test_mystery_generate_doors_and_non_doors_paths(db, randomizers):
    mystery = generator.ALTTPRMystery.__new__(generator.ALTTPRMystery)
    generator.SahasrahBotPresetCore.__init__(mystery, "weighted")

    door_roll = generator.mysterydoors.AlttprMystery(weights={}, settings={"a": 1}, doors=True, branch="stable")
    with mock.patch.object(generator, "mystery_generate", mock.AsyncMock(return_value=door_roll)):
        mystery.preset_data = {}
        result = await mystery.generate(spoilers="off")
    assert result.seed is randomizers.doors.return_value
    assert randomizers.doors.call_args.kwargs == {"settings": {"a": 1}, "spoilers": True, "branch": "stable"}

    z3r_roll = generator.mysterydoors.AlttprMystery(weights={}, settings={}, customizer=True)
    with mock.patch.object(generator, "mystery_generate", mock.AsyncMock(return_value=z3r_roll)):
        result = await mystery.generate(tournament=False, allow_quickswap=False)
    kwargs = randomizers.alttpr.call_args.kwargs
    assert kwargs["endpoint"] == "/api/customizer"
    assert kwargs["settings"] == {"tournament": False, "allow_quickswap": False}

    audits = await models.AuditGeneratedGames.filter(gentype="mystery").order_by("id")
    assert [a.doors for a in audits] == [True, False]


async def test_mystery_retries_then_raises_last_error(db, randomizers):
    from aiohttp.client_exceptions import ClientResponseError

    mystery = generator.ALTTPRMystery("weighted")
    mystery.preset_data = {}
    roll = generator.mysterydoors.AlttprMystery(weights={}, settings={})
    error = ClientResponseError(request_info=mock.Mock(real_url="x"), history=(), status=500)
    randomizers.alttpr.side_effect = error
    with mock.patch.object(generator, "mystery_generate", mock.AsyncMock(return_value=roll)):
        with pytest.raises(ClientResponseError):
            await mystery.generate()
    assert randomizers.alttpr.await_count == 5


# ---------------------------------------------------------------------------
# SM / SMZ3 / CT Jets
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", preset_names("sm"))
async def test_every_sm_preset_generates(db, randomizers, name):
    p = generator.SMPreset(name)
    await p.generate(tournament=False)
    kwargs = randomizers.sm.call_args.kwargs
    assert kwargs["settings"]["race"] == "false"
    assert kwargs["baseurl"].endswith("sm.samus.link")


@pytest.mark.parametrize("name", preset_names("smz3"))
async def test_every_smz3_preset_generates(db, randomizers, name):
    p = generator.SMZ3Preset(name)
    await p.generate()
    kwargs = randomizers.smz3.call_args.kwargs
    assert kwargs["settings"]["race"] == "true"
    assert kwargs["baseurl"].endswith("samus.link")


async def test_sm_spoiler_key_and_urls(db, randomizers):
    p = await generator.SMPreset.custom_from_dict({"settings": {}, "release": "beta"}, "x")
    assert p.baseurl == "https://beta.sm.samus.link"
    assert p.hash_id is None and p.guid is None
    with pytest.raises(Exception, match="not been generated"):
        p.spoiler_url()

    await p.generate(spoilers=True)
    key = p.spoiler_key
    assert len(key) == 20
    assert randomizers.sm.call_args.kwargs["settings"]["spoilerKey"] == key
    assert p.hash_id == "slug123"
    assert p.guid == "guid-1"
    assert p.spoiler_url() == f"https://sm.samus.link/api/spoiler/guid-1?key={key}&yaml=True"
    assert p.spoiler_url(use_yaml=False).endswith("&yaml=False")
    assert (await models.AuditGeneratedGames.get()).hash_id == "slug123"


async def test_sm_without_spoilers_has_no_spoiler_url(db, randomizers):
    p = await generator.SMPreset.custom_from_dict({"settings": {}}, "x")
    await p.generate()
    assert p.spoiler_url() is None


def test_smz3_base_url():
    p = generator.SMZ3Preset()
    p.preset_data = {}
    assert p.baseurl == "https://samus.link"
    p.preset_data = {"release": "beta"}
    assert p.baseurl == "https://beta.samus.link"


@pytest.mark.parametrize("name", preset_names("ctjets"))
async def test_every_ctjets_preset_generates(db, randomizers, name):
    uri = await generator.CTJetsPreset(name).generate()
    assert uri == "https://ctjets.test/seed/1"
    assert "version" in randomizers.ctjets.call_args.kwargs
    assert (await models.AuditGeneratedGames.get()).permalink == uri


# ---------------------------------------------------------------------------
# alttprbot.alttprgen.preset (the older entry points)
# ---------------------------------------------------------------------------


async def test_get_preset_returns_seed_and_preset_dict(db, randomizers):
    seed, preset_dict = await preset.get_preset("open", hints=True, tournament=False)
    assert seed is randomizers.alttpr.return_value
    assert preset_dict["settings"]["hints"] == "on"
    assert randomizers.alttpr.call_args.kwargs["settings"]["tournament"] is False


async def test_generate_preset_dispatches_on_randomizer_key(db, randomizers):
    await preset.generate_preset({"randomizer": "smz3", "settings": {}}, preset="x", tournament=False)
    assert randomizers.smz3.call_args.kwargs["settings"]["race"] == "false"

    await preset.generate_preset({"randomizer": "ctjets", "settings": {}}, preset="x")
    randomizers.ctjets.assert_awaited_once()

    await preset.generate_preset({"settings": {}}, preset="x")  # defaults to alttpr
    randomizers.alttpr.assert_awaited_once()


async def test_fetch_preset_unknown_randomizer_raises_key_error():
    with pytest.raises(KeyError):
        await preset.fetch_preset("open", randomizer="nope")

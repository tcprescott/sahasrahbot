"""Characterization tests for alttprbot/util/config_contract.py.

``validate_config_contract`` reads attributes off the imported ``config``
module. To keep these tests isolated from the real environment/.env, we swap
that reference for a ``SimpleNamespace`` built to satisfy (or deliberately
violate) the contract.
"""

from types import SimpleNamespace

import pytest

from alttprbot.util import config_contract
from alttprbot.util.config_contract import (
    ConfigValidationError,
    _is_blank,
    expected_racetime_category_slugs,
    required_keys,
    validate_config_contract,
)

BASE_KEYS = [
    "DB_HOST",
    "DB_PORT",
    "DB_USER",
    "DB_PASS",
    "DB_NAME",
    "DISCORD_TOKEN",
    "AUDIT_DISCORD_TOKEN",
    "RACETIME_HOST",
    "RACETIME_PORT",
    "RACETIME_URL",
    "RACETIME_COMMAND_PREFIX",
]


PRODUCTION_SLUGS = [
    "alttpr",
    "contra",
    "ct-jets",
    "ff1r",
    "sgl",
    "smb3r",
    "smr",
    "smw-hacks",
    "smz3",
    "twwr",
    "z1r",
    "z2r",
]


def make_debug_config(**overrides):
    """A SimpleNamespace that satisfies the debug-mode contract (slug 'test')."""
    values = {key: f"value-{key}" for key in BASE_KEYS}
    values["DEBUG"] = True
    values["RACETIME_CLIENT_ID_TEST"] = "id"
    values["RACETIME_CLIENT_SECRET_TEST"] = "secret"
    values.update(overrides)
    return SimpleNamespace(**values)


def make_production_config(**overrides):
    """A SimpleNamespace that satisfies the full production contract.

    Builds the dynamic RACETIME_CLIENT_ID_*/SECRET_* keys via the same
    slug.upper().replace('-', '') derivation the validator uses, so hyphenated
    slugs (ct-jets -> CTJETS, smw-hacks -> SMWHACKS) are covered.
    """
    values = {key: f"value-{key}" for key in BASE_KEYS}
    values["DEBUG"] = False
    values["APP_SECRET_KEY"] = "app-secret"
    for slug in PRODUCTION_SLUGS:
        category_key = slug.upper().replace("-", "")
        values[f"RACETIME_CLIENT_ID_{category_key}"] = "id"
        values[f"RACETIME_CLIENT_SECRET_{category_key}"] = "secret"
    values.update(overrides)
    return SimpleNamespace(**values)


# ---- _is_blank ----------------------------------------------------------

@pytest.mark.parametrize("value", [None, "", "   ", "\t\n", [], {}, (), set()])
def test_is_blank_true(value):
    assert _is_blank(value) is True


@pytest.mark.parametrize("value", ["x", " a ", [1], {"k": "v"}, (0,), {0}, 0, False])
def test_is_blank_false(value):
    # Note: numbers and booleans are never "blank" under this contract.
    assert _is_blank(value) is False


# ---- key lists ----------------------------------------------------------

def test_expected_slugs_debug_is_just_test():
    assert expected_racetime_category_slugs(True) == ["test"]


def test_expected_slugs_production_full_list():
    # Pin the exact list: downstream RACETIME_CLIENT_ID_* derivation depends on
    # every element, so element-level regressions must fail.
    assert expected_racetime_category_slugs(False) == PRODUCTION_SLUGS


def test_required_keys_adds_app_secret_only_in_production():
    assert "APP_SECRET_KEY" not in required_keys(True)
    assert "APP_SECRET_KEY" in required_keys(False)


# ---- validate_config_contract ------------------------------------------

def test_valid_debug_config_passes(monkeypatch):
    monkeypatch.setattr(config_contract, "config", make_debug_config())
    # Should not raise.
    validate_config_contract()


def test_missing_base_key_raises(monkeypatch):
    cfg = make_debug_config()
    del cfg.DISCORD_TOKEN
    monkeypatch.setattr(config_contract, "config", cfg)
    with pytest.raises(ConfigValidationError) as exc:
        validate_config_contract()
    assert "DISCORD_TOKEN" in str(exc.value)


def test_blank_base_key_raises(monkeypatch):
    monkeypatch.setattr(config_contract, "config", make_debug_config(DB_NAME="   "))
    with pytest.raises(ConfigValidationError) as exc:
        validate_config_contract()
    assert "DB_NAME" in str(exc.value)


def test_missing_dynamic_category_secret_raises(monkeypatch):
    cfg = make_debug_config()
    del cfg.RACETIME_CLIENT_SECRET_TEST
    monkeypatch.setattr(config_contract, "config", cfg)
    with pytest.raises(ConfigValidationError) as exc:
        validate_config_contract()
    assert "RACETIME_CLIENT_SECRET_TEST" in str(exc.value)


def test_production_requires_app_secret_key(monkeypatch):
    # A debug-shaped config in production mode is missing APP_SECRET_KEY (and
    # the 12 production categories); assert APP_SECRET_KEY is flagged.
    monkeypatch.setattr(config_contract, "config", make_debug_config(DEBUG=False))
    with pytest.raises(ConfigValidationError) as exc:
        validate_config_contract()
    assert "APP_SECRET_KEY" in str(exc.value)


def test_full_production_config_passes(monkeypatch):
    # The production happy path (all 12 categories + APP_SECRET_KEY) must not raise.
    monkeypatch.setattr(config_contract, "config", make_production_config())
    validate_config_contract()


def test_missing_hyphenated_category_key_is_derived_correctly(monkeypatch):
    # 'ct-jets' must derive to RACETIME_CLIENT_SECRET_CTJETS. This is the only
    # case that exercises slug.upper().replace('-', ''); a broken transform
    # (e.g. leaving the hyphen) would flag the wrong key name.
    cfg = make_production_config()
    del cfg.RACETIME_CLIENT_SECRET_CTJETS
    monkeypatch.setattr(config_contract, "config", cfg)
    with pytest.raises(ConfigValidationError) as exc:
        validate_config_contract()
    assert "RACETIME_CLIENT_SECRET_CTJETS" in str(exc.value)


def test_missing_dynamic_category_id_raises(monkeypatch):
    # Complements the SECRET test: pin the RACETIME_CLIENT_ID_{category} format too.
    cfg = make_debug_config()
    del cfg.RACETIME_CLIENT_ID_TEST
    monkeypatch.setattr(config_contract, "config", cfg)
    with pytest.raises(ConfigValidationError) as exc:
        validate_config_contract()
    assert "RACETIME_CLIENT_ID_TEST" in str(exc.value)

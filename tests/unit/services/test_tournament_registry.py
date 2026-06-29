"""Registry-unification guards for ``alttprbot/tournaments.py``.

The hardcoded fallback (used when ``TOURNAMENT_CONFIG_ENABLED`` is false — the production
default) is derived from ``AVAILABLE_TOURNAMENT_HANDLERS`` so it can never dispatch a slug
to a different handler than the catalog / ``config/tournaments.yaml`` path. These tests pin
that single-source invariant and the current migration state.
"""

from alttprbot import tournaments


def _is_migrated_adapter(handler) -> bool:
    """A decomposed handler is an ``OrchestratorAdapter`` subclass (``make_adapter``)."""
    return hasattr(handler, "_orchestrator_cls") and hasattr(handler, "_definition")


def test_hardcoded_fallback_never_drifts_from_catalog():
    # Every slug the hardcoded fallback activates must resolve to the SAME handler object
    # as the catalog — i.e. the fallback selects which slugs are active, never which class.
    for slug, handler in tournaments._HARDCODED_TOURNAMENT_DATA.items():
        assert handler is tournaments.AVAILABLE_TOURNAMENT_HANDLERS[slug], (
            f"hardcoded fallback for {slug!r} drifted from AVAILABLE_TOURNAMENT_HANDLERS"
        )


def test_active_hardcoded_slugs_exist_in_catalog():
    for slug in tournaments._HARDCODED_ACTIVE_SLUGS:
        assert slug in tournaments.AVAILABLE_TOURNAMENT_HANDLERS


def test_league_slugs_are_decomposed_in_catalog():
    # The migrated league handlers dispatch to the new orchestrator adapter in BOTH paths.
    for slug in ("invleague", "alttprleague"):
        assert _is_migrated_adapter(tournaments.AVAILABLE_TOURNAMENT_HANDLERS[slug])


def test_current_migration_state_of_active_production_handlers():
    # Documents (and guards) which active production handlers are decomposed vs still legacy.
    # When alttpr (the qualifier) is migrated, flip it here.
    catalog = tournaments.AVAILABLE_TOURNAMENT_HANDLERS
    assert _is_migrated_adapter(catalog["invleague"])
    assert _is_migrated_adapter(catalog["alttprleague"])
    assert _is_migrated_adapter(catalog["alttprdaily"])  # daily — decomposed (PR7)
    assert _is_migrated_adapter(catalog["smz3"])         # weekly — decomposed (PR7)
    assert not _is_migrated_adapter(catalog["alttpr"])   # qualifier — still legacy

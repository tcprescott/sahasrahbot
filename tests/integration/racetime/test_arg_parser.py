"""Tests for the ex2_* command argument parser.

Ported from the previously-used racetime-bot fork; see
alttprbot/presentation/racetime/util/arg_parser.py.
"""

from alttprbot.presentation.racetime.util.arg_parser import arg_parser


def test_positionals_only():
    assert arg_parser("!newrace standard") == (["!newrace", "standard"], {})


def test_key_value_string():
    positionals, keywords = arg_parser("!newrace --preset=standard")
    assert positionals == ["!newrace"]
    assert keywords == {"preset": "standard"}


def test_key_value_int_coercion():
    _, keywords = arg_parser("!newrace --countdown=900")
    assert keywords["countdown"] == 900
    assert isinstance(keywords["countdown"], int)


def test_key_value_bool_coercion():
    _, keywords = arg_parser("!newrace --quickswap=true --spoiler=false")
    assert keywords == {"quickswap": True, "spoiler": False}


def test_bare_flag_is_true():
    _, keywords = arg_parser("!newrace --quickswap")
    assert keywords == {"quickswap": True}


def test_no_prefix_negates_flag():
    _, keywords = arg_parser("!newrace --no-quickswap")
    assert keywords == {"quickswap": False}


def test_single_dash_short_flag_is_true():
    _, keywords = arg_parser("!newrace -x")
    assert keywords == {"x": True}


def test_case_is_preserved():
    # arg_parser must not fold case: preset names / branches are case-sensitive.
    positionals, keywords = arg_parser("!newrace --preset=MixedCase --branch=Tournament Standard")
    assert positionals == ["!newrace", "Standard"]
    assert keywords == {"preset": "MixedCase", "branch": "Tournament"}


def test_ex2_newrace_positional_offset():
    # ex2_newrace reads positional_args[1] as the preset (index 0 is the command
    # token). Verify arg_parser called on the whole command line keeps that shape.
    positionals, _ = arg_parser("!newrace mypreset live")
    assert positionals[0] == "!newrace"
    assert positionals[1] == "mypreset"


def test_mixed_positionals_and_keywords():
    positionals, keywords = arg_parser(
        "!newrace --preset=standard --quickswap --no-spoiler_race --countdown=900 extra"
    )
    assert positionals == ["!newrace", "extra"]
    assert keywords == {
        "preset": "standard",
        "quickswap": True,
        "spoiler_race": False,
        "countdown": 900,
    }

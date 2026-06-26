"""Characterization tests for LoROM SNES<->PC address conversion.

Pure bitwise math, no external dependencies. See alttprbot/util/rom.py.

Note: ``pc_to_snes_lorom`` sets the within-bank 0x8000 offset bit but NOT the
0x800000 ROM-mirror bit, so it produces addresses like 0x008000 (not 0x808000).
``snes_to_pc_lorom`` masks the bank with 0x7F, so the 0x80 mirror bit is ignored.
"""

import pytest

from alttprbot.util.rom import pc_to_snes_lorom, snes_to_pc_lorom


@pytest.mark.parametrize(
    "snes, expected_pc",
    [
        (0x008000, 0x000000),  # first bank, low offset
        (0x008001, 0x000001),
        (0x00FFFF, 0x007FFF),  # end of first bank
        (0x018000, 0x008000),  # next bank -> PC 0x8000
        (0x808000, 0x000000),  # 0x80 mirror bit is masked off -> same as 0x008000
    ],
)
def test_snes_to_pc_known_values(snes, expected_pc):
    assert snes_to_pc_lorom(snes) == expected_pc


@pytest.mark.parametrize(
    "pc, expected_snes",
    [
        (0x000000, 0x008000),
        (0x000001, 0x008001),
        (0x007FFF, 0x00FFFF),
        (0x008000, 0x018000),
    ],
)
def test_pc_to_snes_known_values(pc, expected_snes):
    assert pc_to_snes_lorom(pc) == expected_snes


@pytest.mark.parametrize("pc", [0x000000, 0x000001, 0x007FFF, 0x008000, 0x123456, 0x3FFFFF])
def test_round_trip_pc_to_snes_to_pc(pc):
    """A valid LoROM PC offset survives a PC -> SNES -> PC round trip."""
    assert snes_to_pc_lorom(pc_to_snes_lorom(pc)) == pc


@pytest.mark.parametrize("snes", [0x008000, 0x00FFFF, 0x018000, 0x7FFFFF])
def test_round_trip_snes_to_pc_to_snes(snes):
    """A canonical LoROM SNES address (bank set, offset 0x8000-0xFFFF) survives
    a SNES -> PC -> SNES round trip. Exercises the direction the PC round trip
    cannot, since pc_to_snes_lorom sets the 0x8000 offset bit that the other
    round trip masks away."""
    assert pc_to_snes_lorom(snes_to_pc_lorom(snes)) == snes

"""HolyImageService unit tests: slug/alias/idx lookup, guards, not-found."""

from unittest.mock import AsyncMock

import pytest

from alttprbot.exceptions import HolyImageNotFound
from alttprbot.services import HolyImageService

CATALOG = {
    "z3r": [
        {"slug": "moldorm", "idx": 1, "title": "Moldorm", "aliases": ["mold"]},
        {"slug": "lanmolas", "idx": 2, "title": "Lanmolas", "aliases": []},
    ],
    "smr": [
        {"slug": "kraid", "idx": 1, "title": "Kraid"},
    ],
}


def _service():
    service = HolyImageService()
    service.get_all_images = AsyncMock(return_value=CATALOG)
    return service


async def test_get_image_by_slug():
    service = _service()
    image, link = await service.get_image("moldorm", "z3r")
    assert image["slug"] == "moldorm"
    assert link == "http://alttp.mymm1.com/holyimage/z3r-moldorm.html"


async def test_get_image_is_case_insensitive():
    service = _service()
    image, _ = await service.get_image("MolDorm", "z3r")
    assert image["slug"] == "moldorm"


async def test_get_image_by_alias():
    service = _service()
    image, _ = await service.get_image("mold", "z3r")
    assert image["slug"] == "moldorm"


async def test_get_image_by_idx():
    service = _service()
    image, _ = await service.get_image("2", "z3r")
    assert image["slug"] == "lanmolas"


async def test_get_image_respects_game():
    service = _service()
    image, link = await service.get_image("kraid", "smr")
    assert image["slug"] == "kraid"
    assert link == "http://alttp.mymm1.com/holyimage/smr-kraid.html"


async def test_get_image_none_slug_raises():
    service = _service()
    with pytest.raises(HolyImageNotFound):
        await service.get_image(None, "z3r")


async def test_get_image_unknown_slug_raises():
    service = _service()
    with pytest.raises(HolyImageNotFound):
        await service.get_image("does-not-exist", "z3r")

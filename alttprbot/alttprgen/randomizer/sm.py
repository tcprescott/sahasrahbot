"""Super Metroid and SMZ3 (samus.link) API clients.

Pure seed-generation code: no Discord or racetime imports. Discord embeds for
these seeds are built in ``alttprbot_discord/util/seed_embeds.py``.
"""
from pyz3r.sm import smClass


class SMClient(smClass):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.randomizer = 'sm'

    @property
    def generated_goal(self):
        return self.randomizer


class SMZ3Client(SMClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.randomizer = 'smz3'

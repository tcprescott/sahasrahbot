import logging
from discord.ext import commands
import os

import yaml


class GuildConfigBot(commands.Bot):
    async def wait_until_ready(self):
        await self._ready.wait()
        await self.wait_for('guild_configs_loaded')


class GuildConfig():
    def __init__(self, guild_id):
        self._configdict = {}
        self.guild_id = guild_id
        self.load()

    def set(self, key, val):
        self._configdict[key] = val
        self.save()

    def get(self, key, default=None):
        return self._configdict.get(key, default)

    def delete(self, key):
        del self._configdict[key]
        self.save()

    def dump(self):
        return self._configdict

    def load(self):
        try:
            with open(os.path.join('data', 'config', f'{self.guild_id}.yaml')) as f:
                self._configdict = yaml.safe_load(f)
        except FileNotFoundError:
            logging.debug(f"No config file for {self.guild_id}, skipping...")

    def save(self):
        with open(os.path.join('data', 'config', f'{self.guild_id}.yaml'), 'w') as f:
            yaml.dump(self._configdict, f)

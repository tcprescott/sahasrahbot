import datetime

import discord

from pyz3r.smvaria import SuperMetroidVaria


class SuperMetroidVariaDiscord(SuperMetroidVaria):
    def embed(self):
        embed = discord.Embed(
            title="Generated Super Metroid Varia Game",
            description=f"**Skills preset: **{self.skills_preset}\n**Settings preset: **{self.settings_preset}",
            color=discord.Colour.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(
            name="Link",
            value=self.url,
            inline=False
        )
        if self.data.get('errorMsg', '') != '':
            embed.add_field(
                name="Warnings",
                value=self.data.get('errorMsg', ''),
                inline=False
            )
        return embed

from pyz3r.smvaria import SuperMetroidVaria
import discord
import datetime


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
        embed.add_field(
            name="Warnings",
            value=self.data.get('errorMsg', None),
            inline=False
        )
        return embed

import discord

# From https://gist.github.com/Rapptz/31a346ed1eb545ddeb0d451d81a60b3b


class EmbedHelpCommand(discord.ext.commands.HelpCommand):
    """This is an example of a HelpCommand that utilizes embeds.
    It's pretty basic but it lacks some nuances that people might expect.
    1. It breaks if you have more than 25 cogs or more than 25 subcommands. (Most people don't reach this)
    2. It doesn't DM users. To do this, you have to override `get_destination`. It's simple.
    Other than those two things this is a basic skeleton to get you started. It should
    be simple to modify if you desire some other behaviour.

    To use this, pass it to the bot constructor e.g.:

    bot = commands.Bot(help_command=EmbedHelpCommand())
    """
    # Set the embed colour here
    COLOUR = discord.Colour.blurple()

    def get_ending_note(self):
        return 'Use {0}{1} [command] for more info on a command.'.format(self.clean_prefix, self.invoked_with)

    def get_command_signature(self, command):  # pylint: disable=no-self-use
        return '{0.qualified_name} {0.signature}'.format(command)

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title='Bot Commands', colour=self.COLOUR)
        description = self.context.bot.description
        if description:
            embed.description = description

        for cog, commands in mapping.items():
            name = 'No Category' if cog is None else cog.qualified_name
            filtered = await self.filter_commands(commands, sort=True)
            if filtered:
                value = '\u2002'.join(c.name for c in commands)
                if cog and cog.description:
                    value = '{0}\n{1}'.format(cog.description, value)

                embed.add_field(name=name, value=value, inline=False)

        embed.set_footer(text=self.get_ending_note(), icon_url=discord.utils.get(
            self.context.bot.emojis, name="SahasrahBot").url)
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(
            title='{0.qualified_name} Commands'.format(cog), colour=self.COLOUR)
        if cog.description:
            embed.description = cog.description

        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for command in filtered:
            embed.add_field(name=f'{self.clean_prefix}{self.get_command_signature(command)}',
                            value=command.short_doc or '...', inline=False)

        embed.set_footer(text=self.get_ending_note(), icon_url=discord.utils.get(
            self.context.bot.emojis, name="SahasrahBot").url)
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        embed = discord.Embed(
            title=f'{self.clean_prefix}{group.qualified_name} {group.signature}', colour=self.COLOUR)
        if group.help:
            embed.description = group.help

        if isinstance(group, discord.ext.commands.Group):
            filtered = await self.filter_commands(group.commands, sort=True)
            for command in filtered:
                embed.add_field(name=f'{self.clean_prefix}{self.get_command_signature(command)}',
                                value=command.short_doc or '...', inline=False)

        embed.set_footer(text=self.get_ending_note(), icon_url=discord.utils.get(
            self.context.bot.emojis, name="SahasrahBot").url)
        await self.get_destination().send(embed=embed)

    # This makes it so it uses the function above
    # Less work for us to do since they're both similar.
    # If you want to make regular command help look different then override it
    send_command_help = send_group_help

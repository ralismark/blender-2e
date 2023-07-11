#!/usr/bin/env python3

"""
Pipe messages from one channel to another
"""

import discord
from discord.ext import commands
import logging

from base import sql, fragment, settings

_L = logging.getLogger(__name__)

pipe_target = settings.ChannelSetting(
        "pipe", sql.TypeAffinity.INTEGER, "ID of Channel to pipe messages to")
setup = fragment.Fragment()

@setup.listen("message")
async def pipe_message(bot: commands.Bot, message: discord.Message):
    """
    Pipe a message if configured
    """
    if (message.guild is None
            or message.type != discord.MessageType.default
            or message.author.bot):
        return # shouldn't reply

    pipeto = pipe_target.get(message)
    if pipeto is None:
        return # not configured

    chan = bot.get_channel(pipeto)

    embed = discord.Embed(description=message.content)
    embed.set_author(name=message.author.display_name,
                     icon_url=message.author.avatar_url_as(format="png", size=64))

    await chan.send(embed=embed)

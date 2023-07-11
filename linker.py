#!/usr/bin/env python3

"""
Use embeds to shorten links.
"""

import logging

import discord
from discord.ext import commands

from base import fragment, settings

_L = logging.getLogger(__name__)

enabled = settings.ScopedToggle(name="linker", description="Enable creation of shortened links?")
setup = fragment.Fragment()

@setup.command("link")
@commands.bot_has_permissions(send_messages=True)
@enabled.enabled
async def make_link(ctx, desc, *, url):
    """
    Create a link
    """
    embed = discord.Embed(title=f":link: {desc}", url=url)
    embed.set_author(name=ctx.author.display_name,
                     icon_url=ctx.author.avatar_url_as(format="png", size=64))
    await ctx.send(embed=embed)

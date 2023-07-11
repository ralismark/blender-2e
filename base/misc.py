#!/usr/bin/env python3

"""
Miscellaneous utilities and helpers
"""

from discord.ext import commands

class DotDict(dict):
    """
    Dot-notation access to dictionary attributes (like in javascript)
    """
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

async def is_admin_or_owner(ctx: commands.Context):
    """
    Check if the person running the command is an admin or the owner
    """
    if await ctx.bot.is_owner(ctx.author):
        return True
    perms = ctx.channel.permissions_for(ctx.author)
    return perms.administrator

DELETE_REACTION = '\u274c'

async def send_deletable(ctx, embed):
    """
    Send embed as deletable message
    """
    foot = (embed.footer.text or "") + ("\n" if embed.footer.text else "")
    embed.set_footer(
        text=foot + f"{DELETE_REACTION} to delete",
        icon_url=embed.footer.icon_url
        )
    msg = await ctx.send(embed=embed)
    await msg.add_reaction(DELETE_REACTION)

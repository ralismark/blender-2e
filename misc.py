#!/usr/bin/env python3

"""
Miscellaneous commands
"""

import asyncio
import logging

import discord
from discord.ext import commands

from base import fragment
from utils import Reservoir

setup = fragment.Fragment()
_L = logging.getLogger(__name__)

@setup.command("remind")
async def remind(ctx, mins: float, *, msg):
    """
    Remind you of something in a while
    """
    await ctx.send(f"\u200b:timer: in {mins} mins", delete_after=5)
    await asyncio.sleep(mins*60)
    await ctx.send(f"\u200b{ctx.author.mention} {msg}")

@setup.command("sample")
async def sample(ctx, user: commands.MemberConverter,
                 channel: commands.TextChannelConverter = None, count: int = 1):
    """
    Get a random message from this person.
    """
    async def take_sample(source):
        res = Reservoir(count)
        try:
            async for item in source:
                res.add(item)
        except asyncio.CancelledError:
            pass
        return res

    if channel is None:
        channel = ctx.channel

    _L.info("sampling user `%s` from channel `%s`", user, channel)

    history = channel.history(limit=None).filter(
        lambda m: m.author == user and 4 <= len(m.clean_content) <= 500
        )

    task = asyncio.ensure_future(take_sample(history))

    async with ctx.channel.typing():
        try:
            await asyncio.wait_for(task, timeout=10)
        except asyncio.TimeoutError:
            pass

    res = await task
    if not res.sample:
        await ctx.send("\u200b:speech_balloon: couldn't find any messages...", delete_after=10)
        return

    out = f"\u200b`{user.display_name}` :speech_balloon: (out of {res.counter} message)"
    for msg in res.sample:
        out += f"\n\"{msg.clean_content}\""

    await ctx.send(out)

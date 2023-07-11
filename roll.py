#!/usr/bin/env python3

"""
Roll dice!
"""

import logging
import random
import re

import discord
from discord.ext import commands

from base import fragment, settings, sql

_L = logging.getLogger(__name__)

cfg = settings.ScopedSetting(name="enable_roll", type_affinity=sql.TypeAffinity.INTEGER,
                             description="Enable dice rolls?\n1=command only, 2=inline + command")
setup = fragment.Fragment()

TO_SMALL = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

def rollexp(expr):
    """
    Roll dice from a dice notation string. Does no error handling
    """
    total = 0
    strings = []

    expr = expr.strip()
    for match in re.finditer(r"([+-])?\s*((\d*)d(\d*)|(\d+))", expr):
        mult = -1 if match.group(1) == '-' else 1

        dcount = match.group(3)
        dsides = match.group(4)
        num = match.group(5)

        strings.append('+' if mult > 0 else '-')

        if num is None:
            # dice
            rolls = [random.randint(1, int(dsides or '20')) for _ in range(int(dcount or '1'))]
            total += sum(rolls) * mult

            strings.append('[' + ' '.join(map(str, rolls)) + ']' + (dsides or '20').translate(TO_SMALL))
        else:
            total += mult * int(num)
            strings.append(str(int(num)))

        expr = expr[match.end():]

    return (total, ' '.join(strings[1:]))

@setup.command("roll")
@cfg.check(bool)
async def roll_dice(ctx, *, rolls):
    """
    Roll dice, using standard dice notation
    """
    total, decomp = rollexp(rolls)
    await ctx.send(f"\u200b{ctx.author.mention} {decomp} → {total}")

@setup.listen("on_message")
async def inline_roll(message: discord.Message):
    """
    Roll inline
    """
    if (message.guild is None
            or message.type != discord.MessageType.default
            or message.author.bot):
        return # shouldn't reply

    out = [f"\u200b{message.author.mention}"]

    for match in re.finditer(r"\[\[(([^\]|]*)\|\s*)?([-+0-9d ]*)\]\]", message.clean_content):
        if (cfg.get(message) or 0) < 2:
            return # settings not high enough
        total, decomp = rollexp(match.group(3))
        tag = match.group(2)
        out.append((f"{tag}: " if tag else "") + f"{decomp} → {total}")

    if len(out) > 1:
        await message.channel.send("\n".join(out))

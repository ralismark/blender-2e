#!/usr/bin/env python3

"""
Make really dumb jokes based on what others say
"""

import logging
import re
import random

import discord
from discord.ext import commands

from base import fragment, settings, config

_L = logging.getLogger(__name__)

enabled = settings.ScopedToggle(name="enable_dad", description="Make bad puns?")
setup = fragment.Fragment()

@setup.listen("on_message")
async def reply(message: discord.Message):
    """
    Send a reply
    """
    if (message.guild is None
            or message.type != discord.MessageType.default
            or message.author.bot):
        return # shouldn't reply

    if not message.channel.permissions_for(message.guild.me).send_messages:
        return # no perms to reply

    for sub in config.get("dad.subs"):
        match = re.search(sub["pattern"], message.clean_content, re.IGNORECASE)
        if match:
            content = random.choice(sub["replacements"])
            groups = (str(s or '').strip() for s in match.groups())
            out = "\u200b" + content.format(match[0], *groups, message=message)
            _L.debug("Candidate `%s` (from %s in %s) -> `%s`", message.clean_content,
                    message.author.name, message.guild.name, out)
            if out and len(out) < 1000:
                if not enabled.get(message):
                    return # Check at last moment possible
                await message.channel.send(out, delete_after=config.get("dad.decay"))
            break

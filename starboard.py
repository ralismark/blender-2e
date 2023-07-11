#!/usr/bin/env python3

"""
A way to remember great messages.
"""

import logging

import discord
from discord.ext import commands

from base import fragment, settings, sql

STAR = '\u2b50'

setup = fragment.Fragment()
_L = logging.getLogger(__name__)

starboard = settings.ScopedSetting(
        name="starboard", type_affinity=sql.TypeAffinity.INTEGER,
        description="ID of channel to put starred items. 0=pin, negative=disable")

threshhold = settings.ScopedSetting(
        name="sb_threshhold", type_affinity=sql.TypeAffinity.INTEGER,
        description="Minimum number of stars to star message. At least 1")

@setup.listen("on_raw_reaction_add")
async def on_star(payload: discord.RawReactionActionEvent):
    """
    Possibly star a message
    """

    channel = setup.bot.get_channel(payload.channel_id)
    try:
        message = await channel.fetch_message(payload.message_id)
    except discord.errors.NotFound:
        return

    star = discord.utils.get(message.reactions, emoji=STAR)

    if (not star # no stars
            or payload.emoji.name != STAR # not star
            or star.me # we've marked this as starred
            or (not message.clean_content and not message.attachments) # empty
       ):
        return

    sb_id = starboard.get(message)
    sb_threshhold = threshhold.get(message)

    if (sb_id is None or sb_id < 0 # disabled
            or star.count < sb_threshhold # not enough
       ):
        return

    if sb_id == 0:
        try:
            await message.pin()
        except discord.HTTPException as exc:
            await channel.send(f"\u200b:x: {exc.text}", delete_after=10)
            return
    else:
        # FIXME this could possibly find a channel in another server. Is this wanted?
        sb_channel = setup.bot.get_channel(sb_id)

        embed = discord.Embed(title=":star:", color=0xf8aa39, url=message.jump_url)
        embed.description = message.clean_content
        embed.set_footer(text=f"#{channel}")
        embed.set_author(name=message.author.display_name,
                         icon_url=message.author.avatar_url_as(format="png", size=64))
        embed.timestamp = message.created_at

        if message.attachments:
            field = "\n".join(f"[{att.filename}]({att.proxy_url})" for att in message.attachments)
            embed.add_field(name="Attachments", value=field, inline=False)

            if message.attachments[0].filename.endswith((".png", ".jpg", ".jpeg")):
                embed.set_image(url=message.attachments[0].proxy_url)
        await sb_channel.send(embed=embed)


    await message.add_reaction(STAR)

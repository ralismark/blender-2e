#!/usr/bin/env python3

"""
Add a karma system for upvoting/downvoting messages
"""

import logging

import discord
from discord.ext import commands

from base import sql, fragment, sql_tables

setup = fragment.Fragment()
_L = logging.getLogger(__name__)

karma = sql_tables.by_user.view({
    "karma": (sql.TypeAffinity.INTEGER, sql.AccessType.READWRITE),
    "karma_given": (sql.TypeAffinity.INTEGER, sql.AccessType.READWRITE),
    })

@setup.listen("on_raw_reaction_add")
async def vote(payload: discord.RawReactionActionEvent):
    """
    Add/remove karma from person
    """
    user = setup.bot.get_user(payload.user_id)
    channel = setup.bot.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)

    if (user.bot # person who added is a bot
            or message.author.bot # message sent by bot
       ):
        return

    _L.debug("reaction, %s", payload.emoji.name)
    return

    delta = 0

    with sql.exclusive:
        own = (karma.select("karma_given", id=user.id) or [[0]])[0][0]
        karma.upsert(karma_given=own+1, id=user.id)

    with sql.exclusive:
        other = (karma.select("karma_given", id=message.author.id) or [[0]])[0][0]
        karma.upsert(karma=other+1, id=message.author.id)


    karma.upsert(user=user.id, channel=channel.id, message=message.id, delta=1)

@setup.listen("on_raw_reaction_remove")
async def unvote(payload: discord.RawReactionActionEvent):
    """
    Undo change to karma
    """
    user = setup.bot.get_user(payload.user_id)
    channel = setup.bot.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)

    if (user.bot # person who added is a bot
            or message.author.bot # message sent by bot
       ):
        return



#!/usr/bin/env python3

"""
Allow the creation of poll
"""

import logging
import typing

import discord
from discord.ext import commands

from base import sql, fragment, settings, config

enabled = settings.Toggle(name="enable_poll", description="Enable the creation of polls?")
setup = fragment.Fragment()

_L = logging.getLogger(__name__)

@setup.command("poll")
@enabled.enabled
async def poll(ctx, query: str, *responses):
    """
    Create a reaction poll. Accepts flags.

    e.g. poll "Critical error" "Abort" "Retry" "Ignore"

    This creates a poll with three options:
    - [A] for "Abort"
    - [B] for "Retry"
    - [C] for "Ignore"

    e.g. poll "Are you with me?"

    This creates a poll with two options:
    - [👍] for yes
    - [👎] for no

    Flags are specified before the query string. A flag begins with one or two
    dashes. A double dash stops flag processing.

    --notify        Send a message that's instantly deleted to create a
                      notification.
    """

    notify = False
    while query.startswith('-'):
        flag = query
        query = responses[0]
        responses = responses[1:]
        if flag == '--':
            break
        elif flag == '--notify':
            notify = True

    if responses:
        embed = discord.Embed

#!/usr/bin/env python3

"""
Implements user-facing features that must be loaded as a fragment
"""

import logging

import discord
from discord.ext import commands

from . import fragment, misc
from .settings import _SETTINGS, Scope

setup = fragment.Fragment()
_L = logging.getLogger(__name__)

@setup.group(pass_context=True)
@commands.check(misc.is_admin_or_owner)
async def settings(ctx):
    """
    List available settings and their value in this current channel.

    Settings can be per-server, per-channel or both. If a setting is both
    per-server and per-channel, different values can be assigned to each. If
    there is no channel-specific value, it falls back on the serverwide value.
    """
    if ctx.invoked_subcommand is None:
        _L.debug("command settings: %d items", len(_SETTINGS))
        embed = discord.Embed(title="Available settings", description=f"{len(_SETTINGS)} available")

        for key, value in _SETTINGS.items():
            field = value.affinity.name.lower()
            if value.description:
                field += ": " + value.description
            field += "\nvalue: " + str(value.get(ctx))
            embed.add_field(name=key, value=field, inline=False)

        await ctx.send(embed=embed)

@settings.command("here")
@commands.check(misc.is_admin_or_owner)
async def setting_here(ctx, option: str):
    """
    Shows the serverwide and channel-specific values of a setting.
    """
    if option not in _SETTINGS:
        raise commands.BadArgument(message=f"`{option}` is not a valid option")

    # TODO listing all option values

    # FIXME api: this is essentially breaking into the setting.
    #
    # Currently, there seems like 2 possible options:
    #
    # 1. We require settings to be able to report all their options. This may
    #    cause problems if there are too many entries, and may place too much
    #    burden on settings implementations.
    # 2. We restrict scopes to just channel/server and take channel as the
    #    context instead of message. Prevents future addition of
    #    user-specific settings.
    #
    # I'm leaning towards 2.

    raise NotImplementedError

# FIXME type verification
#   Right now we're relying on type affinity coercion.
@settings.command("set")
@commands.check(misc.is_admin_or_owner)
async def settings_set(ctx, scope, option: str, *, value=None):
    """
    Set a configuration option.

    Call `settings` to list settings. Scope is one of "server", "channel",
    which determines where the option will apply. If the value is not
    specified, the setting is cleared.
    """
    scope_enum = Scope.from_str(scope)
    if scope_enum is None:
        raise commands.BadArgument(message=f"`{scope}` is not a valid scope")
    if option not in _SETTINGS:
        raise commands.BadArgument(message=f"`{option}` is not a valid option")
    _L.debug("command set: option=%s (%s) scope=%s - value=%s (type %s)",
             option, _SETTINGS[option], value, scope_enum.name, _SETTINGS[option].affinity)

    try:
        _SETTINGS[option].set(ctx, value, scope_enum)
        await ctx.send("\u200b:white_check_mark:", delete_after=10)
    except NotImplementedError as exc:
        await ctx.send(f"\u200bScope not supported - {exc}", delete_after=10)

@settings.command("reset")
@commands.check(misc.is_admin_or_owner)
async def settings_clear(ctx, scope, option: str):
    """
    Clears a configuration option back to null.

    See `settings set` for more.
    """
    scope_enum = Scope.from_str(scope)
    if scope_enum is None:
        raise commands.BadArgument(message=f"`{scope}` is not a valid scope")
    if option not in _SETTINGS:
        raise commands.BadArgument(message=f"`{option}` is not a valid option")
    _L.debug("command clear: option=%s (%s)", option, _SETTINGS[option])

    try:
        _SETTINGS[option].set(ctx, None, scope_enum)
        await ctx.send("\u200b:white_check_mark:", delete_after=10)
    except NotImplementedError as exc:
        await ctx.send(f"\u200bScope not supported - {exc}", delete_after=10)

@setup.listen("on_raw_reaction_add")
async def delete_deletable(payload: discord.RawReactionActionEvent):
    """
    Delete message that have deletable
    """
    user = setup.bot.get_user(payload.user_id)
    channel = setup.bot.get_channel(payload.channel_id)
    try:
        message = await channel.fetch_message(payload.message_id)
    except discord.errors.NotFound:
        return
    del_reaction = discord.utils.get(message.reactions, emoji=misc.DELETE_REACTION)

    if (not del_reaction # no one's reacted delete
            or not del_reaction.me # we haven't reacted
            or payload.emoji.name != misc.DELETE_REACTION # not delete
            or user.bot # a bot (e.g. ourselves)
       ):
        return

    # TODO logging

    await message.delete()

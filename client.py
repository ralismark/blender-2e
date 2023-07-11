#!/usr/bin/env python3

"""
Main bot client
"""

import datetime
import logging
import logging.config
import random
import signal
import sys
import traceback

import discord
from discord.ext import commands

from base import config, misc

if __name__ != "__main__":
    raise RuntimeError("client being imported")

_L = logging.getLogger(__name__)

bot = commands.Bot(command_prefix=commands.when_mentioned)

@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    """
    Handle errors from commands
    """
    # Un-nest
    error = getattr(error, 'original', error)

    # Handle exceptions from user behaviour
    if isinstance(error, commands.CommandOnCooldown):
        hrs = error.retry_after // (60*60)
        mins = error.retry_after // 60 % 60
        secs = error.retry_after % 60
        timestr = "{}{}{:.3}s".format(
            f"{int(hrs)}hrs " if hrs else "",
            f"{int(mins)}mins " if mins else "",
            secs)
        await ctx.send(f"\u200b:timer: You need to wait **{timestr}**"
                       " before you can run this command again",
                       delete_after=min(30, error.retry_after))
        return

    if isinstance(error, commands.DisabledCommand):
        await ctx.send(f"\u200b`{ctx.command}` has been disabled", delete_after=10)
        return

    # user_errs = (commands.UserInputError, commands.CommandNotFound, commands.CheckFailure)
    if isinstance(error, commands.CommandError):
        await ctx.send(f"```fix\n{error}```", delete_after=10)

    else:
        await ctx.send(f"```diff\n-- 500 Internal Server Error --```", delete_after=60)
        _L.error("exception from command %s", ctx.invoked_with, exc_info=error)
        exc_traceback = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        await (await bot.application_info()).owner.send(
            f"\u200bISE! {datetime.datetime.now()}\n```\n{exc_traceback} ```", delete_after=60)


@bot.event
async def on_error(event, *args, **kwargs):
    """
    Handle error from event handler
    """
    _L.error("exception from handling event `%s`, args=%s kwargs=%s",
             event, args, kwargs, exc_info=sys.exc_info())
    exc_traceback = "".join(traceback.format_exception(*sys.exc_info()))
    await (await bot.application_info()).owner.send(
        f"\u200bISE! {datetime.datetime.now()}\n```\n{exc_traceback}", delete_after=60)

@bot.command(hidden=True)
@commands.is_owner()
async def insmod(ctx, *, module):
    """
    Load a module
    """
    _L.warning("manually loading module: %s", module)
    bot.load_extension(module)
    await ctx.send("\u200b:white_check_mark:", delete_after=10)

@bot.command(hidden=True)
@commands.is_owner()
async def rmmod(ctx, *, module):
    """
    Unload a module
    """
    _L.warning("manually removing module: %s", module)
    bot.unload_extension(module)
    await ctx.send("\u200b:white_check_mark:", delete_after=10)

@bot.command(hidden=True)
@commands.is_owner()
async def remod(ctx, *, module):
    """
    Unload then reload a module
    """
    _L.warning("manually removing then readding module: %s", module)
    bot.unload_extension(module)
    bot.load_extension(module)
    await ctx.send("\u200b:white_check_mark:", delete_after=10)

bot.remove_command("help")
@bot.command("help")
async def help_message(ctx: commands.Context, *, command=None):
    """
    Show help about all commands.
    """

    if command is None:
        embed = discord.Embed(
            title="Help",
            description=(bot.description or "")
            )
        embed.set_footer(
            text="Run `help <command>` for information on a specific command."
            )

        for com in bot.commands:
            try:
                if com.hidden or not com.enabled or not await com.can_run(ctx):
                    continue
            except commands.CommandError:
                continue

            embed.add_field(
                name=com.name,
                value=com.short_doc or "_No description available_",
                inline=False
                )
    else:
        com = bot.get_command(command)
        if com is None:
            raise commands.CommandError("Command not found")

        embed = discord.Embed(
            title=f"Help on {com.qualified_name}"
            )
        embed.add_field(
            name="Usage",
            value=f"`{com.qualified_name} {com.signature}`",
            inline=False
            )
        embed.add_field(
            name="Description",
            value=com.help,
            inline=False
            )
        if com.aliases:
            embed.add_field(
                name="Aliases",
                value="\n".join(com.aliases),
                inline=False
                )

    await misc.send_deletable(ctx, embed)

#
# set up logger
#

logging.config.dictConfig(config.get('logging'))

#
# load fragments
#

for mod in config.get("discord.modules"):
    bot.load_extension(mod)

#
# support reload
#

def reload_all_extension():
    """
    Reload all currently loaded extensions
    """
    modules = list(bot.extensions)
    for module in modules:
        _L.warning("Reloaded %s", module)
        try:
            bot.unload_extension(module)
            bot.load_extension(module)
        except commands.ExtensionError:
            _L.error("Error in reloading %s", module, exc_info=sys.exc_info())

bot.loop.add_signal_handler(signal.SIGUSR1, lambda *_: reload_all_extension())

#
# start bot
#

random.seed()
bot.run(config.get("discord.token"))

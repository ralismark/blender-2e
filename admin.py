#!/usr/bin/env python3

"""
Commands related to the management of the bot (but not core to functionality)
"""

import asyncio
import logging
import random

import discord
from discord.ext import commands

from base import fragment, misc, sql_tables

setup = fragment.Fragment()
_L = logging.getLogger(__name__)

@setup.command("!tdump", hidden=True)
@commands.is_owner()
async def table_dump(ctx, *, table):
    """
    Dump out a sql table
    """
    if table not in sql_tables.table_map:
        raise commands.BadArgument(message=f"`{table}` does not exist")

    tsv = sql_tables.table_map[table].dump_tsv()
    await ctx.send(f"```\n{tsv}\n```")

@setup.command("!eval", hidden=True)
@commands.is_owner()
async def evaluate(ctx, *, expr):
    """
    Evaluate an expression
    """
    import traceback
    _L.warning("eval: %s", expr)

    async def apply(coro, then):
        val = await coro
        return then(val)

    # pylint: disable=eval-used
    try:
        res = eval(expr)
        if asyncio.iscoroutine(res):
            res = await res
    except Exception as error:
        exc_traceback = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        await ctx.send(f"```{exc_traceback}```")
    else:
        await ctx.send(str(res))

@setup.command("hello")
async def hello(ctx):
    """
    Hello!
    """
    import sqlite3
    embed = discord.Embed(title="Hello! I am alive")
    embed.add_field(name="Latency", value=round(ctx.bot.latency, 2))
    embed.add_field(name="discord.py version", value=discord.__version__)
    embed.add_field(name="sqlite3.py version", value=sqlite3.version)
    embed.add_field(name="libsqlite3 version", value=sqlite3.sqlite_version)
    await misc.send_deletable(ctx, embed)

@setup.command("asin")
@commands.is_owner()
async def impersonate(ctx, _who: int, where: int, *, msg):
    """
    Say as someone else in another channel
    """
    chan = ctx.get_channel(where) if where else ctx.channel
    if chan:
        await chan.send(msg)

@setup.command("!delete", hidden=True)
@commands.is_owner()
async def delete(ctx, *messages: int):
    """
    Deletes a message
    """
    for msg in messages:
        message = await ctx.channel.fetch_message(msg)
        await message.delete()
        await ctx.send("\u200b:white_check_mark:", delete_after=10)

@setup.command("whois")
async def whois(ctx, *users: commands.UserConverter):
    """
    Who is a person?
    """
    for user in users:
        embed = discord.Embed(
            title=str(user),
            colour=user.colour
            )
        embed.set_thumbnail(url=str(user.avatar_url))
        embed.add_field(name="Bot?", value="yes" if user.bot else "no")
        embed.add_field(name="Creation", value=str(user.created_at))
        embed.add_field(name="ID", value=str(user.id))
        await misc.send_deletable(ctx, embed)

@setup.command("chatlog")
@commands.bot_has_permissions(read_message_history=True)
@commands.is_owner()
async def chatlog(ctx, *, channel: commands.TextChannelConverter = None):
    """
    Get chat log
    """
    import io
    import zlib

    if channel is None:
        channel = ctx.channel

    compress = zlib.compressobj(level=9, wbits=zlib.MAX_WBITS + 16)
    log = bytearray()

    msgcount = 0
    charcount = 0
    logcount = 0

    pending = await ctx.send("pending...")
    async with ctx.channel.typing():
        async for msg in channel.history(limit=None, oldest_first=True):
            created = msg.created_at.strftime("%y-%m-%d %H:%M:%S")
            line = f"[{created}] {msg.author}: {msg.clean_content}"
            if msg.attachments:
                filelist = ", ".join(f"{f.filename}:{f.url}" for f in msg.attachments)
                line += f" [attached: {filelist}]"
            if msg.embeds:
                plural = "s" if len(msg.embeds) > 1 else ""
                line += f" [{len(msg.embeds)} embed{plural}]"

            encoded = (line + "\n").encode()
            log += compress.compress(encoded)

            msgcount += 1
            charcount += len(msg.content)
            logcount += len(encoded)

            if msgcount % 500 == 0:
                await pending.edit(content=f"{msgcount} processed, up to {created}", suppress=False)

        log += compress.flush()

    await pending.delete()
    msg = await ctx.send(
        f"{ctx.author.mention} {charcount} characters across {msgcount} messages. "
        f"Log {logcount//1000} kb long, compressed to {len(log)//1000} kb",
        file=discord.File(io.BytesIO(log), filename=f"{channel.guild.name}--{channel.name}.gz"))

    await ctx.author.send(f"chatlog done -> {msg.jump_url}")


@setup.task
async def activity_randomiser():
    """
    Randomly set an activity
    """
    activities = [
        discord.Activity(type=discord.ActivityType.watching, name="you"),
        discord.Activity(type=discord.ActivityType.playing, name="as a human"),
        discord.Activity(type=discord.ActivityType.playing, name="'a nice game of chess'"),
        ]
    while True:
        setup.bot.activity = random.choice(activities)
        _L.info("Randomising activity")
        await asyncio.sleep(60*60)

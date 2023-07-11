#!/usr/bin/env python3

"""
You know they'll never really die while the Trunk is alive[...]
It lives while the code is shifted, and they live with it, always Going Home.
        -- Moist von Lipwig, Going Postal, Chapter 13

This file contains various bits and pieces.
"""

import logging
import random

import discord
from discord.ext import commands

from base import sql, fragment, sql_tables, misc

# enabled = settings.Toggle(name="clacks", description="Have clacks tower?")
setup = fragment.Fragment()
_L = logging.getLogger(__name__)

score = sql_tables.by_user.view({
    "clacks_score": (sql.TypeAffinity.INTEGER, sql.AccessType.READWRITE)
    })
pd_pool = sql_tables.by_user.view({
    "clacks_pd": (sql.TypeAffinity.INTEGER, sql.AccessType.READWRITE)
    })

def get_clacks(user: discord.User):
    """
    Get a person's clacks
    """
    return (score.select("clacks_score", id=user.id) or [[0]])[0][0]

@setup.command("clack", hidden=True)
@commands.cooldown(1, 60, commands.BucketType.user)
@sql.exclusive
async def clack(ctx, direction: commands.UserConverter = None):
    """
    *clack* *clack* *clack*
    """
    own = get_clacks(ctx.author)
    if direction is None or direction.id == ctx.author.id:
        await ctx.send(f"\u200byou are {own}.")
        return

    if direction.bot:
        await ctx.send(f"\u200bthey're a bot. no clack")
        return

    rand = random.random()
    _L.info("Clack %s: %s -> %s", rand, ctx.author.name, direction.name)

    other = get_clacks(direction)
    if rand > 0.1:
        other -= 1
    own += 1

    punct = '.' if rand > 0.1 else '?'
    await ctx.send(f"\u200b`{direction.name}` is {other}{punct} `{round(rand, 3)}`")

    if rand > 0.9:
        await ctx.send(f"\u200b{ctx.author.mention}, why not try unclacking?")

    score.upsert(clacks_score=other, id=direction.id)
    score.upsert(clacks_score=own, id=ctx.author.id)

@setup.command("unclack", hidden=True)
@commands.cooldown(1, 60, commands.BucketType.user)
@sql.exclusive
async def unclack(ctx, direction: commands.UserConverter):
    """
    *kcalc* *kcalc* *kcalc*
    """
    own = get_clacks(ctx.author)
    if direction.id == ctx.author.id:
        await ctx.send(f"\u200byou are {own}.")
        return

    if direction.bot:
        await ctx.send(f"\u200bthey're a bot. no unclack")
        return

    other = get_clacks(direction)
    other += 1
    own -= 1

    await ctx.send(f"\u200b`{direction.name}` is {other}.")

    score.upsert(clacks_score=other, id=direction.id)
    score.upsert(clacks_score=own, id=ctx.author.id)

@setup.command("daily", hidden=True)
@commands.cooldown(1, 24*60*60, commands.BucketType.user)
@sql.exclusive
async def daily(ctx):
    """
    Get your daily clack...?
    """
    own = get_clacks(ctx.author)
    choices = score.select("id", "clacks_score",
                           id=("!=", ctx.author.id), clacks_score=(">", own-1))
    _L.debug("daily: %s candidates", len(choices))

    if not choices:
        await ctx.send(f"\u200byou are still {own}")
        return

    target = random.choice(choices)
    victim = setup.bot.get_user(target[0])

    score.upsert(id=ctx.author.id, clacks_score=own + 1)
    score.upsert(id=target[0], clacks_score=target[1] - 1)

    _L.info("daily: %s clacked %s", ctx.author, victim)
    await ctx.send(f"\u200byou are {own + 1}. thank {victim.mention} ({victim})")

@setup.command("!dilemma-drain", hidden=True)
@commands.is_owner()
@sql.exclusive
async def dilemma_drain_pool(ctx):
    """
    Clear the dilemma pool
    """
    pool = pd_pool.select("id", clacks_pd=("nonnull",))
    for row in pool:
        pd_pool.upsert(id=row[0], clacks_pd=None)
    await ctx.send("\u200b:white_check_mark:", delete_after=10)

@setup.command("dilemma", hidden=True)
@commands.cooldown(1, 20, commands.BucketType.user)
@sql.exclusive
async def dilemma(ctx, choice: str = None, mode: str = "join", count: int = 1):
    """
    Prisoner's Dilemma.

    - Choice is either "cooperate" or "betray".
    - Mode (optional) is one of "join", "match", or "pool".

    The bot manages a pool of choices. Joining adds your choice to the pool
    (replacing your previous choice). Matching pairs yourself with an existing
    choice in the pool and resolves it. Pooling (not yet implemented) randomly
    decides to either join or match, with the probability based on the number
    of people in the pool.

    When joining, you can also specify a count to remain in the pool for a
    certain number of matches.

    If both people cooperate, the each get +1 clack. If both defect, both get
    -1 clack. Otherwise, the person that defected gets +2 clacks, and the
    person who cooperated gets -2 clacks.
    """
    POOL_TARGET = 10
    POOL_MIN = 2

    if choice not in (None, "cooperate", "betray"):
        await ctx.send(f"\u200bInvalid choice", delete_after=10)

    elif mode not in ("join", "match"):
        await ctx.send(f"\u200bInvalid mode", delete_after=10)

    elif mode == "match" and count != 1:
        await ctx.send(f"\u200bCannot have count when matching", delete_after=10)

    elif count < 1:
        await ctx.send(f"\u200bCount must be positive", delete_after=10)

    elif choice is None:
        pool = pd_pool.select("id", clacks_pd=("nonnull",))
        people = "people" if len(pool) != 1 else "person"
        await ctx.send(f"\u200b{len(pool)} {people} waiting in pool")

    elif mode == "join":
        value = count if choice == "cooperate" else -count
        pd_pool.upsert(id=ctx.author.id, clacks_pd=value)
        pool = pd_pool.select("id", clacks_pd=("nonnull",))
        await ctx.send(f"\u200bYou have joined the pool. {len(pool) - 1} others", delete_after=10)

    elif mode == "match":
        pool = pd_pool.select("id", "clacks_pd", clacks_pd=("nonnull",), id=("!=", ctx.author.id))
        if len(pool) < POOL_MIN:
            await ctx.send(f"\u200bPool too small (min {POOL_MIN})! Try joining instead.",
                           delete_after=10)
            return

        our_choice = 1 if choice == "cooperate" else -1
        partner, other_choice = random.choice(pool)
        other = setup.bot.get_user(partner)

        other_delta, our_delta = {
            (True, True): (1, 1),
            (True, False): (-2, 2),
            (False, True): (2, -2),
            (False, False): (-1, -1)
            }[(other_choice > 0, our_choice > 0)]

        score.upsert(id=ctx.author.id, clacks_score=get_clacks(ctx.author) + our_delta)
        score.upsert(id=other.id, clacks_score=get_clacks(other) + other_delta)

        _L.info("Dilemma: resolved (%s/%s) cooperate %s -> %s",
                ctx.author.name, other.name, (our_choice, other_choice), (our_delta, other_delta))

        await ctx.author.send(
            "\u200bPrisoner's Dilemma: You matched with {} ({}). They decided to {}."
            "`you: {}, they: {}`".format(
                other.mention,
                str(other),
                "cooperate" if other_choice else "defect",
                our_delta,
                other_delta
            ))

        await other.send(
            "\u200bPrisoner's Dilemma: You matched with {} ({}). They decided to {}."
            "`you: {}, they: {}`".format(
                ctx.author.mention,
                str(ctx.author),
                choice,
                other_delta,
                our_delta
            ))

        other_choice = other_choice + 1 if other_choice < 0 else other_choice - 1
        if other_choice == 0:
            other_choice = None

        pd_pool.upsert(id=other.id, clacks_pd=other_choice)

@setup.command("whatisclack", hidden=True)
async def whatisclack(ctx):
    """
    Congratulations, you found the secrets to clacks.
    """
    return
    embed = discord.Embed(
        title="What is clacks?",
        description=
        "Clacks is a secret.\n"
        "Clacks is a discrete scalar unit.\n"
        "Clacks is a social experiment.\n"
        "\n"
        "Initially it was meant to be an easter egg (hence why all commands"
        " are hidden), but the novelty of this mystery has worn off."
        )

    embed.add_field(
        name="Part 1: Clack & Unclack",
        value=
        "Clack and Unclack are a pair of commands. Clack takes one clack from"
        " someone and gives it to you. Unclack does the opposite - gives one of"
        " your clacks to someone else."
        "\n\n"
        "The interesting things comes from the fact that clack has a small"
        " (10%) chance of giving you a clack while not actually taking it away"
        " from the other person. This occurs when the random number (at the end"
        " of the message) is less than 0.1."
        "\n\n"
        "So: do you be generous? Or do you steal others' clacks in hopes of a"
        " net benefit?"
        )

    embed.add_field(
        name="Part 2: Prisoner's Dilemma",
        value=
        "[Prisoner's dilemma](https://en.wikipedia.org/wiki/Prisoner%27s_dilemma)"
        " is a classic problem - the two players can either cooperate or"
        " defect. If both defect, both are punished. If both cooperate,"
        " both are rewarded. However, if one defects and one cooperates,"
        " the one who defects gets a large reward, and the other person"
        " gets a large punishment."
        "\n\n"
        "You can participate in this through `@Blender dilemma`, which matches"
        " you with a random other person. Read the help for that for more"
        " information."
        )

    # embed.add_field(
    #     name="Part 3: Daily clack",
    #     value=
    #     "
    await misc.send_deletable(ctx, embed)

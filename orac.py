#!/usr/bin/env python3

import re
from difflib import SequenceMatcher as SM
import urllib.parse as urlparse
import logging

import aiohttp
from bs4 import BeautifulSoup
import discord
from discord.ext import commands

from base import fragment

_L = logging.getLogger(__name__)

setup = fragment.Fragment()

async def fetch(session, url):
    """
    Async helper to send a GET request
    """
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()

@setup.listen("task")
async def load_problems():
    """
    Load all the problems
    """
    async with aiohttp.ClientSession() as session:
        req = await fetch(session, "http://orac.amt.edu.au/cgi-bin/train/hub.pl?expand=all")

def get_problems():
    """
    Get the orac problem page
    """
    req = requests.get("http://orac.amt.edu.au/cgi-bin/train/hub.pl?expand=all")
    req.raise_for_status()

    # fix some weird numbers being introduced
    text = re.sub(r"\r\n\d*\r\n", "", req.text)

    dom = BeautifulSoup(text, "html.parser")
    tags = dom.select("td.alert-success > a")

    global problems
    problems = {}

    for tag in tags:
        url = re.sub(r"^/", "http://orac.amt.edu.au/", tag['href'])
        attrs = urlparse.parse_qs(urlparse.urlparse(url).query)
        attrs['url'] = url
        problems[tag.text] = attrs

    return problems

def fuzzy_match(name: str):
    """
    Fuzzily match a problem name
    """
    best = (-1, None)
    for problem in problems:
        score = SM(a=name, b=problem).quick_ratio()
        if score > best[0]:
            best = (score, problem)

    return best

def get_solves(problem_id: int):
    """
    Get the number of solves for a problem
    """
    fame_url = "http://orac.amt.edu.au/cgi-bin/train/fame_detail.pl"
    req = requests.get(fame_url, params=dict(problemid=problem_id))

    dom = BeautifulSoup(req.text, "html.parser")
    solves = dom.select("ul.nav + b")[0]

    return int(solves.text)

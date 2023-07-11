#!/usr/bin/env python3

"""
Handle global configuration relevant to the base layer only
"""

import json
import logging
import random

_L = logging.getLogger(__name__)

with open("config.json") as config_file:
    CONFIG = json.load(config_file)

def get(key: str):
    """
    Get a config key
    """
    head = CONFIG
    for seg in key.split("."):
        head = head[seg]
    return head

def pick(key, *args, **kwargs):
    """
    Pick a random message
    """
    head = get(key)
    if not isinstance(head, str):
        head = random.choice(head)
    return head.format(config=CONFIG, R=CONFIG['strings'], *args, **kwargs)

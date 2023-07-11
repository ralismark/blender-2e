#!/usr/bin/env python3

"""
Standard tables for various things
"""

from . import sql

by_server = sql.Table("server")
by_channel = sql.Table("channel")
by_user = sql.Table("user")

table_map = {
    "server": by_server,
    "channel": by_channel,
    "user": by_user,
}

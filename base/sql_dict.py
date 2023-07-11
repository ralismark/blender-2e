#!/usr/bin/env python3

"""
A way to store key-value pairs
"""

assert False, "Incomplete"

from . import sql

class KeyValueTable:
    """
    A table which stores key-value pairs
    """

    def __init__(self, name: str):
        self._table = sql.Table(name)
        self._view = self._table.view({
            "key": (sql.TypeAffinity.TEXT, sql.AccessType.READWRITE),
            "value": (sql.TypeAffinity.BLOB, sql.AccessType.READWRITE)
            })

    def get(self, name: str, default = None):
        """
        Retrieve a value
        """
        result = self._view.select(["value"], key=name)
        if result:
            return result[0][0]
        else:
            return default

    def set(self, name: str, value):
        """
        Set a value
        """
        pass

    def pop(self, name: str):
        pass

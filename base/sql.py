#!/usr/bin/env python3

"""
Interface to the SQL database, allowing for multi-user access.

Note that this only provides the classes to do so; standard
tables are available from `sql_tables`.
"""

import asyncio
import contextvars
import enum
import functools
import logging
import sqlite3
import typing

from . import config

Data = typing.Union[None, int, float, str, bytes]

_L = logging.getLogger(__name__)

def _connect() -> sqlite3.Connection:
    """
    Create a connection
    """
    con = sqlite3.connect(config.get("sql.path"))
    con.row_factory = sqlite3.Row
    con.isolation_level = None
    return con

_SYNC_CON = None
_CTX_CON = contextvars.ContextVar("Connection to database")

def dbase():
    """
    Get the local database connection, creating it if needed
    """
    # pylint: disable=global-statement
    if asyncio.get_event_loop().is_running():
        global _CTX_CON
        # We're in async land
        try:
            return _CTX_CON.get()
        except LookupError:
            _CTX_CON.set(_connect())
            return _CTX_CON.get()
    else:
        global _SYNC_CON
        # Synchronous land
        if _SYNC_CON is None:
            _SYNC_CON = _connect()
        return _SYNC_CON


class AsyncAwareContextDecorator:
    """
    Just like contextlib.ContextDecorator, but preserves the async of the
    wrapped function.
    """

    def __enter__(self):
        raise NotImplementedError

    def __exit__(self, exc_type, exc_value, traceback):
        raise NotImplementedError

    def __call__(self, fun):
        """
        Decorate
        """
        if asyncio.iscoroutinefunction(fun):
            @functools.wraps(fun)
            async def wrapper(*args, **kwargs):
                with self:
                    return await fun(*args, **kwargs)
        else:
            @functools.wraps(fun)
            def wrapper(*args, **kwargs):
                with self:
                    return fun(*args, **kwargs)
        return wrapper


class Savepoint(AsyncAwareContextDecorator):
    """
    An actual SQLite transaction, with proper rollback/release.

    Due to each context having a separate connection, synchronisation is
    (hopefully) not needed.
    """

    def __enter__(self):
        dbase().execute("savepoint tx")
        _L.debug("Entering savepoint")

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_value is None:
            dbase().execute("release savepoint tx")
            _L.debug("Committing savepoint")
        else:
            dbase().execute("rollback transaction to savepoint tx")
            _L.debug("Reverting savepoint")

class Transaction(AsyncAwareContextDecorator):
    """
    A begin/commit/revert transaction
    """

    def __init__(self, kind="deferred"):
        if kind.casefold() not in ("deferred", "immediate", "exclusive"):
            raise ValueError("Invalid transaction type")
        self.kind = kind

    def __enter__(self):
        if dbase().in_transaction:
            raise RuntimeError("Not top-level transaction")
        dbase().execute(f"begin {self.kind}")
        _L.debug("Entering transaction")

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_value is None:
            dbase().execute("commit")
            _L.debug("Committing transaction")
        else:
            dbase().execute("rollback")
            _L.debug("Reverting transaction")

exclusive = Transaction()
transact = Savepoint()

def _ds_run(statement: str, *args, **kwargs):
    _L.debug("sql: %s", statement)
    return dbase().execute(statement, *args, **kwargs)

def esc(ident: str):
    """
    Escape an identifier for use in SQLite.

    This should used as late as possible - only when actually accessing the
    database. Don't escape early.
    """
    ident = str(ident)
    return '"' + ident.replace('"', '""') + '"'

class TypeAffinity(enum.Enum):
    """
    SQLite type affinities
    """
    TEXT = str
    NUMERIC = typing.Union[float, int]
    INTEGER = int
    REAL = float
    BLOB = bytes

    @staticmethod
    def from_str(aff: str) -> "TypeAffinity":
        """
        Determine the type affinity from the string.

        Following code based on rules from <https://www.sqlite.org/datatype3.html>.
        """
        aff = aff.upper() # NOTE does case matter?
        if "INT" in aff:
            return TypeAffinity.INTEGER
        if "CHAR" in aff or "CLOB" in aff or "TEXT" in aff:
            return TypeAffinity.TEXT
        if "BLOB" in aff:
            return TypeAffinity.BLOB
        if "REAL" in aff or "FLOA" in aff or "DOUB" in aff:
            return TypeAffinity.REAL
        return TypeAffinity.NUMERIC

class AccessType(enum.Flag):
    """
    Possible access permissions
    """
    READONLY = 0b01
    READWRITE = 0b11

    def includes(self, val):
        """
        Check if permission contains another
        """
        return (self.value & val.value) == val.value

class Table:
    """
    A table. This should not be publicly instantiated.
    """

    def __init__(self, name: str, id_decl: str = "INTEGER UNIQUE NOT NULL"):
        _L.info("registering table: name=%s id=%s -> %r", name, id_decl, self)
        self.name = name

        # migration use
        self.active_cols = set()
        self.deactivated_cols = set()

        _ds_run("CREATE TABLE IF NOT EXISTS {} (id {})".format(esc(name), id_decl))

    def __str__(self):
        return self.name

    def view(self, fields: typing.Dict[str, typing.Tuple[TypeAffinity, AccessType]]) -> "View":
        """
        Create a view based off this table
        """
        # implicit id
        fields.setdefault("id", (TypeAffinity.INTEGER, AccessType.READWRITE))
        return View(self, fields)

    def columns(self) -> typing.Dict[str, TypeAffinity]:
        """
        Get the columns of the table
        """
        columns = {}
        for row in _ds_run(f"PRAGMA table_info({esc(self)})"):
            columns[row["name"]] = TypeAffinity.from_str(row["type"])
        return columns

    def migrate(self, old, new):
        """
        Attempt to migrate column `old` to `new`. This does not do type checking.
        """
        if old == new:
            raise ValueError(f"Attempting to migrate column `{old}` of table `{self}` to itself")

        if new not in self.active_cols:
            raise ValueError(f"Migration target column `{new}` in table `{self}` does not exist"
                             " - Create appropriate view first")
        if old in self.active_cols:
            raise ValueError(f"Migration source column `{old}` in table `{self} is in use")

        # only actually migrate if the old column exists
        if old in self.columns():
            with transact:
                tbl = esc(self)
                _ds_run(f"UPDATE {tbl} SET {esc(new)}={esc(old)} where {esc(new)} IS NOT NULL")
                _ds_run(f"ALTER {tbl} DROP COLUMN {esc(old)}")

        self.deactivated_cols.add(old)

    def dump_tsv(self) -> str:
        """
        Dump the table as a TSV
        """
        rows = _ds_run(f"SELECT * FROM {esc(self)}")
        out = "\t".join(col[0] for col in rows.description) + "\n"
        for row in rows:
            out += "\t".join(map(str, row)) + "\n"
        return out


class View:
    """
    A restricted view into a table. This ensures the handling of it is done
    correctly, and limits access to only the fields requested.
    """

    def __init__(self,
                 table: Table,
                 fields: typing.Dict[str, typing.Tuple[TypeAffinity, AccessType]]):
        """
        Initialise.

        Fields is a dict of access requirements.
        """
        _L.info("creating view: table=%s fields=[%s] -> %r",
                table, ", ".join(f"{k}: {v[0].name}/{v[1].name}" for k, v in fields.items()), self)
        self._table = table
        self._fields = fields

        columns = table.columns()

        with transact:
            for name, decl in fields.items():
                if name in table.deactivated_cols:
                    raise ValueError(f"Column '{name}' in table '{table}' has been deactivated")
                if name in columns and columns[name] != decl[0]:
                    raise ValueError(f"Column '{name}' in table '{table}' already exists"
                                     f" but has a different type affinity"
                                     f" (existing {columns[name].name} != given {decl[0].name})")
                if name not in columns:
                    # Create column
                    _ds_run(f"ALTER TABLE {esc(table)} ADD COLUMN {esc(name)} {decl[0].name}")

        self._table.active_cols.update(fields.keys())

    def union(self, other: "View") -> "View":
        """
        Create a View from the union of two views.
        """
        # pylint: disable=protected-access
        if self._table != other._table:
            raise ValueError("Cannot create union across different tables"
                             f" '{self._table}' and '{other._table}'")

        fields = self._fields.copy()
        for name, decl in other._fields.items():
            # add fields from other view
            if name not in fields:
                fields[name] = decl
            else:
                affinity, access = decl
                if fields[name][0] != affinity:
                    # NOTE I don't think this is possible - differing affinity
                    # should have been caught at initialisation
                    raise ValueError(f"Column '{name}' in table '{self._table}' has differing"
                                     " type affinities for the two views"
                                     " ({fields[name][0].name} != {affinity})")
                combined_access = access | fields[name][1]
                fields[name] = (affinity, combined_access)

        return View(self._table, fields)



    def select(self, *fields: typing.Iterable[str], **criteria) -> typing.List[sqlite3.Row]:
        """
        SQL SELECT query. This also checks that the specified fields are in the
        initially requested fields.
        """

        if not fields:
            # TODO this should be supported
            raise ValueError(f"Cannot select no columns")

        # checks
        for field in (f for f in fields if f not in self._fields):
            raise ValueError(f"Requested field '{field}' not part of initial specification")

        for check in (c for c in criteria if c not in self._fields):
            raise ValueError(f"Criterion on field '{check}' not part of initial specification")

        params = []

        where = ""

        checks = []
        for field, crit in criteria.items():
            if not isinstance(crit, list):
                crit = [crit]

            for check in crit:
                if not isinstance(check, tuple):
                    # Equal criteria
                    checks.append(f"{esc(field)} IS ?")
                    params.append(check)
                elif check[0] in ("=", "equal"):
                    checks.append(f"{esc(field)} IS ?")
                    params.append(check[1])
                elif check[0] in ("!=", "unequal", "notequal"):
                    checks.append(f"{esc(field)} IS NOT ?")
                    params.append(check[1])
                elif check[0] in ("nonnull", "notnull"):
                    checks.append(f"{esc(field)} IS NOT NULL")
                elif check[0] in ("<", "lt", "less"):
                    checks.append(f"{esc(field)} < ?")
                    params.append(check[1])
                elif check[0] in (">", "gt", "greater"):
                    checks.append(f"{esc(field)} > ?")
                    params.append(check[1])

        where += " AND ".join(checks)
        if where:
            where = " WHERE " + where

        query = "SELECT {} FROM {}{}".format(", ".join(map(esc, fields)), self._table, where)

        return _ds_run(query, params).fetchall()

    def upsert(self, **data):
        """
        Perform an insert or replace.
        """
        if not data:
            # TODO should this be an error?
            return

        for field in data:
            if field not in self._fields:
                raise ValueError(f"Target field '{field}' not part of initial specification")
            if not self._fields[field][1].includes(AccessType.READWRITE):
                raise ValueError(f"Target field '{field}' does not have sufficient permissions" +
                                 " (required '{}' > specified '{}')".format(
                                     AccessType.READWRITE,
                                     self._fields[field][1]
                                 ))

        fields = []
        params = []
        for key, val in data.items():
            fields.append(key)
            params.append(val)

        # TODO use actual upsert when it becomes available
        # statement = "INSERT INTO {} ({}) VALUES ({}) ON CONFLICT (id) DO UPDATE SET {}".format(
        #     esc(self._table),
        #     ", ".join(map(esc, fields)),
        #     ", ".join("?" for f in fields),
        #     ", ".join(f"{esc(k)}=excluded.{esc(k)}" for k in data if k != "id"))

        insert = "INSERT INTO {} ({}) VALUES ({})".format(
            esc(self._table),
            ", ".join(map(esc, fields)),
            ", ".join("?" for f in fields))

        update = "UPDATE {} SET {} WHERE id=?".format(
            esc(self._table),
            ", ".join(f"{esc(f)}=?" for f in fields))

        try:
            _ds_run(insert, params)
        except sqlite3.DatabaseError:
            _ds_run(update, params + [data["id"]])

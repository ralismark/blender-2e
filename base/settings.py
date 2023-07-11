#!/usr/bin/env python3

"""
Provide a unified interface for per-server settings. User-facing API is in
settings_user.py
"""

import abc
import enum
import inspect
import logging
import typing

import discord
from discord.ext import commands

from . import sql, sql_tables

_L = logging.getLogger(__name__)
_SETTINGS = {}

class Scope(enum.Enum):
    """
    Scope of an option
    """
    SERVER = enum.auto()
    # CATEGORY = 2 -- currently not supported
    CHANNEL = enum.auto()

    @staticmethod
    def from_str(scope: str) -> "Scope":
        """
        Get the corresponding enum from a string specifying a name
        """
        scope = scope.casefold()
        for entry in Scope:
            if entry.name.casefold() == scope:
                return entry
        return None

class ScopedSettingBase(abc.ABC):
    """
    A base class for settings with scope
    """
    def __init__(self, *, name: str, type_affinity: sql.TypeAffinity,
                 description: str = None, internal: bool = False, **kwargs):
        super().__init__(**kwargs)
        _L.info("registering scoped setting: name=%s type=%s -> %r", name, type_affinity, self)

        self.name = f"setting.{name}"
        self.affinity = type_affinity
        self.description = description

        # FIXME Old settings are not removed when extensions are unloaded.
        #
        # This is not really a major issue - there won't be problems with users
        # setting this setting, and base.sql can safely handle multiple
        # identical views.
        if not internal:
            _SETTINGS[name] = self

    def make_accessors(self, target_id: int, view: sql.View):
        """
        Helper function to make accessors from target_id and view
        """
        getter = lambda: (view.select(self.name, id=target_id) or [[None]])[0][0]
        def setter(val):
            with sql.exclusive:
                view.upsert(id=target_id, **{self.name: val})

        return getter, setter

    @abc.abstractmethod
    def get_accessors(self, target: discord.Message, scope: Scope) -> \
            typing.Tuple[typing.Callable[[], sql.Data], typing.Callable[[sql.Data], None]]:
        """
        Returns the getter and setter in a tuple relevant to a given message
        and scope, throwing NotImplementedError if nothing appropriate.
        """

    def set(self, target: typing.Union[commands.Context, discord.Message],
            value: sql.Data, scope: Scope = Scope.SERVER):
        """
        Change the setting value in a certain target context and scope. Throws
        NotImplementedError (from get_accessors) is not supported.
        """
        if isinstance(target, commands.Context):
            target = target.message

        _, setter = self.get_accessors(target, scope)
        _L.debug("ScopedSetting.set: name=%s scope=%s value=%s",
                 self.name, scope.name, value)
        setter(value)

    def get(self, target: typing.Union[commands.Context, discord.Message]) -> sql.Data:
        """
        Retrieve the value for a given target context, going down the scope
        order if not supported or not set. Returns None is not set for any
        scope.
        """
        if isinstance(target, commands.Context):
            target = target.message

        for scope in (Scope.CHANNEL, Scope.SERVER):
            try:
                getter, _ = self.get_accessors(target, scope)
            except NotImplementedError:
                continue
            value = getter()
            if value is not None:
                _L.debug("ScopedSetting.get: name=%s -> scope=%s -> %s",
                         self.name, scope.name, value)
                return value
        _L.debug("ScopedSetting.get: name=%s -> None (no scopes)", self.name)
        return None

    def check(self, condition: typing.Callable[[sql.Data], bool] = lambda _: True):
        """
        A check decorator, testing if a setting is set, and also if it passes a
        condition (if given).
        """
        async def check_impl(ctx):
            value = self.get(ctx.message)
            if value is None:
                return False
            if inspect.iscoroutinefunction(condition):
                return await condition(value)
            return condition(value)

        return commands.check(check_impl)

class DeadSetting(ScopedSettingBase):
    """
    A setting which no longer exists. This can be used for migration.
    """
    def __init__(self, *, scopes: typing.Iterable[Scope] = list(Scope), **kwargs):
        super().__init__(internal=True, **kwargs)

        self.scopes = scopes
        self.migrated_to = None

    def migrate_to(self, target: ScopedSettingBase):
        """
        Migrate this setting to another one. Settings must match.
        """
        if self.affinity != target.affinity:
            raise ValueError("Target affinity differs from own affinity")

        if self.migrated_to is not None:
            raise ValueError("Dead setting already migrated")

        # FIXME we do not check that target use the same scopes as this
        #
        # As such, the target might not actually support the given scopes,
        # creating columns/entries in the database that aren't ever referenced.

        scope2table = {
            Scope.CHANNEL: sql_tables.by_channel,
            Scope.SERVER: sql_tables.by_server,
        }

        for scope in self.scopes:
            table = scope2table[scope]
            # XXX this directly touches the tables
            table.migrate(self.name, target.name)

        self.migrated_to = target

    def get_accessors(self, target: discord.Message, scope: Scope):
        """
        Accessors are not available since this setting is dead
        """
        raise NotImplementedError("Setting is dead")

class ScopedSetting(ScopedSettingBase):
    """
    A setting which can have different granularity
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.server_view = sql_tables.by_server.view({
            self.name: (self.affinity, sql.AccessType.READWRITE)
            })
        self.channel_view = sql_tables.by_channel.view({
            self.name: (self.affinity, sql.AccessType.READWRITE)
            })

    def get_accessors(self, target: discord.Message, scope: Scope):
        """
        Returns the getter and setter in a tuple relevant to a given message
        and scope.
        """
        if scope == Scope.SERVER:
            return self.make_accessors(target.guild.id, self.server_view)
        if scope == Scope.CHANNEL:
            return self.make_accessors(target.channel.id, self.channel_view)
        raise NotImplementedError("Invalid scope")

class Setting(ScopedSettingBase):
    """
    A single server-wide configuration option
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.server_view = sql_tables.by_server.view({
            self.name: (self.affinity, sql.AccessType.READWRITE)
            })

    def get_accessors(self, target: discord.Message, scope: Scope):
        if scope == Scope.SERVER:
            return self.make_accessors(target.guild.id, self.server_view)
        raise NotImplementedError("Server scope only")

def truthy(expr):
    """
    Check if expression is truthy
    """
    if expr is None:
        return None

    try:
        return bool(int(expr))
    except ValueError:
        pass

    if isinstance(expr, str):
        if expr.casefold() in ("true", "y", "yes"):
            return True
        if expr.casefold() in ("false", "n", "no"):
            return False

    raise ValueError(f"cannot parse to bool: {repr(expr)}")


# TODO this probably should be a metaclass
def _as_toggle(kind):
    class ToggleSetting(kind):
        """
        A setting that can only be on or off.

        Toggle.enabled is a decorator that checks if the option is set and enabled.
        """

        def __init__(self, **kwargs):
            super().__init__(type_affinity=sql.TypeAffinity.INTEGER, **kwargs)

            # available check
            self.enabled = self.check(bool)

        def get_accessors(self, target: discord.Message, scope: Scope):
            """
            Convert value before settings
            """
            getter, setter = super().get_accessors(target, scope)
            wrapped_setter = lambda data: setter(truthy(data))
            return (getter, wrapped_setter)

    return ToggleSetting

Toggle = _as_toggle(Setting)
ScopedToggle = _as_toggle(ScopedSetting)

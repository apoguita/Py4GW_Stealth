"""Public entry points for Win32 process discovery."""

from typing import Any

from .win32 import Win32


def list_processes() -> list[dict[str, Any]]:
    """Return the currently running Guild Wars client records."""

    return Win32().find_guild_wars()


__all__ = ["Win32", "list_processes"]

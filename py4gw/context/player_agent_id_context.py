"""External reader for the game global holding the player's agent id.

Native ``Context::GetObservingId()`` returns ``*g_player_agent_id_addr``: the
client keeps the agent id of the character you control in a module global, and
while you spectate a match that same global holds the agent you are observing.
It is therefore the registered player agent id, not a DLL-owned value.

``agent.player_agent_id_addr`` resolves scan -> dereference -> validate, so the
resolved value is a stable address inside the client's data section and the id
is one read away. Under this project's caching rule the address is resolved once
and the id is read fresh on every call; see ``docs/READINESS_GATE.md``.
"""

from __future__ import annotations

from ..helpers.target_struct import TargetStruct

import ctypes
from ctypes import Structure, c_uint32
from typing import Any, Protocol, cast

from ..scanner import PatternCatalog, RemoteScanner
from .gw_array import RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by the external context reader."""


class PlayerAgentIdStruct(TargetStruct):
    """The value stored at the player-agent-id global."""

    _pack_ = 1
    _fields_ = [("agent_id", c_uint32)]


assert ctypes.sizeof(PlayerAgentIdStruct) == 0x04


class PlayerAgentId:
    """Resolve the global once and read the current player agent id per call."""

    # Source-compatible static facade state. The injected source updates this
    # through a callback; the external reader refreshes it explicitly.
    _ptr: int = 0
    _cached_ctx: PlayerAgentIdStruct | None = None
    _callback_name = "PlayerAgentIdContext.UpdatePtr"

    _RESOLVER = "agent.player_agent_id_addr"

    def __init__(
        self,
        reader: _memory_reader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
    ) -> None:
        """Create a reader backed by one process and its offset catalog."""

        self._reader = reader
        self._scanner = scanner
        self._patterns = patterns
        self._pointer_address: int | None = None

    @staticmethod
    def get_ptr() -> int:
        """Return the last externally refreshed player-agent-id address."""

        return PlayerAgentId._ptr

    @staticmethod
    def _update_ptr() -> None:
        """Refresh the source-compatible facade from the selected client."""

        from ..client import current_client

        client = current_client()
        if client is None:
            PlayerAgentId._ptr = 0
            PlayerAgentId._cached_ctx = None
            return
        try:
            context = client.player_agent_id
            address = context.resolve_address()
            PlayerAgentId._ptr = address or 0
            PlayerAgentId._cached_ctx = cast(Any, context.read())
        except (OSError, RuntimeError):
            PlayerAgentId._ptr = 0
            PlayerAgentId._cached_ctx = None

    @staticmethod
    def enable() -> None:
        """Declare the source callback operation; callbacks require injection."""

        raise NotImplementedError(
            "PlayerAgentId.enable requires the in-process callback runtime."
        )

    @staticmethod
    def disable() -> None:
        """Clear the external facade cache."""

        PlayerAgentId._ptr = 0
        PlayerAgentId._cached_ctx = None

    @staticmethod
    def get_context() -> PlayerAgentIdStruct | None:
        """Return the last snapshot refreshed through ``_update_ptr``."""

        return PlayerAgentId._cached_ctx

    def initialize(self) -> int | None:
        """Scan once and cache the stable global address."""

        if self._pointer_address is None:
            result = self._patterns.resolve(self._RESOLVER, self._scanner)
            if not result.ok:
                detail = result.message or "the resolver returned no address"
                raise RuntimeError(f"{self._RESOLVER} failed: {detail}")
            self._pointer_address = result.value
        return self._pointer_address or None

    def resolve_address(self) -> int | None:
        """Return the cached global address, if it is available."""

        if self._pointer_address is None:
            return self.initialize()
        return self._pointer_address or None

    @property
    def cached_pointer_address(self) -> int | None:
        """Return the cached global address, if initialized."""

        return self._pointer_address

    def read(self) -> PlayerAgentIdStruct | None:
        """Read the current player agent id through a fresh read."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_context = self._reader.read(
            address, ctypes.sizeof(PlayerAgentIdStruct)
        )
        return PlayerAgentIdStruct.from_buffer_copy(raw_context)


def get() -> PlayerAgentIdStruct | None:
    """Read the player agent id of the current client, if available."""

    from ..client import current_client

    client = current_client()
    return cast(Any, client.read_player_agent_id() if client is not None else None)

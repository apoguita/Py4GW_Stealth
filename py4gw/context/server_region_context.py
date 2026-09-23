"""External layout and reader for Reforged's ``ServerRegion`` value."""

from __future__ import annotations

from ..target_struct import TargetStruct

import ctypes
from ctypes import Structure, c_int32
from typing import Any, Protocol, cast

from ..scanner import PatternCatalog, RemoteScanner
from .gw_array import RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by the external context reader."""


class ServerRegionStruct(TargetStruct):
    """The fixed-width x86 port of Reforged ``ServerRegionStruct``."""

    _pack_ = 1
    _fields_ = [("region_id", c_int32)]


assert ctypes.sizeof(ServerRegionStruct) == 0x04


class ServerRegion:
    """Resolve and decode the current external server-region value."""

    # Source-compatible static facade state. The injected source updates this
    # through a callback; the external reader refreshes it explicitly.
    _ptr: int = 0
    _cached_ctx: ServerRegionStruct | None = None
    _callback_name = "ServerRegion.UpdatePtr"

    _RESOLVER = "map.region_id_addr"

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
        """Return the last externally refreshed server-region address."""

        return ServerRegion._ptr

    @staticmethod
    def _update_ptr() -> None:
        """Refresh the source-compatible facade from the selected client."""

        from ..client import current_client

        client = current_client()
        if client is None:
            ServerRegion._ptr = 0
            ServerRegion._cached_ctx = None
            return
        try:
            context = client.server_region
            address = context.resolve_address()
            ServerRegion._ptr = address or 0
            ServerRegion._cached_ctx = cast(Any, context.read())
        except (OSError, RuntimeError):
            ServerRegion._ptr = 0
            ServerRegion._cached_ctx = None

    @staticmethod
    def enable() -> None:
        """Declare the source callback operation; callbacks require injection."""

        raise NotImplementedError(
            "ServerRegion.enable requires the in-process callback runtime."
        )

    @staticmethod
    def disable() -> None:
        """Clear the external facade cache."""

        ServerRegion._ptr = 0
        ServerRegion._cached_ctx = None

    @staticmethod
    def get_context() -> ServerRegionStruct | None:
        """Return the last snapshot refreshed through ``_update_ptr``."""

        return ServerRegion._cached_ctx

    def resolve_address(self) -> int | None:
        """Return the current region-value address, if it is available."""

        if self._pointer_address is None:
            return self.initialize()
        return self._pointer_address or None

    def initialize(self) -> int | None:
        """Scan once and cache the stable region-value address."""

        if self._pointer_address is None:
            result = self._patterns.resolve(self._RESOLVER, self._scanner)
            if not result.ok:
                detail = result.message or "the resolver returned no address"
                raise RuntimeError(f"{self._RESOLVER} failed: {detail}")
            self._pointer_address = result.value
        return self._pointer_address or None

    @property
    def cached_pointer_address(self) -> int | None:
        """Return the cached region-value address, if initialized."""

        return self._pointer_address

    def read(self) -> ServerRegionStruct | None:
        """Read and decode the current server-region value."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_context = self._reader.read(
            address, ctypes.sizeof(ServerRegionStruct)
        )
        return ServerRegionStruct.from_buffer_copy(raw_context)


def get() -> ServerRegionStruct | None:
    """Read the server region of the current selected client, if available."""

    from ..client import current_client

    client = current_client()
    return cast(Any, client.read_server_region() if client is not None else None)

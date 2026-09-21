"""External layout and reader for Reforged's ``ServerRegion`` value."""

from __future__ import annotations

import ctypes
from ctypes import Structure, c_int32
from typing import Protocol

from ..scanner import PatternCatalog, RemoteScanner
from .gw_array import RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by the external context reader."""


class ServerRegionStruct(Structure):
    """The fixed-width x86 port of Reforged ``ServerRegionStruct``."""

    _pack_ = 1
    _fields_ = [("region_id", c_int32)]


assert ctypes.sizeof(ServerRegionStruct) == 0x04


class ServerRegion:
    """Resolve and decode the current external server-region value."""

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
    return client.read_server_region() if client is not None else None

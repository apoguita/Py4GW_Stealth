"""External readers for Guild Wars intrusive ``GwList`` values."""

from __future__ import annotations

import ctypes
from ctypes import c_uint32
from typing import Generic, Protocol, TypeVar, cast


class RemoteMemoryReader(Protocol):
    """The byte-reading operation needed by a remote list view."""

    def read(self, address: int, size: int) -> bytes: ...


class GWLinkStruct(ctypes.Structure):
    """The fixed-width x86 ``GW::GwLink`` node pointers."""

    _pack_ = 1
    _fields_ = [
        ("prev_link", c_uint32),
        ("next_node", c_uint32),
    ]


class GWListStruct(ctypes.Structure):
    """The fixed-width x86 ``GW::GwList`` header and sentinel link."""

    _pack_ = 1
    _fields_ = [
        ("offset", c_uint32),
        ("link", GWLinkStruct),
    ]


assert ctypes.sizeof(GWLinkStruct) == 0x08
assert ctypes.sizeof(GWListStruct) == 0x0C


_element_type = TypeVar("_element_type", bound=ctypes.Structure)


class RemoteGWListView(Generic[_element_type]):
    """Read a bounded native intrusive list from another process."""

    def __init__(
        self,
        reader: RemoteMemoryReader,
        list_header: GWListStruct,
        list_address: int,
        element_type: type[_element_type],
        max_entries: int = 1024,
    ) -> None:
        """Create a view over one target list header and its element type."""

        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        self._reader = reader
        self._list_header = list_header
        self._list_address = list_address
        self._element_type = element_type
        self._max_entries = max_entries

    def to_list(self) -> list[_element_type]:
        """Read list elements until the sentinel, a loop, or the safety cap."""

        next_node = int(self._list_header.link.next_node)
        if not next_node or next_node & 1:
            return []

        link_offset = int(self._list_header.offset)
        current_link = self._list_address + GWListStruct.link.offset
        visited: set[int] = set()
        result: list[_element_type] = []

        for _ in range(self._max_entries):
            node_address = next_node & ~1
            if node_address < 0x10000 or node_address in visited:
                break
            visited.add(node_address)

            raw_element = self._reader.read(
                node_address, ctypes.sizeof(self._element_type)
            )
            element = cast(
                _element_type,
                self._element_type.from_buffer_copy(raw_element),
            )
            bind_reader = getattr(element, "bind_reader", None)
            if callable(bind_reader):
                element = cast(
                    _element_type,
                    bind_reader(self._reader, node_address),
                )
            result.append(element)

            current_link = node_address + link_offset
            raw_link = self._reader.read(current_link, ctypes.sizeof(GWLinkStruct))
            next_node = GWLinkStruct.from_buffer_copy(raw_link).next_node
            if not next_node or next_node & 1:
                break

        return result

    def __iter__(self):
        return iter(self.to_list())

    def __len__(self) -> int:
        return len(self.to_list())


__all__ = ["GWLinkStruct", "GWListStruct", "RemoteGWListView"]

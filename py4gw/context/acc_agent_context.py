"""External reader for Reforged's maintained ``AccAgentContext`` surface.

The Reforged Python name is ``AccAgentContext`` while the native root is
``GW::Context::AgentContext``.  The root is reached directly through
``GameContext.agent``; no callback or new signature is needed here.
"""

from __future__ import annotations

import ctypes
from ctypes import Structure, c_float, c_uint8, c_uint32
from typing import Any, Protocol, TypeVar, cast

from .game_context import GameContext, GameContextStruct
from .gw_array import GWArray, GWArrayValueView, GWArrayView, RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by nested agent records."""


_value_type = TypeVar("_value_type")


def _read_encoded_wide(reader: _memory_reader, address: int, limit: int = 256) -> str:
    """Read one bounded target UTF-16 string through an x86 pointer."""

    if address < 0x10000:
        return ""
    raw = bytearray()
    for index in range(limit):
        pair = reader.read(address + index * 2, 2)
        if pair == b"\x00\x00":
            break
        raw.extend(pair)
    return bytes(raw).decode("utf-16-le", errors="replace")


def _format_encoded_text(value: str) -> str:
    """Display printable text while preserving Guild Wars encoded values."""

    output: list[str] = []
    for character in value:
        code_point = ord(character)
        if 32 <= code_point <= 126:
            output.append(character)
        elif character == "\n":
            output.append("\\n")
        elif character == "\t":
            output.append("\\t")
        else:
            output.append(f"\\x{code_point:04X}")
    return "".join(output)


class Vec3fStruct(Structure):
    """The native three-float vector used by ``AgentMovement``."""

    _pack_ = 1
    _fields_ = [("x", c_float), ("y", c_float), ("z", c_float)]


class AgentSummaryInfoSubStruct(Structure):
    """The native 0x1C gadget-summary extension record."""

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint32),
        ("h0004", c_uint32),
        ("gadget_id", c_uint32),
        ("h000C", c_uint32),
        ("gadget_name_enc", c_uint32),
        ("h0014", c_uint32),
        ("composite_agent_id", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> AgentSummaryInfoSubStruct:
        """Attach the reader used by the indirect gadget-name pointer."""

        self._remote_reader = reader
        return self

    @property
    def gadget_name_encoded_str(self) -> str:
        """Read the encoded gadget name through the target pointer."""

        if self._remote_reader is None:
            return ""
        return _read_encoded_wide(self._remote_reader, int(self.gadget_name_enc))

    @property
    def gadget_name_str(self) -> str:
        """Return a display-safe gadget name."""

        return _format_encoded_text(self.gadget_name_encoded_str)


class AgentSummaryInfoStruct(Structure):
    """The native 0x0C agent-summary record."""

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint32),
        ("h0004", c_uint32),
        ("extra_info_sub_ptr", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> AgentSummaryInfoStruct:
        """Attach the reader used by the nested summary extension."""

        self._remote_reader = reader
        return self

    @property
    def extra_info_sub(self) -> AgentSummaryInfoSubStruct | None:
        """Read the optional gadget-summary extension."""

        address = int(self.extra_info_sub_ptr)
        if address < 0x10000:
            return None
        if self._remote_reader is None:
            raise RuntimeError("This agent summary is not bound to a memory reader.")
        raw = self._remote_reader.read(
            address, ctypes.sizeof(AgentSummaryInfoSubStruct)
        )
        return AgentSummaryInfoSubStruct.from_buffer_copy(raw).bind_reader(
            self._remote_reader, address
        )


class AgentMovementStruct(Structure):
    """The native 0x80 movement record."""

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint32 * 3),
        ("agent_id", c_uint32),
        ("h0010", c_uint32 * 3),
        ("agent_def", c_uint32),
        ("h0020", c_uint32 * 6),
        ("moving1", c_uint32),
        ("h003C", c_uint32 * 2),
        ("moving2", c_uint32),
        ("h0048", c_uint32 * 7),
        ("h0064", Vec3fStruct),
        ("h0070", c_uint32),
        ("h0074", Vec3fStruct),
    ]


class AccAgentContextStruct(Structure):
    """The complete maintained native ``AgentContext`` layout."""

    _pack_ = 1
    _fields_ = [
        ("h0000_array", GWArray),
        ("h0010", c_uint32 * 5),
        ("h0024", c_uint32),
        ("h0028", c_uint32 * 2),
        ("h0030", c_uint32),
        ("h0034", c_uint32 * 2),
        ("h003C", c_uint32),
        ("h0040", c_uint32 * 2),
        ("h0048", c_uint32),
        ("h004C", c_uint32 * 2),
        ("h0054", c_uint32),
        ("h0058", c_uint32 * 11),
        ("h0084_array", GWArray),
        ("h0094", c_uint32),
        ("agent_summary_info_array", GWArray),
        ("h00A8_array", GWArray),
        ("h00B8_array", GWArray),
        ("rand1", c_uint32),
        ("rand2", c_uint32),
        ("h00D0", c_uint8 * 24),
        ("agent_movement_array", GWArray),
        ("h00F8_array", GWArray),
        ("h0108", c_uint32 * 0x11),
        ("h014C_array", GWArray),
        ("h015C_array", GWArray),
        ("h016C", c_uint32 * 0x10),
        ("instance_timer", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> AccAgentContextStruct:
        """Attach the reader used by all nested array properties."""

        self._remote_reader = reader
        return self

    def _require_reader(self) -> _memory_reader:
        if self._remote_reader is None:
            raise RuntimeError("This agent context is not bound to a memory reader.")
        return self._remote_reader

    def _values(
        self, array: GWArray, element_type: type[_value_type]
    ) -> list[_value_type]:
        return list(GWArrayValueView(self._require_reader(), array, element_type))

    def _pointer_values(self, array: GWArray) -> list[int]:
        return [int(cast(Any, value)) for value in self._values(array, c_uint32)]

    @property
    def h0000_ptrs(self) -> list[int]:
        return self._pointer_values(self.h0000_array)

    @property
    def h0084_ptrs(self) -> list[int]:
        return self._pointer_values(self.h0084_array)

    @property
    def agent_summary_info_list(self) -> list[AgentSummaryInfoStruct]:
        return cast(
            list[AgentSummaryInfoStruct],
            self._values(self.agent_summary_info_array, AgentSummaryInfoStruct),
        )

    @property
    def h00A8_ptrs(self) -> list[int]:
        return self._pointer_values(self.h00A8_array)

    @property
    def h00B8_ptrs(self) -> list[int]:
        return self._pointer_values(self.h00B8_array)

    @property
    def agent_movement_ptrs(self) -> list[AgentMovementStruct]:
        return cast(
            list[AgentMovementStruct],
            GWArrayView(
                self._require_reader(),
                self.agent_movement_array,
                AgentMovementStruct,
            ).to_list(),
        )

    @property
    def valid_agents_ids(self) -> list[int]:
        """Return indexes whose movement pointers are currently non-null."""

        pointers = self._pointer_values(self.agent_movement_array)
        return [index for index, pointer in enumerate(pointers) if pointer >= 0x10000]

    @property
    def h00F8_ptrs(self) -> list[int]:
        return self._pointer_values(self.h00F8_array)

    @property
    def h014C_ptrs(self) -> list[int]:
        return self._pointer_values(self.h014C_array)

    @property
    def h015C_ptrs(self) -> list[int]:
        return self._pointer_values(self.h015C_array)


assert ctypes.sizeof(Vec3fStruct) == 0x0C
assert ctypes.sizeof(AgentSummaryInfoSubStruct) == 0x1C
assert ctypes.sizeof(AgentSummaryInfoStruct) == 0x0C
assert ctypes.sizeof(AgentMovementStruct) == 0x80
assert ctypes.sizeof(AccAgentContextStruct) == 0x1B0
assert AccAgentContextStruct.agent_summary_info_array.offset == 0x98
assert AccAgentContextStruct.agent_movement_array.offset == 0xE8
assert AccAgentContextStruct.h014C_array.offset == 0x14C
assert AccAgentContextStruct.h015C_array.offset == 0x15C
assert AccAgentContextStruct.instance_timer.offset == 0x1AC


class AccAgentContext:
    """Resolve and read the current native agent context."""

    def __init__(self, reader: _memory_reader, game_context: GameContext) -> None:
        """Create a reader using the connected client's cached GameContext."""

        self._reader = reader
        self._game_context = game_context

    def resolve_address(self) -> int | None:
        """Return the current agent-context address, if available."""

        game_address = self._game_context.resolve_address()
        raw_pointer = self._reader.read(
            game_address + GameContextStruct.agent_context.offset, 4
        )
        address = int.from_bytes(raw_pointer, "little")
        return address or None

    def read(self) -> AccAgentContextStruct | None:
        """Read and decode the complete maintained agent structure."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_context = self._reader.read(address, ctypes.sizeof(AccAgentContextStruct))
        return AccAgentContextStruct.from_buffer_copy(raw_context).bind_reader(
            self._reader, address
        )


AgentContext = AccAgentContext
AgentContextStruct = AccAgentContextStruct
Vec3f = Vec3fStruct
AgentSummaryInfoSub = AgentSummaryInfoSubStruct
AgentSummaryInfo = AgentSummaryInfoStruct
AgentMovement = AgentMovementStruct


def get() -> AccAgentContextStruct | None:
    """Read the agent context of the current selected client, if available."""

    from ..client import current_client

    client = current_client()
    return client.read_acc_agent_context() if client is not None else None

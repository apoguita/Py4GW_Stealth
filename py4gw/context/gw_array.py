"""External readers for Reforged's fixed-width ``GW_Array`` values.

Reforged can use ``ctypes`` pointers because it runs inside Guild Wars.  An
external reader must treat every pointer as a target-process address and read
the pointed-to bytes through its memory reader.  These views keep the same
array concepts while making that boundary explicit.
"""

from __future__ import annotations

import ctypes
from ctypes import Structure, c_uint32
from typing import Any, Protocol


class RemoteMemoryReader(Protocol):
    """The byte-reading operation needed by an external array view."""

    def read(self, address: int, size: int) -> bytes: ...


class GWBaseArray(Structure):
    """The 32-bit ``GW::BaseArray`` layout used by the target process."""

    _pack_ = 1
    _fields_ = [
        ("m_buffer", c_uint32),
        ("m_capacity", c_uint32),
        ("m_size", c_uint32),
    ]


class GWArray(Structure):
    """The 32-bit ``GW::Array`` layout used by the target process."""

    _pack_ = 1
    _fields_ = [
        ("m_buffer", c_uint32),
        ("m_capacity", c_uint32),
        ("m_size", c_uint32),
        ("m_param", c_uint32),
    ]


assert ctypes.sizeof(GWBaseArray) == 0x0C
assert ctypes.sizeof(GWArray) == 0x10


def _decode_value(element_type: type[Any], raw: bytes) -> Any:
    """Decode one ctypes value from bytes read from the target process."""

    value = element_type.from_buffer_copy(raw)
    if isinstance(value, Structure):
        return value
    return value.value if hasattr(value, "value") else value


class GWArrayValueView:
    """Read contiguous values from a target-process ``GWArray``."""

    def __init__(
        self,
        reader: RemoteMemoryReader,
        array: GWArray,
        element_type: type[Any],
    ) -> None:
        self._reader = reader
        self._array = array
        self._element_type = element_type

    def valid(self) -> bool:
        """Return whether the header describes a bounded readable array."""

        return bool(self._array.m_buffer) and self._array.m_size <= self._array.m_capacity

    def size(self) -> int:
        """Return the number of elements advertised by the target."""

        return int(self._array.m_size)

    def capacity(self) -> int:
        """Return the target array capacity."""

        return int(self._array.m_capacity)

    def get(self, index: int) -> Any:
        """Read one value, returning ``None`` for an invalid index."""

        if not self.valid() or index < 0 or index >= self.size():
            return None
        element_size = ctypes.sizeof(self._element_type)
        raw = self._reader.read(self._array.m_buffer + index * element_size, element_size)
        value = _decode_value(self._element_type, raw)
        bind_reader = getattr(value, "bind_reader", None)
        if callable(bind_reader):
            return bind_reader(self._reader, self._array.m_buffer + index * element_size)
        return value

    def to_list(self) -> list[Any]:
        """Read all values in the bounded target array."""

        if not self.valid():
            return []
        return [value for index in range(self.size()) if (value := self.get(index)) is not None]

    def __len__(self) -> int:
        return self.size()

    def __getitem__(self, index: int) -> Any:
        value = self.get(index)
        if value is None:
            raise IndexError(index)
        return value

    def __iter__(self):
        return iter(self.to_list())

    def __reversed__(self):
        return reversed(self.to_list())


class GWArrayView:
    """Read an array of target pointers and decode each pointed-to object."""

    def __init__(
        self,
        reader: RemoteMemoryReader,
        array: GWArray,
        element_type: type[Any],
    ) -> None:
        self._reader = reader
        self._array = array
        self._element_type = element_type

    def valid(self) -> bool:
        """Return whether the header describes a bounded readable array."""

        return bool(self._array.m_buffer) and self._array.m_size <= self._array.m_capacity

    def size(self) -> int:
        """Return the number of pointers advertised by the target."""

        return int(self._array.m_size)

    def capacity(self) -> int:
        """Return the target array capacity."""

        return int(self._array.m_capacity)

    def get(self, index: int) -> Any:
        """Read one pointer and the object to which it points."""

        if not self.valid() or index < 0 or index >= self.size():
            return None
        pointer_raw = self._reader.read(self._array.m_buffer + index * 4, 4)
        pointer = int.from_bytes(pointer_raw, "little")
        if pointer < 0x10000:
            return None
        element_size = ctypes.sizeof(self._element_type)
        raw = self._reader.read(pointer, element_size)
        value = _decode_value(self._element_type, raw)
        bind_reader = getattr(value, "bind_reader", None)
        if callable(bind_reader):
            return bind_reader(self._reader, pointer)
        return value

    def to_list(self) -> list[Any]:
        """Read all non-null pointed-to objects in the target array."""

        if not self.valid():
            return []
        return [value for index in range(self.size()) if (value := self.get(index)) is not None]

    def __len__(self) -> int:
        return self.size()

    def __getitem__(self, index: int) -> Any:
        value = self.get(index)
        if value is None:
            raise IndexError(index)
        return value

    def __iter__(self):
        return iter(self.to_list())

    def __reversed__(self):
        return reversed(self.to_list())


# Keep the spellings used by the Reforged source available while the project
# uses normal Python class names in new code.
GW_Array = GWArray
GW_BaseArray = GWBaseArray
GW_Array_View = GWArrayView
GW_Array_Value_View = GWArrayValueView

"""Offline layout checks for the external GadgetContext root."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import GadgetContextStruct, GadgetInfoStruct, GWArray


class _Memory:
    """Read deterministic bytes for the native gadget array tests."""

    def __init__(self, address: int, value: bytes) -> None:
        self.address = address
        self.value = value
        self.reads: list[tuple[int, int]] = []

    def read(self, address: int, size: int) -> bytes:
        self.reads.append((address, size))
        offset = address - self.address
        if offset < 0 or offset + size > len(self.value):
            raise OSError("test read is outside the mapped gadget array")
        return self.value[offset : offset + size]


class GadgetContextOfflineTests(unittest.TestCase):
    """Keep gadget root and record layouts fixed-width."""

    def test_native_layout(self) -> None:
        """The native root and gadget-info record are both 0x10 bytes."""

        self.assertEqual(ctypes.sizeof(GadgetInfoStruct), 0x10)
        self.assertEqual(ctypes.sizeof(GadgetContextStruct), 0x10)
        self.assertEqual(
            [field[0] for field in GadgetInfoStruct._fields_],
            ["h0000", "h0004", "h0008", "name_enc"],
        )
        self.assertEqual(
            [field[0] for field in GadgetContextStruct._fields_], ["gadget_info"]
        )
        self.assertEqual(GadgetInfoStruct.name_enc.offset, 0x0C)
        self.assertEqual(GadgetContextStruct.gadget_info.offset, 0x00)

    def test_array_size_is_reported(self) -> None:
        """The root exposes its count before any record traversal."""

        context = GadgetContextStruct()
        context.gadget_info_array = GWArray(0x120000, 128, 7, 0)
        self.assertEqual(context.array_size, 7)

    def test_default_gadget_read_returns_the_full_advertised_array(self) -> None:
        """The native array is not silently clipped at 256 entries."""

        address = 0x200000
        records = []
        for index in range(300):
            record = GadgetInfoStruct()
            record.h0000 = index
            records.append(bytes(record))
        memory = _Memory(address, b"".join(records))
        context = GadgetContextStruct().bind_reader(memory)
        context.gadget_info = GWArray(address, 300, 300, 0)

        values = context.gadget_infos()

        self.assertEqual(len(values), 300)
        self.assertEqual(values[-1].h0000, 299)
        self.assertEqual(memory.reads, [(address, 300 * ctypes.sizeof(GadgetInfoStruct))])
        self.assertEqual(len(context.gadget_infos(limit=12)), 12)

    def test_gadget_read_rejects_size_over_capacity(self) -> None:
        """An impossible target header cannot become an empty snapshot."""

        context = GadgetContextStruct().bind_reader(_Memory(0x200000, b""))
        context.gadget_info = GWArray(0x200000, 1, 2, 0)

        with self.assertRaisesRegex(ValueError, "exceeds capacity"):
            context.gadget_infos()

    def test_gadget_read_rejects_x86_address_wraparound(self) -> None:
        """A valid-sized array cannot cross the target's address-space end."""

        address = 0xFFFFFFF8
        context = GadgetContextStruct().bind_reader(_Memory(address, b""))
        context.gadget_info = GWArray(address, 1, 1, 0)

        with self.assertRaisesRegex(ValueError, "x86 address space"):
            context.gadget_infos()

    def test_gadget_read_rejects_array_over_external_safety_limit(self) -> None:
        """An unsafe full read raises instead of returning a partial list."""

        context = GadgetContextStruct().bind_reader(_Memory(0x200000, b""))
        context.gadget_info = GWArray(0x200000, 1_048_577, 1_048_577, 0)

        with self.assertRaisesRegex(ValueError, "external read limit"):
            context.gadget_infos()


if __name__ == "__main__":
    unittest.main(verbosity=2)

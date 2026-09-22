"""Offline boundary checks for the external AgentArray reader."""

from __future__ import annotations

import unittest
import ctypes
from typing import Any, cast

from py4gw import (
    AgentAllegiance,
    AgentArray,
    AgentArrayStruct,
    AgentArraySnapshot,
    AgentLivingStruct,
    AgentKind,
    AgentReference,
    GWArray,
)


class MemoryFixtureReader:
    """Serve fixed byte ranges as a small deterministic remote reader."""

    def __init__(self) -> None:
        self._ranges: dict[int, bytes] = {}

    def add(self, address: int, value: bytes) -> None:
        self._ranges[address] = value

    def read(self, address: int, size: int) -> bytes:
        for start, value in self._ranges.items():
            end = start + len(value)
            if start <= address and address + size <= end:
                offset = address - start
                return value[offset : offset + size]
        raise OSError(299, f"unmapped fixture read at 0x{address:08X}")


class MovementContextFixture:
    """Expose the movement-array header needed by one AgentArray snapshot."""

    def __init__(self, movement_array: GWArray) -> None:
        self.agent_movement_array = movement_array
        self.remote_address = 0x00400000

    def read(self) -> MovementContextFixture:
        return self


class AgentArrayOfflineTests(unittest.TestCase):
    """Verify bounded reads and fixed-width target values without a client."""

    def setUp(self) -> None:
        self.reader = MemoryFixtureReader()
        self.array = AgentArray.__new__(AgentArray)
        self.array_address = 0x00100000
        self.array._reader = self.reader
        self.array._max_pointer_slots = 16
        self.array._max_references = 8
        self.array._array_address = self.array_address

    def test_rejects_size_greater_than_capacity(self) -> None:
        """An impossible target header fails before its buffer is read."""

        header = GWArray(0x00200000, 2, 3, 0)
        self.reader.add(self.array_address, bytes(header))

        with self.assertRaisesRegex(RuntimeError, "size 3 greater than capacity 2"):
            self.array.read()

    def test_rejects_null_pointer_buffer(self) -> None:
        """A non-empty array cannot use a null target buffer."""

        header = GWArray(0, 8, 1, 0)
        self.reader.add(self.array_address, bytes(header))

        with self.assertRaisesRegex(RuntimeError, "null buffer"):
            self.array.read()

    def test_decodes_pointer_values_as_fixed_width_x86_addresses(self) -> None:
        """Pointer decoding never expands target values to host pointer width."""

        header = GWArray(0x00200000, 2, 2, 0)
        self.reader.add(self.array_address, bytes(header))
        self.reader.add(
            0x00200000,
            (0xF1234567).to_bytes(4, "little")
            + (0x00ABCDEF).to_bytes(4, "little"),
        )

        values = self.array._read_pointer_values(
            header, 2, self.array_address, "fixture pointer table"
        )

        self.assertEqual(values, (0xF1234567, 0x00ABCDEF))
        self.assertTrue(all(value <= 0xFFFFFFFF for value in values))

    def test_truncates_pointer_table_at_configured_limit(self) -> None:
        """A large reported size is bounded before the pointer-table read."""

        header = GWArray(0x00200000, 64, 32, 0)
        self.reader.add(self.array_address, bytes(header))
        self.reader.add(0x00200000, b"\x00" * (16 * 4))
        cast(Any, self.array)._agent_context = MovementContextFixture(
            GWArray(0, 0, 0, 0)
        )

        snapshot = self.array.read()

        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot.scanned_slots, 16)
        self.assertTrue(snapshot.pointer_table_truncated)

    def test_rejects_reference_after_pointer_slot_is_replaced(self) -> None:
        """A reused array slot is rejected before a full record read."""

        reference = self._add_current_reference()
        self.reader.add(0x00200000, (0x00600000).to_bytes(4, "little"))

        with self.assertRaisesRegex(RuntimeError, "now points to"):
            self.array.read_agent(reference)

    def test_rejects_reference_after_movement_entry_disappears(self) -> None:
        """A removed movement entry invalidates an old snapshot reference."""

        reference = self._add_current_reference()
        self.reader.add(0x00300000, b"\x00" * (4 * 4))

        with self.assertRaisesRegex(RuntimeError, "movement entry is null"):
            self.array.read_agent(reference)

    def test_source_category_methods_are_available_on_snapshot(self) -> None:
        """The source category names expose the validated ID lists."""

        snapshot = AgentArraySnapshot(
            references=(
                AgentReference(1, 0x500000, 0, 0, AgentKind.LIVING,
                               AgentAllegiance.ALLY_NON_ATTACKABLE, None, False),
                AgentReference(2, 0x500100, 1, 0, AgentKind.LIVING,
                               AgentAllegiance.ENEMY, None, True),
                AgentReference(3, 0x500200, 2, 0, AgentKind.ITEM,
                               None, 7, None),
                AgentReference(4, 0x500300, 3, 0, AgentKind.GADGET),
            ),
            reported_size=4,
            reported_capacity=4,
            scanned_slots=4,
            non_null_slots=4,
            invalid_pointer_slots=0,
            zero_id_slots=0,
            stale_slots=0,
            unreadable_slots=0,
            pointer_table_truncated=False,
            reference_limit_reached=False,
        )

        self.assertEqual(snapshot.GetAgentArray(), [1, 2, 3, 4])
        self.assertEqual(snapshot.GetAllyArray(), [1])
        self.assertEqual(snapshot.GetEnemyArray(), [2])
        self.assertEqual(snapshot.GetItemAgentArray(), [3])
        self.assertEqual(snapshot.GetOwnedItemAgentArray(), [3])
        self.assertEqual(snapshot.GetGadgetAgentArray(), [4])
        self.assertEqual(snapshot.GetDeadEnemyArray(), [2])

    def test_living_corpse_signature_matches_source_fields(self) -> None:
        """Corpse diagnostics expose the maintained native comparison tuple."""

        record = AgentLivingStruct()
        record.agent_id = 5
        record.effects = 0x10
        self.assertEqual(len(record.corpse_exploit_signature), 18)
        self.assertEqual(record.corpse_exploit_signature[0], 0x10)

    def test_source_agent_array_struct_keeps_the_native_header(self) -> None:
        """The source-shaped view retains one fixed-width GWArray header."""

        self.assertEqual(ctypes.sizeof(AgentArrayStruct), ctypes.sizeof(GWArray))
        view = AgentArrayStruct()
        view.agent_array = GWArray(0x200000, 8, 4, 0)
        self.assertEqual(int(view.agent_array.m_size), 4)

    def _add_current_reference(self) -> AgentReference:
        """Install one current array/movement pair for validity tests."""

        pointer = 0x00500000
        agent_id = 3
        self.reader.add(
            self.array_address,
            bytes(GWArray(0x00200000, 1, 1, 0)),
        )
        self.reader.add(0x00200000, pointer.to_bytes(4, "little"))
        movement_array = GWArray(0x00300000, 4, 4, 0)
        movement_values = bytearray(4 * 4)
        movement_values[agent_id * 4 : agent_id * 4 + 4] = (
            0x00700000
        ).to_bytes(4, "little")
        self.reader.add(0x00300000, bytes(movement_values))
        cast(Any, self.array)._agent_context = MovementContextFixture(movement_array)
        return AgentReference(agent_id, pointer, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

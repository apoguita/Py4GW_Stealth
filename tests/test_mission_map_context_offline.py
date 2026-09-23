"""Offline declaration checks for source MissionMapContext structures."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    ConnectedClient,
    MissionMapContext,
    MissionMapContextStruct,
    MissionMapSubContext,
    MissionMapSubContext2,
)


class _MemoryReader:
    """Addressable test memory for the source-declared child pointers."""

    def __init__(self, regions: dict[int, bytes]) -> None:
        self._regions = regions
        self.read_calls: list[tuple[int, int]] = []

    def read(self, address: int, size: int) -> bytes:
        self.read_calls.append((address, size))
        for base, contents in self._regions.items():
            if base <= address < base + len(contents):
                start = address - base
                return contents[start : start + size]
        raise OSError(f"unmapped test address 0x{address:08X}")


class MissionMapContextOfflineTests(unittest.TestCase):
    """Keep source fields and fixed x86 structure layout in parity."""

    def test_root_can_be_read_when_a_caller_supplies_the_context_address(self) -> None:
        source = MissionMapContextStruct()
        source.size.x = 1024.0
        source.size.y = 768.0
        source.player_mission_map_pos.x = 12.0
        source.player_mission_map_pos.y = 34.0
        address = 0x150000

        context = MissionMapContextStruct.read_at(
            _MemoryReader({address: bytes(source)}), address
        )

        self.assertEqual(context.address, address)
        self.assertEqual(context.size.x, 1024.0)
        self.assertEqual(context.size.y, 768.0)
        self.assertEqual(context.player_mission_map_pos.x, 12.0)
        self.assertEqual(context.player_mission_map_pos.y, 34.0)

    def test_connected_client_exposes_the_supplied_address_reader(self) -> None:
        source = MissionMapContextStruct()
        source.frame_id = 0x5678
        address = 0x150000
        client = object.__new__(ConnectedClient)
        setattr(client, "_reader", _MemoryReader({address: bytes(source)}))

        context = client.read_mission_map_context(address)

        self.assertIsNotNone(context)
        assert context is not None
        self.assertEqual(context.address, address)
        self.assertEqual(context.frame_id, 0x5678)

    def test_root_read_rejects_invalid_address_and_short_data(self) -> None:
        with self.assertRaisesRegex(ValueError, "outside x86"):
            MissionMapContextStruct.read_at(_MemoryReader({}), 0xFFFF)

        with self.assertRaisesRegex(ValueError, "expected 72"):
            MissionMapContextStruct.read_at(_MemoryReader({0x150000: b"short"}), 0x150000)

    def test_invalid_subcontext_limit_fails_before_memory_is_read(self) -> None:
        reader = _MemoryReader({})

        with self.assertRaisesRegex(ValueError, "max_subcontexts must be positive"):
            MissionMapContextStruct.read_at(reader, 0x150000, max_subcontexts=0)

        self.assertEqual(reader.read_calls, [])

    def test_structure_sizes_and_offsets(self) -> None:
        self.assertEqual(ctypes.sizeof(MissionMapSubContext), 0x38)
        self.assertEqual(ctypes.sizeof(MissionMapSubContext2), 0x58)
        self.assertEqual(ctypes.sizeof(MissionMapContextStruct), 0x48)
        expected_offsets = {
            MissionMapSubContext: {"h0000": 0x00},
            MissionMapSubContext2: {
                "h0000": 0x00,
                "player_mission_map_pos": 0x04,
                "h000c": 0x0C,
                "mission_map_size": 0x10,
                "unk": 0x18,
                "mission_map_pan_offset": 0x1C,
                "mission_map_pan_offset2": 0x24,
                "unk2": 0x2C,
                "unk3": 0x34,
            },
            MissionMapContextStruct: {
                "size": 0x00,
                "h0008": 0x08,
                "last_mouse_location": 0x0C,
                "frame_id": 0x14,
                "player_mission_map_pos": 0x18,
                "h0020": 0x20,
                "h0030": 0x30,
                "h0034": 0x34,
                "h0038": 0x38,
                "h003c": 0x3C,
                "h0040": 0x40,
                "h0044": 0x44,
            },
        }
        for structure, fields in expected_offsets.items():
            for field, expected_offset in fields.items():
                with self.subTest(structure=structure.__name__, field=field):
                    self.assertEqual(getattr(structure, field).offset, expected_offset)

    def test_source_field_names_and_order(self) -> None:
        expected_fields = {
            MissionMapSubContext: ["h0000"],
            MissionMapSubContext2: [
                "h0000", "player_mission_map_pos", "h000c", "mission_map_size",
                "unk", "mission_map_pan_offset", "mission_map_pan_offset2",
                "unk2", "unk3",
            ],
            MissionMapContextStruct: [
                "size", "h0008", "last_mouse_location", "frame_id",
                "player_mission_map_pos", "h0020", "h0030", "h0034", "h0038",
                "h003c", "h0040", "h0044",
            ],
        }
        for structure, expected in expected_fields.items():
            with self.subTest(structure=structure.__name__):
                self.assertEqual([name for name, _ in structure._fields_], expected)

    def test_source_child_properties_read_pointer_array_and_pointer(self) -> None:
        first = MissionMapSubContext()
        first.h0000[:] = range(0x0E)
        second = MissionMapSubContext()
        second.h0000[:] = range(10, 24)
        subcontext2 = MissionMapSubContext2()
        subcontext2.player_mission_map_pos.x = 12.5
        subcontext2.player_mission_map_pos.y = -8.25
        array = (ctypes.c_uint32 * 4)(0x110000, 0x120000, 0, 0)
        regions = {
            0x100000: bytes(array),
            0x110000: bytes(first),
            0x120000: bytes(second),
            0x130000: bytes(subcontext2),
        }
        reader = _MemoryReader(regions)
        context = MissionMapContextStruct()
        context.h0020.m_buffer = 0x100000
        context.h0020.m_capacity = 4
        context.h0020.m_size = 2
        context.h003c = 0x130000
        context.bind_reader(reader, address=0x140000)

        self.assertEqual(context.address, 0x140000)
        self.assertEqual([entry.h0000[0] for entry in context.subcontexts], [0, 10])
        decoded_subcontext2 = context.subcontext2
        if decoded_subcontext2 is None:
            self.fail("The non-null source pointer should produce a record.")
        self.assertEqual(decoded_subcontext2.player_mission_map_pos.x, 12.5)
        self.assertEqual(decoded_subcontext2.player_mission_map_pos.y, -8.25)

    def test_source_child_properties_validate_remote_pointer_headers(self) -> None:
        context = MissionMapContextStruct()
        context.h0020.m_size = 2
        context.h0020.m_capacity = 1
        context.bind_reader(_MemoryReader({}))
        with self.assertRaisesRegex(ValueError, "invalid header"):
            _ = context.subcontexts

        context.h0020.m_size = 0
        context.h0020.m_capacity = 0
        context.h003c = 0x10000
        with self.assertRaisesRegex(OSError, "unmapped"):
            _ = context.subcontext2

    def test_callback_facade_matches_source_members_and_external_limit(self) -> None:
        MissionMapContext.disable()
        self.assertEqual(MissionMapContext.get_ptr(), 0)
        self.assertIsNone(MissionMapContext.get_context())
        with self.assertRaisesRegex(NotImplementedError, "callback"):
            MissionMapContext.enable()
        with self.assertRaisesRegex(NotImplementedError, "callback"):
            MissionMapContext._update_ptr()


if __name__ == "__main__":
    unittest.main(verbosity=2)

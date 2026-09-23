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
    AgentStruct,
    AgentKind,
    AgentReference,
    GWArray,
)
from py4gw.context.agent_array import (
    AgentGadgetStruct,
    AgentItemStruct,
    AgentNative,
    DyeInfoStruct,
    EquipmentStruct,
    ItemDataStruct,
    ReforgedAgentLivingStruct,
    ReforgedEquipmentItemsUnionStruct,
    ReforgedEquipmentStruct,
    ReforgedItemDataStruct,
    TagInfoStruct,
    VisibleEffectStruct,
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


class ZeroReader:
    """Provide zero-filled pointer targets for empty nested records."""

    def read(self, address: int, size: int) -> bytes:
        return bytes(size)


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
        self.array._context_view = None
        self.array._cache_context_validator = None

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
        self.array._snapshot = snapshot
        self.assertEqual(self.array.GetGadgetArray(), [4])

    def test_corpse_exploit_helpers_match_the_source(self) -> None:
        """Corpse state and its diagnostic signature use source fields."""

        living = AgentLivingStruct()
        living.effects = 1
        living.model_state = 2
        living.type_map = 3
        living.player_number = 4
        living.agent_model_type = 5
        living.animation_code = 6
        living.animation_id = 7
        living.h00D4[:] = (8, 9, 10)
        living.h00E4[:] = (11, 12)
        living.h0140 = 13
        living.h0160[:] = (14, 15, 16, 17)
        living.h0180 = 18
        living.hp = 1.0
        self.assertEqual(living.corpse_exploit_state, "alive")
        self.assertEqual(
            living.corpse_exploit_signature,
            tuple(range(1, 19)),
        )

        living.hp = 0.0
        living.effects = 0x0004
        self.assertEqual(living.corpse_exploit_state, "used_corpse")
        living.effects = 0
        self.assertEqual(living.corpse_exploit_state, "exploitable")

    def test_reforged_item_facade_names_are_available(self) -> None:
        """The external instance facade keeps Reforged's item method names."""

        reference = AgentReference(
            3, 0x500200, 0, 0, AgentKind.ITEM, None, 7, None
        )
        snapshot = AgentArraySnapshot(
            references=(reference,),
            reported_size=1,
            reported_capacity=1,
            scanned_slots=1,
            non_null_slots=1,
            invalid_pointer_slots=0,
            zero_id_slots=0,
            stale_slots=0,
            unreadable_slots=0,
            pointer_table_truncated=False,
            reference_limit_reached=False,
        )
        self.array._snapshot = snapshot

        self.assertEqual(self.array.GetItemArray(), [3])
        self.assertEqual(self.array.GetOwnedItemArray(), [3])

    def test_source_agent_array_list_helpers(self) -> None:
        """Pure source helpers preserve their list and callback behavior."""

        self.assertCountEqual(
            AgentArray.Manipulation.Merge([1, 2], [2, 3]), [1, 2, 3]
        )
        self.assertCountEqual(
            AgentArray.Manipulation.Subtract([1, 2, 2, 3], [2]), [1, 3]
        )
        self.assertCountEqual(
            AgentArray.Manipulation.Intersect([1, 2, 2, 3], [2, 3, 4]),
            [2, 3],
        )
        self.assertEqual(
            AgentArray.Sort.ByCondition([3, 1, 2], lambda agent_id: agent_id),
            [1, 2, 3],
        )
        self.assertEqual(
            AgentArray.Sort.ByCondition(
                [3, 1, 2], lambda agent_id: agent_id, reverse=True
            ),
            [3, 2, 1],
        )
        self.assertEqual(
            AgentArray.Filter.ByCondition(
                [1, 2, 3], lambda agent_id: agent_id > 1
            ),
            [2, 3],
        )
        self.assertEqual(AgentArray.Filter.ByCondition(None, bool), [])

    def test_source_facade_lifecycle_names_are_exposed(self) -> None:
        """The instance facade exposes source lifecycle names safely."""

        self.array._array_address = 0x00100000
        self.array._snapshot = AgentArraySnapshot(
            references=(),
            reported_size=0,
            reported_capacity=0,
            scanned_slots=0,
            non_null_slots=0,
            invalid_pointer_slots=0,
            zero_id_slots=0,
            stale_slots=0,
            unreadable_slots=0,
            pointer_table_truncated=False,
            reference_limit_reached=False,
        )
        cast(Any, self.array)._living_snapshot = object()

        self.assertEqual(self.array.get_ptr(), 0x00100000)
        self.assertIsNone(self.array.get_context())
        with self.assertRaisesRegex(NotImplementedError, "injected callback"):
            self.array.enable()

        self.array.reset_cache()

        self.assertIsNone(self.array.snapshot)
        self.assertIsNone(self.array._living_snapshot)
        self.assertEqual(self.array.get_ptr(), 0x00100000)

        self.array.disable()

        self.assertEqual(self.array.get_ptr(), 0)

    def test_agent_struct_field_names_and_source_layout_variants(self) -> None:
        """Record source field names and keep Python/native ItemData distinct."""

        self.assertEqual(
            [field[0] for field in EquipmentStruct._fields_][0], "vtable"
        )
        self.assertEqual(
            [field[0] for field in VisibleEffectStruct._fields_],
            ["unk", "id", "has_ended"],
        )
        self.assertEqual(
            [field[0] for field in ReforgedItemDataStruct._fields_],
            ["model_file_id", "type", "dye", "value", "interaction"],
        )
        self.assertEqual(
            [field[0] for field in ReforgedEquipmentItemsUnionStruct._fields_],
            [
                "items", "weapon", "offhand", "chest", "legs", "head",
                "feet", "hands", "costume_body", "costume_head",
            ],
        )
        self.assertEqual(
            [field[0] for field in ReforgedEquipmentStruct._fields_],
            [
                "vtable", "h0004", "h0008", "h000C", "left_hand_ptr",
                "right_hand_ptr", "h0018", "shield_ptr", "left_hand_map",
                "right_hand_map", "head_map", "shield_map", "items_union",
                "ids_union",
            ],
        )
        self.assertEqual(ctypes.sizeof(ItemDataStruct), 0x10)
        self.assertEqual(ItemDataStruct.type.offset, 0x04)
        self.assertEqual(ItemDataStruct.dye.offset, 0x05)
        self.assertEqual(ItemDataStruct.value.offset, 0x08)
        self.assertEqual(ctypes.sizeof(ReforgedItemDataStruct), 0x13)
        self.assertEqual(ReforgedItemDataStruct.type.offset, 0x04)
        self.assertEqual(ReforgedItemDataStruct.dye.offset, 0x08)
        self.assertEqual(ReforgedItemDataStruct.value.offset, 0x0B)
        self.assertEqual(ctypes.sizeof(ReforgedEquipmentItemsUnionStruct), 0xAB)
        self.assertEqual(ctypes.sizeof(ReforgedEquipmentStruct), 0xF3)
        self.assertEqual(ReforgedEquipmentStruct.items_union.offset, 0x24)
        self.assertEqual(ReforgedEquipmentStruct.ids_union.offset, 0xCF)
        self.assertEqual(ctypes.sizeof(ReforgedAgentLivingStruct), 0x1C2)
        self.assertEqual(ReforgedAgentLivingStruct.allegiance.offset, 0x1B5)
        self.assertNotIn(
            "h01C2", [field[0] for field in ReforgedAgentLivingStruct._fields_]
        )

    def test_native_record_sizes_and_offsets_match_source_layout(self) -> None:
        """Keep external ctypes records at the maintained x86 native offsets."""

        self.assertEqual(ctypes.sizeof(AgentStruct), 0xC4)
        self.assertEqual(AgentStruct.agent_id.offset, 0x2C)
        self.assertEqual(AgentStruct.type.offset, 0x9C)
        self.assertEqual(ctypes.sizeof(AgentItemStruct), 0xD4)
        self.assertEqual(ctypes.sizeof(AgentGadgetStruct), 0xE4)

        self.assertEqual(ctypes.sizeof(AgentLivingStruct), 0x1C4)
        self.assertEqual(AgentLivingStruct.owner.offset, 0xC4)
        self.assertEqual(AgentLivingStruct.equipment_ptr_ptr.offset, 0xFC)
        self.assertEqual(AgentLivingStruct.tags_ptr.offset, 0x108)
        self.assertEqual(AgentLivingStruct.visible_effects_list.offset, 0x174)
        self.assertEqual(AgentLivingStruct.allegiance.offset, 0x1B5)
        self.assertEqual(AgentLivingStruct.h01C2.offset, 0x1C2)
        self.assertEqual(ctypes.sizeof(ReforgedAgentLivingStruct), 0x1C2)

        self.assertEqual(ctypes.sizeof(EquipmentStruct), 0xD8)
        self.assertEqual(EquipmentStruct.vtable.offset, 0x00)
        self.assertEqual(EquipmentStruct.left_hand_map.offset, 0x20)
        self.assertEqual(EquipmentStruct.items_union.offset, 0x24)
        self.assertEqual(EquipmentStruct.ids_union.offset, 0xB4)
        self.assertEqual(VisibleEffectStruct.id.offset, 0x04)

    def test_source_structure_snapshot_methods(self) -> None:
        """Copied Reforged structures expose their declared value snapshots."""

        dye = DyeInfoStruct()
        dye.dye_tint = 7
        dye.dye1 = 1
        dye.dye2 = 2
        dye.dye3 = 3
        dye.dye4 = 4
        self.assertEqual(dye.snapshot().dye4, 4)

        item = ItemDataStruct()
        item.model_file_id = 120
        item.type = 5
        item.dye.dye_tint = 7
        item.value = 42
        item.interaction = 9
        item_snapshot = item.snapshot()
        self.assertEqual(item_snapshot.model_file_id, 120)
        self.assertEqual(item_snapshot.type, 5)
        self.assertEqual(item_snapshot.dye.dye_tint, 7)
        self.assertEqual(item_snapshot.value, 42)
        self.assertEqual(item_snapshot.interaction, 9)

        source_equipment = ReforgedEquipmentStruct()
        source_equipment.left_hand_map = 0
        source_equipment.items_union.items[0].model_file_id = 321
        source_equipment.items_union.items[0].type = 4
        source_equipment.items_union.items[0].value = 12
        source_snapshot = source_equipment.snapshot()
        self.assertIsNotNone(source_snapshot.left_hand)
        assert source_snapshot.left_hand is not None
        self.assertEqual(source_snapshot.left_hand.model_file_id, 321)
        self.assertEqual(source_snapshot.left_hand.type, 4)
        self.assertEqual(source_snapshot.left_hand.value, 12)

        tag = TagInfoStruct()
        tag.guild_id = 0x1234
        tag.primary = 3
        self.assertEqual(tag.snapshot().guild_id, 0x1234)
        self.assertEqual(tag.snapshot().primary, 3)

        effect = VisibleEffectStruct()
        effect.id = 77
        effect.has_ended = 1
        self.assertEqual(effect.effect_id, 77)
        self.assertEqual(effect.snapshot().id, 77)

        agent = AgentLivingStruct().bind_reader(ZeroReader(), 0x00500000)
        snapshot = agent.snapshot_living()
        self.assertEqual(snapshot.owner, 0)
        self.assertEqual(snapshot.visible_effects, [])

    def test_item_and_gadget_source_snapshots(self) -> None:
        """Derived native records expose their Reforged snapshot methods."""

        item = AgentItemStruct()
        item.owner = 3
        item.item_id = 41
        item.extra_type = 8
        self.assertEqual(item.snapshot_item().item_id, 41)

        gadget = AgentGadgetStruct()
        gadget.gadget_id = 29
        self.assertEqual(gadget.snapshot_gadget().gadget_id, 29)

        common = AgentStruct()
        common.agent_id = 88
        common_snapshot = common.snapshot()
        self.assertIsInstance(common_snapshot, AgentNative)
        self.assertEqual(common_snapshot.agent_id, 88)

    def test_source_agent_array_struct_keeps_the_native_header(self) -> None:
        """The source-shaped view retains one fixed-width GWArray header."""

        self.assertEqual(ctypes.sizeof(AgentArrayStruct), ctypes.sizeof(GWArray))
        view = AgentArrayStruct()
        view.agent_array = GWArray(0x200000, 8, 4, 0)
        self.assertEqual(int(view.agent_array.m_size), 4)

    def test_source_agent_array_struct_cache_helpers(self) -> None:
        """Source cache helpers use the current validated external snapshot."""

        snapshot = AgentArraySnapshot(
            references=(
                AgentReference(1, 0x500000, 0, 0, AgentKind.LIVING,
                               AgentAllegiance.ALLY_NON_ATTACKABLE, None, False),
                AgentReference(2, 0x500100, 1, 0, AgentKind.LIVING,
                               AgentAllegiance.ENEMY, None, True),
                AgentReference(3, 0x500200, 2, 0, AgentKind.ITEM,
                               None, 7, None),
            ),
            reported_size=3,
            reported_capacity=3,
            scanned_slots=3,
            non_null_slots=3,
            invalid_pointer_slots=0,
            zero_id_slots=0,
            stale_slots=0,
            unreadable_slots=0,
            pointer_table_truncated=False,
            reference_limit_reached=False,
        )
        self.array._cache_context_validator = lambda: False
        view = AgentArrayStruct().bind_external(self.array, snapshot)

        view._ensure_fields()
        self.assertEqual(view.frame_counter, 0)
        self.assertEqual(view.frame_throttle, 2)
        self.assertEqual(view.GetAgentArray(), [])

        self.array._cache_context_validator = lambda: True
        view._ensure_cache_up_to_date()
        self.assertEqual(view.GetAgentArray(), [1, 2, 3])
        self.assertEqual(view.GetAllyArray(), [1])
        self.assertEqual(view.GetEnemyArray(), [2])
        self.assertEqual(view.GetItemAgentArray(), [3])
        self.assertEqual(view.GetDeadEnemyArray(), [2])

        view._drop_cache()
        self.assertIsNone(view._allegiance_cache)
        self.assertEqual(view._agent_by_id, {})
        self.assertEqual(view.GetAgentArray(), [])

        view._ensure_cache_up_to_date()
        self.assertEqual(view.GetAgentArray(), [1, 2, 3])

        self.array._context_view = view
        self.array._update_cache()
        self.assertEqual(view.GetDeadEnemyArray(), [2])

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

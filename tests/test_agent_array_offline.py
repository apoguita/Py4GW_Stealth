"""Offline boundary checks for the external AgentArray reader."""

from __future__ import annotations

import unittest
import ctypes
from typing import Any, cast
from unittest import mock

from py4gw.context.acc_agent_context import AccAgentContext
from py4gw.context.gw_array import GWArrayView

from py4gw import (
    Allegiance,
    AgentArrayStruct,
    AgentLivingStruct,
    AgentStruct,
    GWArray,
)
from py4gw.context.agent_array import (
    AgentArray,
    AgentGadgetStruct,
    AgentType,
    AgentItemStruct,
    AgentNative,
    DyeInfoStruct,
    EquipmentStruct,
    ItemDataStruct,
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


class AgentArrayOfflineTests(unittest.TestCase):
    """Verify bounded reads and fixed-width target values without a client."""

    def setUp(self) -> None:
        self.reader = MemoryFixtureReader()
        self.array = AgentArray.__new__(AgentArray)
        self.array_address = 0x00100000
        self.array._reader = self.reader
        self.array._array_address = self.array_address
        self.array._context_view = None
        self.array._cache_context_validator = None

    def test_rejects_size_greater_than_capacity(self) -> None:
        """A header whose size exceeds its capacity describes no readable array."""

        view = GWArrayView(self.reader, GWArray(0x00200000, 2, 3, 0), AgentStruct)

        self.assertFalse(view.valid())
        self.assertEqual(view.to_list(), [])

    def test_rejects_null_pointer_buffer(self) -> None:
        """A non-empty array with a null target buffer describes none either."""

        view = GWArrayView(self.reader, GWArray(0, 8, 1, 0), AgentStruct)

        self.assertFalse(view.valid())
        self.assertEqual(view.to_list(), [])

    def test_decodes_pointer_values_as_fixed_width_x86_addresses(self) -> None:
        """Pointer decoding never expands target values to host pointer width."""

        self.reader.add(
            0x00200000,
            (0xF1234567).to_bytes(4, "little")
            + (0x00ABCDEF).to_bytes(4, "little"),
        )
        self.reader.add(0xF1234567, bytes(ctypes.sizeof(AgentStruct)))
        self.reader.add(0x00ABCDEF, bytes(ctypes.sizeof(AgentStruct)))
        view = GWArrayView(self.reader, GWArray(0x00200000, 2, 2, 0), AgentStruct)

        values = [cast(Any, entry).remote_address for entry in view.to_list()]

        self.assertEqual(values, [0xF1234567, 0x00ABCDEF])
        self.assertTrue(all(value <= 0xFFFFFFFF for value in values))

    def test_source_category_methods_are_the_views_not_a_snapshots(self) -> None:
        """The category names live on the context view, fed by the array itself.

        They used to be answered from a reference snapshot this port built; the source declares
        them on ``AgentArrayStruct`` and fills them from its own agent array, which is what
        ``test_source_agent_array_struct_buckets_the_array_the_source_s_way`` now pins. What is
        pinned here is that the view carries them and the facade does not.
        """

        for name in (
            "GetAgentArray",
            "GetAllyArray",
            "GetNeutralArray",
            "GetEnemyArray",
            "GetSpiritPetArray",
            "GetMinionArray",
            "GetNPCMinipetArray",
            "GetItemAgentArray",
            "GetOwnedItemAgentArray",
            "GetGadgetAgentArray",
            "GetDeadAllyArray",
            "GetDeadEnemyArray",
        ):
            with self.subTest(member=name):
                self.assertTrue(hasattr(AgentArrayStruct, name))
                self.assertFalse(hasattr(AgentArray, name))


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
        """The two source files' names for the item and gadget lists are kept apart.

        ``AgentContext.py`` declares ``GetItemAgentArray``/``GetOwnedItemAgentArray``/
        ``GetGadgetAgentArray``; the shorter ``GetItemArray``/``GetOwnedItemArray``/``GetGadgetArray``
        are ``AgentArray.py``'s, and its own second route bridges them (``AgentArray.py:145``). The
        context view keeps only its own names; the class in ``py4gw/agent_array.py`` carries the
        others.
        """

        from py4gw import agent_array as agent_array_module

        for short, context_name in (
            ("GetItemArray", "GetItemAgentArray"),
            ("GetOwnedItemArray", "GetOwnedItemAgentArray"),
            ("GetGadgetArray", "GetGadgetAgentArray"),
        ):
            with self.subTest(name=short):
                self.assertTrue(hasattr(agent_array_module.AgentArray, short))
                self.assertTrue(hasattr(AgentArrayStruct, context_name))
                self.assertFalse(hasattr(AgentArrayStruct, short))

    def test_source_agent_array_list_helpers(self) -> None:
        """The list helpers belong to ``AgentArray.py``'s class, not to this context.

        The context view used to carry copies of ``Manipulation``/``Sort``/``Filter`` — its own
        docstring said they were *"copied from Reforged's AgentArray facade"*. They live in
        ``py4gw/agent_array.py``, the port of that file, and are exercised there
        (``tests/test_agent_array_class_offline.py``); what is pinned here is that the context view
        no longer carries a second copy.
        """

        for name in ("Manipulation", "Sort", "Filter", "Routines"):
            with self.subTest(helper=name):
                self.assertFalse(hasattr(AgentArray, name))

    def test_source_facade_lifecycle_names_are_exposed(self) -> None:
        """The instance facade exposes source lifecycle names safely.

        ``get_context`` is the source's own accessor for the view (``AgentContext.py:1473-1474``);
        with no frame loop here it builds the view when asked, so the fixture maps an array header
        for it to read.
        """

        self.array._array_address = 0x00100000
        self.reader.add(self.array_address, bytes(GWArray(0, 0, 0, 0)))

        self.assertEqual(self.array.get_ptr(), 0x00100000)
        context = self.array.get_context()
        self.assertIsNotNone(context, "get_context builds the view on demand")
        self.assertEqual(self.array.get_context(), context, "get_context keeps the view")
        with self.assertRaisesRegex(NotImplementedError, "injected callback"):
            self.array.enable()

        self.array.reset_cache()

        self.assertIsNone(self.array._context_view)
        self.assertEqual(self.array.get_ptr(), 0x00100000)

        self.array.disable()

        self.assertEqual(self.array.get_ptr(), 0)

    def test_agent_struct_field_names_and_native_item_layout(self) -> None:
        """Record the source field names and the native embedded-item offsets."""

        self.assertEqual(
            [field[0] for field in EquipmentStruct._fields_][0], "vtable"
        )
        self.assertEqual(
            [field[0] for field in VisibleEffectStruct._fields_],
            ["unk", "id", "has_ended"],
        )
        self.assertEqual(
            [field[0] for field in EquipmentStruct._fields_],
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

    def test_native_record_sizes_and_offsets_match_source_layout(self) -> None:
        """Keep external ctypes records at the maintained x86 native offsets.

        These are the layouts native's own ``static_assert``s carry. Reforged's Python declarations
        of the same records are smaller (``ItemData`` 0x13, ``Equipment`` 0xF3, ``AgentLiving``
        0x1C2) because they declare the packed C++ members rather than the padded record; the
        build's asserts and the reading side both use the native sizes, so the external records
        follow native.
        """

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

        self.assertEqual(ctypes.sizeof(EquipmentStruct), 0xD8)
        self.assertEqual(EquipmentStruct.vtable.offset, 0x00)
        self.assertEqual(EquipmentStruct.left_hand_map.offset, 0x20)
        self.assertEqual(EquipmentStruct.items_union.offset, 0x24)
        self.assertEqual(EquipmentStruct.ids_union.offset, 0xB4)
        self.assertEqual(VisibleEffectStruct.id.offset, 0x04)

    def test_source_structure_snapshot_methods(self) -> None:
        """The native records expose the source's declared value snapshots."""

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

        equipment = EquipmentStruct()
        equipment.left_hand_map = 0
        equipment.items_union.items[0].model_file_id = 321
        equipment.items_union.items[0].type = 4
        equipment.items_union.items[0].value = 12
        equipment_snapshot = equipment.snapshot()
        self.assertIsNotNone(equipment_snapshot.left_hand)
        assert equipment_snapshot.left_hand is not None
        self.assertEqual(equipment_snapshot.left_hand.model_file_id, 321)
        self.assertEqual(equipment_snapshot.left_hand.type, 4)
        self.assertEqual(equipment_snapshot.left_hand.value, 12)

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

    def test_source_agent_array_struct_buckets_the_array_the_source_s_way(self) -> None:
        """The category caches come from the array itself (``AgentContext.py:1160-1256``).

        The source walks its own agent array, gates each id on ``AccAgentContext``'s
        ``valid_agents_ids``, and buckets by the ``is_*_type`` flags and ``living.allegiance``. This
        pins that order with three records — one ally, one *dead* enemy, one owned item — so a
        member that stops reading the array, or buckets in another order, fails here.
        """

        pointers_address = 0x00300000
        addresses = {1: 0x00400000, 2: 0x00401000, 3: 0x00402000}
        self.reader.add(
            pointers_address,
            b"".join(value.to_bytes(4, "little") for value in addresses.values()),
        )

        living_size = ctypes.sizeof(AgentLivingStruct)
        raw = bytearray(living_size)
        living = AgentLivingStruct.from_buffer(raw)
        living.agent_id = 1
        living.type = int(AgentType.LIVING)
        living.allegiance = int(Allegiance.Ally)
        living.effects = 0
        self.reader.add(addresses[1], bytes(raw))

        raw = bytearray(living_size)
        living = AgentLivingStruct.from_buffer(raw)
        living.agent_id = 2
        living.type = int(AgentType.LIVING)
        living.allegiance = int(Allegiance.Enemy)
        living.effects = 0x0010  # dead
        self.reader.add(addresses[2], bytes(raw))

        raw = bytearray(ctypes.sizeof(AgentItemStruct))
        item = AgentItemStruct.from_buffer(raw)
        item.agent_id = 3
        item.type = int(AgentType.ITEM)
        item.owner = 7
        self.reader.add(addresses[3], bytes(raw))

        valid_agents = mock.Mock()
        valid_agents.valid_agents_ids = [1, 2, 3]
        with mock.patch.object(
            AccAgentContext, "get_context", staticmethod(lambda: valid_agents)
        ):
            header = GWArray(pointers_address, 4, 3, 0)
            view = AgentArrayStruct.from_buffer_copy(bytes(header)).bind_external(
                self.array, self.reader
            )

            self.assertEqual(view.GetAgentArray(), [1, 2, 3])
            self.assertEqual(view.GetAllyArray(), [1])
            self.assertEqual(view.GetEnemyArray(), [2])
            self.assertEqual(view.GetDeadEnemyArray(), [2])
            self.assertEqual(view.GetItemAgentArray(), [3])
            self.assertEqual(view.GetOwnedItemAgentArray(), [3])
            self.assertEqual(view.GetGadgetAgentArray(), [])
            self.assertEqual(view.GetNeutralArray(), [])
            by_id = view.GetAgentByID(2)
            self.assertIsNotNone(by_id)
            self.assertEqual(cast(Any, by_id).agent_id, 2)

        view._drop_cache()
        self.assertIsNone(view._allegiance_cache)
        self.assertEqual(view._agent_by_id, {})
        self.assertEqual(view.GetAgentArray(), [])

    def test_the_context_gate_stops_the_buckets(self) -> None:
        """``_cache_contexts_are_available`` (``AgentContext.py:1122-1137``) gates the rebuild."""

        self.array._cache_context_validator = lambda: False
        header = GWArray(0x00300000, 4, 1, 0)
        view = AgentArrayStruct.from_buffer_copy(bytes(header)).bind_external(
            self.array, self.reader
        )

        self.assertEqual(view.GetAgentArray(), [])
        self.assertIsNone(view._allegiance_cache)


if __name__ == "__main__":
    unittest.main(verbosity=2)

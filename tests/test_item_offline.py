"""Offline tests for the ported ``item`` module: the ``Item`` class and the ``PyItem`` binding under it.

**What is pinned.** Two different things, because this module is two different things:

1. **The surface.** ``Item.py``'s 122 declarations — the ``Bag`` enum, the ``Item`` class, its five
   nested namespaces and their members, the three constants and the four module functions — are
   compared against the **source's own AST**, name by name, nesting by nesting, decorators included.
   Nothing dropped, nothing renamed, nothing re-nested, and the port's own additions are named and
   accounted for (they are the binding, which the source reaches as ``import PyItem``).
2. **The reads.** ``PyItem`` and the members over it are driven against a fixture: the **real** ported
   item record (``ItemStruct``) built from bytes, with a real modifier array behind it, so
   ``GetContext``'s field copies, the derived flags and the modifier readers are all exercised.

The name trio is checked on the paths that need no client decoder — a missing item answers ``"No Item"``
and is ready, and an item never asked about answers ``""`` and is not ready. The decode itself is the
client's (``py4gw/ui/async_decode.py``) and is exercised by the live probe.
"""

from __future__ import annotations

import ast
import ctypes
import struct
import types
import unittest
from pathlib import Path
from typing import Any, cast
from unittest import mock

from py4gw import item as item_module
from py4gw import mods_core
from py4gw.native_src.item import py_inventory
from py4gw.context.item_context import DyeInfoStruct, ItemModifierStruct, ItemStruct
from py4gw.enums_src.game_data_enums import Attribute, DyeColor
from py4gw.enums_src.item_enums import ItemType, Rarity
from py4gw.map import Map
from py4gw.mods_types import ModifierIdentifier

SOURCE_FILE = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\Item.py")

#: The binding names this module carries, which the source reaches as ``import PyItem``.
BINDING_MEMBERS = {
    "_unported",
    "item_type_name",
    "dye_color_name",
    "PyItemType",
    "PyDyeColor",
    "PyDyeInfo",
    "PyItem",
}

#: The item the fixture builds: a gold sword with a damage mod and a requirement mod.
ITEM_ID = 5
MODEL_ID = 1234
#: The modifier words the fixture's item carries. The decoder reads the identifier out of bits 20-29,
#: so the identifier goes in shifted left by twenty (`(word >> 16) >> 4 & 0x3FF`), with `arg1` in bits
#: 8-15 and `arg2` in bits 0-7 — the same construction the mods_core test uses.
DAMAGE_WORD = (int(ModifierIdentifier.Damage) << 20) | (0x12 << 8) | 0x03
REQUIREMENT_WORD = (int(ModifierIdentifier.AttributeRequirement) << 20) | (0x08 << 8) | 0x04


def _surface(nodes: list[ast.stmt]) -> dict[str, Any]:
    """A class/member map of an AST body: classes recurse, functions record their decorators."""

    out: dict[str, Any] = {}
    for node in nodes:
        if isinstance(node, ast.ClassDef):
            out[node.name] = _surface(node.body)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = [ast.unparse(d) for d in node.decorator_list]
        elif (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            out[node.targets[0].id] = "assign"
    return out


def _missing(side: dict[str, Any], other: dict[str, Any], path: str = "") -> list[str]:
    """Names ``side`` declares that ``other`` does not, recursion included."""

    problems: list[str] = []
    for name, value in side.items():
        if name not in other:
            problems.append(f"{path}{name}")
        elif isinstance(value, dict):
            if not isinstance(other[name], dict):
                problems.append(f"{path}{name} (class vs member)")
            else:
                problems += _missing(value, other[name], f"{path}{name}.")
        elif isinstance(other[name], dict):
            problems.append(f"{path}{name} (member vs class)")
        elif value != other[name]:
            problems.append(f"{path}{name} (decorators {value} != {other[name]})")
    return problems


class _FakeReader:
    """A reader over a dictionary of address ranges — the same `read(address, size)` the port uses."""

    def __init__(self, regions: dict[int, bytes]) -> None:
        self._regions = regions

    def read(self, address: int, size: int) -> bytes:
        for start, data in self._regions.items():
            if start <= address and address + size <= start + len(data):
                offset = address - start
                return data[offset : offset + size]
        raise OSError(f"no region covers 0x{address:08X}+{size}")


def _modifier_words() -> bytes:
    return struct.pack("<II", DAMAGE_WORD, REQUIREMENT_WORD)


def _item_bytes() -> bytes:
    """A 0x54-byte item record, field for field, with the two modifiers pointing at their array."""

    buffer = bytearray(ctypes.sizeof(ItemStruct))
    struct.pack_into("<I", buffer, 0x00, ITEM_ID)          # item_id
    struct.pack_into("<I", buffer, 0x04, 0)                # agent_id
    struct.pack_into("<I", buffer, 0x08, 0)                # bag_equipped
    struct.pack_into("<I", buffer, 0x0C, 0)                # bag
    struct.pack_into("<I", buffer, 0x10, 0x40000)          # mod_struct (the array's address)
    struct.pack_into("<I", buffer, 0x14, 2)                # mod_struct_size
    struct.pack_into("<I", buffer, 0x18, 0)                # customized (null pointer)
    struct.pack_into("<I", buffer, 0x1C, 0x9000)           # model_file_id
    buffer[0x20] = int(ItemType.Sword)                     # type
    buffer[0x21] = 3                                       # dye_tint
    buffer[0x22] = 0x21                                    # dye1 = 1, dye2 = 2
    struct.pack_into("<H", buffer, 0x24, 100)              # value
    struct.pack_into("<I", buffer, 0x28, 0x20000)          # interaction: gold
    struct.pack_into("<I", buffer, 0x2C, MODEL_ID)         # model_id
    struct.pack_into("<I", buffer, 0x48, 0)                # item_formula
    buffer[0x4A] = 1                                       # is_material_salvageable
    struct.pack_into("<H", buffer, 0x4C, 7)                # quantity
    buffer[0x4E] = 0                                       # equipped
    buffer[0x4F] = 3                                       # profession
    buffer[0x50] = 2                                       # slot
    return bytes(buffer)


class _FakeItemContext:
    """The client's item-context **reader**: `read()` hands out the record the port reads through.

    ``ItemContextStruct.GetItemById`` and its ``read_inventory`` are members of the *record*, not of the
    reader — the shape pyright caught when this fake had them flat.
    """

    def __init__(self, records: dict[int, ItemStruct]) -> None:
        self._records = records
        self._context = _FakeItemContextStruct(records)

    def read(self) -> _FakeItemContextStruct:
        return self._context

    def get_composite_model_ids(self, model_file_id: int) -> list[int]:
        if int(model_file_id) != 0x9000:
            return []
        return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]


class _FakeItemContextStruct:
    """The item context's own record."""

    def __init__(self, records: dict[int, ItemStruct]) -> None:
        self._records = records

    def GetItemById(self, item_id: int) -> ItemStruct | None:
        return self._records.get(int(item_id))

    def read_inventory(self) -> None:
        """This fixture's client holds no inventory: every bag is empty."""

        return None


class _FakeClient:
    def __init__(self, records: dict[int, ItemStruct], reader: _FakeReader) -> None:
        self.item_context = _FakeItemContext(records)
        self.reader = reader


class _TradeLookup:
    """Stand in for the source trade-context item lookup, as the item-record tests use it.

    ``ItemStruct.IsOfferedInTrade`` reads the player's trade offer through the trade context, so a
    record that is not bound to one refuses — which is why the fixture binds this.
    """

    def __init__(self, offered_ids: set[int]) -> None:
        self.offered_ids = offered_ids

    def is_item_offered(self, item_id: int) -> bool:
        return int(item_id) in self.offered_ids

    def read(self) -> _TradeLookup:
        return self


def _fixture() -> tuple[Any, Any]:
    """Build the client and patch ``require_client`` plus the map gate for one test."""

    reader = _FakeReader({0x40000: _modifier_words()})
    record = ItemStruct.from_buffer_copy(_item_bytes()).bind_reader(
        reader, 0x50000, cast(Any, _TradeLookup(set()))
    )
    client = _FakeClient({ITEM_ID: record}, reader)
    return client, record


@unittest.skipUnless(SOURCE_FILE.is_file(), f"the Reforged source is not present at {SOURCE_FILE}")
class ItemSurfaceTests(unittest.TestCase):
    """The port declares the source's members, in the source's nesting."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _surface(ast.parse(SOURCE_FILE.read_text(encoding="utf-8")).body)
        cls.port = _surface(
            ast.parse(
                (Path(__file__).resolve().parents[1] / "py4gw" / "item.py").read_text(
                    encoding="utf-8"
                )
            ).body
        )

    def test_every_source_member_is_declared(self) -> None:
        """Nothing dropped, renamed or re-nested."""

        self.assertEqual(_missing(self.source, self.port), [])

    def test_the_port_adds_only_the_binding(self) -> None:
        """The names the port has and the source does not are the binding, and nothing else."""

        self.assertEqual(sorted(_missing(self.port, self.source)), sorted(BINDING_MEMBERS))

    def test_the_item_class_holds_its_six_namespaces_and_seventeen_methods(self) -> None:
        """`Item`'s own shape: 6 nested namespaces and the 17 static methods of the source."""

        item = self.port["Item"]
        nested = {name for name, value in item.items() if isinstance(value, dict)}
        self.assertEqual(
            nested, {"Mods", "Rarity", "Properties", "Type", "Usage", "Dye"}
        )
        methods = {name for name, value in item.items() if not isinstance(value, dict)}
        self.assertEqual(len(methods), 17, sorted(methods))
        for name in methods:
            with self.subTest(member=name):
                self.assertIn("staticmethod", item[name])

    def test_the_nested_namespaces_hold_the_source_member_counts(self) -> None:
        """22 + 6 + 21 + 8 + 10 + 4 members, as counted from the source."""

        item = self.port["Item"]
        self.assertEqual(len(item["Mods"]), 22, sorted(item["Mods"]))
        self.assertEqual(len(item["Rarity"]), 6)
        self.assertEqual(len(item["Properties"]), 21)
        self.assertEqual(len(item["Type"]), 8)
        self.assertEqual(len(item["Usage"]), 10)
        self.assertEqual(len(item["Dye"]), 4, sorted(item["Dye"]))


class ItemBindingTests(unittest.TestCase):
    """``PyItem``'s own reads, over the fixture record."""

    def setUp(self) -> None:
        self.client, self.record = _fixture()
        self.patchers = [
            mock.patch.object(item_module, "require_client", lambda: self.client),
            mock.patch.object(Map, "IsMapReady", staticmethod(lambda: True)),
        ]
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in self.patchers:
            patcher.stop()

    def test_get_context_copies_the_records_fields(self) -> None:
        """Every field `GetContext` copies, from the record the client holds."""

        binding = item_module.PyItem(ITEM_ID)
        self.assertEqual(binding.item_id, ITEM_ID)
        self.assertEqual(binding.agent_id, 0)
        self.assertEqual(binding.agent_item_id, ITEM_ID)
        self.assertEqual(binding.model_id, MODEL_ID)
        self.assertEqual(binding.model_file_id, 0x9000)
        self.assertEqual(binding.value, 100)
        self.assertEqual(binding.quantity, 7)
        self.assertEqual(binding.profession, 3)
        self.assertEqual(binding.slot, 2)
        self.assertEqual(binding.is_material_salvageable, 1)
        self.assertFalse(binding.is_customized)

    def test_get_context_reports_the_type_and_its_name(self) -> None:
        """`item_type` is the binding's own type object, and it names the type."""

        binding = item_module.PyItem(ITEM_ID)
        self.assertEqual(binding.item_type.ToInt(), int(ItemType.Sword))
        self.assertEqual(binding.item_type.GetName(), "Sword")
        self.assertEqual(binding.item_type, item_module.PyItemType(int(ItemType.Sword)))

    def test_get_context_reads_the_derived_flags_from_the_record(self) -> None:
        """The flags come from the record's own methods, so the record's rules decide them."""

        binding = item_module.PyItem(ITEM_ID)
        self.assertTrue(binding.is_weapon)
        self.assertFalse(binding.is_armor)
        self.assertTrue(binding.is_rarity_gold)
        self.assertEqual(binding.rarity, Rarity.Gold)
        self.assertFalse(binding.is_stackable)

    def test_get_context_reads_the_dye_record(self) -> None:
        """`dye_info` is the record's three-byte dye record, in the binding's own shape."""

        binding = item_module.PyItem(ITEM_ID)
        self.assertEqual(binding.dye_info.dye_tint, 3)
        self.assertEqual(binding.dye_info.dye1.ToInt(), 1)
        self.assertEqual(binding.dye_info.dye2.ToInt(), 2)
        self.assertTrue(binding.dye_info.ToString().startswith("DyeInfo { dye_tint: 3,"))

    def test_the_modifiers_are_the_records_own_words(self) -> None:
        """`modifiers` holds the real record type, in array order."""

        binding = item_module.PyItem(ITEM_ID)
        self.assertEqual(len(binding.modifiers), 2)
        self.assertIsInstance(binding.modifiers[0], ItemModifierStruct)
        self.assertEqual(binding.modifiers[0].GetArg1(), 0x12)
        self.assertEqual(binding.modifiers[1].GetArg2(), 0x04)

    def test_a_missing_item_leaves_the_defaults(self) -> None:
        """`GetItemById` finds nothing, so `GetContext` returns early and the defaults stand."""

        binding = item_module.PyItem(4242)
        self.assertEqual(binding.item_id, 4242)
        self.assertEqual(binding.model_id, 0)
        self.assertEqual(binding.modifiers, [])
        self.assertEqual(binding.item_type.ToInt(), int(ItemType.Unknown))

    def test_the_map_gate_is_the_records_first_check(self) -> None:
        """With the map not ready the record is not read at all — native's own order."""

        with mock.patch.object(Map, "IsMapReady", staticmethod(lambda: False)):
            binding = item_module.PyItem(ITEM_ID)
        self.assertEqual(binding.model_id, 0)

    def test_is_item_valid_answers_from_the_context(self) -> None:
        """`IsItemValid` is `GetItemById(id) is not None`."""

        binding = item_module.PyItem(ITEM_ID)
        self.assertTrue(binding.IsItemValid(ITEM_ID))
        self.assertFalse(binding.IsItemValid(4242))

    def test_the_composite_model_ids_come_from_the_context(self) -> None:
        """The static member answers the record's eleven file ids."""

        self.assertEqual(item_module.PyItem.GetCompositeModelIDs(0x9000), list(range(1, 12)))
        self.assertEqual(item_module.PyItem.GetCompositeModelIDs(0), [])
        self.assertEqual(item_module.PyItem.GetCompositeModelIDs(0x7777), [])


class ItemNameTests(unittest.TestCase):
    """The name trio on the paths that need no client decoder."""

    def setUp(self) -> None:
        self.client, self.record = _fixture()
        self.patchers = [
            mock.patch.object(item_module, "require_client", lambda: self.client),
            mock.patch.object(Map, "IsMapReady", staticmethod(lambda: True)),
        ]
        for patcher in self.patchers:
            patcher.start()
        item_module._item_name_map.clear()
        item_module._item_name_requests.clear()

    def tearDown(self) -> None:
        for patcher in self.patchers:
            patcher.stop()
        item_module._item_name_map.clear()
        item_module._item_name_requests.clear()

    def test_an_item_never_asked_about_answers_empty_and_not_ready(self) -> None:
        """Native's map holds nothing for that id, so `GetName` is empty."""

        binding = item_module.PyItem(ITEM_ID)
        self.assertEqual(binding.GetName(), "")
        self.assertFalse(binding.IsItemNameReady())

    def test_a_missing_item_answers_no_item_and_is_ready(self) -> None:
        """Native stores `"No Item"` and marks it ready when `GetItemById` finds nothing."""

        binding = item_module.PyItem(4242)
        binding.RequestName()
        self.assertEqual(binding.GetName(), "No Item")
        self.assertTrue(binding.IsItemNameReady())

    def test_request_name_with_no_item_id_does_nothing(self) -> None:
        """`if (!item_id) return;` — native's own first line."""

        binding = item_module.PyItem(0)
        binding.RequestName()
        self.assertEqual(item_module._item_name_map, {})
        self.assertEqual(binding.GetName(), "")


class ItemMembersTests(unittest.TestCase):
    """`Item`'s members over the fixture item."""

    def setUp(self) -> None:
        self.client, self.record = _fixture()
        self.patchers = [
            mock.patch.object(item_module, "require_client", lambda: self.client),
            # `Item.Mods` and four `Item.Properties` readers decode through `mods_core`, and the two bag
            # members walk `py_inventory`'s bags: each reaches the client through its own import of
            # `require_client` — the same port, three names.
            mock.patch.object(mods_core, "require_client", lambda: self.client),
            mock.patch.object(py_inventory, "require_client", lambda: self.client),
            mock.patch.object(Map, "IsMapReady", staticmethod(lambda: True)),
        ]
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in self.patchers:
            patcher.stop()

    def test_the_simple_readers_answer_the_records_fields(self) -> None:
        """The members that are one field read, in the source's own delegation."""

        item = item_module.Item
        self.assertEqual(item.GetAgentID(ITEM_ID), 0)
        self.assertEqual(item.GetAgentItemID(ITEM_ID), ITEM_ID)
        self.assertEqual(item.GetModelID(ITEM_ID), MODEL_ID)
        self.assertEqual(item.GetModelFileID(ITEM_ID), 0x9000)
        self.assertEqual(item.GetSlot(ITEM_ID), 2)
        self.assertEqual(item.Properties.GetValue(ITEM_ID), 100)
        self.assertEqual(item.Properties.GetQuantity(ITEM_ID), 7)
        self.assertEqual(item.Properties.GetProfession(ITEM_ID), 3)
        self.assertEqual(item.Properties.GetInteraction(ITEM_ID), 0x20000)
        self.assertEqual(item.Properties.GetItemFormula(ITEM_ID), 0)

    def test_the_item_type_pair_is_the_bindings_own_pair(self) -> None:
        """`GetItemType` answers the int and the name, from two binding instances as the source does."""

        self.assertEqual(item_module.Item.GetItemType(ITEM_ID), (int(ItemType.Sword), "Sword"))
        self.assertTrue(item_module.Item.IsWeapon(ITEM_ID))
        self.assertFalse(item_module.Item.IsArmorType(ITEM_ID))

    def test_the_rarity_names_are_the_bindings_names(self) -> None:
        """The five rarity readers compare the name the binding produced."""

        rarity_value, rarity_name = item_module.Item.Rarity.GetRarity(ITEM_ID)
        self.assertEqual(rarity_name, "Gold")
        self.assertEqual(rarity_value, int(Rarity.Gold))
        self.assertTrue(item_module.Item.Rarity.IsGold(ITEM_ID))
        self.assertFalse(item_module.Item.Rarity.IsWhite(ITEM_ID))

    def test_the_type_and_usage_namespaces_read_the_records_flags(self) -> None:
        """Each member is the record's own rule, through the binding's flag."""

        item = item_module.Item
        self.assertTrue(item.Type.IsWeapon(ITEM_ID))
        self.assertFalse(item.Type.IsArmor(ITEM_ID))
        self.assertFalse(item.Type.IsMaterial(ITEM_ID))
        self.assertFalse(item.Usage.IsSalvageKit(ITEM_ID))

    def test_the_modifier_readers_decode_the_fixture_words(self) -> None:
        """`Item.Mods` and the modifier-derived `Item.Properties` readers over the real words.

        **One source quirk is pinned here.** ``Item.Mods.ModifierExists`` and ``GetModifierValues``
        compare the binding's own ``GetIdentifier()`` — ``mod >> 16`` (``item_bindings.cpp:38``) — with
        the identifier the caller passes, while the decoder reads ``(mod >> 16) >> 4``
        (``mods_core.py:194``). The two are a factor of sixteen apart, so those two members match only
        the binding's spelling of the identifier (``0x27A1`` for a Damage word), never ``ModId.Damage``
        (``0x27A``). That is the source's own comparison, kept as it is.
        """

        item = item_module.Item
        binding_identifier = DAMAGE_WORD >> 16
        self.assertEqual(binding_identifier, 0x27A0)
        self.assertEqual(item.Mods.GetModifierCount(ITEM_ID), 2)
        self.assertTrue(item.Mods.ModifierExists(ITEM_ID, binding_identifier))
        self.assertFalse(item.Mods.ModifierExists(ITEM_ID, int(item_module.ModId.Damage)))
        self.assertEqual(
            item.Mods.GetModifierValues(ITEM_ID, binding_identifier), (0x1203, 0x12, 0x03)
        )
        self.assertIn(item_module.ModId.Damage, item.Mods.GetMods(ITEM_ID))
        self.assertEqual(
            item.Mods.GetRaw(ITEM_ID, item_module.ModId.Damage), (0x12, 0x03)
        )
        damage = item.Properties.GetDamage(ITEM_ID)
        self.assertEqual(len(damage), 2)
        self.assertTrue(all(isinstance(value, int) for value in damage))

    def test_the_requirement_reader_answers_the_attribute(self) -> None:
        """`GetRequirement` reads the requirement modifier's subtype and value."""

        requirement = item_module.Item.Properties.GetRequirement(ITEM_ID)
        self.assertIsInstance(requirement[0], Attribute)
        self.assertIsInstance(requirement[1], int)

    def test_the_dye_namespace_reads_the_dye_record(self) -> None:
        """`GetInfo` and `GetChannels` over the fixture's three-byte dye record.

        `GetChannels` maps each channel through `DyeColor`, so what it answers are `DyeColor`
        members, not the binding's own colour objects — the source's own `_dc` helper.
        """

        info = item_module.Item.Dye.GetInfo(ITEM_ID)
        self.assertEqual(info.dye_tint, 3)
        tint, channels = item_module.Item.Dye.GetChannels(ITEM_ID)
        self.assertEqual(tint, 3)
        self.assertEqual([int(channel) for channel in channels], [1, 2, 0, 0])
        self.assertEqual(channels[0], DyeColor.Mixed)
        self.assertEqual(channels[1], DyeColor.Blue)
        self.assertEqual(channels[2], DyeColor.NoColor)

    def test_get_dye_color_reads_the_first_non_zero_argument(self) -> None:
        """`GetDyeColor` walks the modifiers and answers the first non-zero `GetArg1`."""

        self.assertEqual(item_module.Item.GetDyeColor(ITEM_ID), 0x12)

    def test_the_two_bag_members_walk_the_bags_and_answer_the_defaults(self) -> None:
        """`GetItemIdFromModelID` and `GetItemByAgentID` go through the ported bag surface.

        Both walk ``[Bag.Backpack, Bag.Belt_Pouch, Bag.Bag_1, Bag.Bag_2]`` and answer ``0`` / ``None``
        when nothing matches — which is what this fixture has: a client whose item context reports no
        inventory record, so every bag is empty. The positive path (a bag that holds items, and the
        ``model_id``/``agent_id`` comparison finding one) is exercised in
        ``tests/test_py_inventory_offline.py``, over a real bag record with real item records in it.
        """

        self.client.item_context.read().read_inventory = lambda: None
        self.assertEqual(item_module.Item.GetItemIdFromModelID(MODEL_ID), 0)
        self.assertIsNone(item_module.Item.GetItemByAgentID(7))

    def test_the_bag_enum_is_the_sources_own(self) -> None:
        """Every bag id, in the source's spelling and order."""

        self.assertEqual(
            [(member.name, member.value) for member in item_module.Bag],
            [
                ("NoBag", 0), ("Backpack", 1), ("Belt_Pouch", 2), ("Bag_1", 3), ("Bag_2", 4),
                ("Equipment_Pack", 5), ("Material_Storage", 6), ("Unclaimed_Items", 7),
                ("Storage_1", 8), ("Storage_2", 9), ("Storage_3", 10), ("Storage_4", 11),
                ("Storage_5", 12), ("Storage_6", 13), ("Storage_7", 14), ("Storage_8", 15),
                ("Storage_9", 16), ("Storage_10", 17), ("Storage_11", 18), ("Storage_12", 19),
                ("Storage_13", 20), ("Storage_14", 21), ("Equipped_Items", 22), ("Max", 23),
            ],
        )
        self.assertTrue(item_module.Bag.Backpack.value == 1)

    def test_the_module_constants_are_the_sources(self) -> None:
        """The three constants at the top of the source's tail section."""

        self.assertEqual(item_module.SUMMONING_SICKNESS_EFFECT_ID, 2886)
        self.assertIn(513, item_module.KNOWN_SUMMONING_STONE_CREATURE_MODEL_IDS)
        self.assertIn(9264, item_module.KNOWN_SUMMONING_STONE_CREATURE_MODEL_IDS)
        self.assertEqual(len(item_module.KNOWN_SUMMONING_STONE_CREATURE_MODEL_IDS), 20)
        self.assertEqual(
            item_module.KNOWN_SUMMONING_STONE_CREATURE_ENC_NAMES, {"\\x8103\\x06FE"}
        )

    def test_the_helpers_are_the_bindings_own_helpers(self) -> None:
        """`item_type_name` and `dye_color_name` name every value the binding names."""

        self.assertEqual(item_module.item_type_name(int(ItemType.Sword)), "Sword")
        self.assertEqual(item_module.item_type_name(int(ItemType.Unknown)), "Unknown")
        self.assertEqual(item_module.item_type_name(999), "Unknown")
        self.assertEqual(item_module.dye_color_name(int(DyeColor.NoColor)), "None")
        self.assertEqual(item_module.dye_color_name(int(DyeColor.Blue)), "Blue")
        self.assertEqual(item_module.dye_color_name(999), "None")

    def test_the_dye_binding_defaults_are_the_bindings_defaults(self) -> None:
        """`PyDyeInfo()` is the default the binding hands out; the record form copies a record."""

        empty = item_module.PyDyeInfo()
        self.assertEqual(empty.dye_tint, 0)
        self.assertEqual(empty.dye1.ToInt(), 0)
        info = DyeInfoStruct()
        info.dye_tint = 9
        info.dye1 = 4
        copied = item_module.PyDyeInfo(info)
        self.assertEqual(copied.dye_tint, 9)
        self.assertEqual(copied.dye1.ToInt(), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)

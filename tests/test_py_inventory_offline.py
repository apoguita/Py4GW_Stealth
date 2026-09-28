"""Offline tests for the ported ``py_inventory`` module: the bag surface and the action surface.

**What is pinned.** Native's ``PyInventory`` binding (``inventory_bindings.cpp``, 216 lines) as this port
serves it: ``Bag``'s snapshot and item list over **real** ported records (``BagStruct``/``ItemStruct``
built from bytes behind a reader, the same construction the item-record tests use), the reads
(``GetIsStorageOpen``, the gold pair, ``GetHoveredItemID`` over the tooltip payload), the actions that
call this port's catalog resolvers (recorded through a fake client, because offline there is no client
to call), the dict snapshot ``get_bag``, and â€” member by member â€” the exact piece each raising member
names, so a missing guard cannot quietly become a wrong action.
"""

from __future__ import annotations

import ctypes
import struct
import unittest
from typing import Any, cast
from unittest import mock

from py4gw import item as item_module
from py4gw import py_inventory
from py4gw.context.gw_array import GWArray
from py4gw.context.instance_info_context import AreaInfoStruct, InstanceType, Region
from py4gw.context.item_context import BagStruct, BagType, InventoryStruct, ItemStruct
from py4gw.enums_src.item_enums import MAX_GOLD_CHARACTER, MAX_GOLD_STORAGE
from py4gw.item import PyItem
from py4gw.map import Map

#: Where the fixture puts things.
ITEM_A = 0x00500000
ITEM_B = 0x00500054
ITEM_TABLE = 0x00400000
BAG = 0x00280000
#: A second bag record, used to give an item an owning bag of a chosen ``BagType``.
GUARD_BAG = 0x00290000
INVENTORY = 0x00100000

ITEM_A_ID = 101
ITEM_B_ID = 102


class _Reader:
    """A reader over address ranges, the shape the ported records read through."""

    def __init__(self) -> None:
        self.regions: dict[int, bytes] = {}

    def add(self, address: int, data: bytes) -> None:
        self.regions[address] = data

    def read(self, address: int, size: int) -> bytes:
        for start, data in self.regions.items():
            if start <= address and address + size <= start + len(data):
                offset = address - start
                return data[offset : offset + size]
        raise OSError(f"no region covers 0x{address:08X}+{size}")


class _Tooltip:
    def __init__(self, payload: int, payload_len: int) -> None:
        self.payload = payload
        self.payload_len = payload_len


class _FakeItemContext:
    """The client's item-context **reader**: its state reads, and `read()` for the record.

    The shape matters: the port reaches the item array and the inventory relationship through the
    record `read()` hands out (``ItemContextStruct``), not through the reader itself â€” the item record
    tests and pyright both caught that when this fake had them flat.
    """

    def __init__(self, reader: _Reader, items: dict[int, ItemStruct], bag: BagStruct,
                 inventory: InventoryStruct, storage_open: bool) -> None:
        self._reader = reader
        self._records = _FakeItemContextStruct(items, bag, inventory)
        self.is_storage_open = storage_open

    def read(self) -> _FakeItemContextStruct:
        return self._records


class _FakeItemContextStruct:
    """The item context's own record: `GetItemById` and `read_inventory`."""

    def __init__(self, items: dict[int, ItemStruct], bag: BagStruct,
                 inventory: InventoryStruct) -> None:
        self._items = items
        self._bag = bag
        self._inventory = inventory

    def read_inventory(self) -> InventoryStruct | None:
        return self._inventory

    def GetItemById(self, item_id: int) -> ItemStruct | None:
        return self._items.get(int(item_id))


class _FakeInstanceInfo:
    """``GWContext.InstanceInfo()`` with one map record, for the chest guard's region read."""

    def __init__(self, map_info: AreaInfoStruct | None) -> None:
        self._map_info = map_info

    def GetMapInfo(self) -> AreaInfoStruct | None:
        return self._map_info


class _FakeGWContext:
    """``GWContext`` carrying that instance info."""

    def __init__(self, map_info: AreaInfoStruct | None) -> None:
        self._instance_info = _FakeInstanceInfo(map_info)

    def InstanceInfo(self) -> _FakeInstanceInfo:
        return self._instance_info


class _FakeWorldContext:
    """The world record's one field the salvage call reads (``item_methods.cpp:52-55``)."""

    def __init__(self, salvage_session_id: int) -> None:
        self.salvage_session_id = salvage_session_id


class _FakeClient:
    def __init__(self, **kwargs: Any) -> None:
        self.reader = kwargs["reader"]
        self.item_context = kwargs["item_context"]
        self.tooltip = kwargs.get("tooltip")
        self.world = kwargs.get("world", _FakeWorldContext(4242))
        self.calls: list[tuple[str, int, tuple[int, ...]]] = []
        self.messages: list[tuple[int, int, int]] = []
        self.resolvable: set[str] = set(kwargs.get("resolvable", ()))

    def resolves(self, name: str) -> bool:
        return name in self.resolvable

    def call_function(self, name: str, form: Any, *args: int) -> None:
        self.calls.append((name, int(form), tuple(int(a) for a in args)))

    def send_ui_message(self, message_id: int, wparam: int, lparam: int) -> None:
        self.messages.append((int(message_id), int(wparam), int(lparam)))

    def read_current_tooltip(self) -> _Tooltip | None:
        return self.tooltip

    def read_world_context(self) -> _FakeWorldContext:
        return self.world


class _TradeLookup:
    """Stand in for the trade context, as the item-record tests use it.

    ``ItemStruct.IsOfferedInTrade`` reads the player's trade offer through the trade context, so a
    record that is not bound to one refuses â€” which is why every record here is bound to this.
    """

    def __init__(self, offered_ids: set[int]) -> None:
        self.offered_ids = offered_ids

    def is_item_offered(self, item_id: int) -> bool:
        return int(item_id) in self.offered_ids

    def read(self) -> _TradeLookup:
        return self


def _item_record(reader: _Reader, address: int, item_id: int, agent_id: int, model_id: int,
                 quantity: int, slot: int) -> ItemStruct:
    """One real ``ItemStruct`` written into the reader at ``address``."""

    buffer = bytearray(ctypes.sizeof(ItemStruct))
    struct.pack_into("<I", buffer, 0x00, item_id)
    struct.pack_into("<I", buffer, 0x04, agent_id)
    struct.pack_into("<I", buffer, 0x2C, model_id)
    struct.pack_into("<H", buffer, 0x4C, quantity)
    buffer[0x50] = slot
    reader.add(address, bytes(buffer))
    return ItemStruct.from_buffer_copy(bytes(buffer)).bind_reader(
        reader, address, cast(Any, _TradeLookup(set()))
    )


def _fixture(resolvable: tuple[str, ...] = ()) -> tuple[_FakeClient, dict[str, Any]]:
    """A client whose bag holds two items, with an inventory record and a tooltip."""

    reader = _Reader()
    item_a = _item_record(reader, ITEM_A, ITEM_A_ID, 7, 1234, 3, 0)
    item_b = _item_record(reader, ITEM_B, ITEM_B_ID, 9, 5678, 1, 1)
    reader.add(ITEM_TABLE, struct.pack("<II", ITEM_A, ITEM_B))

    bag = BagStruct()
    bag.bag_type = 1
    bag.index = 1
    bag.container_item = 0
    bag.items_count = 2
    bag.items = GWArray(ITEM_TABLE, 2, 2, 0)
    bag.bind_reader(reader, BAG)
    reader.add(BAG, bytes(bag))

    inventory = InventoryStruct()
    inventory.bags[1] = BAG
    inventory.gold_character = 5000
    inventory.gold_storage = 1234
    inventory.bind_reader(reader, INVENTORY)
    reader.add(INVENTORY, bytes(inventory))

    context = _FakeItemContext(
        reader, {ITEM_A_ID: item_a, ITEM_B_ID: item_b}, bag, inventory, storage_open=True
    )
    client = _FakeClient(
        reader=reader, item_context=context, resolvable=resolvable, tooltip=None
    )
    return client, {"reader": reader, "bag": bag, "items": {ITEM_A_ID: item_a, ITEM_B_ID: item_b}}


class _FixtureCase(unittest.TestCase):
    """A test case with the client patched in and the map gate open."""

    resolvable: tuple[str, ...] = ()

    def setUp(self) -> None:
        self.client, self.parts = _fixture(self.resolvable)
        self.patchers = [
            mock.patch.object(py_inventory, "require_client", lambda: self.client),
            # `Bag.GetItems` answers `PyItem`s, and constructing one reads the record through `item.py`'s
            # own import of `require_client` â€” the same port, a second name.
            mock.patch.object(item_module, "require_client", lambda: self.client),
            mock.patch.object(Map, "IsMapReady", staticmethod(lambda: True)),
        ]
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in self.patchers:
            patcher.stop()


class BagTests(_FixtureCase):
    """`Bag` over the real bag record."""

    def test_the_context_copies_the_bag_record(self) -> None:
        """`GetContext`'s five fields, from the record the client holds."""

        bag = py_inventory.Bag(1, "Backpack")
        self.assertEqual(bag.id, 1)
        self.assertEqual(bag.name, "Backpack")
        self.assertEqual(bag.container_item, 0)
        self.assertEqual(bag.items_count, 2)
        self.assertTrue(bag.is_inventory_bag)
        self.assertFalse(bag.is_storage_bag)
        self.assertFalse(bag.is_material_storage)

    def test_the_size_is_the_array_size_and_the_count_is_the_field(self) -> None:
        """`GetSize` reads `items.size()`; `GetItemCount` answers what `GetContext` copied."""

        bag = py_inventory.Bag(1)
        self.assertEqual(bag.GetSize(), 2)
        self.assertEqual(bag.GetItemCount(), 2)

    def test_the_items_are_pyitem_objects_with_the_records_fields(self) -> None:
        """`GetItems` answers `PyItem`s â€” Reforged's callers read attributes off them."""

        bag = py_inventory.Bag(1)
        items = bag.GetItems()
        self.assertEqual([item.item_id for item in items], [ITEM_A_ID, ITEM_B_ID])
        self.assertTrue(all(isinstance(item, PyItem) for item in items))
        self.assertEqual(items[0].model_id, 1234)
        self.assertEqual(items[0].quantity, 3)
        self.assertEqual(items[1].agent_id, 9)
        self.assertEqual(items[1].slot, 1)

    def test_a_null_slot_is_skipped_and_the_others_keep_their_order(self) -> None:
        """Native skips a null pointer; the slot order is the array's own."""

        bag = py_inventory.Bag(1)
        self.parts["reader"].add(ITEM_TABLE, struct.pack("<II", 0, ITEM_B))
        items = bag.GetItems()
        self.assertEqual([item.item_id for item in items], [ITEM_B_ID])

    def test_an_invalid_bag_id_finds_no_record(self) -> None:
        """`GW::item::GetBag` requires `0 < bag_id < Max`."""

        for bag_id in (0, 23, 99):
            with self.subTest(bag_id=bag_id):
                bag = py_inventory.Bag(bag_id)
                self.assertEqual(bag.GetSize(), 0)
                self.assertEqual(bag.GetItems(), [])
                self.assertFalse(bag.is_inventory_bag)

    def test_the_map_gate_comes_first(self) -> None:
        """With the map not ready the record is not read at all."""

        with mock.patch.object(Map, "IsMapReady", staticmethod(lambda: False)):
            bag = py_inventory.Bag(1)
            items = bag.GetItems()
            size = bag.GetSize()
        self.assertEqual(items, [])
        self.assertEqual(size, 0)
        self.assertEqual(bag.items_count, 0)

    def test_the_default_name_is_the_bindings_default(self) -> None:
        """`Bag(id, name="")` is the binding's own default (``py::arg("name") = ""``)."""

        self.assertEqual(py_inventory.Bag(1).name, "")
        self.assertEqual(py_inventory.Bag(1, "Backpack").name, "Backpack")


class InventoryReadTests(_FixtureCase):
    """`PyInventory`'s reads."""

    def test_the_storage_flag_is_the_contexts_own(self) -> None:
        """`GetIsStorageOpen` reads the resolved storage-open address."""

        self.assertTrue(py_inventory.PyInventory().GetIsStorageOpen())
        self.client.item_context.is_storage_open = False
        self.assertFalse(py_inventory.PyInventory().GetIsStorageOpen())

    def test_the_gold_pair_is_the_inventory_records(self) -> None:
        """`GetGoldAmount`/`GetGoldAmountInStorage` are the record's two fields."""

        inventory = py_inventory.PyInventory()
        self.assertEqual(inventory.GetGoldAmount(), 5000)
        self.assertEqual(inventory.GetGoldAmountInStorage(), 1234)

    def test_the_gold_pair_answers_zero_without_an_inventory(self) -> None:
        """Native's `i ? i->gold_character : 0`."""

        self.client.item_context.read().read_inventory = lambda: None
        inventory = py_inventory.PyInventory()
        self.assertEqual(inventory.GetGoldAmount(), 0)
        self.assertEqual(inventory.GetGoldAmountInStorage(), 0)

    def test_no_tooltip_means_no_hovered_item(self) -> None:
        """`GetHoveredItem` returns null when the client shows no tooltip."""

        self.assertEqual(py_inventory.PyInventory().GetHoveredItemID(), 0)
        self.assertEqual(py_inventory.get_hovered_item_id(), 0)

    def test_a_one_word_item_tooltip_answers_its_item(self) -> None:
        """Payload length 8, two words: `{item_id, 0xff}`."""

        self.client.reader.add(0x00600000, struct.pack("<II", ITEM_A_ID, 0xFF))
        self.client.tooltip = _Tooltip(0x00600000, 0x8)
        self.assertEqual(py_inventory.PyInventory().GetHoveredItemID(), ITEM_A_ID)

    def test_a_two_word_item_tooltip_answers_the_first_non_zero_id(self) -> None:
        """Payload length 0xC, three words: `{item_id, item_id, 0xff}` â€” first non-zero wins."""

        self.client.reader.add(0x00600000, struct.pack("<III", 0, ITEM_B_ID, 0xFF))
        self.client.tooltip = _Tooltip(0x00600000, 0xC)
        self.assertEqual(py_inventory.PyInventory().GetHoveredItemID(), ITEM_B_ID)

    def test_a_tooltip_that_is_not_an_item_answers_nothing(self) -> None:
        """A payload of another length, or one whose marker word is not `0xff`."""

        self.client.reader.add(0x00600000, struct.pack("<IIII", ITEM_A_ID, 1, 2, 3))
        self.client.tooltip = _Tooltip(0x00600000, 0x8)
        self.assertEqual(py_inventory.PyInventory().GetHoveredItemID(), 0)
        self.client.tooltip = _Tooltip(0x00600000, 0x10)
        self.assertEqual(py_inventory.PyInventory().GetHoveredItemID(), 0)


class InventoryActionTests(_FixtureCase):
    """The actions, over the resolvers this port has."""

    resolvable = (
        py_inventory._DROP_ITEM_FUNC,
        py_inventory._DROP_GOLD_FUNC,
        py_inventory._CHANGE_GOLD_FUNC,
        py_inventory._DESTROY_ITEM_FUNC,
    )

    def test_drop_item_calls_the_drop_resolver_with_the_id_and_quantity(self) -> None:
        """`DropItem` â†’ `g_drop_item_func(item->item_id, quantity)`."""

        py_inventory.PyInventory().DropItem(ITEM_A_ID, 2)
        self.assertEqual(
            self.client.calls,
            [(py_inventory._DROP_ITEM_FUNC, 2, (ITEM_A_ID, 2))],
        )

    def test_drop_item_does_nothing_for_a_missing_item(self) -> None:
        """The binding's own guard: `if (item) Enqueue(...)`."""

        py_inventory.PyInventory().DropItem(4242, 1)
        self.assertEqual(self.client.calls, [])

    def test_destroy_item_calls_the_resolver_for_any_id(self) -> None:
        """The binding checks no item for this one."""

        py_inventory.PyInventory().DestroyItem(4242)
        self.assertEqual(self.client.calls, [(py_inventory._DESTROY_ITEM_FUNC, 4, (4242,))])

    def test_drop_gold_requires_the_character_to_hold_it(self) -> None:
        """`g_drop_gold_func && GetGoldAmountOnCharacter() >= amount`."""

        inventory = py_inventory.PyInventory()
        inventory.DropGold(5000)
        self.assertEqual(self.client.calls, [(py_inventory._DROP_GOLD_FUNC, 4, (5000,))])
        self.client.calls.clear()
        inventory.DropGold(5001)
        self.assertEqual(self.client.calls, [])

    def test_deposit_gold_moves_an_explicit_amount_through_change_gold(self) -> None:
        """`DepositGold(amount)` â†’ `ChangeGold(character - amount, storage + amount)`."""

        py_inventory.PyInventory().DepositGold(1000)
        self.assertEqual(
            self.client.calls,
            [(py_inventory._CHANGE_GOLD_FUNC, 2, (4000, 2234))],
        )

    def test_deposit_gold_refuses_what_the_limits_forbid(self) -> None:
        """The storage maximum and the character's own purse, as the methods layer checks them."""

        self.client.item_context.read()._inventory.gold_storage = MAX_GOLD_STORAGE - 10
        self.client.calls.clear()
        py_inventory.PyInventory().DepositGold(100)
        self.assertEqual(self.client.calls, [])
        self.client.item_context.read()._inventory.gold_storage = 0
        py_inventory.PyInventory().DepositGold(5001)
        self.assertEqual(self.client.calls, [])

    def test_deposit_gold_with_zero_moves_what_fits(self) -> None:
        """`amount == 0` is `min(MAX_GOLD_STORAGE - storage, character)`."""

        self.client.item_context.read()._inventory.gold_storage = MAX_GOLD_STORAGE - 100
        py_inventory.PyInventory().DepositGold(0)
        self.assertEqual(
            self.client.calls, [(py_inventory._CHANGE_GOLD_FUNC, 2, (4900, MAX_GOLD_STORAGE))]
        )

    def test_withdraw_gold_moves_an_explicit_amount_the_other_way(self) -> None:
        """`WithdrawGold(amount)` â†’ `ChangeGold(character + amount, storage - amount)`."""

        py_inventory.PyInventory().WithdrawGold(1000)
        self.assertEqual(
            self.client.calls, [(py_inventory._CHANGE_GOLD_FUNC, 2, (6000, 234))]
        )

    def test_withdraw_gold_refuses_what_the_limits_forbid(self) -> None:
        """The character maximum (100,000) and the storage's own holdings."""

        self.client.item_context.read()._inventory.gold_character = MAX_GOLD_CHARACTER - 10
        py_inventory.PyInventory().WithdrawGold(100)
        self.assertEqual(self.client.calls, [])
        self.client.item_context.read()._inventory.gold_character = 0
        py_inventory.PyInventory().WithdrawGold(2000)
        self.assertEqual(self.client.calls, [])

    def test_change_gold_requires_the_totals_to_add_up(self) -> None:
        """`(storage + character) == (new_character + new_storage)` â€” the methods layer's check."""

        py_inventory.PyInventory()._change_gold(1, 1)
        self.assertEqual(self.client.calls, [])
        py_inventory.PyInventory()._change_gold(4000, 2234)
        self.assertEqual(
            self.client.calls, [(py_inventory._CHANGE_GOLD_FUNC, 2, (4000, 2234))]
        )

    def test_pick_up_item_sends_the_interact_message_with_the_agent(self) -> None:
        """`kSendInteractItem` with `kInteractAgent{item->agent_id, call_target == 1}`."""

        py_inventory.PyInventory().PickUpItem(ITEM_A_ID)
        self.assertEqual(self.client.messages, [(0x3000000F, 7, 0)])
        py_inventory.PyInventory().PickUpItem(ITEM_B_ID, True)
        self.assertEqual(self.client.messages[-1], (0x3000000F, 9, 1))

    def test_pick_up_item_does_nothing_for_a_missing_item(self) -> None:
        """The binding's own guard again."""

        py_inventory.PyInventory().PickUpItem(4242)
        self.assertEqual(self.client.messages, [])

    def test_a_missing_resolver_means_no_call(self) -> None:
        """Native checks the function pointer before calling it."""

        self.client.resolvable = set()
        inventory = py_inventory.PyInventory()
        inventory.DropItem(ITEM_A_ID, 1)
        inventory.DestroyItem(ITEM_A_ID)
        inventory.DropGold(10)
        inventory.DepositGold(10)
        self.assertEqual(self.client.calls, [])


class GetBagSnapshotTests(_FixtureCase):
    """`get_bag`, the dict snapshot."""

    def test_the_snapshot_carries_the_bindings_keys(self) -> None:
        """Every key native writes, with the record's values."""

        snapshot = py_inventory.get_bag(1)
        self.assertEqual(
            sorted(snapshot),
            [
                "container_item", "id", "is_inventory_bag", "is_material_storage",
                "is_storage_bag", "items", "items_count", "size",
            ],
        )
        self.assertEqual(snapshot["id"], 1)
        self.assertEqual(snapshot["items_count"], 2)
        self.assertEqual(snapshot["size"], 2)
        self.assertTrue(snapshot["is_inventory_bag"])

    def test_the_snapshot_items_are_the_dicts_native_builds(self) -> None:
        """`get_bag` keeps native's dict shape, unlike `Bag.GetItems` (which Reforged reads)."""

        snapshot = py_inventory.get_bag(1)
        self.assertEqual(
            snapshot["items"],
            [
                {"item_id": ITEM_A_ID, "slot": 0, "model_id": 1234, "quantity": 3},
                {"item_id": ITEM_B_ID, "slot": 1, "model_id": 5678, "quantity": 1},
            ],
        )

    def test_an_invalid_bag_gives_the_empty_snapshot(self) -> None:
        """Native returns the zeroed dict when the bag is not there."""

        for bag_id in (0, 23):
            with self.subTest(bag_id=bag_id):
                snapshot = py_inventory.get_bag(bag_id)
                self.assertEqual(snapshot["items"], [])
                self.assertEqual(snapshot["size"], 0)
                self.assertFalse(snapshot["is_inventory_bag"])


class MoveItemTests(_FixtureCase):
    """`MoveItem`, which needed the four-word call form and now has it."""

    resolvable = (py_inventory._MOVE_ITEM_FUNC,)

    def test_it_calls_the_move_resolver_with_four_words(self) -> None:
        """`g_move_item_func(item->item_id, quantity, bag->index, slot)` (``item_methods.cpp:164``)."""

        py_inventory.PyInventory().MoveItem(ITEM_A_ID, 1, 0, 2)
        self.assertEqual(
            self.client.calls,
            [(py_inventory._MOVE_ITEM_FUNC, 8, (ITEM_A_ID, 2, 1, 0))],
        )

    def test_the_quantity_is_clamped_to_what_the_item_holds(self) -> None:
        """`quantity <= 0` means all of it; more than it holds means all of it."""

        inventory = py_inventory.PyInventory()
        inventory.MoveItem(ITEM_A_ID, 1, 0, 0)
        self.assertEqual(self.client.calls[-1][2], (ITEM_A_ID, 3, 1, 0))
        inventory.MoveItem(ITEM_A_ID, 1, 0, 99)
        self.assertEqual(self.client.calls[-1][2], (ITEM_A_ID, 3, 1, 0))

    def test_a_slot_beyond_the_bags_array_is_refused(self) -> None:
        """`bag->items.size() < slot` — the methods layer's own bound."""

        py_inventory.PyInventory().MoveItem(ITEM_A_ID, 1, 5, 1)
        self.assertEqual(self.client.calls, [])

    def test_a_missing_item_or_bag_is_refused(self) -> None:
        """The binding looks the item up first, and the methods layer takes the bag."""

        inventory = py_inventory.PyInventory()
        inventory.MoveItem(4242, 1, 0, 1)
        inventory.MoveItem(ITEM_A_ID, 3, 0, 1)
        self.assertEqual(self.client.calls, [])


class CanAccessXunlaiChestTests(_FixtureCase):
    """``CanAccessXunlaiChest``: an outpost, and never presearing (``item_methods.cpp:57-62``)."""

    def _chest(self, instance_type: int, region: int | None) -> bool:
        area_info: AreaInfoStruct | None = None
        if region is not None:
            area_info = AreaInfoStruct()
            area_info.region = region
        with mock.patch.object(Map, "GetInstanceType", staticmethod(lambda: instance_type)):
            with mock.patch.object(py_inventory, "GWContext", _FakeGWContext(area_info)):
                return py_inventory._can_access_xunlai_chest()

    def test_only_an_outpost_reaches_the_chest(self) -> None:
        """``GetInstanceType() != Outpost`` answers false before the map record is read at all."""

        self.assertFalse(self._chest(InstanceType.EXPLORABLE, int(Region.Region_Kryta)))
        self.assertFalse(self._chest(InstanceType.LOADING, int(Region.Region_Kryta)))
        self.assertTrue(self._chest(InstanceType.OUTPOST, int(Region.Region_Kryta)))

    def test_presearing_is_the_one_region_that_may_not(self) -> None:
        """``region != Region_Presearing``, and a record that cannot be read is false."""

        self.assertFalse(self._chest(InstanceType.OUTPOST, int(Region.Region_Presearing)))
        self.assertFalse(self._chest(InstanceType.OUTPOST, None))


class InteractGuardTests(_FixtureCase):
    """``IsStorageBag``, ``IsStorageItem`` and ``CanInteractWithItem`` over real bag records."""

    def _item_in(self, bag_type: int) -> ItemStruct:
        """One item record whose ``bag`` pointer names a bag record of ``bag_type``."""

        bag = BagStruct()
        bag.bag_type = int(bag_type)
        self.parts["reader"].add(GUARD_BAG, bytes(bag))
        item = self.client.item_context.read().GetItemById(ITEM_A_ID)
        assert item is not None
        item.bag = GUARD_BAG
        return item

    def test_the_free_storage_item_rule_is_storage_only(self) -> None:
        """``IsStorageItem(item)`` is ``IsStorageBag(item->bag)`` — material storage is not storage."""

        guard = py_inventory._is_storage_item
        self.assertTrue(guard(self.client, self._item_in(BagType.Storage)))
        self.assertFalse(guard(self.client, self._item_in(BagType.MaterialStorage)))
        self.assertFalse(guard(self.client, self._item_in(BagType.Inventory)))
        self.assertFalse(guard(self.client, self._item_in(BagType.Equipped)))

    def test_a_null_item_answers_the_chest_question(self) -> None:
        """``item && !IsStorageItem(item) || CanAccessXunlaiChest()`` — ``&&`` binds tighter."""

        guard = py_inventory._can_interact_with_item
        with mock.patch.object(py_inventory, "_can_access_xunlai_chest", lambda: False):
            self.assertFalse(guard(self.client, None))
        with mock.patch.object(py_inventory, "_can_access_xunlai_chest", lambda: True):
            self.assertTrue(guard(self.client, None))

    def test_a_storage_item_needs_the_chest(self) -> None:
        """The first branch fails for a storage item, so only ``CanAccessXunlaiChest`` can pass it."""

        item = self._item_in(BagType.Storage)
        guard = py_inventory._can_interact_with_item
        with mock.patch.object(py_inventory, "_can_access_xunlai_chest", lambda: False):
            self.assertFalse(guard(self.client, item))
        with mock.patch.object(py_inventory, "_can_access_xunlai_chest", lambda: True):
            self.assertTrue(guard(self.client, item))


class GuardedActionTests(_FixtureCase):
    """`UseItem`, `EquipItem` and `IdentifyItem` — the three the interact guard was holding."""

    resolvable = (
        py_inventory._USE_ITEM_FUNC,
        py_inventory._EQUIP_ITEM_FUNC,
        py_inventory._IDENTIFY_ITEM_FUNC,
    )

    def _in_storage(self) -> None:
        """Point the first item's bag pointer at a storage bag record."""

        bag = BagStruct()
        bag.bag_type = int(BagType.Storage)
        self.parts["reader"].add(GUARD_BAG, bytes(bag))
        item = self.client.item_context.read().GetItemById(ITEM_A_ID)
        assert item is not None
        item.bag = GUARD_BAG

    def test_use_item_calls_the_resolver_with_the_items_own_id(self) -> None:
        """``g_use_item_func(item->item_id)`` — one word (``item_methods.cpp:114-121``)."""

        py_inventory.PyInventory().UseItem(ITEM_A_ID)
        self.assertEqual(self.client.calls, [(py_inventory._USE_ITEM_FUNC, 4, (ITEM_A_ID,))])

    def test_use_item_does_nothing_for_a_missing_item(self) -> None:
        """``if (!(g_use_item_func && item))`` — the binding looks the item up first."""

        py_inventory.PyInventory().UseItem(4242)
        self.assertEqual(self.client.calls, [])

    def test_a_storage_item_is_refused_until_the_chest_is_reachable(self) -> None:
        """The guard's own shape: refused by its first branch, allowed by ``CanAccessXunlaiChest``."""

        self._in_storage()
        with mock.patch.object(py_inventory, "_can_access_xunlai_chest", lambda: False):
            py_inventory.PyInventory().UseItem(ITEM_A_ID)
        self.assertEqual(self.client.calls, [])
        with mock.patch.object(py_inventory, "_can_access_xunlai_chest", lambda: True):
            py_inventory.PyInventory().UseItem(ITEM_A_ID)
        self.assertEqual(self.client.calls, [(py_inventory._USE_ITEM_FUNC, 4, (ITEM_A_ID,))])

    def test_equip_item_takes_the_agent_the_caller_gave(self) -> None:
        """``g_equip_item_func(item->item_id, agent_id)`` (``:123-134``)."""

        py_inventory.PyInventory().EquipItem(ITEM_A_ID, 7)
        self.assertEqual(self.client.calls, [(py_inventory._EQUIP_ITEM_FUNC, 2, (ITEM_A_ID, 7))])

    def test_an_empty_agent_id_means_the_controlled_character(self) -> None:
        """``if (!agent_id) agent_id = agent::GetControlledCharacterId();``."""

        with mock.patch("py4gw.player.Player.GetAgentID", staticmethod(lambda: 77)):
            py_inventory.PyInventory().EquipItem(ITEM_A_ID, 0)
        self.assertEqual(self.client.calls, [(py_inventory._EQUIP_ITEM_FUNC, 2, (ITEM_A_ID, 77))])

    def test_identify_item_passes_the_ids_the_caller_gave(self) -> None:
        """The methods layer guards both records and calls with its own two arguments."""

        py_inventory.PyInventory().IdentifyItem(ITEM_A_ID, ITEM_B_ID)
        self.assertEqual(
            self.client.calls,
            [(py_inventory._IDENTIFY_ITEM_FUNC, 2, (ITEM_A_ID, ITEM_B_ID))],
        )


class SalvageTests(_FixtureCase):
    """``Salvage`` and the module's ``salvage``: the binding's guards, then ``SalvageStart``."""

    resolvable = (py_inventory._SALVAGE_START_FUNC,)

    def test_the_binding_guard_needs_a_kit_and_a_salvageable_item(self) -> None:
        """``kit->IsSalvageKit() && item->IsSalvagable()`` (``inventory_bindings.cpp:115-120``)."""

        py_inventory.PyInventory().Salvage(ITEM_A_ID, ITEM_B_ID)
        py_inventory.salvage(ITEM_A_ID, ITEM_B_ID)
        self.assertEqual(self.client.calls, [])
        self.assertEqual(self.client.messages, [])

    def test_a_missing_record_does_nothing(self) -> None:
        """``if (item && kit && ...)`` — a missing id stops before the guard chain."""

        py_inventory.PyInventory().Salvage(4242, ITEM_B_ID)
        py_inventory.salvage(ITEM_A_ID, 4242)
        self.assertEqual(self.client.calls, [])
        self.assertEqual(self.client.messages, [])

    def test_salvage_start_sends_the_packet_then_calls_the_resolver(self) -> None:
        """``kPreStartSalvage{item_id, kit_id}``, then ``g_salvage_start_func(kit, session, item)``."""

        self.assertTrue(py_inventory._salvage_start(self.client, ITEM_A_ID, ITEM_B_ID))
        self.assertEqual(
            self.client.messages,
            [(py_inventory._K_PRE_START_SALVAGE, ITEM_B_ID, ITEM_A_ID)],
        )
        self.assertEqual(
            self.client.calls,
            [(py_inventory._SALVAGE_START_FUNC, 5, (ITEM_A_ID, 4242, ITEM_B_ID))],
        )

    def test_salvage_start_needs_its_resolver(self) -> None:
        """``!(g_salvage_start_func && ...)`` answers false and sends nothing."""

        self.client.resolvable = set()
        self.assertFalse(py_inventory._salvage_start(self.client, ITEM_A_ID, ITEM_B_ID))
        self.assertEqual(self.client.messages, [])
        self.assertEqual(self.client.calls, [])


class UnportedMemberTests(_FixtureCase):
    """Every raising member names its own missing piece."""

    def test_each_raising_member_names_what_it_needs(self) -> None:
        """The StoC path and the frame-click path are what is left, and both are named."""

        inventory = py_inventory.PyInventory()
        cases = (
            ("PyInventory.OpenXunlaiWindow", inventory.OpenXunlaiWindow, "StoC"),
            ("PyInventory.AcceptSalvageWindow", inventory.AcceptSalvageWindow, "frame-click"),
            ("accept_salvage_window", py_inventory.accept_salvage_window, "frame-click"),
        )
        for member, call, expected in cases:
            with self.subTest(member=member):
                with self.assertRaises(NotImplementedError) as caught:
                    call()
                message = str(caught.exception)
                self.assertIn(member, message)
                self.assertIn(expected, message)

    def test_the_gold_limits_are_the_sources_own_constants(self) -> None:
        """The two limits `Item_enums` declares, used by the deposit and withdraw checks."""

        self.assertEqual(MAX_GOLD_STORAGE, 1_000_000)
        self.assertEqual(MAX_GOLD_CHARACTER, 100_000)


if __name__ == "__main__":
    unittest.main(verbosity=2)

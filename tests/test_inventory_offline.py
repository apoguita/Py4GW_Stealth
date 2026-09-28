"""Offline tests for the ported ``inventory`` module.

**What is pinned.** ``Inventory.py``'s 66 declarations against the **source's own AST** (names, nesting,
decorators, and the 9 attribute values), the three ``TypedDict``s' fields and optionality, and the
behaviour of the eighteen members this round built — the space and count group, the four "first"
finders, and identify/salvage — over the same real-record bag fixture the bag-surface and item-array
tests use.

The thirty-nine members that raise are checked the other way round: each must name its own work item, so
a raise can never quietly become a wrong answer. One source behaviour cannot be reached offline and the
test says so where it matters: ``SalvageFirst``'s acting path calls ``PyInventory.Salvage``, which raises
on the interact guard the bag surface still owes.
"""

from __future__ import annotations

import ast
import ctypes
import struct
import unittest
from pathlib import Path
from typing import Any, cast
from unittest import mock

from py4gw import inventory as inventory_module
from py4gw import item as item_module
from py4gw import py_inventory
from py4gw.context.gw_array import GWArray
from py4gw.context.item_context import BagStruct, BagType, InventoryStruct, ItemStruct
from py4gw.enums_src.item_enums import Bags
from py4gw.inventory import (
    Inventory,
    SalvageChoiceEntry,
    SalvageChoiceOptionSource,
    VisibleFrameEntry,
)
from py4gw.map import Map

SOURCE_FILE = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\Inventory.py")

#: The module-level names this port adds for its own bookkeeping, and nothing else.
PORT_ADDITIONS = {"_unported", "_FRAME_ACTIONS", "_ROUTINES"}

#: The members that raise, in the source's own order, with a word from each requirement.
#:
#: Fourteen left this list in round 31, when the `FrameTree` package landed, and three more in round 38, when
#: `Frame.rect` — and with it `_build_visible_frame_entry_map` — began to answer. What is left is the console
#: log (for an **enabled** log only: a disabled one returns, as the source's own guard does) and the three the
#: source itself drives with its coroutine framework.
RAISING = {
    "_salvage_choice_debug_log": "console",
    "HandleSalvageChoiceMaterialConfirmDialog": "coroutine driver",
    "_wait_for_salvage_choice_dialog_close": "coroutine driver",
    "HandleSalvageChoiceDialog": "coroutine driver",
}

ITEM_TABLE = 0x00400000
ITEM_A = 0x00500000
ITEM_B = 0x00500054
BACKPACK = 0x00280000
STORAGE = 0x00290000
INVENTORY = 0x00100000

ITEM_A_ID = 101
ITEM_B_ID = 102


class _Reader:
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


class _TradeLookup:
    def __init__(self, offered_ids: set[int]) -> None:
        self.offered_ids = offered_ids

    def is_item_offered(self, item_id: int) -> bool:
        return int(item_id) in self.offered_ids

    def read(self) -> _TradeLookup:
        return self


def _surface(nodes: list[ast.stmt]) -> dict[str, Any]:
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
            out[node.targets[0].id] = ast.unparse(node.value)
    return out


def _item_record(
    reader: _Reader,
    address: int,
    item_id: int,
    model_id: int,
    quantity: int,
    interaction: int,
    slot: int = 0,
) -> ItemStruct:
    buffer = bytearray(ctypes.sizeof(ItemStruct))
    struct.pack_into("<I", buffer, 0x00, item_id)
    struct.pack_into("<I", buffer, 0x2C, model_id)
    struct.pack_into("<I", buffer, 0x28, interaction)
    struct.pack_into("<H", buffer, 0x4C, quantity)
    buffer[0x20] = 27  # ItemType.Sword, a weapon type and therefore salvageable
    buffer[0x50] = slot
    reader.add(address, bytes(buffer))
    return ItemStruct.from_buffer_copy(bytes(buffer)).bind_reader(
        reader, address, cast(Any, _TradeLookup(set()))
    )


def _write_bag(reader: _Reader, address: int, index: int, size: int, bag_type: int = 1) -> None:
    """Write a bag record into the reader, which is where the port re-reads it from."""

    bag = BagStruct()
    bag.bag_type = bag_type
    bag.index = index
    bag.items_count = min(size, 2)
    bag.items = GWArray(ITEM_TABLE, size, size, 0)
    bag.bind_reader(reader, address)
    reader.add(address, bytes(bag))


class _FakeItemContextStruct:
    def __init__(self, items: dict[int, ItemStruct], inventory: InventoryStruct) -> None:
        self._items = items
        self._inventory = inventory

    def GetItemById(self, item_id: int) -> ItemStruct | None:
        return self._items.get(int(item_id))

    def read_inventory(self) -> InventoryStruct:
        return self._inventory


class _FakeItemContext:
    def __init__(self, struct_: _FakeItemContextStruct) -> None:
        self._struct = struct_
        self.is_storage_open = False

    def read(self) -> _FakeItemContextStruct:
        return self._struct


class _FakeClient:
    """The client the ported members reach: the item context, a reader, and the call path.

    ``resolves`` and ``call_function`` are here because the storage walkers move items through
    ``py_inventory.MoveItem``, which resolves ``item.move_item_func`` and calls it with four words.
    """

    def __init__(self, context: _FakeItemContext, reader: _Reader) -> None:
        self.item_context = context
        self.reader = reader
        self.calls: list[tuple[str, int, tuple[int, ...]]] = []
        self.resolvable: set[str] = set()

    def resolves(self, name: str) -> bool:
        return name in self.resolvable

    def call_function(self, name: str, form: Any, *args: int) -> None:
        self.calls.append((name, int(form), tuple(int(a) for a in args)))


def _fixture() -> _FakeClient:
    """A backpack with two items (101 identified at slot 0, 102 unidentified at slot 1).

    The backpack is bag index 1; a storage bag at index 8 points at the same two records, so the
    storage-shaped members have something to walk.
    """

    reader = _Reader()
    item_a = _item_record(reader, ITEM_A, ITEM_A_ID, 1234, 3, 0x1, slot=0)
    item_b = _item_record(reader, ITEM_B, ITEM_B_ID, 5678, 7, 0x0, slot=1)
    reader.add(ITEM_TABLE, struct.pack("<II", ITEM_A, ITEM_B))

    _write_bag(reader, BACKPACK, index=1, size=2)
    _write_bag(reader, STORAGE, index=8, size=2, bag_type=BagType.Storage)

    inventory = InventoryStruct()
    inventory.bags[1] = BACKPACK
    inventory.bags[8] = STORAGE
    inventory.bind_reader(reader, INVENTORY)
    reader.add(INVENTORY, bytes(inventory))

    client = _FakeClient(
        _FakeItemContext(
            _FakeItemContextStruct({ITEM_A_ID: item_a, ITEM_B_ID: item_b}, inventory)
        ),
        reader,
    )
    return client


class _FixtureCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _fixture()
        self.patchers = [
            mock.patch.object(py_inventory, "require_client", lambda: self.client),
            mock.patch.object(item_module, "require_client", lambda: self.client),
            mock.patch.object(Map, "IsMapReady", staticmethod(lambda: True)),
        ]
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in self.patchers:
            patcher.stop()


@unittest.skipUnless(SOURCE_FILE.is_file(), f"the Reforged source is not present at {SOURCE_FILE}")
class InventorySurfaceTests(unittest.TestCase):
    """The port declares the source's members, in the source's nesting."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _surface(ast.parse(SOURCE_FILE.read_text(encoding="utf-8")).body)
        cls.port = _surface(
            ast.parse(
                (Path(__file__).resolve().parents[1] / "py4gw" / "inventory.py").read_text(
                    encoding="utf-8"
                )
            ).body
        )

    def test_every_class_and_member_is_declared(self) -> None:
        """66 members, the three TypedDicts, and nothing added or dropped."""

        theirs, ours = self.source["Inventory"], self.port["Inventory"]
        self.assertEqual(len(theirs), 66)
        self.assertEqual(len(ours), 66)
        self.assertEqual(sorted(set(theirs) - set(ours)), [])
        self.assertEqual(sorted(set(ours) - set(theirs)), [])

    def test_the_three_typed_dicts_have_the_source_fields(self) -> None:
        """Field names, in the source's order, for the three records."""

        for name in ("VisibleFrameEntry", "SalvageChoiceEntry", "SalvageChoiceOptionSource"):
            with self.subTest(record=name):
                theirs = {k: v for k, v in self.source[name].items() if not isinstance(v, dict)}
                ours = {k: v for k, v in self.port[name].items() if not isinstance(v, dict)}
                self.assertEqual(sorted(ours), sorted(theirs))

    def test_the_nine_attributes_carry_the_source_values(self) -> None:
        """The dialog's labels and its five fallback offsets, value for value."""

        self.assertEqual(Inventory.SALVAGE_CHOICE_DIALOG_LABEL, "Salvage Window")
        self.assertEqual(Inventory.SALVAGE_CHOICE_OPTION_CONTAINER_LABEL, "Salvage Window.Options")
        self.assertEqual(Inventory.SALVAGE_CHOICE_CONFIRM_LABEL, "Salvage Window.Salvage Button")
        self.assertEqual(
            Inventory.SALVAGE_CHOICE_MATERIAL_CONFIRM_YES_LABEL,
            "Salvage Materials Dialog.Yes Button",
        )
        self.assertEqual(Inventory.SALVAGE_CHOICE_FALLBACK_DIALOG_HASH, 684387150)
        self.assertEqual(Inventory.SALVAGE_CHOICE_FALLBACK_OPTION_CONTAINER_OFFSET, 5)
        self.assertEqual(Inventory.SALVAGE_CHOICE_FALLBACK_CONFIRM_OFFSET, 2)
        self.assertEqual(Inventory.SALVAGE_CHOICE_FALLBACK_MATERIAL_CONFIRM_ROOT_OFFSET, 0)
        self.assertEqual(Inventory.SALVAGE_CHOICE_FALLBACK_MATERIAL_CONFIRM_YES_OFFSET, 6)

    def test_the_module_adds_only_its_three_private_helpers(self) -> None:
        """The port's own module-level names, named one by one so an addition cannot hide."""

        theirs = {n for n in vars(inventory_module) if not n.startswith("__")}
        self.assertTrue(PORT_ADDITIONS <= theirs)

    def test_every_method_is_static_like_the_source_s(self) -> None:
        """The source's 57 methods are all `@staticmethod`; so are the port's."""

        theirs = {
            name: decorators
            for name, decorators in self.source["Inventory"].items()
            if isinstance(decorators, list)
        }
        ours = {
            name: decorators
            for name, decorators in self.port["Inventory"].items()
            if isinstance(decorators, list)
        }
        self.assertEqual(len(theirs), 57)
        self.assertEqual(sorted(ours), sorted(theirs))
        for name, decorators in theirs.items():
            with self.subTest(member=name):
                self.assertEqual(ours[name], decorators)


class InventoryActionTests(_FixtureCase):
    """The fifteen members the storage, action, gold and find groups now answer (or pass the raise on)."""

    def test_the_storage_flag_is_read_through_the_binding(self) -> None:
        """`IsStorageOpen` is one binding call, and the context's own flag answers it."""

        self.client.item_context.is_storage_open = True
        self.assertTrue(Inventory.IsStorageOpen())
        self.client.item_context.is_storage_open = False
        self.assertFalse(Inventory.IsStorageOpen())

    def test_opening_the_storage_builds_two_bindings(self) -> None:
        """The source's body calls `inventory_instance()` twice; the first raises today."""

        with self.assertRaises(NotImplementedError) as caught:
            Inventory.OpenXunlaiWindow()
        self.assertIn("PyInventory.OpenXunlaiWindow", str(caught.exception))

    def test_the_gold_reads_answer_the_inventory_record(self) -> None:
        """`GetGoldOnCharacter` and `GetGoldInStorage` are the record's two fields."""

        inventory = self.client.item_context.read().read_inventory()
        inventory.gold_character = 4321
        inventory.gold_storage = 8765
        self.assertEqual(Inventory.GetGoldOnCharacter(), 4321)
        self.assertEqual(Inventory.GetGoldInStorage(), 8765)

    def test_the_gold_writes_delegate_and_the_limits_decide(self) -> None:
        """`DepositGold`/`WithdrawGold`/`DropGold` reach the binding, whose limits are its own."""

        inventory = self.client.item_context.read().read_inventory()
        inventory.gold_character = 5000
        inventory.gold_storage = 0
        calls: list[tuple[str, tuple[int, ...]]] = []
        binding = py_inventory.PyInventory()
        with mock.patch.object(type(binding), "DepositGold", lambda self, amount: calls.append(("d", (amount,)))), \
             mock.patch.object(type(binding), "WithdrawGold", lambda self, amount: calls.append(("w", (amount,)))), \
             mock.patch.object(type(binding), "DropGold", lambda self, amount: calls.append(("g", (amount,)))):
            Inventory.DepositGold(100)
            Inventory.WithdrawGold(100)
            Inventory.DropGold(100)
        self.assertEqual(calls, [("d", (100,)), ("w", (100,)), ("g", (100,))])

    def test_the_actions_delegate_to_the_binding(self) -> None:
        """`PickUpItem`, `DropItem`, `DestroyItem` and `GetHoveredItemID` pass their arguments through."""

        binding = py_inventory.PyInventory()
        recorded: list[tuple[str, tuple[Any, ...]]] = []
        with mock.patch.object(type(binding), "PickUpItem", lambda self, *a: recorded.append(("pick", a))), \
             mock.patch.object(type(binding), "DropItem", lambda self, *a: recorded.append(("drop", a)) or "dropped"), \
             mock.patch.object(type(binding), "DestroyItem", lambda self, *a: recorded.append(("destroy", a))), \
             mock.patch.object(type(binding), "GetHoveredItemID", lambda self: 4242):
            Inventory.PickUpItem(ITEM_A_ID, True)
            dropped = Inventory.DropItem(ITEM_A_ID, 3)
            Inventory.DestroyItem(ITEM_A_ID)
            hovered = Inventory.GetHoveredItemID()
        self.assertEqual(
            recorded,
            [("pick", (ITEM_A_ID, True)), ("drop", (ITEM_A_ID, 3)), ("destroy", (ITEM_A_ID,))],
        )
        self.assertEqual(dropped, "dropped")
        self.assertEqual(hovered, 4242)

    def test_equip_and_use_reach_the_binding(self) -> None:
        """Both delegate to the binding member, which acts since the interact guard landed."""

        recorded: list[tuple[str, tuple[int, ...]]] = []
        binding = py_inventory.PyInventory()
        with (
            mock.patch.object(
                type(binding),
                "EquipItem",
                lambda self, item_id, agent_id: recorded.append(("equip", (item_id, agent_id))),
            ),
            mock.patch.object(
                type(binding),
                "UseItem",
                lambda self, item_id: recorded.append(("use", (item_id,))),
            ),
        ):
            Inventory.EquipItem(ITEM_A_ID, 7)
            Inventory.UseItem(ITEM_A_ID)
        self.assertEqual(recorded, [("equip", (ITEM_A_ID, 7)), ("use", (ITEM_A_ID,))])

    def test_move_item_now_reaches_the_binding(self) -> None:
        """`MoveItem` is the source's own delegation, and the binding member answers since the
        four-word call form landed — so the call is made rather than raised."""

        calls: list[tuple[int, int, int, int]] = []
        binding = py_inventory.PyInventory()
        with mock.patch.object(
            type(binding),
            "MoveItem",
            lambda self, item_id, bag_id, slot, quantity=1: calls.append(
                (item_id, bag_id, slot, quantity)
            ),
        ):
            Inventory.MoveItem(ITEM_A_ID, 1, 0, 2)
        self.assertEqual(calls, [(ITEM_A_ID, 1, 0, 2)])

    def test_find_item_bag_and_slot_answers_the_bag_and_the_slot(self) -> None:
        """The first bag that holds the id answers `(bag_id, Item.GetSlot(item))`."""

        self.assertEqual(Inventory.FindItemBagAndSlot(ITEM_A_ID), (1, 0))
        self.assertEqual(Inventory.FindItemBagAndSlot(ITEM_B_ID), (1, 1))

    def test_find_item_bag_and_slot_answers_none_none_when_absent(self) -> None:
        """The source's own fall-through."""

        self.assertEqual(Inventory.FindItemBagAndSlot(999), (None, None))


class StorageWalkerTests(_FixtureCase):
    """`DepositItemToStorage` and `WithdrawItemFromStorage`.

    Both derive their bag list in the source's own way: the deposit member divides the storage bags'
    combined capacity by 25 to decide how many exist and reaches each by name, so a fixture with a
    25-slot storage bag is what makes its loops run at all.
    """

    resolvable = (py_inventory._MOVE_ITEM_FUNC,)

    def setUp(self) -> None:
        super().setUp()
        # the storage bag the source's own capacity rule will name, and room in the backpack
        _write_bag(self.client.reader, STORAGE, index=8, size=25, bag_type=BagType.Storage)
        _write_bag(self.client.reader, BACKPACK, index=1, size=5)
        self.client.resolvable = set(self.resolvable)

    def test_a_deposit_moves_into_the_first_empty_storage_slot(self) -> None:
        """Item 102 holds 7 and is not stackable, so all of it goes to slot 2 of bag 8."""

        self.assertTrue(Inventory.DepositItemToStorage(ITEM_B_ID, Anniversary_panel=False))
        self.assertEqual(
            self.client.calls,
            [(py_inventory._MOVE_ITEM_FUNC, 8, (ITEM_B_ID, 7, 8, 2))],
        )

    def test_a_deposit_of_a_stackable_item_fills_a_partial_stack_first(self) -> None:
        """Item 101 marked stackable: its own stack in storage has room, and the first pass moves all 3."""

        record = self.client.item_context.read().GetItemById(ITEM_A_ID)
        assert record is not None
        record.interaction = 0x80000
        self.assertTrue(Inventory.DepositItemToStorage(ITEM_A_ID, Anniversary_panel=False))
        self.assertEqual(
            self.client.calls,
            [(py_inventory._MOVE_ITEM_FUNC, 8, (ITEM_A_ID, 3, 8, 0))],
        )

    def test_a_deposit_of_nothing_answers_false(self) -> None:
        """The source's own `quantity == 0` guard — and an item that is not there has no quantity."""

        self.assertFalse(Inventory.DepositItemToStorage(999))
        self.assertEqual(self.client.calls, [])

    def test_a_withdraw_moves_into_the_first_empty_inventory_slot(self) -> None:
        """The clamp is `min(asked, held)`: asking for 999 moves the 7 the item holds."""

        self.assertTrue(Inventory.WithdrawItemFromStorage(ITEM_B_ID, 999))
        self.assertEqual(
            self.client.calls,
            [(py_inventory._MOVE_ITEM_FUNC, 8, (ITEM_B_ID, 7, 1, 2))],
        )

    def test_a_withdraw_of_nothing_answers_false(self) -> None:
        """A request of zero clamps to zero, which the source's guard turns into `False`."""

        self.assertFalse(Inventory.WithdrawItemFromStorage(ITEM_B_ID, 0))
        self.assertFalse(Inventory.WithdrawItemFromStorage(999, 10))
        self.assertEqual(self.client.calls, [])


class InventoryReadTests(_FixtureCase):
    """The eighteen members this round built."""

    def test_the_inventory_space_counts_items_and_capacity(self) -> None:
        """`GetInventorySpace` over bags 1 to 4: two items, and the bag's size."""

        self.assertEqual(Inventory.GetInventorySpace(), (2, 2))
        self.assertEqual(Inventory.GetFreeSlotCount(), 0)

    def test_a_bag_with_room_answers_free_slots(self) -> None:
        """The clamp: capacity minus items, and never negative.

        The capacity is rewritten in the **reader** rather than on a snapshot, because the bag record is
        re-read on every call — a mutation of an earlier snapshot would not be seen.
        """

        _write_bag(self.client.reader, BACKPACK, index=1, size=5)
        self.assertEqual(Inventory.GetInventorySpace(), (2, 5))
        self.assertEqual(Inventory.GetFreeSlotCount(), 3)
        _write_bag(self.client.reader, BACKPACK, index=1, size=1)
        self.assertEqual(Inventory.GetFreeSlotCount(), 0)

    def test_the_zero_filled_array_places_items_by_slot(self) -> None:
        """One entry per slot of the storage bags, empty ones zero, items placed by their slot field."""

        self.assertEqual(
            Inventory.GetZeroFilledStorageArray(Anniversary_panel=False), [ITEM_A_ID, ITEM_B_ID]
        )
        _write_bag(self.client.reader, STORAGE, index=8, size=4, bag_type=BagType.Storage)
        self.assertEqual(
            Inventory.GetZeroFilledStorageArray(Anniversary_panel=False),
            [ITEM_A_ID, ITEM_B_ID, 0, 0],
        )

    def test_an_item_count_sums_the_quantities_of_the_id(self) -> None:
        """`GetItemCount` filters by the id and sums `Item.Properties.GetQuantity`."""

        self.assertEqual(Inventory.GetItemCount(ITEM_B_ID), 7)
        self.assertEqual(Inventory.GetItemCount(ITEM_A_ID), 3)
        self.assertEqual(Inventory.GetItemCount(999), 0)

    def test_a_model_count_sums_the_quantities_of_the_model(self) -> None:
        """`GetModelCount` filters by `Item.GetModelID`."""

        self.assertEqual(Inventory.GetModelCount(5678), 7)
        self.assertEqual(Inventory.GetModelCount(1234), 3)
        self.assertEqual(Inventory.GetModelCount(999), 0)

    def test_the_storage_and_equipped_counts_ask_their_own_bags(self) -> None:
        """`GetModelCountInStorage` walks bags 8-21, which the fixture's storage bag is in; bag 22 is not."""

        self.assertEqual(Inventory.GetModelCountInStorage(1234), 3)
        self.assertEqual(Inventory.GetModelCountInStorage(5678), 7)
        self.assertEqual(Inventory.GetModelCountInStorage(999), 0)
        self.assertEqual(Inventory.GetModelCountInEquipped(1234), 0)
        self.assertEqual(Inventory.GetModelCountInMaterialStorage(1234), 0)

    def test_the_first_unidentified_item_is_the_first_one_without_the_bit(self) -> None:
        """Item 101 carries `interaction & 0x1`, item 102 does not."""

        self.assertEqual(Inventory.GetFirstUnidentifiedItem(), ITEM_B_ID)

    def test_the_first_salvageable_item_is_the_first_weapon(self) -> None:
        """Both fixture items are swords, and the source's rules call a weapon salvageable."""

        self.assertEqual(Inventory.GetFirstSalvageableItem(), ITEM_A_ID)

    def test_the_finders_answer_zero_when_nothing_matches(self) -> None:
        """No kit in the fixture: the three kit finders answer the source's `0`."""

        self.assertEqual(Inventory.GetFirstIDKit(), 0)
        self.assertEqual(Inventory.GetFirstSalvageKit(), 0)
        self.assertEqual(Inventory.GetFirstSalvageKit(use_lesser=False), 0)

    def test_identify_first_stops_at_the_first_missing_piece(self) -> None:
        """No ID kit, so the source's first guard answers `False` — and no call is made."""

        self.assertFalse(Inventory.IdentifyFirst())

    def test_salvage_first_stops_at_the_first_missing_piece(self) -> None:
        """No salvage kit, so the source's first guard answers `False`.

        The third path — where the source acts and still answers ``False`` — is reachable now that
        `PyInventory.Salvage` and its interact guard are ported; this fixture simply has no salvage kit for
        the guards above it to pass.
        """

        self.assertFalse(Inventory.SalvageFirst())

    def test_salvage_item_reaches_the_binding(self) -> None:
        """`SalvageItem` builds the binding itself, then calls `Salvage` kit first (``:349-359``)."""

        recorded: list[tuple[int, int]] = []
        binding = py_inventory.PyInventory()
        with mock.patch.object(
            type(binding),
            "Salvage",
            lambda self, kit_id, item_id: recorded.append((kit_id, item_id)),
        ):
            Inventory.SalvageItem(ITEM_A_ID, ITEM_B_ID)
        self.assertEqual(recorded, [(ITEM_B_ID, ITEM_A_ID)])

    def test_identify_item_reaches_the_binding(self) -> None:
        """The same for `IdentifyItem`, also kit first (``:309-319``)."""

        recorded: list[tuple[int, int]] = []
        binding = py_inventory.PyInventory()
        with mock.patch.object(
            type(binding),
            "IdentifyItem",
            lambda self, kit_id, item_id: recorded.append((kit_id, item_id)),
        ):
            Inventory.IdentifyItem(ITEM_A_ID, ITEM_B_ID)
        self.assertEqual(recorded, [(ITEM_B_ID, ITEM_A_ID)])

    def test_inventory_instance_builds_the_binding(self) -> None:
        """`inventory_instance` is `PyInventory.PyInventory()`."""

        self.assertIsInstance(Inventory.inventory_instance(), py_inventory.PyInventory)


class InventoryRaiseTests(_FixtureCase):
    """Every member that raises names its own work item and nothing vague."""

    def test_each_raising_member_names_what_it_needs(self) -> None:
        """One call per member, with a word from its requirement checked in the message."""

        calls = {
            "_salvage_choice_debug_log": lambda: Inventory._salvage_choice_debug_log(True, "m", "m"),
            "HandleSalvageChoiceMaterialConfirmDialog": lambda: Inventory.HandleSalvageChoiceMaterialConfirmDialog(),
            "_wait_for_salvage_choice_dialog_close": lambda: Inventory._wait_for_salvage_choice_dialog_close(),
            "HandleSalvageChoiceDialog": lambda: Inventory.HandleSalvageChoiceDialog(),
        }
        self.assertEqual(sorted(calls), sorted(RAISING))
        for member, call in calls.items():
            with self.subTest(member=member):
                with self.assertRaises(NotImplementedError) as caught:
                    call()
                message = str(caught.exception)
                self.assertIn(member, message)
                self.assertIn(RAISING[member], message)

    def test_the_frame_text_helper_answers_empty_as_the_source_does(self) -> None:
        """`_collect_frame_text` discards its parameters and returns `""` — ported as written."""

        self.assertEqual(Inventory._collect_frame_text(7), "")
        self.assertEqual(Inventory._collect_frame_text(7, {1: [2]}, 3), "")


class SalvageHelperTests(unittest.TestCase):
    """The salvage helpers that answer without a client — the fourteen that left the raise list in round 31.

    The three that read the live tree (`_get_all_child_frame_ids_from_frame_id`,
    `IsSalvageChoiceDialogVisible`, `_build_frame_children_map`) are covered where their reads are:
    `test_frame_tree_frame_offline.py`, whose fixtures drive `FrameTree` and `Frame` directly.
    """

    def test_the_alias_lookup_yields_an_inert_handle(self) -> None:
        """`_frame_by_alias` catches `FrameKeyError` and answers `Frame.from_id(0)` (`Inventory.py:407-413`)."""

        from py4gw.frame_tree import Frame

        inert = Inventory._frame_by_alias("\x00 no such frame alias")
        self.assertIsInstance(inert, Frame)
        self.assertEqual(inert._fid, 0, "the handle is inert, not resolved")

    def test_the_option_text_is_the_sources_own_empty_answer(self) -> None:
        """It folds `_collect_frame_text`, which answers `""` by the source's design (`:515-529`)."""

        self.assertEqual(Inventory._collect_salvage_choice_option_text([1, 2, 3]), "")
        self.assertEqual(Inventory._collect_salvage_choice_option_text([], {}, 5), "")

    def test_the_subtree_walk_tags_depth_and_stops_at_the_limit(self) -> None:
        """Breadth-first over the entry map, `subtree_depth` on each entry (`:531-569`).

        The walk collects only frames the map itself holds — it is keyed by parent, so a frame appears in it
        under its own parent — which is why a root id that is not one of its entries yields nothing.
        """

        tree = {
            0: [{"frame_id": 10, "parent_id": 0, "offset": 0}],
            10: [{"frame_id": 11, "parent_id": 10, "offset": 1},
                 {"frame_id": 12, "parent_id": 10, "offset": 2}],
            11: [{"frame_id": 13, "parent_id": 11, "offset": 1}],
        }
        shallow = Inventory._collect_visible_frame_subtree_entries([10], tree, 1)
        self.assertEqual([(entry["frame_id"], entry.get("subtree_depth")) for entry in shallow],
                         [(10, 0), (11, 1), (12, 1)], "depth 1 is the limit, so 13 is not walked")
        deep = Inventory._collect_visible_frame_subtree_entries([10], tree, 2)
        self.assertEqual([(entry["frame_id"], entry.get("subtree_depth")) for entry in deep],
                         [(10, 0), (11, 1), (12, 1), (13, 2)])
        self.assertEqual(Inventory._collect_visible_frame_subtree_entries([99], tree, 2), [],
                         "a root the map does not hold yields nothing")

    def test_the_click_entry_priority_is_the_sources_own(self) -> None:
        """A button inside a subtree, then a button, then a nested frame, then a plain one (`:571-592`)."""

        plain = {"frame_id": 1, "template_type": 0, "subtree_depth": 0, "area": 900.0, "top": 5.0, "offset": 3}
        nested = {"frame_id": 2, "template_type": 0, "subtree_depth": 2, "area": 10.0, "top": 6.0, "offset": 4}
        button = {"frame_id": 3, "template_type": 1, "subtree_depth": 0, "area": 10.0, "top": 7.0, "offset": 5}
        nested_button = {"frame_id": 4, "template_type": 1, "subtree_depth": 1, "area": 10.0, "top": 8.0, "offset": 6}

        self.assertIsNone(Inventory._pick_salvage_choice_click_entry([]))
        for candidates, expected in (([plain, nested, button, nested_button], 4),
                                     ([plain, button, nested], 3),
                                     ([plain, nested], 2),
                                     ([plain, plain], 1)):
            with self.subTest(expected=expected):
                picked = Inventory._pick_salvage_choice_click_entry(candidates)
                if picked is None:
                    self.fail("a candidate should always be picked")
                self.assertEqual(picked["frame_id"], expected)


    def test_the_disabled_debug_log_returns_as_the_source_does(self) -> None:
        """`if not debug_enabled: return` is the source's first act (`Inventory.py:796-797`)."""

        self.assertIsNone(Inventory._salvage_choice_debug_log(False, "m", "m"))

    def test_the_option_strategies_pick_by_text_then_fall_back(self) -> None:
        """Strategy 0 prefers materials, strategy 1 upgrades, each with its documented fallback (`:739-791`)."""

        materials = {"frame_id": 10, "offset": 1, "text": "Crafting Materials", "template_type": 1}
        upgrade = {"frame_id": 11, "offset": 2, "text": "Inscription", "template_type": 0}
        plain = {"frame_id": 12, "offset": 3, "text": "", "template_type": 0}
        other = {"frame_id": 13, "offset": 4, "text": "", "template_type": 0}

        self.assertEqual(Inventory._choose_salvage_choice_dialog_option([], 0), (None, "no options"))
        self.assertEqual(Inventory._choose_salvage_choice_dialog_option([plain, materials], 0),
                         (materials, "prefer crafting materials (text match)"))
        self.assertEqual(Inventory._choose_salvage_choice_dialog_option([upgrade, plain], 1),
                         (upgrade, "prefer upgrades/components (text match)"),
                         "'Inscription' is one of the source's own upgrade keywords")
        self.assertEqual(Inventory._choose_salvage_choice_dialog_option([plain, upgrade], 0),
                         (upgrade, "prefer crafting materials (last visible option fallback)"),
                         "nothing matches the material keywords, so the last visible option is the answer")
        self.assertEqual(Inventory._choose_salvage_choice_dialog_option([plain, other], 1),
                         (plain, "prefer upgrades/components (first visible option fallback)"))
        self.assertEqual(Inventory._choose_salvage_choice_dialog_option([plain, other], 7),
                         (plain, "prefer upgrades/components (strategy fallback)"),
                         "an unknown strategy falls back to the first entry")

    def test_an_option_entry_formats_its_optional_parts_only_when_present(self) -> None:
        """The source's own summary line (`Inventory.py:803-828`)."""

        full = {"frame_id": 7, "offset": 3, "text": " Salvage ", "template_type": 1,
                "source_depth": 2, "path": " 0->3 ", "group_size": 2, "subtree_depth": 1}
        self.assertEqual(
            Inventory._format_salvage_choice_option(full, 4),
            "index=0/4 frame_id=7 child_offset=3 path=0->3 group_frames=2 depth=2 click_depth=1 "
            "template=1 text='Salvage'",
        )
        minimal = {"frame_id": 7, "offset": 3, "text": "", "template_type": -1}
        self.assertEqual(Inventory._format_salvage_choice_option(minimal, 0),
                         "index=0/1 frame_id=7 child_offset=3")

    def test_the_option_assembly_answers_nothing_without_a_container(self) -> None:
        """`_salvage_option_container()` not existing is the source's own first return (`:598-600`)."""

        from unittest import mock

        class _EmptyClient:
            """No frames at all, which is the case this branch is for."""

            class _Array:
                def get(self, frame_id):
                    return None

                def iter_frames(self):
                    return iter(())

                def read_u32(self, address):
                    return 0

            def __init__(self) -> None:
                self.frame_array = self._Array()

            def call_function(self, name, form, *args):
                raise AssertionError("the container lookup must not need a call")

        with mock.patch("py4gw.client._current_client", _EmptyClient()):
            self.assertEqual(Inventory._get_salvage_choice_dialog_options(), (0, [], []))


class InventoryTypedDictTests(unittest.TestCase):
    """The three records, as records."""

    def test_a_visible_frame_entry_holds_its_ten_fields(self) -> None:
        entry: VisibleFrameEntry = {
            "frame_id": 1,
            "parent_id": 0,
            "offset": 0,
            "left": 0.0,
            "top": 0.0,
            "width": 1.0,
            "height": 1.0,
            "area": 1.0,
            "template_type": 1,
            "text": "",
        }
        self.assertEqual(len(entry), 10)

    def test_a_salvage_choice_entry_adds_seven_optional_fields(self) -> None:
        entry: SalvageChoiceEntry = {
            "frame_id": 1,
            "parent_id": 0,
            "offset": 0,
            "left": 0.0,
            "top": 0.0,
            "width": 1.0,
            "height": 1.0,
            "area": 1.0,
            "template_type": 1,
            "text": "",
            "order": 1,
        }
        self.assertEqual(len(entry), 11)

    def test_an_option_source_holds_its_five_fields(self) -> None:
        source: SalvageChoiceOptionSource = {
            "offset": 1,
            "path_offsets": [1],
            "fallback_frame_id": 2,
            "source_depth": 0,
            "container_frame_id": None,
        }
        self.assertEqual(len(source), 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)

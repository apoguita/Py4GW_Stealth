"""Offline tests for the ported ``item_array`` module.

**What is pinned.** ``ItemArray.py``'s fourteen declarations — the four static methods and the three
nested namespaces — against the **source's own AST**, and then the behaviour: the id list a set of bags
produces, the ``None`` cases, the two condition namespaces, and the two adaptations this port records
(the dropped ``@frame_cache`` and the console log lines it has nowhere to send).

The bag fixture is the real ported machinery: ``BagStruct``/``ItemStruct`` records built from bytes behind
a reader, reached through the item-context reader's ``read()`` — the same construction the bag-surface
tests use, so this file exercises ``ItemArray`` over the same path a live client would take.
"""

from __future__ import annotations

import ast
import ctypes
import struct
import unittest
from pathlib import Path
from typing import Any, cast
from unittest import mock

from py4gw.native_src.item import py_inventory
from py4gw import item_array
from py4gw.context.gw_array import GWArray
from py4gw.context.item_context import BagStruct, InventoryStruct, ItemStruct
from py4gw.item import Bag, Item
from py4gw.item_array import ItemArray
from py4gw.map import Map

SOURCE_FILE = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\ItemArray.py")

#: The three members whose source decorator this port drops, and the decorator it drops.
FRAME_CACHED = {"GetItemArray", "GetAllBags", "GetBag"}
DROPPED_DECORATOR = "frame_cache(category='ItemArray', source_lib='GetItemArray')"

ITEM_TABLE = 0x00400000
ITEM_A = 0x00500000
ITEM_B = 0x00500054
BACKPACK = 0x00280000
EMPTY_BAG = 0x00290000
INVENTORY = 0x00100000

ITEM_A_ID = 101
ITEM_B_ID = 102
BACKPACK_ITEMS = 2


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


class _TradeLookup:
    """Stand in for the trade context, which `ItemStruct.IsOfferedInTrade` reads through."""

    def __init__(self, offered_ids: set[int]) -> None:
        self.offered_ids = offered_ids

    def is_item_offered(self, item_id: int) -> bool:
        return int(item_id) in self.offered_ids

    def read(self) -> _TradeLookup:
        return self


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


def _item_record(reader: _Reader, address: int, item_id: int, model_id: int, quantity: int) -> ItemStruct:
    buffer = bytearray(ctypes.sizeof(ItemStruct))
    struct.pack_into("<I", buffer, 0x00, item_id)
    struct.pack_into("<I", buffer, 0x2C, model_id)
    struct.pack_into("<H", buffer, 0x4C, quantity)
    reader.add(address, bytes(buffer))
    return ItemStruct.from_buffer_copy(bytes(buffer)).bind_reader(
        reader, address, cast(Any, _TradeLookup(set()))
    )


def _bag_record(reader: _Reader, address: int, index: int, table: int, size: int) -> BagStruct:
    bag = BagStruct()
    bag.bag_type = 1
    bag.index = index
    bag.items_count = size
    bag.items = GWArray(table, size, size, 0)
    bag.bind_reader(reader, address)
    reader.add(address, bytes(bag))
    return bag


class _FakeItemContextStruct:
    """The item context's own record: the item lookup and the inventory relationship."""

    def __init__(self, items: dict[int, ItemStruct], inventory: InventoryStruct) -> None:
        self._items = items
        self._inventory = inventory

    def GetItemById(self, item_id: int) -> ItemStruct | None:
        return self._items.get(int(item_id))

    def read_inventory(self) -> InventoryStruct:
        return self._inventory


class _FakeItemContext:
    """The reader: its record through `read()`."""

    def __init__(self, struct_: _FakeItemContextStruct, storage_open: bool = False) -> None:
        self._struct = struct_
        self.is_storage_open = storage_open

    def read(self) -> _FakeItemContextStruct:
        return self._struct


class _FakeClient:
    def __init__(self, context: _FakeItemContext) -> None:
        self.item_context = context


def _fixture() -> dict[str, Any]:
    """A backpack holding two items, an empty second bag, and an inventory pointing at both."""

    reader = _Reader()
    item_a = _item_record(reader, ITEM_A, ITEM_A_ID, 1234, 3)
    item_b = _item_record(reader, ITEM_B, ITEM_B_ID, 5678, 1)
    reader.add(ITEM_TABLE, struct.pack("<II", ITEM_A, ITEM_B))

    backpack = _bag_record(reader, BACKPACK, 1, ITEM_TABLE, BACKPACK_ITEMS)
    empty = _bag_record(reader, EMPTY_BAG, 3, ITEM_TABLE, 0)

    inventory = InventoryStruct()
    inventory.bags[1] = BACKPACK
    inventory.bags[3] = EMPTY_BAG
    inventory.bind_reader(reader, INVENTORY)
    reader.add(INVENTORY, bytes(inventory))

    context = _FakeItemContext(
        _FakeItemContextStruct({ITEM_A_ID: item_a, ITEM_B_ID: item_b}, inventory)
    )
    return {
        "reader": reader,
        "client": _FakeClient(context),
        "backpack": backpack,
        "empty": empty,
        "items": {ITEM_A_ID: item_a, ITEM_B_ID: item_b},
    }


class _FixtureCase(unittest.TestCase):
    """A test case with the client patched into every module that reaches for it."""

    def setUp(self) -> None:
        self.parts = _fixture()
        self.client = self.parts["client"]
        # Each module reaches the client through its own import of `require_client`: `py_inventory` for the
        # bags, `item` for the `PyItem` objects the bag hands out.
        from py4gw import item as item_module

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
class ItemArraySurfaceTests(unittest.TestCase):
    """The port declares the source's members, in the source's nesting."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _surface(ast.parse(SOURCE_FILE.read_text(encoding="utf-8")).body)
        cls.port = _surface(
            ast.parse(
                (Path(__file__).resolve().parents[1] / "py4gw" / "item_array.py").read_text(
                    encoding="utf-8"
                )
            ).body
        )

    def test_the_same_classes_and_members_are_declared(self) -> None:
        """Every class, nested namespace and member name, with nothing added or dropped."""

        def names(side: dict[str, Any], path: str = "") -> set[str]:
            found: set[str] = set()
            for name, value in side.items():
                found.add(f"{path}{name}")
                if isinstance(value, dict):
                    found |= names(value, f"{path}{name}.")
            return found

        theirs, ours = names(self.source), names(self.port)
        self.assertEqual(sorted(theirs - ours), [], "names the source has and the port does not")
        self.assertEqual(sorted(ours - theirs), [], "names the port has and the source does not")

    def test_the_decorators_match_except_the_dropped_frame_cache(self) -> None:
        """Three members carry `@frame_cache` in the source; here it is gone, and only there."""

        differences: list[str] = []
        for name, decorators in self.source["ItemArray"].items():
            if not isinstance(decorators, list):
                continue
            ours = self.port["ItemArray"][name]
            if decorators == ours:
                continue
            carries_frame_cache = (
                len(decorators) == 2
                and decorators[0] == "staticmethod"
                and decorators[1].startswith("frame_cache(")
            )
            if not (carries_frame_cache and name in FRAME_CACHED and ours == ["staticmethod"]):
                differences.append(f"{name}: source {decorators} port {ours}")
        self.assertEqual(differences, [], "unexpected decorator differences")
        for name in FRAME_CACHED:
            with self.subTest(member=name):
                self.assertEqual(self.port["ItemArray"][name], ["staticmethod"])

    def test_the_three_namespaces_hold_the_source_member_counts(self) -> None:
        """`Filter` 2, `Manipulation` 3, `Sort` 2 — counted from the source's own tree."""

        item_array_class = self.port["ItemArray"]
        self.assertEqual(len(item_array_class["Filter"]), 2, sorted(item_array_class["Filter"]))
        self.assertEqual(len(item_array_class["Manipulation"]), 3)
        self.assertEqual(len(item_array_class["Sort"]), 2)


class CreateBagListTests(unittest.TestCase):
    """`CreateBagList` over ids that are and are not bags."""

    def test_valid_ids_become_bag_members(self) -> None:
        """(1, 2, 3, 4, 7, 10) — the source's own docstring example."""

        self.assertEqual(
            ItemArray.CreateBagList(1, 2, 3, 4, 7, 10),
            [
                Bag.Backpack,
                Bag.Belt_Pouch,
                Bag.Bag_1,
                Bag.Bag_2,
                Bag.Unclaimed_Items,
                Bag.Storage_3,
            ],
        )

    def test_an_invalid_id_is_dropped_and_the_rest_survive(self) -> None:
        """The source's `except ValueError` logs and drops the id; the drop is what is ported."""

        self.assertEqual(ItemArray.CreateBagList(1, 99, 3), [Bag.Backpack, Bag.Bag_1])
        self.assertEqual(ItemArray.CreateBagList(99), [])

    def test_no_ids_give_an_empty_list(self) -> None:
        """The source's loop simply does not run."""

        self.assertEqual(ItemArray.CreateBagList(), [])


class GetItemArrayTests(_FixtureCase):
    """`GetItemArray` over the fixture's bags."""

    def test_the_ids_come_out_in_bag_then_slot_order(self) -> None:
        """Both bags asked for, in the order they were given."""

        ids = ItemArray.GetItemArray([Bag.Backpack, Bag.Bag_1])
        self.assertEqual(ids, [ITEM_A_ID, ITEM_B_ID])

    def test_an_empty_bag_contributes_nothing(self) -> None:
        """A bag record with no items."""

        self.assertEqual(ItemArray.GetItemArray([Bag.Bag_1]), [])
        self.assertEqual(ItemArray.GetItemArray([Bag.Bag_1, Bag.Backpack]), [ITEM_A_ID, ITEM_B_ID])

    def test_a_bag_that_cannot_be_read_is_skipped(self) -> None:
        """The source's own `except Exception` skips that bag and keeps the others."""

        self.assertEqual(ItemArray.GetItemArray([Bag.NoBag, Bag.Backpack]), [ITEM_A_ID, ITEM_B_ID])

    def test_an_int_is_not_a_bag_and_is_skipped(self) -> None:
        """`bag_enum.value` on an int raises, which the source's own try swallows."""

        self.assertEqual(ItemArray.GetItemArray([1]), [])  # type: ignore[list-item]

    def test_no_bags_give_an_empty_list(self) -> None:
        """The loop does not run."""

        self.assertEqual(ItemArray.GetItemArray([]), [])


class GetAllBagsAndGetBagTests(_FixtureCase):
    """`GetAllBags` and `GetBag`."""

    def test_get_all_bags_answers_the_bags_that_hold_something(self) -> None:
        """Every bag except `NoBag` is asked, and only the non-empty ones are kept."""

        self.assertEqual(ItemArray.GetAllBags(), [Bag.Backpack])

    def test_get_bag_answers_none_for_every_argument(self) -> None:
        """**A source finding**: neither an `int` nor a `Bag` member can make this member answer a bag.

        With an `int` the first line comes back empty (``GetItemArray`` reads ``.value`` off it and its own
        ``except`` swallows the error); with a `Bag` member that line works but ``PyInventory.Bag(bag,
        ...)`` cannot take an ``Enum``, and the source's own ``except Exception: return None`` answers
        ``None``. Both paths are the source's, and both are pinned here.
        """

        self.assertIsNone(ItemArray.GetBag(1))
        self.assertIsNone(ItemArray.GetBag(99))
        # Deliberate: a `Bag` member is what the source's docstring tells callers to pass, and the point
        # of this test is that it answers `None` too. The ignores are the annotation disagreeing.
        self.assertIsNone(ItemArray.GetBag(Bag.Backpack))  # type: ignore[arg-type]
        self.assertIsNone(ItemArray.GetBag(Bag.Bag_1))  # type: ignore[arg-type]

    def test_get_bag_refuses_an_enum_the_way_the_binding_does(self) -> None:
        """The reason the `Bag` path answers `None`: the binding's own `int` conversion."""

        with self.assertRaises(TypeError):
            py_inventory.Bag(Bag.Backpack, str(Bag.Backpack))  # type: ignore[arg-type]
        self.assertEqual(py_inventory.Bag(Bag.Backpack.value, Bag.Backpack.name).items_count, 2)


class ConditionNamespaceTests(unittest.TestCase):
    """`Filter` and `Sort`, which reach `Item` by name — and `Manipulation`, which does not.

    **One source quirk is pinned here.** The attribute name is looked up with plain `getattr(Item, name)`,
    which does not walk a dot: the source's own docstring example passes ``'Properties.GetValue'``, and
    that name is not an attribute of `Item`, so `ByAttribute` excludes every item while
    `SortByAttribute` raises its ``ValueError``. Both are the source's behaviour, kept as written and
    asserted below; the tests that exercise the mechanism use a flat member name, which is what works.
    """

    def test_by_attribute_filters_on_a_named_member(self) -> None:
        """`Filter.ByAttribute` calls `getattr(Item, attribute)` and keeps the items that pass."""

        values = {1: 10, 2: 0, 3: 30}
        with mock.patch.object(Item, "GetModelID", staticmethod(lambda item_id: values[item_id])):
            self.assertEqual(ItemArray.Filter.ByAttribute([1, 2, 3], "GetModelID"), [1, 3])
            self.assertEqual(
                ItemArray.Filter.ByAttribute(
                    [1, 2, 3], "GetModelID", condition_func=lambda value: value > 20
                ),
                [3],
            )
            self.assertEqual(
                ItemArray.Filter.ByAttribute([1, 2, 3], "GetModelID", negate=True), [2]
            )

    def test_by_attribute_with_an_unknown_name_excludes_or_includes_on_negate(self) -> None:
        """The source's own `hasattr` branch: exclude by default, include when negating."""

        self.assertEqual(ItemArray.Filter.ByAttribute([1, 2, 3], "NotAMember"), [])
        self.assertEqual(ItemArray.Filter.ByAttribute([1, 2, 3], "NotAMember", negate=True), [1, 2, 3])

    def test_the_dotted_name_the_source_documents_is_not_an_attribute(self) -> None:
        """The source's own example, `'Properties.GetValue'`, takes the `hasattr` branch it names."""

        self.assertFalse(hasattr(Item, "Properties.GetValue"))
        self.assertEqual(ItemArray.Filter.ByAttribute([1, 2, 3], "Properties.GetValue"), [])
        with self.assertRaises(ValueError) as caught:
            ItemArray.Sort.SortByAttribute([1, 2, 3], "Properties.GetValue")
        self.assertEqual(str(caught.exception), "Invalid attribute: Properties.GetValue")

    def test_by_condition_filters_with_the_callers_function(self) -> None:
        """`Filter.ByCondition` is `list(filter(filter_func, item_array))`."""

        self.assertEqual(
            ItemArray.Filter.ByCondition([1, 2, 3, 4], lambda item_id: item_id % 2 == 0), [2, 4]
        )

    def test_manipulation_is_the_three_set_operations(self) -> None:
        """`Merge`, `Subtract` and `Intersect` on the source's own arrays."""

        self.assertEqual(sorted(ItemArray.Manipulation.Merge([1, 2], [2, 3])), [1, 2, 3])
        self.assertEqual(ItemArray.Manipulation.Subtract([1, 2], [2, 3]), [1])
        self.assertEqual(ItemArray.Manipulation.Intersect([1, 2], [2, 3]), [2])

    def test_merge_deduplicates(self) -> None:
        """The source's own docstring warns the result is not in input order, and is unique."""

        self.assertEqual(sorted(ItemArray.Manipulation.Merge([3, 1], [1, 2])), [1, 2, 3])

    def test_sort_by_attribute_sorts_on_a_named_member(self) -> None:
        """`Sort.SortByAttribute` sorts by the value `getattr(Item, attribute)` answers."""

        values = {1: 30, 2: 10, 3: 20}
        with mock.patch.object(Item, "GetModelID", staticmethod(lambda item_id: values[item_id])):
            self.assertEqual(ItemArray.Sort.SortByAttribute([1, 2, 3], "GetModelID"), [2, 3, 1])
            self.assertEqual(
                ItemArray.Sort.SortByAttribute([1, 2, 3], "GetModelID", reverse=True), [1, 3, 2]
            )

    def test_sort_by_attribute_raises_for_an_unknown_name(self) -> None:
        """The source's own `ValueError(f"Invalid attribute: {attribute}")`."""

        with self.assertRaises(ValueError) as caught:
            ItemArray.Sort.SortByAttribute([1, 2], "NotAMember")
        self.assertEqual(str(caught.exception), "Invalid attribute: NotAMember")

    def test_sort_by_condition_sorts_on_the_callers_function(self) -> None:
        """`Sort.SortByCondition` is `sorted(item_array, key=condition_func, reverse=reverse)`."""

        self.assertEqual(
            ItemArray.Sort.SortByCondition([3, 1, 2], lambda item_id: item_id), [1, 2, 3]
        )
        self.assertEqual(
            ItemArray.Sort.SortByCondition([3, 1, 2], lambda item_id: item_id, reverse=True), [3, 2, 1]
        )


class AdaptationTests(unittest.TestCase):
    """The two recorded adaptations, so neither can regress silently."""

    def test_the_three_members_are_not_frame_cached(self) -> None:
        """No `frame_cache` wrapper survives on the members that carried it."""

        for name in FRAME_CACHED:
            with self.subTest(member=name):
                member = getattr(ItemArray, name)
                self.assertFalse(hasattr(member, "__wrapped__"))
                self.assertTrue(callable(member))

    def test_reading_twice_reads_twice(self) -> None:
        """With the memo gone, a second call goes to the client again — the observable difference."""

        parts = _fixture()
        client = parts["client"]
        calls: list[int] = []
        original = client.item_context.read().read_inventory

        def counting() -> Any:
            calls.append(1)
            return original()

        client.item_context.read().read_inventory = counting  # type: ignore[method-assign]
        with mock.patch.object(py_inventory, "require_client", lambda: client), mock.patch.object(
            Map, "IsMapReady", staticmethod(lambda: True)
        ):
            first = ItemArray.GetItemArray([Bag.Backpack])
            second = ItemArray.GetItemArray([Bag.Backpack])
        self.assertEqual(first, second)
        self.assertGreaterEqual(len(calls), 2, "the second call did not reach the client")


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Offline tests for the ported merchant surface.

Three things are pinned, all against the sources rather than against a transcription:

* **``Trading`` is the source's class, name for name, nesting for nesting, in order.** The source
  file is ``Merchant.py`` (197 lines) and the class inside it is ``Trading``; its four nested
  namespaces are what a caller reaches as ``Trading.Trader.GetOfferedItems()``, so a flat port with
  the same seventeen names would still be wrong.
* **``PyMerchant`` is native's binding class, method for method.** The list is read out of
  ``merchant_bindings.cpp``'s own ``.def("...", &PyMerchant::...`` lines, so a member added to or
  dropped from the binding shows up here.
* **Every member answers, and the words it builds are the source's own.** The eight writes are
  driven against a stand-in client that records what was written into the block and which function
  was called, so the record layout — nine words for ``TransactItems``, eight for ``RequestQuote``,
  and each field where ``ui.h``'s struct declares it — is checked by value rather than by reading
  the code. **Nothing in this file declares a member that refuses**: class is ported, so the raising
  set is empty and this suite says so.

The state behind the class (``PY4GW::listeners::Merchant()``) is ``py4gw/listeners.py`` and the
packet handlers under it are ``py4gw/game_thread/packets.py``; their own behaviour is pinned in
``tests/test_listeners_offline.py`` and ``tests/test_packets_offline.py``.
"""

from __future__ import annotations

import ast
import struct
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import py4gw.merchant as merchant_module
from py4gw.merchant import (
    COLLECTOR_BUY,
    CRAFTER_BUY,
    GIVE_IDS_OFFSET,
    GIVE_QUANTITIES_OFFSET,
    MAX_GIVE_ITEMS,
    MERCHANT_BUY,
    MERCHANT_SELL,
    RECEIVED_ID_OFFSET,
    REQUEST_QUOTE_FUNC,
    TRANSACT_ITEM_FUNC,
    TRANSACTION_RECORD_OFFSET,
    TRADER_BUY,
    TRADER_SELL,
    PyMerchant,
    Trading,
)

REFORGED_SOURCE = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\Merchant.py")
NATIVE_BINDING = Path(
    r"C:\Users\Apo\Py4GW_Reforged_Native\src\GW\merchant\merchant_bindings.cpp"
)

#: The members that need nothing from the client, and are therefore the ones native itself answers
#: without the listener: ``get_trader_item_list2`` is its own constant ``{}`` ("legacy never
#: populated", ``merchant_bindings.cpp:200``) and ``update`` is its own no-op ("legacy no-op", ``:205``).
SELF_CONTAINED: frozenset[str] = frozenset(
    {
        "Trading.merchant_instance",
        "Trading.Trader.GetOfferedItems2",
        "PyMerchant.get_trader_item_list2",
        "PyMerchant.update",
    }
)

#: The live item record's address the stand-in client answers with. Native builds ``&item->item_id``
#: out of it and the tests below expect exactly that address in the record.
ITEM_ADDRESS = 0x00A1B2C4

#: ``PyMerchant``'s members, in the binding's own order, read from the source by the test below.
NATIVE_BINDING_MEMBERS: tuple[str, ...] = (
    "trader_buy_item",
    "trader_sell_item",
    "trader_request_quote",
    "trader_request_sell_quote",
    "merchant_buy_item",
    "merchant_sell_item",
    "crafter_buy_item",
    "collector_buy_item",
    "get_trader_item_list",
    "get_trader_item_list2",
    "get_merchant_item_list",
    "get_quoted_value",
    "get_quoted_item_id",
    "is_transaction_complete",
    "update",
)

#: ``Trading``'s members and its four nested namespaces, in the source's order.
REFORGED_TRADING_MEMBERS: tuple[str, ...] = (
    "merchant_instance",
    "IsTransactionComplete",
)
REFORGED_NESTED: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Trader",
        (
            "GetQuotedItemID",
            "GetQuotedValue",
            "GetOfferedItems",
            "GetOfferedItems2",
            "RequestQuote",
            "RequestSellQuote",
            "BuyItem",
            "SellItem",
        ),
    ),
    ("Merchant", ("BuyItem", "SellItem", "GetOfferedItems")),
    ("Crafter", ("CraftItem", "GetOfferedItems")),
    ("Collector", ("ExchangeItem", "GetOfferedItems")),
)


class _Item:
    """One item record, with the address native's pointer is built from."""

    def __init__(self, address: int) -> None:
        self.address = address


class _ItemContext:
    """The stand-in for ``ItemContextStruct``: the one member the merchant writes call."""

    def __init__(self, items: dict[int, int]) -> None:
        self._items = items

    def GetItemById(self, item_id: int) -> _Item | None:
        address = self._items.get(int(item_id))
        return None if address is None else _Item(address)


class _Bridge:
    """The stand-in for the bridge: what was placed in the block, and where."""

    #: Where the data-region words start, so a "region offset" has an address to answer with.
    REGION_BASE = 0x70000000

    def __init__(self) -> None:
        self.writes: list[tuple[int, bytes]] = []

    def write_data(self, offset: int, payload: bytes) -> int:
        self.writes.append((int(offset), bytes(payload)))
        return self.REGION_BASE + int(offset)

    def words_at(self, offset: int) -> list[int]:
        """Return the words written at one region offset, or an empty list."""

        for written_offset, payload in self.writes:
            if written_offset == offset:
                return [
                    struct.unpack_from("<I", payload, index * 4)[0]
                    for index in range(len(payload) // 4)
                ]
        return []


class _Client:
    """The stand-in client the merchant members are driven against."""

    def __init__(self, items: dict[int, int] | None = None, resolves: bool = True) -> None:
        self.bridge = _Bridge()
        self.items = _ItemContext({0x10: ITEM_ADDRESS} if items is None else items)
        self.resolvable = resolves
        self.calls: list[tuple[str, int, int, int]] = []

    def read_item_context(self) -> _ItemContext:
        return self.items

    def resolves(self, name: str) -> bool:
        return self.resolvable

    def call_function(
        self,
        name: str,
        form: Any,
        arg1: int = 0,
        arg2: int = 0,
        arg3: int = 0,
        arg4: int = 0,
        arg5: int = 0,
    ) -> object:
        self.calls.append((name, int(arg1), int(arg2), int(form)))
        return None


class _MerchantTestCase(unittest.TestCase):
    """Drives the members against a stand-in client, which is the current one while they run."""

    def setUp(self) -> None:
        self.client = _Client()
        patcher = mock.patch("py4gw.client._current_client", self.client)
        patcher.start()
        self.addCleanup(patcher.stop)
        # The listener's state is the class's other half; these tests read and set it directly.
        from py4gw.listeners import Merchant

        self.listener = Merchant()

    def record(self) -> list[int]:
        """Return the transaction record the member built, as words."""

        return self.client.bridge.words_at(TRANSACTION_RECORD_OFFSET)

    def call(self) -> tuple[str, int, int, int]:
        """Return the one call the member made: name, words, count, form."""

        self.assertEqual(len(self.client.calls), 1, "one call per write")
        return self.client.calls[0]

    def ids_address(self) -> int:
        return self.client.bridge.REGION_BASE + GIVE_IDS_OFFSET

    def quantities_address(self) -> int:
        return self.client.bridge.REGION_BASE + GIVE_QUANTITIES_OFFSET

    def received_address(self) -> int:
        return self.client.bridge.REGION_BASE + RECEIVED_ID_OFFSET


def _source_trading() -> dict[str, list[str]]:
    """``Merchant.py``'s ``Trading`` tree: members and nested namespaces, in order."""

    tree = ast.parse(REFORGED_SOURCE.read_text(encoding="utf-8"))
    trading = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Trading"
    )
    out: dict[str, list[str]] = {"Trading": []}
    for child in trading.body:
        if isinstance(child, ast.ClassDef):
            out[child.name] = [
                m.name for m in child.body if isinstance(m, ast.FunctionDef)
            ]
        elif isinstance(child, ast.FunctionDef):
            out["Trading"].append(child.name)
    return out


def _source_binding_members() -> list[str]:
    """The binding's own ``.def`` lines, in order: what ``PyMerchant`` exposes."""

    text = NATIVE_BINDING.read_text(encoding="utf-8", errors="replace")
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('.def("') and "&PyMerchant::" in stripped:
            out.append(stripped.split('"')[1])
    return out


class SurfaceParityTests(unittest.TestCase):
    """The port is the source's class and the binding's class, name for name."""

    def test_trading_is_the_sources_class(self) -> None:
        if not REFORGED_SOURCE.is_file():
            self.skipTest(f"Reforged's Merchant.py is not at {REFORGED_SOURCE}")

        source = _source_trading()
        self.assertEqual(source["Trading"], list(REFORGED_TRADING_MEMBERS))
        for path, members in REFORGED_NESTED:
            with self.subTest(namespace=path):
                self.assertEqual(source[path], list(members))

    def test_every_source_member_exists_nested_as_declared(self) -> None:
        for member in REFORGED_TRADING_MEMBERS:
            with self.subTest(member=f"Trading.{member}"):
                self.assertTrue(hasattr(Trading, member), f"Trading.{member} is missing")
        for path, members in REFORGED_NESTED:
            owner = getattr(Trading, path)
            self.assertIsInstance(owner, type, f"Trading.{path} must be a nested class")
            for member in members:
                with self.subTest(member=f"Trading.{path}.{member}"):
                    self.assertTrue(
                        hasattr(owner, member), f"Trading.{path}.{member} is missing"
                    )

    def test_py_merchant_is_the_bindings_class(self) -> None:
        """Read from the binding's own ``.def`` lines, so drift on either side is caught."""

        if not NATIVE_BINDING.is_file():
            self.skipTest(f"Native's merchant_bindings.cpp is not at {NATIVE_BINDING}")

        self.assertEqual(_source_binding_members(), list(NATIVE_BINDING_MEMBERS))
        actual = [name for name in vars(PyMerchant) if not name.startswith("_")]
        self.assertEqual(actual, list(NATIVE_BINDING_MEMBERS))

    def test_no_public_member_beyond_the_sources(self) -> None:
        declared = set(REFORGED_TRADING_MEMBERS) | {path for path, _ in REFORGED_NESTED}
        actual = {name for name in vars(Trading) if not name.startswith("_")}
        self.assertEqual(actual - declared, set())

        for path, members in REFORGED_NESTED:
            with self.subTest(namespace=path):
                owner = getattr(Trading, path)
                self.assertEqual(
                    {n for n in vars(owner) if not n.startswith("_")} - set(members), set()
                )

    def test_every_declared_member_answers_and_none_refuses(self) -> None:
        """The class is ported: no member of the surface raises ``NotImplementedError``.

        Checked on the source of the module rather than by calling — several members need a client —
        so a member that goes back to raising shows up here whatever it is called with.
        """

        tree = ast.parse(
            Path(merchant_module.__file__).read_text(encoding="utf-8")
        )
        refusing: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for child in ast.walk(node):
                if (
                    isinstance(child, ast.Raise)
                    and isinstance(child.exc, ast.Call)
                    and isinstance(child.exc.func, ast.Name)
                    and child.exc.func.id == "_unported"
                ):
                    refusing.append(node.name)
        self.assertEqual(refusing, [])


class StateReadTests(_MerchantTestCase):
    """The five reads go to ``PY4GW::listeners::Merchant()``, as native's bodies do."""

    def test_the_quoted_state_is_the_listeners(self) -> None:
        self.listener.OnPriceReceived(0x1234, 250)

        self.assertEqual(PyMerchant().get_quoted_item_id(), 0x1234)
        self.assertEqual(PyMerchant().get_quoted_value(), 250)

    def test_the_transaction_flag_is_the_listeners(self) -> None:
        self.listener.ResetTransaction()
        self.assertFalse(PyMerchant().is_transaction_complete())

        self.listener.OnTransactionComplete()

        self.assertTrue(PyMerchant().is_transaction_complete())

    def test_the_two_item_lists_are_the_listeners_own_two(self) -> None:
        """Native's crossed names, kept: ``GetTraderItems`` reads ``merch_items_`` and
        ``GetMerchantItems`` reads ``merchant_window_items_`` (``merchant_bindings.cpp:199-201``)."""

        self.listener.OnNormalMerchantItemsReceived([7, 8, 9], 3)
        self.listener._merch_items.extend([1, 2])

        self.assertEqual(PyMerchant().get_trader_item_list(), [1, 2])
        self.assertEqual(PyMerchant().get_merchant_item_list(), [7, 8, 9])

    def test_the_facade_reaches_the_same_state(self) -> None:
        self.listener.OnPriceReceived(0x99, 42)

        self.assertEqual(Trading.Trader.GetQuotedItemID(), 0x99)
        self.assertEqual(Trading.Trader.GetQuotedValue(), 42)
        self.assertEqual(Trading.Trader.GetOfferedItems(), [])
        self.assertEqual(Trading.Merchant.GetOfferedItems(), [])
        self.assertEqual(Trading.Crafter.GetOfferedItems(), [])
        self.assertEqual(Trading.Collector.GetOfferedItems(), [])

    def test_the_two_members_that_need_nothing_answer_as_the_source_does(self) -> None:
        """``get_trader_item_list2`` is native's constant; ``update`` is its no-op."""

        self.assertEqual(PyMerchant().get_trader_item_list2(), [])
        self.assertIsNone(PyMerchant().update())
        self.assertEqual(Trading.Trader.GetOfferedItems2(), [])

    def test_merchant_instance_is_a_real_object_of_the_binding_class(self) -> None:
        """Native's ``PyMerchant`` has no state, so this is the object and not a stand-in."""

        instance = Trading.merchant_instance()
        self.assertIsInstance(instance, PyMerchant)
        self.assertIsNot(Trading.merchant_instance(), instance)


class WriteTests(_MerchantTestCase):
    """The eight writes, by the words they build and the function they call."""

    def test_trader_buy_item(self) -> None:
        """``merchant_bindings.cpp:27-46``: nothing given, one item received, ``cost * 1``."""

        self.assertTrue(PyMerchant().trader_buy_item(0x10, 500))

        name, offset, count, _form = self.call()
        self.assertEqual(name, TRANSACT_ITEM_FUNC)
        self.assertEqual(offset, TRANSACTION_RECORD_OFFSET)
        self.assertEqual(count, 9)
        self.assertEqual(
            self.record(), [TRADER_BUY, 500, 0, 0, 0, 0, 1, ITEM_ADDRESS, 0]
        )

    def test_trader_sell_item(self) -> None:
        """``:47-66``: the same shape the other way round, with the price as ``gold_recv``."""

        self.assertTrue(PyMerchant().trader_sell_item(0x10, 500))

        self.assertEqual(
            self.record(), [TRADER_SELL, 0, 1, ITEM_ADDRESS, 0, 500, 0, 0, 0]
        )

    def test_trader_request_quote(self) -> None:
        """``:67-84``: eight words, the **buy** type, and the id in ``recv``."""

        self.assertTrue(PyMerchant().trader_request_quote(0x10))

        name, offset, count, _form = self.call()
        self.assertEqual(name, REQUEST_QUOTE_FUNC)
        self.assertEqual(offset, TRANSACTION_RECORD_OFFSET)
        self.assertEqual(count, 8)
        self.assertEqual(self.record(), [TRADER_BUY, 0, 0, 0, 0, 0, 1, ITEM_ADDRESS])

    def test_trader_request_sell_quote(self) -> None:
        """``:85-102``: the same, with ``TraderSell`` and the id in ``give``."""

        self.assertTrue(PyMerchant().trader_request_sell_quote(0x10))

        self.assertEqual(self.record(), [TRADER_SELL, 0, 0, 1, ITEM_ADDRESS, 0, 0, 0])

    def test_merchant_buy_and_sell_are_the_trader_shapes_with_their_own_type(self) -> None:
        self.assertTrue(PyMerchant().merchant_buy_item(0x10, 500))
        self.assertEqual(
            self.record(), [MERCHANT_BUY, 500, 0, 0, 0, 0, 1, ITEM_ADDRESS, 0]
        )
        self.client.calls.clear()
        self.client.bridge.writes.clear()

        self.assertTrue(PyMerchant().merchant_sell_item(0x10, 500))

        self.assertEqual(
            self.record(), [MERCHANT_SELL, 0, 1, ITEM_ADDRESS, 0, 500, 0, 0, 0]
        )

    def test_crafter_buy_item_places_the_two_lists_and_the_received_id(self) -> None:
        """``:148-170``: the vectors' data, the function's own ``item_id`` address, and no guard."""

        self.assertTrue(PyMerchant().crafter_buy_item(0x20, 30, [1, 2], [3, 4]))

        self.assertEqual(
            self.record(),
            [
                CRAFTER_BUY,
                30,
                2,
                self.ids_address(),
                self.quantities_address(),
                0,
                1,
                self.received_address(),
                0,
            ],
        )
        self.assertEqual(self.client.bridge.words_at(GIVE_IDS_OFFSET), [1, 2])
        self.assertEqual(self.client.bridge.words_at(GIVE_QUANTITIES_OFFSET), [3, 4])
        self.assertEqual(self.client.bridge.words_at(RECEIVED_ID_OFFSET), [0x20])

    def test_collector_buy_item_is_the_crafter_shape_with_its_own_type(self) -> None:
        """``:173-196``: the same records; only the transaction type differs."""

        self.assertTrue(PyMerchant().collector_buy_item(0x21, 30, [5], [6]))

        self.assertEqual(
            self.record(),
            [
                COLLECTOR_BUY,
                30,
                1,
                self.ids_address(),
                self.quantities_address(),
                0,
                1,
                self.received_address(),
                0,
            ],
        )
        self.assertEqual(self.client.bridge.words_at(RECEIVED_ID_OFFSET), [0x21])

    def test_an_empty_ingredient_list_is_a_null_pointer_and_no_placement(self) -> None:
        """Native's own ``empty() ? nullptr : data()`` (``:156-157``)."""

        self.assertTrue(PyMerchant().crafter_buy_item(0x20, 30, [], []))

        self.assertEqual(self.record()[3], 0)
        self.assertEqual(self.record()[4], 0)
        self.assertEqual(self.client.bridge.words_at(GIVE_IDS_OFFSET), [])

    def test_two_lists_of_different_lengths_are_refused(self) -> None:
        """``:151-153`` and ``:176-178``: no call, no reset, no record."""

        self.assertFalse(PyMerchant().crafter_buy_item(0x20, 30, [1, 2], [3]))
        self.assertFalse(PyMerchant().collector_buy_item(0x20, 30, [], [1]))

        self.assertEqual(self.client.calls, [])
        self.assertEqual(self.client.bridge.writes, [])

    def test_more_ingredients_than_the_block_can_hold_is_refused(self) -> None:
        """Native's vector grows and the block cannot, so the port has a bound and names it."""

        too_many = list(range(MAX_GIVE_ITEMS + 1))

        with self.assertRaises(ValueError) as caught:
            PyMerchant().crafter_buy_item(0x20, 30, too_many, too_many)

        self.assertIn(str(MAX_GIVE_ITEMS), str(caught.exception))
        self.assertEqual(self.client.calls, [])

    def test_an_item_that_is_not_there_is_a_false_and_no_call(self) -> None:
        """``:30``: ``if (item)`` is the whole guard, and nothing else happens without it."""

        self.assertFalse(PyMerchant().trader_buy_item(0xDEAD, 500))
        self.assertFalse(PyMerchant().merchant_sell_item(0xDEAD, 500))
        self.assertFalse(PyMerchant().trader_request_quote(0xDEAD))

        self.assertEqual(self.client.calls, [])
        self.assertEqual(self.client.bridge.writes, [])

    def test_a_function_that_is_not_in_the_catalog_is_a_false(self) -> None:
        """``merchant_methods.cpp:17-21``: a null function pointer answers false, not an error."""

        self.client.resolvable = False

        self.assertFalse(PyMerchant().trader_buy_item(0x10, 500))
        self.assertFalse(PyMerchant().trader_request_quote(0x10))

        self.assertEqual(self.client.calls, [])

    def test_every_write_resets_the_flag_the_source_resets(self) -> None:
        """*"they must still fire here, at the same points, or the flags latch"* (``:22-24``)."""

        for call in (
            lambda: PyMerchant().trader_buy_item(0x10, 1),
            lambda: PyMerchant().trader_sell_item(0x10, 1),
            lambda: PyMerchant().merchant_buy_item(0x10, 1),
            lambda: PyMerchant().merchant_sell_item(0x10, 1),
            lambda: PyMerchant().crafter_buy_item(0x20, 1, [1], [1]),
            lambda: PyMerchant().collector_buy_item(0x20, 1, [1], [1]),
        ):
            with self.subTest(call=call):
                self.listener.OnTransactionComplete()
                self.assertTrue(self.listener.IsTransactionComplete())

                call()

                self.assertFalse(self.listener.IsTransactionComplete())
                self.client.calls.clear()
                self.client.bridge.writes.clear()

    def test_every_quote_resets_the_quote_the_source_resets(self) -> None:
        for call in (
            lambda: PyMerchant().trader_request_quote(0x10),
            lambda: PyMerchant().trader_request_sell_quote(0x10),
        ):
            with self.subTest(call=call):
                self.listener._quoted_value = 123

                call()

                self.assertEqual(self.listener.GetQuotedValue(), -1)
                self.client.calls.clear()
                self.client.bridge.writes.clear()

    def test_the_facade_returns_nothing_and_still_writes(self) -> None:
        """``Trading``'s own members are ``-> None`` in the source and discard the binding's answer."""

        self.assertIsNone(Trading.Trader.BuyItem(0x10, 500))
        self.assertIsNone(Trading.Trader.SellItem(0x10, 500))
        self.assertIsNone(Trading.Trader.RequestQuote(0x10))
        self.assertIsNone(Trading.Trader.RequestSellQuote(0x10))
        self.assertIsNone(Trading.Merchant.BuyItem(0x10, 500))
        self.assertIsNone(Trading.Merchant.SellItem(0x10, 500))
        self.assertIsNone(Trading.Crafter.CraftItem(0x20, 30, [1], [1]))
        self.assertIsNone(Trading.Collector.ExchangeItem(0x21, 30, [1], [1]))

        self.assertEqual(len(self.client.calls), 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)


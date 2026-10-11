"""Offline tests for the refusal-only action modules: trade, merchant, and the Ui_ mirror.

No client and no elevation. Every function in these modules refuses, so what is being established is
that the refusals are *actionable*: each cites its own body line, names the mechanism, and -- where the
port already holds the members a route would be built from -- names them, so the next person does not
have to rediscover them.
"""

from __future__ import annotations

import inspect
import unittest

from py4gw.gwa3 import cmd_merchant, cmd_trade


def _arguments(routine: object) -> tuple[object, ...]:
    """One argument per parameter without a default."""

    return tuple(
        1
        for parameter in inspect.signature(routine).parameters.values()  # type: ignore[arg-type]
        if parameter.default is inspect.Parameter.empty
    )


def _calls(module: object) -> tuple[tuple[str, tuple[object, ...]], ...]:
    return tuple(
        (name, _arguments(getattr(module, name))) for name in module.__all__  # type: ignore[attr-defined]
    )


class TradeRefusalTests(unittest.TestCase):
    """`GwAu3_Cmd_Trade.au3`: 18 functions across three mechanisms, all refused."""

    def test_every_function_refuses_with_a_citation(self) -> None:
        calls = _calls(cmd_trade)
        self.assertEqual(len(calls), 18)
        for name, args in calls:
            with self.subTest(function=name):
                with self.assertRaises(NotImplementedError) as raised:
                    getattr(cmd_trade, name)(*args)
                message = str(raised.exception)
                self.assertIn("GwAu3_Cmd_Trade.au3:", message)
                self.assertIn("py4gw", message)

    def test_the_three_mechanisms_are_told_apart(self) -> None:
        """A packet spelling, a session spelling and GwAu3's own slot are not the same refusal."""

        with self.assertRaises(NotImplementedError) as packet:
            cmd_trade.Trade_AcceptTrade_()
        self.assertIn("forges no", str(packet.exception))

        with self.assertRaises(NotImplementedError) as session:
            cmd_trade.Trade_AcceptTrade()
        self.assertIn("command queue", str(session.exception))

        with self.assertRaises(NotImplementedError) as slot:
            cmd_trade.Trade_GetTradePartner()
        self.assertIn("controller-side state", str(slot.exception))

    def test_the_argument_kind_difference_is_recorded(self) -> None:
        """`Trade_OfferItem_` takes an id where `Trade_OfferItem` takes an item."""

        with self.assertRaises(NotImplementedError) as raised:
            cmd_trade.Trade_OfferItem_(1, 1)
        self.assertIn("takes an id where its plain twin takes an item", str(raised.exception))


class MerchantRefusalTests(unittest.TestCase):
    """`GwAu3_Cmd_Merchant.au3`: 2 routed, 5 refused, and each refusal names the ported members."""

    def test_the_reads_are_routed(self) -> None:
        from unittest import mock

        with mock.patch.object(
            cmd_merchant.Trading.Merchant, "GetOfferedItems", return_value=[11, 0, 33]
        ):
            self.assertEqual(cmd_merchant.Merchant_GetMerchantItemsSize(), 3)
            # Mode 1 is the one-based slot -- and a **zero entry is skipped before the slot test**,
            # because that is where GwAu3's own `ContinueLoop` sits (`GwAu3_Cmd_Merchant.au3:26-28`).
            # So slot 2 answers 0 here even though it is inside the list: GwAu3 never looks at it.
            self.assertEqual(cmd_merchant.Merchant_GetMerchantItemPtr(2, 1), 0)
            self.assertEqual(cmd_merchant.Merchant_GetMerchantItemPtr(3, 1), 33)
            self.assertEqual(cmd_merchant.Merchant_GetMerchantItemPtr(1, 1), 11)

        with mock.patch.object(
            cmd_merchant.Trading.Merchant, "GetOfferedItems", return_value=[11, 22]
        ), mock.patch.object(cmd_merchant.Item, "GetModelID", side_effect=lambda i: 900 + i):
            self.assertEqual(cmd_merchant.Merchant_GetMerchantItemPtr(922, 0), 22)
            self.assertEqual(cmd_merchant.Merchant_GetMerchantItemPtr(999, 0), 0)
            # An unknown mode answers 0, which is GwAu3's own Case Else.
            self.assertEqual(cmd_merchant.Merchant_GetMerchantItemPtr(11, 7), 0)

    def test_the_five_refusals_name_the_ported_members(self) -> None:
        calls = {
            "Merchant_GetMerchantItemsBase": (),
            "Merchant_BuyItem": (1,),
            "Merchant_SellItem": (1,),
            "Merchant_CraftItem": (1, 2, 3),
            "Merchant_CollectorExchange": (1, 2, 3),
        }
        for name, args in calls.items():
            with self.subTest(function=name):
                with self.assertRaises(NotImplementedError) as raised:
                    getattr(cmd_merchant, name)(*args)
                message = str(raised.exception)
                self.assertIn("GwAu3_Cmd_Merchant.au3", message)
                self.assertIn("py4gw/merchant.py", message)

    def test_the_declared_surface_is_the_sources_own(self) -> None:
        self.assertEqual(len(cmd_merchant.__all__), 7)


if __name__ == "__main__":
    unittest.main()

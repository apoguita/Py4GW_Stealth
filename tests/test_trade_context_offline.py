"""Offline layout checks for the external TradeContext reader."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import TradeContextStruct, TradeItemStruct, TradePlayerStruct


class TradeContextOfflineTests(unittest.TestCase):
    """Keep the trade records fixed-width and flag properties local."""

    def test_native_layout_sizes(self) -> None:
        """The records match the native x86 definitions."""

        self.assertEqual(ctypes.sizeof(TradeItemStruct), 0x08)
        self.assertEqual(ctypes.sizeof(TradePlayerStruct), 0x14)
        self.assertEqual(ctypes.sizeof(TradeContextStruct), 0x38)

    def test_trade_flags(self) -> None:
        """Trade state flags decode without remote reads."""

        context = TradeContextStruct()
        context.flags = 0x7
        self.assertTrue(context.is_trade_initiated)
        self.assertTrue(context.is_trade_offered)
        self.assertTrue(context.is_trade_accepted)


if __name__ == "__main__":
    unittest.main(verbosity=2)

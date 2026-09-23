"""Offline layout checks for the external TradeContext reader."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import GWArray, TradeContextStruct, TradeItemStruct, TradePlayerStruct


class BufferReader:
    """Return one known block for a bounded context-array test."""

    def __init__(self, address: int, value: bytes) -> None:
        self.address = address
        self.value = value
        self.reads: list[tuple[int, int]] = []

    def read(self, address: int, size: int) -> bytes:
        self.reads.append((address, size))
        if address != self.address:
            raise AssertionError(f"Unexpected read address: 0x{address:08X}")
        return self.value[:size]


class TradeContextOfflineTests(unittest.TestCase):
    """Keep the trade records fixed-width and flag properties local."""

    def test_native_layout_sizes(self) -> None:
        """The records match the native x86 definitions."""

        self.assertEqual(ctypes.sizeof(TradeItemStruct), 0x08)
        self.assertEqual(ctypes.sizeof(TradePlayerStruct), 0x14)
        self.assertEqual(ctypes.sizeof(TradeContextStruct), 0x38)
        self.assertEqual(TradePlayerStruct.items.offset, 0x04)
        self.assertEqual(TradeContextStruct.player.offset, 0x10)
        self.assertEqual(TradeContextStruct.partner.offset, 0x24)

    def test_native_field_names_and_order(self) -> None:
        """The Python records preserve the native C++ structure fields."""

        self.assertEqual(
            [field[0] for field in TradeItemStruct._fields_],
            ["item_id", "quantity"],
        )
        self.assertEqual(
            [field[0] for field in TradePlayerStruct._fields_],
            ["gold", "items"],
        )
        self.assertEqual(
            [field[0] for field in TradeContextStruct._fields_],
            ["flags", "h0004", "player", "partner"],
        )

    def test_trade_flags(self) -> None:
        """Trade state flags decode without remote reads."""

        context = TradeContextStruct()
        self.assertEqual(TradeContextStruct.TRADE_CLOSED, 0)
        self.assertEqual(TradeContextStruct.TRADE_INITIATED, 1)
        self.assertEqual(TradeContextStruct.TRADE_OFFER_SEND, 2)
        self.assertEqual(TradeContextStruct.TRADE_ACCEPTED, 4)
        context.flags = (
            TradeContextStruct.TRADE_INITIATED
            | TradeContextStruct.TRADE_OFFER_SEND
            | TradeContextStruct.TRADE_ACCEPTED
        )
        self.assertTrue(context.is_trade_initiated)
        self.assertTrue(context.is_trade_offered)
        self.assertTrue(context.is_trade_accepted)
        self.assertTrue(context.GetIsTradeInitiated())
        self.assertTrue(context.GetIsTradeOffered())
        self.assertTrue(context.GetIsTradeAccepted())

    def test_offer_reads_every_advertised_item(self) -> None:
        """Offer traversal does not silently stop at the former 64-item cap."""

        items = [TradeItemStruct(i + 1, i + 10) for i in range(70)]
        raw = b"".join(bytes(item) for item in items)
        reader = BufferReader(0x20000, raw)
        player = TradePlayerStruct().bind_reader(reader)
        player.items = GWArray(0x20000, 70, 70, 0)

        observed = player.offered_items

        self.assertEqual(len(observed), 70)
        self.assertEqual(observed[-1].item_id, 70)
        self.assertEqual(reader.reads, [(0x20000, 70 * ctypes.sizeof(TradeItemStruct))])

    def test_offer_rejects_oversized_array_without_truncating(self) -> None:
        """An excessive advertised array errors rather than returning a prefix."""

        reader = BufferReader(0x20000, b"")
        player = TradePlayerStruct().bind_reader(reader)
        player.items = GWArray(0x20000, 0xFFFFFFFF, 0xFFFFFFFF, 0)

        with self.assertRaisesRegex(ValueError, "exceeds the per-array read limit"):
            _ = player.offered_items

        self.assertEqual(reader.reads, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

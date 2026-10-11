"""Offline tests for `Item_GetBagPtr` / `Item_GetBagInfo`.

No client and no elevation. The bag family is where GwAu3's offsets have to be read *through* this
project's own nested structures, so what is being established is the arithmetic and the case shapes:

* the three keys that land on the port's nested `GWArray` (``ItemArray``, ``FakeSlots``, ``Slots``)
  map to ``m_buffer``, ``m_capacity`` and ``m_size`` -- in that order, which the structure's own size
  and field offsets decide;
* the five ``Is*`` keys compare ``bag_type`` and answer a **boolean**, not the number they compare;
* ``EmptySlots`` is GwAu3's subtraction rather than a stored value.
"""

from __future__ import annotations

import ctypes
import unittest
from unittest import mock

from py4gw.context.item_context import BagStruct
from py4gw.gwa3 import data_item


def _bag(**values: int) -> BagStruct:
    """A bag record whose bytes hold the given values, materialized the way the port materializes one."""

    buffer = (ctypes.c_uint8 * ctypes.sizeof(BagStruct))()
    for name, value in values.items():
        offset = getattr(BagStruct, name).offset
        ctypes.memmove(ctypes.addressof(buffer) + offset, ctypes.byref(ctypes.c_uint32(value)), 4)
    return BagStruct.from_buffer_copy(bytes(buffer))


class BagOffsetTests(unittest.TestCase):
    """The three keys that read through the port's nested array."""

    def test_the_nested_array_offsets_are_what_say_so(self) -> None:
        """`items` is 16 bytes at +0x18, so +0x1C is its capacity and +0x20 its size."""

        # The declared type comes from `_fields_`: a class-level `CField` carries an offset but no type
        # (the same reason the generators read `_fields_` for nested types).
        array_type = dict((name, kind) for name, kind in BagStruct._fields_)["items"]
        self.assertEqual(BagStruct.items.offset, 0x18)
        self.assertEqual(BagStruct.items_count.offset, 0x10)
        self.assertEqual(array_type.m_buffer.offset, 0x00)
        self.assertEqual(array_type.m_capacity.offset, 0x04)
        self.assertEqual(array_type.m_size.offset, 0x08)
        self.assertEqual(ctypes.sizeof(BagStruct), 0x28)

    def test_item_array_fake_slots_and_slots_read_the_array(self) -> None:
        """The three keys must come back in the order the offsets put them."""

        raw = (ctypes.c_uint8 * ctypes.sizeof(BagStruct))()
        ctypes.memmove(
            ctypes.addressof(raw) + BagStruct.items.offset,
            ctypes.byref((ctypes.c_uint32 * 4)(0x1111, 0x2222, 0x3333, 0x4444)),
            16,
        )
        ctypes.memmove(
            ctypes.addressof(raw) + BagStruct.items_count.offset,
            ctypes.byref(ctypes.c_uint32(7)),
            4,
        )
        record = BagStruct.from_buffer_copy(bytes(raw))

        with mock.patch.object(data_item, "Item_GetBagPtr", return_value=record):
            self.assertEqual(data_item.Item_GetBagInfo(1, "ItemArray"), 0x1111)
            self.assertEqual(data_item.Item_GetBagInfo(1, "FakeSlots"), 0x2222)
            self.assertEqual(data_item.Item_GetBagInfo(1, "Slots"), 0x3333)
            self.assertEqual(data_item.Item_GetBagInfo(1, "EmptySlots"), 0x3333 - 7)


class BagCaseShapeTests(unittest.TestCase):
    """The `Switch`'s own shapes: a plain read, a comparison, and an arithmetic."""

    def test_the_named_fields_read_their_offsets(self) -> None:
        # `_unknown0` is not a keyword-safe name for the helper, so the record is built by hand.
        raw = (ctypes.c_uint8 * ctypes.sizeof(BagStruct))()
        for name, value in (
            ("bag_type", 1), ("index", 2), ("_unknown0", 0xB46), ("container_item", 5),
            ("items_count", 6), ("bag_array", 7),
        ):
            ctypes.memmove(
                ctypes.addressof(raw) + getattr(BagStruct, name).offset,
                ctypes.byref(ctypes.c_uint32(value)),
                4,
            )
        record = BagStruct.from_buffer_copy(bytes(raw))

        with mock.patch.object(data_item, "Item_GetBagPtr", return_value=record):
            self.assertEqual(data_item.Item_GetBagInfo(1, "BagType"), 1)
            self.assertEqual(data_item.Item_GetBagInfo(1, "Index"), 2)
            # GwAu3 calls +0x8 the bag's ID; the port declares that offset as `_unknown0`, and the
            # placeholder is what answers it.
            self.assertEqual(data_item.Item_GetBagInfo(1, "ID"), 0xB46)
            self.assertEqual(data_item.Item_GetBagInfo(1, "ContainerItem"), 5)
            self.assertEqual(data_item.Item_GetBagInfo(1, "ItemCount"), 6)
            self.assertEqual(data_item.Item_GetBagInfo(1, "Bag"), 7)

        del record

    def test_the_is_keys_answer_booleans(self) -> None:
        """GwAu3's five comparisons on `bag_type` (`GwAu3_Data_Item.au3:176-190`)."""

        cases = {
            "IsInventoryBag": 1,
            "IsEquipped": 2,
            "IsNotCollected": 3,
            "IsStorage": 4,
            "IsMaterialStorage": 5,
        }
        for key, value in cases.items():
            with self.subTest(key=key, value=value):
                with mock.patch.object(
                    data_item, "Item_GetBagPtr", return_value=_bag(bag_type=value)
                ):
                    self.assertIs(data_item.Item_GetBagInfo(1, key), True)
                with mock.patch.object(
                    data_item, "Item_GetBagPtr", return_value=_bag(bag_type=99)
                ):
                    self.assertIs(data_item.Item_GetBagInfo(1, key), False)

    def test_the_guards_answer_zero_first(self) -> None:
        with mock.patch.object(data_item, "Item_GetBagPtr") as resolver:
            self.assertEqual(data_item.Item_GetBagInfo(1, ""), 0)
            resolver.assert_not_called()

        with mock.patch.object(data_item, "Item_GetBagPtr", return_value=None):
            self.assertEqual(data_item.Item_GetBagInfo(99, "Slots"), 0)

        with mock.patch.object(data_item, "Item_GetBagPtr", return_value=_bag(bag_type=1)):
            self.assertEqual(data_item.Item_GetBagInfo(1, "NoSuchField"), 0)


class BagPointerTests(unittest.TestCase):
    """`Item_GetBagPtr`: the index convention and the record short-circuit."""

    def test_the_index_is_the_bag_number(self) -> None:
        """Bag `n` is the record at `n`, which is what GwAu3's `4 * n` stride addresses."""

        bags = [_bag(bag_type=0), _bag(bag_type=1), _bag(bag_type=1)]
        client = mock.MagicMock()
        client.read_item_bags.return_value = bags
        with mock.patch.object(data_item, "require_client", return_value=client):
            self.assertIs(data_item.Item_GetBagPtr(1), bags[1])
            self.assertIsNone(data_item.Item_GetBagPtr(3))
            self.assertIsNone(data_item.Item_GetBagPtr(-1))

    def test_a_record_comes_back_unchanged(self) -> None:
        record = _bag(bag_type=1)
        with mock.patch.object(data_item, "require_client") as reader:
            self.assertIs(data_item.Item_GetBagPtr(record), record)
            reader.assert_not_called()


if __name__ == "__main__":
    unittest.main()

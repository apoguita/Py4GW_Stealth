"""Offline tests for the item resolvers added to `py4gw/gwa3/data_item.py`.

No client and no elevation. These three functions are what every ``Item_*`` call in GwAu3 that takes a
``$a_v_Item`` goes through, so what is being established is that they resolve the same *thing* GwAu3
resolves and refuse nothing they should answer.

The inventory members are here too -- ``Item_GetInventoryPtr``, ``Item_GetInventoryInfo`` and
``Item_GetModStruct`` -- because they are declared in the same source file and are what
``Equipment/UtilityAI_WeaponSets.au3`` reads the four weapon sets through. The fakes below are an
inventory struct and a reader holding **real** ``ItemStruct`` bytes, so the record a pointer resolves
to is the structure the port actually parses.
"""

from __future__ import annotations

import unittest
from unittest import mock

from py4gw.context import ItemStruct
from py4gw.gwa3 import data_item


class _Record:
    """A stand-in for the materialized record the layer reads."""

    def __init__(self, item_id: int) -> None:
        self.item_id = item_id


class _Inventory:
    """The inventory struct's fields the ported members read, at GwAu3's own offsets."""

    def __init__(self, **slots: int) -> None:
        self.bundle = slots.get("bundle", 0)
        self.weapon_set0 = slots.get("weapon_set0", 0)
        self.offhand_set0 = slots.get("offhand_set0", 0)
        self.weapon_set1 = slots.get("weapon_set1", 0)
        self.offhand_set1 = slots.get("offhand_set1", 0)
        self.weapon_set2 = slots.get("weapon_set2", 0)
        self.offhand_set2 = slots.get("offhand_set2", 0)
        self.weapon_set3 = slots.get("weapon_set3", 0)
        self.offhand_set3 = slots.get("offhand_set3", 0)
        self.active_weapon_set = slots.get("active_weapon_set", 0)
        self.gold_character = slots.get("gold_character", 0)
        self.gold_storage = slots.get("gold_storage", 0)


class _Reader:
    """A reader that answers the bytes it was given for an address."""

    def __init__(self, addresses: dict[int, bytes]) -> None:
        self.addresses = addresses

    def read(self, address: int, size: int) -> bytes:
        return self.addresses[address][:size]


class _Client:
    def __init__(self, inventory: _Inventory | None, reader: _Reader) -> None:
        self._inventory = inventory
        self.reader = reader

    def read_inventory(self) -> _Inventory | None:
        return self._inventory


def _item_bytes(item_id: int, agent_id: int = 0, model_id: int = 0, item_type: int = 0) -> bytes:
    """The real structure's own bytes, so the parse under test is the port's."""

    record = ItemStruct()
    record.item_id = item_id
    record.agent_id = agent_id
    record.model_id = model_id
    record.type = item_type
    return bytes(record)


class ItemItemIDTests(unittest.TestCase):
    """`Item_ItemID`: the id, from an id or from a record."""

    def test_an_id_is_answered_as_given(self) -> None:
        self.assertEqual(data_item.Item_ItemID(4242), 4242)

    def test_a_record_answers_its_id(self) -> None:
        """GwAu3's DllStruct arm, which is this layer's equivalent of holding a record."""

        self.assertEqual(data_item.Item_ItemID(_Record(77)), 77)


class ItemGetItemPtrTests(unittest.TestCase):
    """`Item_GetItemPtr`: GwAu3 answers a pointer, this answers the record."""

    def test_a_zero_id_answers_none_without_reading(self) -> None:
        with mock.patch.object(data_item, "_record") as record:
            self.assertIsNone(data_item.Item_GetItemPtr(0))
            record.assert_not_called()

    def test_an_id_resolves_through_the_same_read_the_family_uses(self) -> None:
        expected = _Record(9)
        with mock.patch.object(data_item, "_record", return_value=expected) as record:
            self.assertIs(data_item.Item_GetItemPtr(9), expected)
            record.assert_called_once_with(9)

    def test_a_record_is_answered_unchanged(self) -> None:
        """GwAu3's own short-circuit: an argument that is already a pointer comes back unchanged."""

        record = _Record(5)
        with mock.patch.object(data_item, "_record") as read:
            self.assertIs(data_item.Item_GetItemPtr(record), record)
            read.assert_not_called()


class ItemGetItemInfoByPtrTests(unittest.TestCase):
    """`Item_GetItemInfoByPtr`: the same field table, reached through a record."""

    def test_an_empty_field_name_answers_zero_first(self) -> None:
        with mock.patch.object(data_item, "Item_GetItemInfoByItemID") as accessor:
            self.assertEqual(data_item.Item_GetItemInfoByPtr(_Record(1), ""), 0)
            accessor.assert_not_called()

    def test_no_record_answers_zero(self) -> None:
        self.assertEqual(data_item.Item_GetItemInfoByPtr(None, "ModelID"), 0)

    def test_a_field_is_answered_by_the_generated_table(self) -> None:
        with mock.patch.object(
            data_item, "Item_GetItemInfoByItemID", return_value=19140
        ) as accessor:
            self.assertEqual(data_item.Item_GetItemInfoByPtr(_Record(8), "ModelID"), 19140)
            accessor.assert_called_once_with(8, "ModelID")

    def test_the_whole_item_surface_is_exported(self) -> None:
        """The accessor **and** the readers GwAu3 declares in the same source file.

        `GwAu3_Data_Item.au3` declares thirty-one functions and this module carries twenty-one of them:
        the family accessor the generator builds a table for, ``Item_GetItemContextPtr`` (the item
        context, answered as the record rather than as its address), and the resolvers, bag walkers and
        inventory readers every ``Item_*`` call goes through. They live here rather than in a module of
        their own because a family is one source file.
        """

        self.assertEqual(
            sorted(data_item.__all__),
            [
                "Item_FindItemByAgentID",
                "Item_FindItemByModelID",
                "Item_GetBagInfo",
                "Item_GetBagItemArray",
                "Item_GetBagPtr",
                "Item_GetInventoryArray",
                "Item_GetInventoryIDByAgentID",
                "Item_GetInventoryInfo",
                "Item_GetInventoryPtr",
                "Item_GetItemArray",
                "Item_GetItemBySlot",
                "Item_GetItemContextPtr",
                "Item_GetItemInfoByItemID",
                "Item_GetItemInfoByPtr",
                "Item_GetItemInventoryID",
                "Item_GetItemIsCommonMaterial",
                "Item_GetItemPtr",
                "Item_GetMaxItems",
                "Item_GetModByIdentifier",
                "Item_GetModStruct",
                "Item_ItemID",
            ],
        )
        for name in data_item.__all__:
            self.assertTrue(callable(getattr(data_item, name)), name)


class ItemGetInventoryPtrTests(unittest.TestCase):
    def test_it_answers_the_materialized_inventory_record(self) -> None:
        inventory = _Inventory(gold_character=1234)

        class _Connection:
            def read_inventory(self) -> _Inventory:
                return inventory

        with mock.patch.object(data_item, "require_client", lambda: _Connection()):
            self.assertIs(data_item.Item_GetInventoryPtr(), inventory)


class ItemGetInventoryInfoTests(unittest.TestCase):
    """`Item_GetInventoryInfo`: GwAu3's case list, one entry at a time."""

    WEAPON = 0x1000
    OFFHAND = 0x2000

    def _client(self, **slots: int) -> _Client:
        return _Client(
            _Inventory(**slots),
            _Reader(
                {
                    self.WEAPON: _item_bytes(101, agent_id=7, model_id=5, item_type=2),
                    self.OFFHAND: _item_bytes(202, agent_id=8, model_id=6, item_type=24),
                }
            ),
        )

    def _patch(self, **slots: int) -> _Client:
        client = self._client(**slots)
        patcher = mock.patch.object(data_item, "require_client", lambda: client)
        patcher.start()
        self.addCleanup(patcher.stop)
        return client

    def test_an_empty_field_name_answers_zero_before_the_client_is_touched(self) -> None:
        with mock.patch.object(data_item, "require_client") as connect:
            self.assertEqual(data_item.Item_GetInventoryInfo(""), 0)
            connect.assert_not_called()

    def test_no_inventory_record_answers_zero_for_every_key(self) -> None:
        """``If $l_p_Ptr = 0 ... Then Return 0`` at ``GwAu3_Data_Item.au3:18``."""

        self._patch()
        with mock.patch.object(data_item, "require_client", lambda: _Client(None, _Reader({}))):
            self.assertEqual(data_item.Item_GetInventoryInfo("WeaponSet0WeaponPtr"), 0)

    def test_an_unknown_field_name_answers_zero(self) -> None:
        self._patch()
        self.assertEqual(data_item.Item_GetInventoryInfo("NotAKey"), 0)

    def test_a_bag_key_reaches_the_bag_accessor_with_the_sources_index(self) -> None:
        """``+0x04`` is the array's element one, ``+0x58`` -- equipped items -- element twenty-two."""

        self._patch()
        expected = {
            "Backpack": 1,
            "BackpackPtr": 1,
            "BeltPouch": 2,
            "Bag1Ptr": 3,
            "Bag2": 4,
            "EquipmentPack": 5,
            "MaterialStoragePtr": 6,
            "UnclaimedItems": 7,
            "Storage1": 8,
            "Storage14Ptr": 21,
            "EquippedItemsPtr": 22,
            "EquippedItems": 22,
        }
        with mock.patch.object(data_item, "Item_GetBagPtr") as bag:
            bag.side_effect = lambda index: f"bag{index}"
            for key, index in expected.items():
                with self.subTest(key=key):
                    self.assertEqual(data_item.Item_GetInventoryInfo(key), f"bag{index}")
            self.assertEqual(bag.call_count, len(expected))

    def test_a_weapon_pointer_key_answers_the_record_it_addresses(self) -> None:
        self._patch(weapon_set0=self.WEAPON, offhand_set0=self.OFFHAND)
        weapon = data_item.Item_GetInventoryInfo("WeaponSet0WeaponPtr")
        self.assertEqual(int(weapon.item_id), 101)
        offhand = data_item.Item_GetInventoryInfo("WeaponSet0OffhandPtr")
        self.assertEqual(int(offhand.item_id), 202)
        self.assertEqual(int(offhand.type), 24)

    def test_the_three_id_keys_read_through_the_pointer(self) -> None:
        self._patch(weapon_set3=self.WEAPON)
        self.assertEqual(data_item.Item_GetInventoryInfo("WeaponSet3WeaponItemID"), 101)
        self.assertEqual(data_item.Item_GetInventoryInfo("WeaponSet3WeaponAgentID"), 7)
        self.assertEqual(data_item.Item_GetInventoryInfo("WeaponSet3WeaponModelID"), 5)

    def test_the_bundle_keys_read_through_the_bundle_pointer(self) -> None:
        self._patch(bundle=self.OFFHAND)
        self.assertEqual(data_item.Item_GetInventoryInfo("BundleItemID"), 202)
        self.assertEqual(data_item.Item_GetInventoryInfo("BundleAgentID"), 8)
        self.assertEqual(data_item.Item_GetInventoryInfo("BundleModelID"), 6)

    def test_a_null_pointer_answers_none_for_the_record_and_zero_for_the_ids(self) -> None:
        """A zero pointer is this layer's ``None``; reading a field through it is GwAu3's zero."""

        self._patch(weapon_set0=0)
        self.assertIsNone(data_item.Item_GetInventoryInfo("WeaponSet0WeaponPtr"))
        self.assertEqual(data_item.Item_GetInventoryInfo("WeaponSet0WeaponItemID"), 0)
        self.assertEqual(data_item.Item_GetInventoryInfo("WeaponSet0WeaponModelID"), 0)

    def test_the_three_counters_answer_the_structs_own_fields(self) -> None:
        self._patch(active_weapon_set=2, gold_character=1500, gold_storage=99)
        self.assertEqual(data_item.Item_GetInventoryInfo("ActiveWeaponSet"), 2)
        self.assertEqual(data_item.Item_GetInventoryInfo("GoldCharacter"), 1500)
        self.assertEqual(data_item.Item_GetInventoryInfo("GoldStorage"), 99)

    def test_every_key_the_source_declares_is_answered_by_something(self) -> None:
        """All thirty-six weapon/bundle keys and the forty-four bag names are in the tables."""

        self.assertEqual(len(data_item._INVENTORY_ITEM_KEYS), 36)
        self.assertEqual(len(data_item._INVENTORY_BAGS), 44)


class ItemGetModStructTests(unittest.TestCase):
    """`Item_GetModStruct`: the mod array's bytes in the text form GwAu3 returns."""

    def test_the_bytes_are_answered_as_upper_case_hex_behind_the_sources_0x(self) -> None:
        record = _Record(9)
        with mock.patch.object(data_item, "Item_GetItemPtr", lambda item: record), mock.patch.object(
            data_item, "Item_GetItemInfoByPtr", lambda rec, field: 0x3000 if field == "ModStruct" else 2
        ), mock.patch.object(
            data_item,
            "require_client",
            lambda: _Client(None, _Reader({0x3000: bytes.fromhex("de0168240500d822")})),
        ):
            text = data_item.Item_GetModStruct(9)
        self.assertEqual(text, "0xDE0168240500D822")
        self.assertEqual(len(text), 18)

    def test_no_mod_pointer_answers_the_empty_string(self) -> None:
        """``If $l_p_ModStruct = 0 Then Return ""`` at ``GwAu3_Data_Item.au3:779``."""

        with mock.patch.object(data_item, "Item_GetItemPtr", lambda item: _Record(9)), mock.patch.object(
            data_item, "Item_GetItemInfoByPtr", lambda rec, field: 0
        ):
            self.assertEqual(data_item.Item_GetModStruct(9), "")

    def test_an_item_the_client_does_not_hold_answers_an_empty_string(self) -> None:
        with mock.patch.object(data_item, "Item_GetItemPtr", lambda item: None):
            self.assertEqual(data_item.Item_GetModStruct(9), "")


if __name__ == "__main__":
    unittest.main()

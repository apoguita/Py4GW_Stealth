"""Offline tests for `py4gw/gwa3/data_friend.py` -- the last read family.

No client and no elevation. What is being established is the one thing that makes this family different
from the other seven: **its offsets do not all agree with GwAu3's**, so the tests pin which keys are
routed, which refuse, and the arithmetic that decides it.
"""

from __future__ import annotations

import ctypes
import unittest
from unittest import mock

from py4gw.context.friend_list_context import FriendStruct
from py4gw.gwa3 import data_friend


def _friend(
    friend_type: int = 1,
    status: int = 1,
    alias: str = "",
    uuid: bytes = b"\x00" * 16,
) -> FriendStruct:
    """A friend record whose bytes hold the given values, materialized the port's way."""

    raw = (ctypes.c_uint8 * ctypes.sizeof(FriendStruct))()
    ctypes.memmove(
        ctypes.addressof(raw) + FriendStruct.type.offset, ctypes.byref(ctypes.c_uint32(friend_type)), 4
    )
    ctypes.memmove(
        ctypes.addressof(raw) + FriendStruct.status.offset,
        ctypes.byref(ctypes.c_uint32(status)),
        4,
    )
    ctypes.memmove(ctypes.addressof(raw) + FriendStruct.uuid.offset, uuid, len(uuid))
    encoded = [(ord(character)) for character in alias] + [0]
    ctypes.memmove(
        ctypes.addressof(raw) + FriendStruct.alias.offset,
        ctypes.byref((ctypes.c_uint16 * len(encoded))(*encoded)),
        len(encoded) * 2,
    )
    return FriendStruct.from_buffer_copy(bytes(raw))


class _Listing:
    """A stand-in for the ported friend list, with the five counts and a record lookup."""

    def __init__(self, records: list[FriendStruct], counts: tuple[int, int, int, int] = (1, 0, 0, 0)):
        self.records = records
        self.counts = counts
        self.status = 1

    def get_number_of_friends(self) -> int:
        return self.counts[0]

    def get_number_of_ignores(self) -> int:
        return self.counts[1]

    def get_number_of_partners(self) -> int:
        return self.counts[2]

    def get_number_of_traders(self) -> int:
        return self.counts[3]

    def get_my_status(self) -> int:
        return self.status

    def get_friend(self, index: int):
        if 0 <= index < len(self.records):
            return self.records[index]
        return None

    def find_friend(self, alias=None, character_name=None, friend_type=None):
        wanted = alias if alias is not None else character_name
        for record in self.records:
            if data_friend._decode(record.alias) == wanted:
                return record
        return None


class FriendFieldTests(unittest.TestCase):
    """The four keys whose offsets agree, and the keys computed from them."""

    def setUp(self) -> None:
        self.record = _friend(friend_type=1, status=2, alias="Koss")
        self.listing = _Listing([self.record])
        patches = [mock.patch.object(data_friend, "get", return_value=self.listing)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_the_agreeing_offsets_answer(self) -> None:
        self.assertEqual(data_friend.Friend_GetFriendInfo(1, "Type"), 1)
        self.assertEqual(data_friend.Friend_GetFriendInfo(1, "FriendType"), 1)
        self.assertEqual(data_friend.Friend_GetFriendInfo(1, "Status"), 2)
        self.assertEqual(data_friend.Friend_GetFriendInfo(1, "FriendStatus"), 2)
        self.assertEqual(data_friend.Friend_GetFriendInfo(1, "Name"), "Koss")
        self.assertEqual(data_friend.Friend_GetFriendInfo(1, "Alias"), "Koss")
        self.assertEqual(data_friend.Friend_GetFriendInfo(1, "UUID"), b"\x00" * 16)

    def test_the_computed_keys_use_gwau3s_own_tables(self) -> None:
        self.assertEqual(data_friend.Friend_GetFriendInfo(1, "TypeName"), "Friend")
        self.assertEqual(data_friend.Friend_GetFriendInfo(1, "StatusName"), "Do Not Disturb")
        self.assertIs(data_friend.Friend_GetFriendInfo(1, "IsFriend"), True)
        self.assertIs(data_friend.Friend_GetFriendInfo(1, "IsIgnored"), False)
        self.assertIs(data_friend.Friend_GetFriendInfo(1, "IsOnline"), False)
        self.assertIs(data_friend.Friend_GetFriendInfo(1, "IsOffline"), False)

        online = _friend(status=1)
        self.listing.records = [online]
        self.assertIs(data_friend.Friend_GetFriendInfo(1, "IsOnline"), True)
        ignored = _friend(friend_type=2)
        self.listing.records = [ignored]
        self.assertIs(data_friend.Friend_GetFriendInfo(1, "IsIgnored"), True)
        self.assertIs(data_friend.Friend_GetFriendInfo(1, "IsFriend"), False)

    def test_the_number_and_the_index_are_one_based(self) -> None:
        """GwAu3 indexes the record at `4 * number`, so number 1 is the first record.

        The fixture's counts have to agree with its records: GwAu3's own guard is
        ``If $l_i_FriendNumber > $l_i_TotalFriends Then Return 0``, and the total comes from the list
        header's four counts -- not from how many records a reader happens to hold.
        """

        self.listing.records = [_friend(alias="A"), _friend(alias="B"), _friend(alias="C")]
        self.listing.counts = (3, 0, 0, 0)
        self.assertEqual(data_friend.Friend_GetFriendInfo(2, "Number"), 2)
        self.assertEqual(data_friend.Friend_GetFriendInfo(2, "Index"), 2)
        self.assertEqual(data_friend.Friend_GetFriendInfo("B", "Number"), 2)

        # And a number past the header's total answers 0, even where a record exists.
        self.listing.counts = (1, 0, 0, 0)
        self.assertEqual(data_friend.Friend_GetFriendInfo(2, "Number"), 0)

    def test_a_name_resolves_through_the_alias(self) -> None:
        self.assertEqual(data_friend.Friend_GetFriendInfo("Koss", "Type"), 1)

    def test_the_guards_answer_zero_first(self) -> None:
        """GwAu3's own: an empty identifier or an empty field name, before anything is read."""

        self.assertEqual(data_friend.Friend_GetFriendInfo("", "Type"), 0)
        self.assertEqual(data_friend.Friend_GetFriendInfo(1, ""), 0)
        # A number outside 1..total answers 0, and so does a name that is not on the list.
        self.assertEqual(data_friend.Friend_GetFriendInfo(9, "Type"), 0)
        self.assertEqual(data_friend.Friend_GetFriendInfo("Nobody", "Type"), 0)
        # An unrecognised field name is GwAu3's EndSwitch fallthrough.
        self.assertEqual(data_friend.Friend_GetFriendInfo(1, "NoSuchField"), 0)


class FriendOffsetTests(unittest.TestCase):
    """The finding this family carries: three keys refuse because the structures disagree."""

    def test_the_arithmetic_that_makes_them_disagree(self) -> None:
        """A 20-character wide string is 40 bytes, so the port's alias spans into GwAu3's `FriendID`."""

        self.assertEqual(FriendStruct.alias.offset, 0x18)
        self.assertEqual(FriendStruct.charname.offset, 0x40)
        self.assertEqual(FriendStruct.friend_id.offset, 0x68)
        self.assertEqual(FriendStruct.zone_id.offset, 0x6C)
        self.assertEqual(ctypes.sizeof(FriendStruct), 112)

    def test_the_six_affected_keys_refuse(self) -> None:
        for key in (
            "ConnectedName",
            "CharName",
            "Playing",
            "FriendID",
            "MapID",
            "ZoneID",
        ):
            with self.subTest(key=key):
                with self.assertRaises(NotImplementedError) as raised:
                    data_friend.Friend_GetFriendInfo(1, key)
                message = str(raised.exception)
                self.assertIn("GwAu3_Data_Friend.au3", message)
                self.assertIn("py4gw/context/friend_list_context.py", message)

    def test_the_pointer_key_refuses_as_an_address(self) -> None:
        with self.assertRaises(NotImplementedError) as raised:
            data_friend.Friend_GetFriendInfo(1, "Ptr")
        self.assertIn("hands out no client addresses", str(raised.exception))

    def test_the_list_pointer_refuses_as_an_address(self) -> None:
        with self.assertRaises(NotImplementedError) as raised:
            data_friend.Friend_GetFriendListPtr()
        self.assertIn("no client addresses", str(raised.exception))


class FriendListInfoTests(unittest.TestCase):
    """The list's own five keys -- all routed, because every one of their offsets agrees."""

    def test_the_counts_come_from_the_ported_reader(self) -> None:
        listing = _Listing([], counts=(3, 1, 2, 4))
        listing.status = 2
        with mock.patch.object(data_friend, "get", return_value=listing):
            self.assertEqual(data_friend.Friend_GetFriendListInfo("NumberOfFriend"), 3)
            self.assertEqual(data_friend.Friend_GetFriendListInfo("NumberOfIgnore"), 1)
            self.assertEqual(data_friend.Friend_GetFriendListInfo("NumberOfPartner"), 2)
            self.assertEqual(data_friend.Friend_GetFriendListInfo("NumberOfTrade"), 4)
            self.assertEqual(data_friend.Friend_GetFriendListInfo("PlayerStatus"), 2)

    def test_the_guards_answer_zero(self) -> None:
        with mock.patch.object(data_friend, "get", return_value=None):
            self.assertEqual(data_friend.Friend_GetFriendListInfo("NumberOfFriend"), 0)
        with mock.patch.object(data_friend, "get", return_value=_Listing([])):
            self.assertEqual(data_friend.Friend_GetFriendListInfo(""), 0)
            self.assertEqual(data_friend.Friend_GetFriendListInfo("NoSuchField"), 0)

    def test_the_player_status_comes_from_the_ported_member(self) -> None:
        with mock.patch.object(data_friend.Player, "GetPlayerStatus", return_value=3) as status:
            self.assertEqual(data_friend.Friend_GetMyStatus(), 3)
            status.assert_called_once_with()


class FriendNameTableTests(unittest.TestCase):
    """The two tables, verbatim -- GwAu3's own spelling is what a script compares against."""

    def test_the_status_names(self) -> None:
        self.assertEqual(data_friend.Friend_GetFriendStatusName(0), "Offline")
        self.assertEqual(data_friend.Friend_GetFriendStatusName(1), "Online")
        self.assertEqual(data_friend.Friend_GetFriendStatusName(2), "Do Not Disturb")
        self.assertEqual(data_friend.Friend_GetFriendStatusName(3), "Away")
        self.assertEqual(data_friend.Friend_GetFriendStatusName(99), "Unknown")

    def test_the_type_names(self) -> None:
        self.assertEqual(data_friend.Friend_GetFriendTypeName(1), "Friend")
        self.assertEqual(data_friend.Friend_GetFriendTypeName(2), "Ignore")
        self.assertEqual(data_friend.Friend_GetFriendTypeName(3), "Player")
        self.assertEqual(data_friend.Friend_GetFriendTypeName(4), "Trade")
        self.assertEqual(data_friend.Friend_GetFriendTypeName(99), "Unknown")

    def test_the_composed_predicates(self) -> None:
        listing = _Listing([_friend(friend_type=1, alias="Koss")])
        with mock.patch.object(data_friend, "get", return_value=listing):
            self.assertTrue(data_friend.Friend_IsFriend("Koss"))
            self.assertFalse(data_friend.Friend_IsIgnored("Koss"))
            # A name on neither list answers False for both, which is GwAu3's own shape.
            self.assertFalse(data_friend.Friend_IsFriend("Nobody"))
            self.assertFalse(data_friend.Friend_IsIgnored("Nobody"))

    def test_the_declared_surface(self) -> None:
        """Eight functions, which is what `GwAu3_Data_Friend.au3` declares."""

        self.assertEqual(len(data_friend.__all__), 8)


if __name__ == "__main__":
    unittest.main()

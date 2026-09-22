"""Offline layout and decoding checks for the external FriendList reader."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import FriendListStruct, FriendStatus, FriendStruct, FriendType, GWArray


class _Memory:
    """Deterministic byte store for bounded friend-record reads."""

    def __init__(self) -> None:
        self._blocks: dict[int, bytes] = {}

    def add(self, address: int, value: bytes) -> None:
        self._blocks[address] = value

    def read(self, address: int, size: int) -> bytes:
        for start, value in self._blocks.items():
            if start <= address and address + size <= start + len(value):
                offset = address - start
                return value[offset : offset + size]
        raise OSError(f"unmapped read: 0x{address:08X}+{size}")


class FriendListOfflineTests(unittest.TestCase):
    """Check fixed-width records without opening a Guild Wars process."""

    def test_layout_matches_native_offsets(self) -> None:
        """The root and entry sizes match the native x86 layouts."""

        self.assertEqual(ctypes.sizeof(FriendStruct), 0x70)
        self.assertEqual(ctypes.sizeof(FriendListStruct), 0xA4)
        self.assertEqual(FriendStruct.alias.offset, 0x18)
        # The native comment labels this field +0x2C, but the declared
        # 20-wide-character alias occupies 0x28 bytes, placing it at 0x40.
        self.assertEqual(FriendStruct.character_name.offset, 0x40)
        self.assertEqual(FriendListStruct.number_of_friends.offset, 0x24)
        self.assertEqual(FriendListStruct.player_status.offset, 0xA0)

    def test_decodes_friend_properties(self) -> None:
        """Friend type, status, UTF-16 names, and UUID remain readable."""

        friend = FriendStruct()
        friend.friend_type = FriendType.friend
        friend.status = FriendStatus.online
        friend.uuid[:] = bytes(range(16))
        friend.alias[:] = [ord(value) for value in "Alias"] + [0] * 15
        friend.character_name[:] = [
            ord(value) for value in "Character"
        ] + [0] * 11

        self.assertEqual(friend.type, FriendType.friend)
        self.assertEqual(friend.friend_status, FriendStatus.online)
        self.assertEqual(friend.alias_str, "Alias")
        self.assertEqual(friend.character_name_str, "Character")
        self.assertEqual(friend.uuid_bytes, bytes(range(16)))

    def test_unknown_enum_values_are_safe(self) -> None:
        """Unknown future enum values do not make a snapshot unreadable."""

        friend = FriendStruct()
        friend.friend_type = 99
        friend.status = 99
        self.assertEqual(friend.type, FriendType.unknown)
        self.assertEqual(friend.friend_status, FriendStatus.unknown)

    def test_source_lookup_and_count_helpers(self) -> None:
        """Read-only lookups match the native friend-list helper behavior."""

        memory = _Memory()
        pointer_array_address = 0x00200000
        friend_address = 0x00300000
        friend = FriendStruct()
        friend.friend_type = FriendType.friend
        friend.status = FriendStatus.online
        friend.uuid[:] = bytes(range(16))
        friend.alias[:] = [ord(value) for value in "Alias"] + [0] * 15
        friend.character_name[:] = [ord(value) for value in "Character"] + [0] * 11
        memory.add(pointer_array_address, friend_address.to_bytes(4, "little"))
        memory.add(friend_address, bytes(friend))

        context = FriendListStruct().bind_reader(memory)
        context.friends_array = GWArray(pointer_array_address, 1, 1, 0)
        context.number_of_friends = 1
        context.player_status = FriendStatus.away

        indexed = context.get_friend(0)
        found = context.find_friend(alias="Alias")
        self.assertIsNotNone(indexed)
        self.assertIsNotNone(found)
        assert indexed is not None
        assert found is not None
        self.assertEqual(indexed.alias_str, "Alias")
        self.assertEqual(found.friend_id, 0)
        self.assertIsNotNone(context.get_friend_by_uuid(bytes(range(16))))
        self.assertEqual(context.get_number_of_friends(), 1)
        self.assertEqual(context.get_my_status(), FriendStatus.away)


if __name__ == "__main__":
    unittest.main(verbosity=2)

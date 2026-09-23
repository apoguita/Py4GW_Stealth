"""Live Guild Wars tests for the external FriendList reader."""

from __future__ import annotations

import unittest

from py4gw import (
    FriendList,
    FriendListStruct,
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    Win32,
)


class LiveFriendListTests(unittest.TestCase):
    """Verify FriendList resolution and bounded records against a client."""

    @classmethod
    def setUpClass(cls) -> None:
        """Open the first discovered client with read-only access."""

        cls.win32 = Win32()
        clients = cls.win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")

        cls.pid = int(clients[0]["pid"])
        module = cls.win32.get_main_module(cls.pid)
        cls.reader = ProcessMemoryReader(cls.win32, cls.pid)
        cls.scanner = RemoteScanner(
            cls.reader,
            int(module["base_address"]),
            int(module["size"]),
        )
        cls.scanner.initialize()
        cls.friend_list = FriendList(
            cls.reader,
            cls.scanner,
            PatternCatalog.from_directory("offsets"),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle after the live checks."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_resolves_live_friend_list(self) -> None:
        """The JSON resolver locates the native friend-list object."""

        address = self.friend_list.resolve_address()
        self.assertIsNotNone(address)
        self.assertGreater(address or 0, 0)
        self.assertEqual(address, self.friend_list.cached_context_address)
        print(f"Live FriendList: 0x{address or 0:08X}")

    def test_reads_live_friend_list(self) -> None:
        """The root counts and bounded friend entries can be read safely."""

        snapshot = self.friend_list.read()
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertIsInstance(snapshot, FriendListStruct)
        self.assertLessEqual(
            int(snapshot.friends.m_size),
            int(snapshot.friends.m_capacity),
        )
        friends = snapshot.friend_records
        self.assertLessEqual(len(friends), 512)
        print(
            "Live friend list: "
            f"friends={snapshot.number_of_friends}, "
            f"ignores={snapshot.number_of_ignores}, "
            f"entries={len(friends)}, status={snapshot.status.name}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

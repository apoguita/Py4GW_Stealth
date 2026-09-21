"""Live Guild Wars tests for the external PartyContext reader."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    GameContext,
    HenchmanPartyMemberStruct,
    HeroPartyMemberStruct,
    PartyContext,
    PartyContextStruct,
    PartyInfoStruct,
    PartySearchStruct,
    PatternCatalog,
    PlayerPartyMemberStruct,
    ProcessMemoryReader,
    RemoteScanner,
    Win32,
)


class LivePartyContextTests(unittest.TestCase):
    """Verify PartyContext and its nested remote arrays against Guild Wars."""

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
        patterns = PatternCatalog.from_directory("offsets")
        cls.game_context = GameContext(cls.reader, cls.scanner, patterns)
        cls.game_context.initialize()
        cls.context = PartyContext(cls.reader, cls.game_context)

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle after the live checks."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_layout_matches_native_party_context(self) -> None:
        """Keep the party root and nested records aligned with native source."""

        self.assertEqual(ctypes.sizeof(PlayerPartyMemberStruct), 0x0C)
        self.assertEqual(ctypes.sizeof(HeroPartyMemberStruct), 0x18)
        self.assertEqual(ctypes.sizeof(HenchmanPartyMemberStruct), 0x34)
        self.assertEqual(ctypes.sizeof(PartyInfoStruct), 0x84)
        self.assertEqual(ctypes.sizeof(PartySearchStruct), 0x94)
        self.assertEqual(ctypes.sizeof(PartyContextStruct), 0xD0)
        self.assertEqual(PartyContextStruct.player_party_ptr.offset, 0x54)
        self.assertEqual(PartyContextStruct.party_search_array.offset, 0xC0)

    def test_resolves_live_party_context(self) -> None:
        """Follow the direct GameContext.party pointer."""

        address = self.context.resolve_address()
        if address is None:
            self.skipTest("The connected client has no active PartyContext.")
        self.assertGreater(address, 0)
        print(f"Live PartyContext: 0x{address:08X}")

    def test_reads_live_party_context_and_nested_data(self) -> None:
        """Read the root flags, party records, and nested member arrays."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The connected client has no active PartyContext.")

        self.assertEqual(len(bytes(snapshot)), 0xD0)
        parties = snapshot.parties
        player_party = snapshot.player_party
        self.assertLessEqual(
            len(parties), int(snapshot.parties_array.m_capacity)
        )
        if player_party is not None:
            self.assertEqual(len(bytes(player_party)), 0x84)
            self.assertLessEqual(
                len(player_party.players),
                int(player_party.players_array.m_capacity),
            )
        print(
            "Live party: "
            f"leader={snapshot.is_party_leader}, parties={len(parties)}, "
            f"searches={len(snapshot.party_searches)}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

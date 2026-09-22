"""Live read-only checks for the external AccountContext root."""

from __future__ import annotations

import unittest

from py4gw import AccountContext, GameContext, PatternCatalog, ProcessMemoryReader, RemoteScanner, Win32


class LiveAccountContextTests(unittest.TestCase):
    """Verify the direct GameContext account pointer and root arrays."""

    @classmethod
    def setUpClass(cls) -> None:
        """Open the first running client with read-only access."""

        cls.win32 = Win32()
        clients = cls.win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")
        cls.pid = int(clients[0]["pid"])
        module = cls.win32.get_main_module(cls.pid)
        cls.reader = ProcessMemoryReader(cls.win32, cls.pid)
        cls.scanner = RemoteScanner(
            cls.reader, int(module["base_address"]), int(module["size"])
        )
        cls.scanner.initialize()
        cls.game_context = GameContext(
            cls.reader, cls.scanner, PatternCatalog.from_directory("offsets")
        )
        cls.game_context.initialize()
        cls.context = AccountContext(cls.reader, cls.game_context)

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_reads_account_root(self) -> None:
        """Read the fixed root and report its bounded array headers."""

        address = self.context.resolve_address()
        if address is None:
            self.skipTest("The client has no active AccountContext.")
        snapshot = self.context.read()
        self.assertIsNotNone(snapshot)
        if snapshot is None:
            return
        self.assertEqual(len(bytes(snapshot)), 0x138)
        print(
            "Live AccountContext: "
            f"0x{address:08X}, arrays={snapshot.array_sizes}, "
            f"flags=0x{int(snapshot.account_flags):08X}"
        )

    def test_reads_source_account_queries(self) -> None:
        """Read the account arrays used by native item and skill helpers."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The client has no active AccountContext.")

        counts = snapshot.account_unlocked_count_list
        skills = snapshot.unlocked_account_skill_words
        if counts is not None:
            self.assertLessEqual(
                len(counts), int(snapshot.account_unlocked_counts.m_capacity)
            )
            self.assertGreaterEqual(snapshot.material_storage_stack_size, 250)
        if skills is not None:
            self.assertLessEqual(
                len(skills), int(snapshot.unlocked_account_skills.m_capacity)
            )
        print(
            "Live account queries: "
            f"unlock_counts={len(counts or [])}, skill_words={len(skills or [])}, "
            f"material_stack={snapshot.material_storage_stack_size}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

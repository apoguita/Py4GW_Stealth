"""Small tests for the single-class process-discovery interface."""

from __future__ import annotations

import unittest

from py4gw import Win32


class Win32Tests(unittest.TestCase):
    """Test behavior that does not require a Guild Wars client to be running."""

    def setUp(self) -> None:
        """Create one Win32 object for each test."""

        self.win32 = Win32()

    def test_process_names_are_compared_case_insensitively(self) -> None:
        """The executable filename is the only candidate matching rule."""

        self.assertTrue(self.win32._is_guild_wars_name("Gw.exe"))
        self.assertTrue(self.win32._is_guild_wars_name("GW.EXE"))
        self.assertFalse(self.win32._is_guild_wars_name("GuildWars.exe"))

    def test_format_empty_result(self) -> None:
        """An empty result has a clear display message."""

        self.assertEqual(
            self.win32.format_processes([]),
            "No Gw.exe candidates are currently running.",
        )

    def test_real_process_listing_returns_basic_records(self) -> None:
        """The real read-only API returns positive PIDs and executable names."""

        processes = self.win32.list_processes()

        self.assertIsInstance(processes, list)
        for process in processes:
            self.assertGreaterEqual(process["pid"], 0)
            self.assertIsInstance(process["name"], str)


if __name__ == "__main__":
    unittest.main(verbosity=2)

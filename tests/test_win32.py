"""Small tests for the single-class process-discovery interface."""

from __future__ import annotations

import ctypes
import unittest
from ctypes import wintypes

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

    def test_elevation_is_reported_as_a_boolean(self) -> None:
        """The token query answers, without touching another process.

        Which value it returns depends on the shell this suite was started from,
        so only the shape is pinned here. Both directions are covered by running
        the suite each way: unelevated, `py4gw.connect` refuses; elevated, the
        connect-based live suites run.
        """

        elevated = self.win32.is_elevated()

        self.assertIsInstance(elevated, bool)

    def test_the_elevation_check_does_not_leak_a_handle(self) -> None:
        """It opens this process's token, so the handle has to go back."""

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        count = wintypes.DWORD()

        kernel32.GetProcessHandleCount(kernel32.GetCurrentProcess(), ctypes.byref(count))
        before = count.value
        for _ in range(200):
            self.win32.is_elevated()
        kernel32.GetProcessHandleCount(kernel32.GetCurrentProcess(), ctypes.byref(count))

        self.assertLessEqual(count.value, before + 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Offline tests for explicit process-reader ownership."""

from __future__ import annotations

import unittest

from py4gw import ProcessMemoryReader


class _TestWin32:
    """Small test double for the Win32 memory boundary."""

    def __init__(self) -> None:
        self.closed_handles: list[int] = []

    def open_process_memory(self, pid: int) -> int:
        self.opened_pid = pid
        return 7

    def close_process_memory(self, handle: int) -> None:
        self.closed_handles.append(handle)

    def read_process_memory(self, handle: int, address: int, size: int) -> bytes:
        self.read_request = (handle, address, size)
        return b"x" * size


class ProcessMemoryReaderTests(unittest.TestCase):
    """Verify lifetime and read delegation without a live target."""

    def test_context_manager_closes_handle(self) -> None:
        """The reader closes the handle it opened."""

        win32 = _TestWin32()
        with ProcessMemoryReader(win32, 1234) as reader:
            self.assertEqual(reader.read(0x1000, 3), b"xxx")
            self.assertFalse(reader.is_closed)

        self.assertEqual(win32.closed_handles, [7])
        self.assertTrue(reader.is_closed)

    def test_read_after_close_is_rejected(self) -> None:
        """A released handle cannot be reused accidentally."""

        win32 = _TestWin32()
        reader = ProcessMemoryReader(win32, 1234)
        reader.close()

        with self.assertRaises(RuntimeError):
            reader.read(0x1000, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

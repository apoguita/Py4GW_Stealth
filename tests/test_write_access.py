"""Live tests for the write transport and the fail-closed patch sequence.

**These tests write to the client's memory.** That is the point of them, and the
scope is deliberately narrow:

* every write targets memory this test allocated itself, with ``VirtualAllocEx``;
* nothing belonging to the client is modified — not its code, not its data;
* every allocation is released in a ``finally``, so a failed test still frees it;
* the patch sequence is exercised against that allocation, not against client
  code. It suspends and resumes the client's threads, which is momentary and is
  undone on every path, but it is a real intervention and this is where it is
  proven.

Rollback: freeing the allocation returns the client to the state it was in. The
client's own memory is never written, so there is nothing else to undo.

They need an **elevated** controller. Unelevated, Windows denies
``PROCESS_VM_WRITE``, ``PROCESS_VM_OPERATION`` and ``PROCESS_CREATE_THREAD`` with
error 5, and the class skips with that reason rather than failing.

Run from the project directory with Guild Wars running, from an elevated shell::

    python -m unittest tests.test_write_access -v
"""

from __future__ import annotations

import unittest

import py4gw
from py4gw.game_thread.patcher import Patcher
from py4gw.win32.write_access import WriteAccess

ACCESS_DENIED = 5
BUFFER_SIZE = 64


class LiveWriteAccessTests(unittest.TestCase):
    """Verify the transport and the patch sequence against a real process."""

    pid: int
    access: WriteAccess
    module_base: int
    module_size: int

    @classmethod
    def setUpClass(cls) -> None:
        """Find the client and open a write transport to it."""

        clients = py4gw.Win32().find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")
        cls.pid = int(clients[0]["pid"])

        module = py4gw.Win32().get_main_module(cls.pid)
        cls.module_base = int(module["base_address"])
        cls.module_size = int(module["size"])

        try:
            cls.access = WriteAccess(cls.pid)
        except OSError as error:
            if getattr(error, "errno", None) == ACCESS_DENIED or error.args[0] == 5:
                raise unittest.SkipTest(
                    "The controller must be elevated: Windows denied write "
                    f"access to pid {cls.pid} with error 5. Run this suite from "
                    "an elevated shell."
                ) from error
            raise

    @classmethod
    def tearDownClass(cls) -> None:
        """Release the write transport."""

        access = getattr(cls, "access", None)
        if access is not None:
            access.close()

    def allocate(self, size: int = BUFFER_SIZE) -> int:
        """Allocate a buffer in the client and register it for release."""

        address = self.access.allocate(size)
        self.addCleanup(self.access.free, address)
        return address

    # -- the transport -----------------------------------------------------

    def test_the_transport_reports_the_process_it_opened(self) -> None:
        self.assertEqual(self.access.pid, self.pid)
        self.assertNotEqual(self.access.handle, 0)

    def test_allocate_write_and_read_back(self) -> None:
        """The whole reason this module exists: memory we can write to."""

        address = self.allocate()
        pattern = bytes(range(BUFFER_SIZE))
        self.access.write(address, pattern)
        self.assertEqual(self.access.read(address, BUFFER_SIZE), pattern)

    def test_a_second_write_overwrites_the_first(self) -> None:
        address = self.allocate()
        self.access.write(address, b"\x11" * 16)
        self.access.write(address, b"\x22" * 16)
        self.assertEqual(self.access.read(address, 16), b"\x22" * 16)

    def test_the_allocation_is_not_inside_the_client_module(self) -> None:
        """We write to memory we own, never into the client's image."""

        address = self.allocate()
        self.assertFalse(
            self.module_base <= address < self.module_base + self.module_size,
            f"the allocation at 0x{address:08X} landed inside the client module "
            f"0x{self.module_base:08X}+0x{self.module_size:X}",
        )

    def test_the_client_threads_can_be_enumerated(self) -> None:
        thread_ids = self.access.list_thread_ids()
        self.assertGreater(len(thread_ids), 0)
        for thread_id in thread_ids:
            self.assertGreater(thread_id, 0)

    def test_a_thread_context_can_be_read(self) -> None:
        """Reading an instruction pointer is what makes a patch safe."""

        thread_ids = self.access.list_thread_ids()
        handle = self.access.open_thread(thread_ids[0])
        try:
            self.access.suspend_thread(handle)
            try:
                eip = self.access.thread_eip(handle)
            finally:
                self.access.resume_thread(handle)
        finally:
            self.access.close_thread(handle)

        self.assertNotEqual(eip, 0)
        self.assertLess(eip, 0xFFFFFFFF)

    # -- the patch sequence ------------------------------------------------

    def test_patch_and_restore_our_own_allocation(self) -> None:
        """Run the whole fail-closed sequence against a real process.

        The address is memory this test allocated, so no client code is touched.
        Everything else is real: the threads are suspended, their instruction
        pointers are read, the page protection changes, the write lands, the
        instruction cache is flushed, and the original bytes go back.
        """

        address = self.allocate()
        original = bytes(range(16)) + bytes(BUFFER_SIZE - 16)
        replacement = bytes(reversed(range(16))) + bytes(BUFFER_SIZE - 16)
        self.access.write(address, original)

        patcher = Patcher(self.access, self.pid)
        patcher.patch(address, original, replacement)
        self.assertEqual(self.access.read(address, BUFFER_SIZE), replacement)
        self.assertEqual(patcher.installed, (address,))

        patcher.restore(address)
        self.assertEqual(self.access.read(address, BUFFER_SIZE), original)
        self.assertEqual(patcher.installed, ())

    def test_patching_twice_is_refused(self) -> None:
        address = self.allocate()
        original = bytes(BUFFER_SIZE)
        replacement = b"\x90" * BUFFER_SIZE
        self.access.write(address, original)

        patcher = Patcher(self.access, self.pid)
        patcher.patch(address, original, replacement)
        self.addCleanup(patcher.restore, address)

        with self.assertRaises(RuntimeError):
            patcher.patch(address, original, replacement)

    def test_restore_refuses_when_the_bytes_are_no_longer_ours(self) -> None:
        """Something else changed it; putting our bytes back would be wrong."""

        address = self.allocate()
        original = bytes(BUFFER_SIZE)
        replacement = b"\x90" * BUFFER_SIZE
        self.access.write(address, original)

        patcher = Patcher(self.access, self.pid)
        patcher.patch(address, original, replacement)
        self.access.write(address, original)

        with self.assertRaises(RuntimeError):
            patcher.restore(address)

    # -- the boundary ------------------------------------------------------

    def test_the_read_only_transport_still_works(self) -> None:
        """Writes need elevation; reads never did, and still do not."""

        win32 = py4gw.Win32()
        handle = win32.open_process_memory(self.pid)
        try:
            head = win32.read_process_memory(handle, self.module_base, 2)
        finally:
            win32.close_process_memory(handle)
        self.assertEqual(head, b"MZ")


if __name__ == "__main__":
    unittest.main(verbosity=2)

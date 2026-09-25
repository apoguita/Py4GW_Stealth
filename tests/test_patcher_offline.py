"""Offline tests for the fail-closed patch sequence.

No client is involved: the target is a ``bytearray`` and a set of pretend
threads, so the ordering, the refusals and the cleanup can all be checked
directly. What is *not* proven here is that the Win32 calls behave as assumed —
that needs a live client, and a live client needs explicit scope for a write.

The properties worth guarding hardest:

* nothing is written unless the bytes were verified first, twice;
* a thread standing in the patch window blocks the write rather than being
  written over;
* every suspended thread is resumed and every handle closed, on success, on
  refusal and on timeout;
* a restore refuses when the bytes are no longer ours.
"""

from __future__ import annotations

import unittest

from py4gw.game_thread.patcher import PAGE_EXECUTE_READWRITE, Patcher

BASE = 0x00400000
TARGET = 0x00401000
ORIGINAL = bytes.fromhex("55 8B EC 81 EC 00 01 00 00")
PATCH = bytes.fromhex("E9 11 22 33 44 90 90 90 90")

PAGE_READ = 0x02
PAGE_EXECUTE_READ = 0x20


class FakeTarget:
    """A target process with pretend memory and pretend threads.

    ``eip_plan`` maps a thread id to the instruction pointers it should report,
    one per read; the last value repeats. That is how a test makes a thread
    "move out of the window" on a later attempt.
    """

    def __init__(
        self,
        memory: bytes,
        thread_ids: tuple[int, ...] = (101, 102),
        eips: dict[int, int] | None = None,
        eip_plan: dict[int, list[int]] | None = None,
    ) -> None:
        self.memory = bytearray(memory)
        self.thread_ids = list(thread_ids)
        self.eips = dict(eips or {tid: BASE + 0x9000 for tid in thread_ids})
        self.eip_plan = {k: list(v) for k, v in (eip_plan or {}).items()}
        self.operations: list[tuple[str, int, int]] = []
        self.suspends = 0
        self.opened: set[int] = set()
        self.closed: set[int] = set()
        self.resumed: set[int] = set()
        self.protection = {TARGET: PAGE_EXECUTE_READ}
        self.fail_protect = False

    # -- reads and writes --------------------------------------------------

    def read(self, address: int, size: int) -> bytes:
        self.operations.append(("read", address, size))
        return bytes(self.memory[address - BASE : address - BASE + size])

    def write(self, address: int, data: bytes) -> None:
        self.operations.append(("write", address, len(data)))
        start = address - BASE
        self.memory[start : start + len(data)] = data

    def protect(self, address: int, size: int, protection: int) -> int:
        if self.fail_protect:
            raise OSError(5, "VirtualProtectEx failed (simulated)")
        self.operations.append(("protect", address, protection))
        previous = self.protection.get(address, PAGE_EXECUTE_READ)
        self.protection[address] = protection
        return previous

    def flush_instruction_cache(self, address: int, size: int) -> None:
        self.operations.append(("flush", address, size))

    # -- threads -----------------------------------------------------------

    def list_thread_ids(self) -> list[int]:
        self.operations.append(("list_threads", 0, len(self.thread_ids)))
        return list(self.thread_ids)

    def open_thread(self, thread_id: int) -> int:
        handle = 0x1000 + thread_id
        self.opened.add(handle)
        return handle

    def suspend_thread(self, thread_handle: int) -> int:
        self.operations.append(("suspend", thread_handle, 0))
        self.suspends += 1
        return 0

    def resume_thread(self, thread_handle: int) -> int:
        self.operations.append(("resume", thread_handle, 0))
        self.resumed.add(thread_handle)
        return 0

    def thread_eip(self, thread_handle: int) -> int:
        thread_id = thread_handle - 0x1000
        plan = self.eip_plan.get(thread_id)
        if plan:
            return plan.pop(0) if len(plan) > 1 else plan[0]
        return self.eips[thread_id]

    def close_thread(self, thread_handle: int) -> None:
        self.closed.add(thread_handle)

    # -- helpers for assertions -------------------------------------------

    def code(self) -> bytes:
        return bytes(self.memory[TARGET - BASE : TARGET - BASE + len(PATCH)])

    def kinds(self) -> list[str]:
        return [name for name, _, _ in self.operations]

    def leaked_handles(self) -> set[int]:
        return self.opened - self.closed


def new_target(**kwargs: object) -> FakeTarget:
    """Build a target whose memory holds the expected original bytes."""

    memory = bytearray(0x10000)
    memory[TARGET - BASE : TARGET - BASE + len(ORIGINAL)] = ORIGINAL
    return FakeTarget(bytes(memory), **kwargs)  # type: ignore[arg-type]


class PatchTests(unittest.TestCase):
    """The write path, and every reason it refuses."""

    def test_patch_writes_the_bytes_and_restores_protection(self) -> None:
        target = new_target()
        Patcher(target, pid=1234).patch(TARGET, ORIGINAL, PATCH)

        self.assertEqual(target.code(), PATCH)

        kinds = target.kinds()
        written = kinds.index("write")
        self.assertEqual(
            kinds[written - 1 : written + 3],
            ["protect", "write", "flush", "protect"],
        )
        self.assertEqual(target.operations[written - 1][2], PAGE_EXECUTE_READWRITE)
        self.assertEqual(target.operations[written + 2][2], PAGE_EXECUTE_READ)

    def test_patch_verifies_before_writing(self) -> None:
        """The first thing that happens is a read, before any suspension."""

        target = new_target()
        Patcher(target, pid=1234).patch(TARGET, ORIGINAL, PATCH)
        self.assertEqual(target.kinds()[0], "read")
        self.assertLess(target.kinds().index("read"), target.kinds().index("suspend"))

    def test_refuses_when_the_bytes_are_not_expected(self) -> None:
        target = new_target()
        target.memory[TARGET - BASE] = 0x90

        with self.assertRaises(RuntimeError) as caught:
            Patcher(target, pid=1234).patch(TARGET, ORIGINAL, PATCH)

        self.assertIn("0x00401000", str(caught.exception))
        self.assertIn("Nothing was written", str(caught.exception))
        self.assertNotIn("write", target.kinds())
        self.assertEqual(target.suspends, 0)

    def test_refuses_while_a_thread_is_inside_the_window(self) -> None:
        target = new_target(eips={101: TARGET + 4, 102: BASE + 0x9000})

        with self.assertRaises(TimeoutError) as caught:
            Patcher(target, pid=1234, timeout_ms=20).patch(
                TARGET, ORIGINAL, PATCH
            )

        self.assertIn("still inside", str(caught.exception))
        self.assertIn("Nothing was written", str(caught.exception))
        self.assertNotIn("write", target.kinds())

    def test_waits_for_a_thread_to_leave_the_window(self) -> None:
        """A thread standing in the window blocks the write, then moves on."""

        target = new_target(eip_plan={101: [TARGET + 4, BASE + 0x9000]})
        Patcher(target, pid=1234, timeout_ms=500).patch(TARGET, ORIGINAL, PATCH)

        self.assertEqual(target.code(), PATCH)
        self.assertGreaterEqual(target.suspends, 4)

    def test_a_thread_at_the_end_of_the_window_is_not_inside_it(self) -> None:
        target = new_target(eips={101: TARGET + len(ORIGINAL), 102: BASE})
        Patcher(target, pid=1234).patch(TARGET, ORIGINAL, PATCH)
        self.assertEqual(target.code(), PATCH)

    def test_refuses_on_a_zero_instruction_pointer(self) -> None:
        target = new_target(eips={101: 0, 102: BASE + 0x9000})

        with self.assertRaises(RuntimeError) as caught:
            Patcher(target, pid=1234).patch(TARGET, ORIGINAL, PATCH)

        self.assertIn("zero instruction pointer", str(caught.exception))
        self.assertNotIn("write", target.kinds())

    def test_every_thread_is_released_on_success(self) -> None:
        target = new_target()
        Patcher(target, pid=1234).patch(TARGET, ORIGINAL, PATCH)
        self.assertEqual(target.leaked_handles(), set())
        self.assertEqual(target.resumed, target.opened)
        self.assertEqual(target.suspends, len(target.thread_ids))

    def test_every_thread_is_released_on_refusal(self) -> None:
        target = new_target()
        target.memory[TARGET - BASE] = 0x90

        with self.assertRaises(RuntimeError):
            Patcher(target, pid=1234).patch(TARGET, ORIGINAL, PATCH)

        self.assertEqual(target.leaked_handles(), set())

    def test_every_thread_is_released_on_timeout(self) -> None:
        target = new_target(eips={101: TARGET, 102: BASE})
        with self.assertRaises(TimeoutError):
            Patcher(target, pid=1234, timeout_ms=10).patch(
                TARGET, ORIGINAL, PATCH
            )
        self.assertEqual(target.leaked_handles(), set())

    def test_every_thread_is_released_when_the_write_fails(self) -> None:
        target = new_target()
        target.fail_protect = True

        with self.assertRaises(OSError):
            Patcher(target, pid=1234).patch(TARGET, ORIGINAL, PATCH)

        self.assertEqual(target.leaked_handles(), set())
        self.assertEqual(target.code(), ORIGINAL)

    def test_a_second_patch_of_the_same_address_is_refused(self) -> None:
        target = new_target()
        patcher = Patcher(target, pid=1234)
        patcher.patch(TARGET, ORIGINAL, PATCH)

        with self.assertRaises(RuntimeError) as caught:
            patcher.patch(TARGET, ORIGINAL, PATCH)
        self.assertIn("already patched", str(caught.exception))

    def test_patch_arguments_are_validated(self) -> None:
        target = new_target()
        patcher = Patcher(target, pid=1234)

        with self.assertRaises(ValueError):
            patcher.patch(0, ORIGINAL, PATCH)
        with self.assertRaises(ValueError):
            patcher.patch(TARGET, b"", b"")
        with self.assertRaises(ValueError):
            patcher.patch(TARGET, ORIGINAL, PATCH[:-1])
        self.assertNotIn("write", target.kinds())

    def test_patcher_arguments_are_validated(self) -> None:
        target = new_target()
        with self.assertRaises(ValueError):
            Patcher(target, pid=0)
        with self.assertRaises(ValueError):
            Patcher(target, pid=1, timeout_ms=0)


class RestoreTests(unittest.TestCase):
    """Putting the original bytes back is conditional on them still being ours."""

    def test_restore_puts_the_original_bytes_back(self) -> None:
        target = new_target()
        patcher = Patcher(target, pid=1234)
        patcher.patch(TARGET, ORIGINAL, PATCH)
        patcher.restore(TARGET)

        self.assertEqual(target.code(), ORIGINAL)
        self.assertEqual(patcher.installed, ())

    def test_restore_refuses_when_the_bytes_are_no_longer_ours(self) -> None:
        """Something else changed the code; putting ours back would corrupt it."""

        target = new_target()
        patcher = Patcher(target, pid=1234)
        patcher.patch(TARGET, ORIGINAL, PATCH)

        target.memory[TARGET - BASE] = 0xCC
        with self.assertRaises(RuntimeError) as caught:
            patcher.restore(TARGET)

        self.assertIn("before the restore", str(caught.exception))
        self.assertIn("Nothing was written", str(caught.exception))
        self.assertNotIn("write", target.kinds()[-3:])

    def test_restore_refuses_an_address_it_did_not_patch(self) -> None:
        target = new_target()
        with self.assertRaises(RuntimeError) as caught:
            Patcher(target, pid=1234).restore(TARGET)
        self.assertIn("nothing to restore", str(caught.exception))

    def test_restore_releases_every_thread(self) -> None:
        target = new_target()
        patcher = Patcher(target, pid=1234)
        patcher.patch(TARGET, ORIGINAL, PATCH)
        patcher.restore(TARGET)
        self.assertEqual(target.leaked_handles(), set())

    def test_restore_all_restores_newest_first(self) -> None:
        memory = bytearray(0x10000)
        memory[TARGET - BASE : TARGET - BASE + len(ORIGINAL)] = ORIGINAL
        second = TARGET + 0x100
        memory[second - BASE : second - BASE + len(ORIGINAL)] = ORIGINAL
        target = FakeTarget(bytes(memory))

        patcher = Patcher(target, pid=1234)
        patcher.patch(TARGET, ORIGINAL, PATCH)
        patcher.patch(second, ORIGINAL, PATCH)
        self.assertEqual(patcher.installed, (TARGET, second))

        patcher.restore_all()
        self.assertEqual(patcher.installed, ())
        self.assertEqual(target.code(), ORIGINAL)


if __name__ == "__main__":
    unittest.main(verbosity=2)

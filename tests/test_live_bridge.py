"""Live Guild Wars test for the game-thread bridge.

**This is the first test in this project that changes the client.** It installs an
entry hook inside ``Gw.exe``, publishes commands that the client's own game thread
runs, and puts the function's original bytes back afterwards. Nothing else in the
client is modified: the block and the dispatcher live in memory this test
allocates.

Run it from an **elevated** shell while Guild Wars is running, and be in a map::

    python -m unittest tests.test_live_bridge -v

What it proves: the resolver finds ``leave_game_thread_func`` on the live client
and its entry bytes are the ones the patch declares; the hook is placed, fires on
the client's own thread, and the function keeps returning through the trampoline;
a command published by this process is taken by the client, run, and completed
with the result the payload computed; the completion event arrives; the ring is
reused past its depth; and the original bytes are back at the end.

What it does not prove: that any Guild Wars function can be called. The call
vocabulary — a bounded target and a typed argument form — does not exist yet, and
the payload refuses every operation that would need it.
"""

from __future__ import annotations

import hashlib
import unittest

import py4gw
from py4gw.game_thread.bridge import Bridge
from py4gw.game_thread.shared_block import (
    COMMAND_DEPTH,
    PING_RESULT,
    RESULT_UNKNOWN_OPERATION,
    CommandState,
    Operation,
    pending,
)
from py4gw.memory import ProcessMemoryReader
from py4gw.scanner import PatternCatalog, RemoteScanner
from py4gw.win32 import Win32
from py4gw.win32.write_access import WriteAccess

#: The resolver that locates the function whose thread should run our work.
RESOLVER = "game_thread.leave_game_thread_func"

#: The whole instructions the entry patch replaces. Read from this client build
#: before anything is written: push ebp / mov ebp, esp / sub esp, 0x220.
DISPLACED = bytes.fromhex("55 8B EC 81 EC 20 02 00 00")

#: How many times the hooked function has to run before the placement counts as
#: wired up, and how long it gets to do it.
HIT_TARGET = 2
HIT_TIMEOUT_MS = 5000

#: How long one command gets. Generous: the client only takes work when its own
#: thread reaches the hooked function.
COMMAND_TIMEOUT_MS = 5000

#: How much of the code section is read at a time when hashing it.
TEXT_CHUNK = 0x10000

ACCESS_DENIED = 5


class LiveBridgeTests(unittest.TestCase):
    """The bridge, installed on the running client."""

    pid: int
    target: int
    access: WriteAccess
    bridge: Bridge
    hits: int

    # -- setup and teardown ------------------------------------------------

    @classmethod
    def setUpClass(cls) -> None:
        win32 = py4gw.Win32()
        clients = win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")
        cls.pid = int(clients[0]["pid"])

        cls.target = cls._resolve_target(win32, cls.pid)
        observed = cls._read_entry(win32, cls.pid, cls.target)
        if observed != DISPLACED:
            raise AssertionError(
                f"pid {cls.pid}: 0x{cls.target:08X} does not hold the entry bytes "
                f"this test declares: expected {DISPLACED.hex(' ')}, observed "
                f"{observed.hex(' ')}. Either the client build changed or the "
                "resolver points at something else - nothing was written."
            )

        cls.text_before = cls._text_digest(win32, cls.pid)

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

        cls.bridge = Bridge(cls.access, cls.pid, timeout_ms=COMMAND_TIMEOUT_MS)
        cls.bridge.install(cls.target, DISPLACED)

        try:
            cls.hits = cls.bridge.wait_for_hits(HIT_TARGET, HIT_TIMEOUT_MS)
        except TimeoutError as error:
            # Put the client back before reporting: the hook is placed and
            # verified, but the game thread is not running that function.
            cls.bridge.remove()
            cls.access.close()
            raise unittest.SkipTest(
                f"pid {cls.pid}: the hook is placed on 0x{cls.target:08X} and the "
                f"entry bytes matched, but the function did not run within "
                f"{HIT_TIMEOUT_MS} ms. Be in a map rather than at a menu. "
                f"Original bytes restored. ({error})"
            ) from error

    @classmethod
    def tearDownClass(cls) -> None:
        """Take the hook out, confirm the code is back, and report what is left."""

        bridge = getattr(cls, "bridge", None)
        access = getattr(cls, "access", None)
        if bridge is not None and bridge.installed:
            bridge.remove()

        win32 = py4gw.Win32()
        observed = cls._read_entry(win32, cls.pid, cls.target)
        text_after = cls._text_digest(win32, cls.pid)
        block = bridge.block_address if bridge is not None else 0
        dispatcher = bridge.dispatcher_address if bridge is not None else 0
        if access is not None:
            access.close()

        print(
            f"\nleave_game_thread_func     = 0x{cls.target:08X}\n"
            f"displaced entry bytes      = {DISPLACED.hex(' ')}\n"
            f"hook hits                  = {cls.hits}\n"
            f"entry after remove         = {observed.hex(' ')}\n"
            f"code section before        = {cls.text_before[0][:32]}... "
            f"({cls.text_before[1]} bytes)\n"
            f"code section after         = {text_after[0][:32]}... "
            f"({text_after[1]} bytes)\n"
            f"left mapped (on purpose)   = block 0x{block:08X}, "
            f"dispatcher 0x{dispatcher:08X}"
        )

        if observed != DISPLACED:
            raise AssertionError(
                f"pid {cls.pid}: 0x{cls.target:08X} was left holding "
                f"{observed.hex(' ')}, not its original {DISPLACED.hex(' ')}."
            )
        if text_after != cls.text_before:
            raise AssertionError(
                f"pid {cls.pid}: the code section changed during the run: "
                f"{cls.text_before[0]} before, {text_after[0]} after. The entry "
                "patch is the only code this project writes, so anything else is "
                "a defect."
            )

    # -- what was placed ---------------------------------------------------

    def test_the_hook_fired_on_the_game_thread(self) -> None:
        self.assertTrue(self.bridge.installed)
        self.assertGreaterEqual(self.bridge.hits(), HIT_TARGET)
        self.assertGreaterEqual(self.hits, HIT_TARGET)

    # -- one round trip per operation --------------------------------------

    def test_ping_round_trips_through_the_client(self) -> None:
        record = self.bridge.submit(Operation.PING)

        self.assertEqual(record.state, CommandState.DONE)
        self.assertEqual(record.result, PING_RESULT)

    def test_echo_returns_its_argument(self) -> None:
        record = self.bridge.submit(Operation.ECHO_U32, 0x5A5A5A5A)

        self.assertEqual(record.state, CommandState.DONE)
        self.assertEqual(record.result, 0x5A5A5A5A)

    def test_add_adds_its_arguments(self) -> None:
        record = self.bridge.submit(Operation.ADD_U32, 40, 2)

        self.assertEqual(record.state, CommandState.DONE)
        self.assertEqual(record.result, 42)

    def test_a_nop_completes_with_no_result(self) -> None:
        record = self.bridge.submit(Operation.NOP)

        self.assertEqual(record.state, CommandState.DONE)
        self.assertEqual(record.result, 0)

    def test_an_unknown_operation_fails_in_the_client(self) -> None:
        """The refusal happens on the game thread, not in this process."""

        record = self.bridge.submit(99)

        self.assertEqual(record.state, CommandState.FAILED)
        self.assertEqual(record.result, RESULT_UNKNOWN_OPERATION)

    # -- the event channel -------------------------------------------------

    def test_the_completion_event_comes_back(self) -> None:
        record = self.bridge.submit(Operation.PING)

        matching = [
            event
            for event in self.bridge.completions()
            if event.sequence == record.sequence
        ]
        self.assertTrue(
            matching,
            f"no completion event for sequence {record.sequence}",
        )
        event = matching[0]
        self.assertEqual(event.arg0, Operation.PING)
        self.assertEqual(event.arg1, CommandState.DONE)
        self.assertEqual(event.arg2, PING_RESULT & 0xFFFFFFFF)

    # -- the queue over a full lap -----------------------------------------

    def test_the_command_ring_is_reused_past_its_depth(self) -> None:
        start = self.bridge.header().command_written
        laps = COMMAND_DEPTH + 1
        for index in range(laps):
            record = self.bridge.submit(Operation.ECHO_U32, index)
            self.assertEqual(record.result, index)

        header = self.bridge.header()
        self.assertEqual(header.command_written, start + laps)
        self.assertEqual(pending(header.command_written, header.command_taken), 0)
        # The commands crossed a lap boundary, so slots that had already held a
        # command were used again.
        self.assertGreater(
            header.command_written // COMMAND_DEPTH, start // COMMAND_DEPTH
        )

    # -- the client is still the client ------------------------------------

    def test_the_hooked_function_keeps_running(self) -> None:
        """The trampoline replays the displaced bytes, so the client goes on."""

        before = self.bridge.hits()
        self.bridge.wait_for_hits(2, HIT_TIMEOUT_MS)

        self.assertGreater(self.bridge.hits(), before)

    def test_the_client_is_still_there(self) -> None:
        pids = [int(process["pid"]) for process in py4gw.Win32().find_guild_wars()]
        self.assertIn(self.pid, pids)

    # -- resolution --------------------------------------------------------

    @staticmethod
    def _resolve_target(win32: Win32, pid: int) -> int:
        """Find the hooked function the way every other read here does."""

        module = win32.get_main_module(pid)
        with ProcessMemoryReader(win32, pid) as reader:
            scanner = RemoteScanner(
                reader,
                int(module["base_address"]),
                int(module["size"]),
            )
            scanner.initialize()
            catalog = PatternCatalog.from_directory("offsets")
            result = catalog.resolve(RESOLVER, scanner)
        if not result.ok:
            raise AssertionError(
                f"pid {pid}: {RESOLVER} did not resolve: {result.message}"
            )
        return int(result.value)

    @staticmethod
    def _read_entry(win32: Win32, pid: int, address: int) -> bytes:
        """Read the entry bytes through a fresh read-only handle."""

        with ProcessMemoryReader(win32, pid) as reader:
            return reader.read(address, len(DISPLACED))

    @staticmethod
    def _text_digest(win32: Win32, pid: int) -> tuple[str, int]:
        """Return a hash of the client's whole code section.

        The hook changes nine bytes of it for as long as it is installed. Hashing
        the section before and after is what turns "we only wrote the entry patch"
        into something checked rather than assumed.
        """

        module = win32.get_main_module(pid)
        digest = hashlib.sha256()
        size = 0
        with ProcessMemoryReader(win32, pid) as reader:
            scanner = RemoteScanner(
                reader,
                int(module["base_address"]),
                int(module["size"]),
            )
            scanner.initialize()
            section = scanner.get_section_range("text")
            address = section.start
            while address < section.end:
                chunk = min(TEXT_CHUNK, section.end - address)
                digest.update(reader.read(address, chunk))
                size += chunk
                address += chunk
        return digest.hexdigest(), size


if __name__ == "__main__":
    unittest.main()

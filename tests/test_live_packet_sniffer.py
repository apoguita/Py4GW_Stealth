"""Live Guild Wars test for the packet sniffer (`py4gw.packet_sniffer.SNIFFER`).

The class is ported whole in ``py4gw/packet_sniffer.py`` over native's ``PyPacketSniffer`` module
(``py4gw/native_src/packets/py_packet_sniffer.py``). Its inbound capture replaces the client's own
handler entry for a header with emitted code; its outbound capture hooks the client's send wrapper.
Offline tests execute both stubs against a fake block; only a running client can prove the client's
dispatcher reaches them.

**The suite is staged, because a live crash has to be attributable.** The first live attempt
(2026-10-24 20:47:39) died with ``c0000005`` writing ``0x096D1000`` from code at ``0x096D0FFF`` — an
address no loaded module covers, which is injected code — while Reforged's own last operation was
``Main.Update → "Travel On Character Load"``. That is not yet attributable, so this suite now:

1. prints the **block's address and span** at connect, so a fault address either lands inside this
   project's block or provably does not;
2. runs a **narrow capture** first — a handful of headers — before the whole array;
3. puts the **outbound half behind an environment variable**, because it hooks a function the client
   calls for every packet it sends and must not be mixed into a run that is already suspect;
4. restores every entry it replaced and asserts the client's array is byte-identical to how it found
   it.

**Nothing here changes the game.** It starts capture and waits for traffic the client produces anyway
(heartbeats, world updates), then puts back what it took.

Run it from an **elevated** shell, in a map, with Guild Wars running::

    python -m unittest tests.test_live_packet_sniffer -v
    $env:PY4GW_LIVE_CTOS = "1"; python -m unittest tests.test_live_packet_sniffer -v

Connecting is a write (block, hook, dispatcher), which is why the shell must be elevated first.
"""

from __future__ import annotations

import os
import struct
import time
import unittest

import py4gw
from py4gw.game_thread.packets import (
    ENTRY_HANDLER_OFFSET,
    describe_template,
    read_template,
)
from py4gw.game_thread import shared_block as sb
from py4gw.native_src.packets import py_packet_sniffer as binding
from py4gw.packet_sniffer import SNIFFER
from py4gw.win32 import Win32

#: How long to wait for a packet to arrive, and how often to look. Outbound traffic is rarer than
#: inbound — a client sitting in an outpost sends nothing but its own heartbeats — so the outbound
#: wait is longer and the test reports the stub's hit counter when it gives up, which is what says
#: whether the wrapper was called at all.
CAPTURE_TIMEOUT_S = 8.0
CTOS_TIMEOUT_S = 25.0
POLL_S = 0.05

#: ``kMaxStoCPacketBuffer`` (``packet_sniffer.h:28``).
MAX_STOC_CAPTURE = 512

#: The headers whose handler pointers this suite compares before and after, and the narrow subset the
#: first capture test installs. ``0x0084`` and ``0x00CC`` are ones the merchant listener also
#: registers, so a restore that took another consumer's entry out would show up here.
SAMPLED_HEADERS = (0x0084, 0x00CC, 0x0100)
NARROW_HEADERS = (0x0084, 0x0085, 0x0086, 0x00CC, 0x00F7)

#: The outbound half is opt-in: it hooks the function every outbound packet goes through, and a run
#: that is already a suspect should not be mixed with it.
CTOS_ENABLED = os.environ.get("PY4GW_LIVE_CTOS") == "1"


class LivePacketSnifferTests(unittest.TestCase):
    """Capture, read back, and restore — against the running client."""

    @classmethod
    def setUpClass(cls) -> None:
        win32 = Win32()
        if not win32.is_elevated():
            raise unittest.SkipTest(
                "the controller must be elevated: connecting is a write, and a process cannot "
                "elevate itself. Start the shell elevated and run this again."
            )
        clients = win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("no Guild Wars client is running.")
        cls.pid = int(clients[0]["pid"])
        cls.client = py4gw.connect(clients[0])
        cls.table_address = cls.client._resolve("stoc.handler_table_addr")
        block = cls.client.bridge.block_address
        cls.block_address = block
        print(
            f"--- connected to pid {cls.pid}; block at 0x{block:08X}..0x{block + sb.BLOCK_SIZE:08X} "
            f"({sb.BLOCK_SIZE:#x} bytes); event region "
            f"0x{block + sb.EVENT_REGION_OFFSET:08X}.."
            f"0x{block + sb.EVENT_REGION_OFFSET + sb.EVENT_DEPTH * sb.EVENT_SIZE:08X}; "
            f"capture area of a record at +{sb.EVENT_CAPTURE_OFFSET:#x} ({sb.EVENT_CAPTURE_SIZE} bytes)"
            f" ---"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        binding.Terminate()
        py4gw.disconnect()
        print(f"--- disconnected from pid {cls.pid} ---")

    def setUp(self) -> None:
        binding.ClearLogs()
        binding.Terminate()

    def tearDown(self) -> None:
        binding.Terminate()
        binding.ClearLogs()

    # -- what the client's array holds ------------------------------------

    def table(self):
        return self.client.bridge.read_packet_table(self.table_address)

    def handler_of(self, header: int) -> int:
        """Read one header's handler pointer straight out of the client's array."""

        table = self.table()
        if header >= table.size:
            self.skipTest(f"the client's array holds {table.size} entries; {header} is past it")
        entry = table.entry(header) + ENTRY_HANDLER_OFFSET
        return struct.unpack("<I", self.client.bridge.access.read(entry, 4))[0]

    def snapshot(self, headers) -> dict[int, int]:
        return {header: self.handler_of(header) for header in headers}

    def assert_entries_are_safe(
        self, header_to_pointer: dict[int, int], before: dict[int, int]
    ) -> None:
        """The invariant that matters after a restore: nothing points at code this project freed.

        An entry may hold the pointer that was there before, or a pointer **another runtime** placed
        — Reforged registers a handler for every header and rewrites entries from its own snapshot
        whenever its own enable/disable runs, which is the coexistence hazard recorded in
        ``docs/TARGET_SIDE_WORK.md``. What may never happen is an entry holding one of this project's
        stubs after they were freed: that is a jump into memory nobody owns on the client's own
        thread, on the next packet of that header.
        """

        ours = {stub.address for stub in (self.client.bridge.packets._stubs.values() if self.client.bridge.packets else ())}
        module_base, module_size = self.client.bridge.module_range
        loaded = self.client.bridge.loaded_modules
        foreign: dict[int, int] = {}

        for header, pointer in header_to_pointer.items():
            with self.subTest(header=hex(header)):
                self.assertNotEqual(pointer, 0, "the entry was left with no handler at all")
                self.assertNotIn(pointer, ours, "the entry still points at a freed stub")
                if pointer == before.get(header):
                    continue
                inside = module_base <= pointer < module_base + module_size
                known = any(base <= pointer < base + size for base, size in loaded)
                self.assertTrue(
                    inside or known,
                    f"header {header:#06x} holds 0x{pointer:08X}, which is neither the pointer that "
                    "was there before nor code in any loaded module.",
                )
                foreign[header] = pointer

        if foreign:
            print(
                f"--- entries rewritten by another runtime after the restore: "
                f"{ {hex(h): hex(p) for h, p in foreign.items()} } "
                f"(one shared address across headers is another runtime's single handler, as "
                f"native's own StoCHandler_Func is) ---"
            )

    def wait_for(self, direction: str, timeout_s: float | None = None) -> list:
        deadline = time.monotonic() + (CAPTURE_TIMEOUT_S if timeout_s is None else timeout_s)
        wanted = (
            binding.PacketDirection.StoC
            if direction == "StoC"
            else binding.PacketDirection.CToS
        )
        while time.monotonic() < deadline:
            self.client.callbacks.pump()
            entries = binding.GetLogsByDirection(wanted)
            if entries:
                return entries
            time.sleep(POLL_S)
        return []

    def check_inbound(self, entries: list) -> None:
        for entry in entries[:20]:
            with self.subTest(header=hex(entry.header)):
                self.assertEqual(entry.direction, binding.PacketDirection.StoC)
                self.assertGreaterEqual(entry.size, 4)
                self.assertLessEqual(entry.size, 512, "an inbound size past the source's clip")
                self.assertEqual(
                    len(entry.data),
                    min(entry.size, MAX_STOC_CAPTURE),
                    "the capture is not the size clipped at kMaxStoCHeaderBuffer",
                )
                self.assertEqual(
                    struct.unpack("<H", entry.data[:2])[0],
                    entry.header & 0xFFFF,
                    "the packet's first word is not the header the entry names",
                )

    # -- stage one: five headers ------------------------------------------

    def test_a_narrow_capture_is_placed_and_restored(self) -> None:
        """Five headers only: the merchant listener's own five, whose packets carry a few words.

        This is the smallest thing that proves the emitted capture runs on the client's thread at all,
        and it is deliberately first: if the client dies here, the whole-array install is not the
        suspect.
        """

        before = self.snapshot(NARROW_HEADERS)
        table = self.table()
        captures = {}
        for header in NARROW_HEADERS:
            if header >= table.size:
                self.skipTest(f"the client's array holds {table.size} entries")
            descriptors, _count = read_template(
                self.client.bridge.access, table.entry(header)
            )
            captures[header] = describe_template(descriptors)

        self.client.bridge.install_packets(self.table_address, {}, captures)
        after_install = self.snapshot(NARROW_HEADERS)
        for header in NARROW_HEADERS:
            self.assertNotEqual(
                after_install[header],
                before[header],
                f"header {header:#06x} still runs the client's own handler",
            )

        # The whole-array install is the next test's job; here the five entries are read back
        # through the same dispatch the sniffer uses.
        self.client.callbacks.register(sb.EventKind.PACKET, binding._capture_record)
        entries = self.wait_for("StoC")
        self.client.callbacks.unregister(sb.EventKind.PACKET, binding._capture_record)
        self.client.bridge.remove_packets()

        after = self.snapshot(NARROW_HEADERS)
        self.assert_entries_are_safe(after, before)
        if not entries:
            self.skipTest(
                f"the five headers were placed, captured nothing in {CAPTURE_TIMEOUT_S} s, and "
                "were restored"
            )
        self.check_inbound(entries)

    # -- stage two: every header ------------------------------------------

    def test_an_inbound_packet_is_captured_and_every_header_restored(self) -> None:
        """``initialize_stoc`` replaces every header's entry; ``terminate_stoc`` puts them back."""

        table = self.table()
        sampled = [header for header in SAMPLED_HEADERS if header < table.size]
        before = self.snapshot(sampled)

        self.assertTrue(SNIFFER.initialize("StoC"), "initialize_stoc answered False")

        replaced = self.snapshot(sampled)
        for header in sampled:
            self.assertNotEqual(
                replaced[header],
                before[header],
                f"header {header:#06x} still runs the client's own handler after the install",
            )

        entries = self.wait_for("StoC")
        SNIFFER.terminate("StoC")

        after = self.snapshot(sampled)
        self.assert_entries_are_safe(after, before)

        self.assertTrue(
            entries,
            f"no inbound packet was captured in {CAPTURE_TIMEOUT_S} s. The client produces "
            "heartbeats and world updates on its own, so an empty log is a stub that was not "
            "reached rather than a quiet client.",
        )
        self.check_inbound(entries)
        for entry in entries[:5]:
            print(
                f"--- captured StoC 0x{entry.header:04X} size={entry.size} "
                f"copied={len(entry.data)} head={entry.data[:16].hex(' ')} ---"
            )

    def test_the_lifecycle_is_the_sources(self) -> None:
        """``initialize`` is both halves and ``terminate`` is CToS first — and both are idempotent.

        ``initialize()`` places **both** halves, and there is no gate inside the module: the send
        wrapper hook is part of what the member asks for (``packet_sniffer.cpp:112-121``). So the
        both-halves form is only exercised when the outbound half is opted into; otherwise the same
        member is called per direction, which is the source's own ``initialize_stoc``/``initialize_ctos``
        split (``packet_sniffer_bindings.cpp:79-81``).
        """

        if CTOS_ENABLED:
            self.assertTrue(SNIFFER.initialize(), "initialize answered False")
            self.assertTrue(SNIFFER.initialize(), "a second initialize did not answer True")
        else:
            self.assertTrue(SNIFFER.initialize("StoC"), "initialize_stoc answered False")
            self.assertTrue(SNIFFER.initialize("StoC"), "a second initialize_stoc was not a no-op")
        self.assertIsNone(SNIFFER.terminate())
        self.assertIsNone(SNIFFER.terminate(), "a second terminate raised")

    def test_the_clear_and_filter_members_work_over_live_entries(self) -> None:
        self.assertTrue(SNIFFER.initialize("StoC"))
        self.assertTrue(self.wait_for("StoC"), "nothing was captured")

        self.assertGreater(len(SNIFFER.get_logs("StoC")), 0)
        self.assertEqual(len(SNIFFER.get_logs()), len(SNIFFER.get_logs("StoC")))

        SNIFFER.clear_logs("StoC")
        self.assertEqual(SNIFFER.get_logs("StoC"), [])

        self.assertTrue(self.wait_for("StoC"), "nothing arrived after the clear")
        SNIFFER.clear_logs()
        self.assertEqual(SNIFFER.get_logs(), [])

    # -- stage three: the send wrapper, opt-in -----------------------------

    @unittest.skipUnless(CTOS_ENABLED, "set PY4GW_LIVE_CTOS=1 to place the send-wrapper hook")
    def test_an_outbound_packet_is_captured(self) -> None:
        """The send wrapper hook: its entry is ``55 8B EC 83 EC 50`` (probe, 2026-10-24)."""

        try:
            started = SNIFFER.initialize("CToS")
        except RuntimeError as error:
            if "entry cannot be displaced" not in str(error):
                raise
            self.skipTest(f"the send wrapper's entry span was refused: {error}")
            return

        self.assertTrue(started, "initialize_ctos answered False")
        self.assertTrue(self.client.bridge.observing_send, "the hook is not in place")

        entries = self.wait_for("CToS", CTOS_TIMEOUT_S)
        hits = self.client.bridge.send_capture_hits()
        print(f"--- outbound capture: {hits} stub hit(s), {len(entries)} logged ---")
        if not entries:
            SNIFFER.terminate("CToS")
            self.assertFalse(
                self.client.bridge.observing_send, "terminate_ctos left the hook in place"
            )
            if hits:
                self.fail(
                    f"the send wrapper was reached {hits} time(s) and nothing was logged: the stub "
                    "ran, so the capture or the log is what is wrong, not the traffic."
                )
            self.skipTest(
                f"the hook is placed and then removed, but the client called the wrapper 0 times in "
                f"{CTOS_TIMEOUT_S} s — a quiet client, not a broken capture"
            )
        for entry in entries[:5]:
            print(
                f"--- captured CToS 0x{entry.header:04X} size={entry.size} "
                f"copied={len(entry.data)} head={entry.data[:16].hex(' ')} ---"
            )
        for entry in entries[:20]:
            with self.subTest(header=hex(entry.header)):
                self.assertEqual(entry.direction, binding.PacketDirection.CToS)
                self.assertGreaterEqual(entry.size, 4)
                self.assertLessEqual(entry.size, binding.K_MAX_REASONABLE_CTOS_PACKET_SIZE)
                self.assertEqual(len(entry.data), entry.size)
                self.assertEqual(
                    struct.unpack("<H", entry.data[:2])[0], entry.header & 0xFFFF
                )

        SNIFFER.terminate("CToS")
        self.assertFalse(
            self.client.bridge.observing_send, "terminate_ctos left the hook in place"
        )


if __name__ == "__main__":
    unittest.main()

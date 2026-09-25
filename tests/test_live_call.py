"""Live Guild Wars test for the call path: the first thing the client is made to do.

This test goes one step past ``test_live_bridge.py``. That one proves this project
can run *its own* code on the client's thread; this one proves a command can make
the client do something it did not ask for — call one of its own functions.

The call is ``ui::SendUIMessage``, resolved from the pattern catalog the same way
every other address here is, with ``UIMessage::kSendChangeTarget`` and a two-word
packet. That is exactly the call ``agent_methods.cpp:132-135`` makes, and it is
**the only thing in this test that changes any game state**: it targets the
player's own character, which is a thing a player does by clicking, and it is
reversible by clicking elsewhere.

Everything else is a refusal that happens before the client is called at all, and
that is asserted here too, live, because a guard that only refuses in a fake target
has not refused anything.

Run it from an **elevated** shell while Guild Wars is running, and be in a map::

    python -m unittest tests.test_live_call -v

What it proves: the descriptor table resolves to a real client function inside the
module; a command naming that slot reaches it on the game thread and completes; a
slot naming an address outside the module is refused **in the client** without being
called; the completion event comes back; and the client's code is byte-identical
afterwards.

What it does not prove: that the game changed. The player's current target is
``g_current_target_id``, a global Native maintains from a ``kChangeTarget``
UI-message hook, and no readable context holds it — which is why
``Player.GetTargetID`` refuses in this library. Observing an effect needs the same
function hooked rather than called.
"""

from __future__ import annotations

import hashlib
import time
import unittest

import py4gw
from py4gw.game_thread.bridge import Bridge
from py4gw.game_thread.callbacks import Callbacks, EventListener
from py4gw.game_thread.shared_block import (
    DESCRIPTOR_DEPTH,
    CallForm,
    CommandState,
    Descriptor,
    EventKind,
    EventRecord,
    Operation,
)
from py4gw.memory import ProcessMemoryReader
from py4gw.player import Player
from py4gw.scanner import PatternCatalog, RemoteScanner
from py4gw.win32 import Win32
from py4gw.win32.write_access import WriteAccess

#: The function whose thread runs our work, and the functions we call and watch.
HOOK_RESOLVER = "game_thread.leave_game_thread_func"
CALL_RESOLVER = "ui.send_ui_message_func"
CHANGE_TARGET_RESOLVER = "agent.change_target_func"

#: ``UIMessage::kChangeTarget`` (``UI_enums.py:87``): the client's own notice that
#: its target changed. Its packet starts with the manual target id.
CHANGE_TARGET_MESSAGE = 0x10000020

#: What the observing hook displaces at the message sender's entry. Eight bytes
#: and not the ten that also cover the ``jae`` after them, because a relative
#: branch replayed from the trampoline would branch to the wrong place.
UI_DISPLACED = bytes.fromhex("55 8B EC 8B 45 08 83 F8 56")

#: The whole instructions the entry patch replaces, read from this client build
#: before anything is written.
DISPLACED = bytes.fromhex("55 8B EC 81 EC 20 02 00 00")

#: ``ui::UIMessage::kSendChangeTarget`` (``constants/ui.h:186``), whose packet is
#: ``{target_id, auto_target_id}``.
SEND_CHANGE_TARGET = 0x3000000B

#: Which table slot holds the message sender, which holds the target setter, and
#: which holds a deliberate out-of-module address used to ask the payload's guard
#: for an answer.
SLOT_UI_MESSAGE = 0
SLOT_CHANGE_TARGET = 0
SLOT_OUTSIDE = 1
OUTSIDE_ADDRESS = 0x00001000

HIT_TARGET = 2
HIT_TIMEOUT_MS = 5000
COMMAND_TIMEOUT_MS = 5000
TEXT_CHUNK = 0x10000
ACCESS_DENIED = 5


class LiveCallTests(unittest.TestCase):
    """One call, made by the client's own thread, with its guard exercised."""

    pid: int
    target: int
    call_target: int
    agent_id: int
    module_base: int
    module_size: int
    access: WriteAccess
    bridge: Bridge
    hits: int

    # -- setup and teardown ------------------------------------------------

    @classmethod
    def setUpClass(cls) -> None:
        win32 = Win32()
        clients = win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")
        cls.pid = int(clients[0]["pid"])

        if not win32.is_elevated():
            raise unittest.SkipTest(
                "The controller must be elevated: connecting asserts it, and the "
                "write rights are denied without it. Run this suite from an "
                "elevated shell."
            )

        module = win32.get_main_module(cls.pid)
        cls.module_base = int(module["base_address"])
        cls.module_size = int(module["size"])

        cls.target = cls._resolve(win32, cls.pid, HOOK_RESOLVER)
        cls.call_target = cls._resolve(win32, cls.pid, CALL_RESOLVER)

        observed = cls._read_entry(win32, cls.pid, cls.target)
        if observed != DISPLACED:
            raise AssertionError(
                f"pid {cls.pid}: 0x{cls.target:08X} does not hold the entry bytes "
                f"this test declares: expected {DISPLACED.hex(' ')}, observed "
                f"{observed.hex(' ')}. Nothing was written."
            )
        if not cls.module_base <= cls.call_target < cls.module_base + cls.module_size:
            raise AssertionError(
                f"pid {cls.pid}: {CALL_RESOLVER} resolved to 0x{cls.call_target:08X}, "
                f"outside the client module 0x{cls.module_base:08X}.."
                f"0x{cls.module_base + cls.module_size:08X}. Nothing was written."
            )

        cls.text_before = cls._text_digest(win32, cls.pid)

        client = py4gw.connect(clients[0], game_thread=False)  # this test hooks the client itself
        try:
            cls.agent_id = int(Player.GetAgentID())
        finally:
            py4gw.disconnect()
        if not cls.agent_id:
            raise unittest.SkipTest(
                "Log a character into a map before running this test: the packet "
                "this test sends names an agent, and no player agent was readable."
            )

        try:
            cls.access = WriteAccess(cls.pid)
        except OSError as error:
            if getattr(error, "errno", None) == ACCESS_DENIED or error.args[0] == 5:
                raise unittest.SkipTest(
                    f"Windows denied write access to pid {cls.pid} with error 5. "
                    "Run this suite from an elevated shell."
                ) from error
            raise

        cls.bridge = Bridge(cls.access, cls.pid, timeout_ms=COMMAND_TIMEOUT_MS)
        cls.bridge.install(
            cls.target,
            DISPLACED,
            calls={
                SLOT_UI_MESSAGE: Descriptor(
                    target=cls.call_target, form=CallForm.UI_MESSAGE
                ),
                SLOT_OUTSIDE: Descriptor(
                    target=OUTSIDE_ADDRESS, form=CallForm.UI_MESSAGE
                ),
            },
            module_base=cls.module_base,
            module_size=cls.module_size,
        )

        try:
            cls.hits = cls.bridge.wait_for_hits(HIT_TARGET, HIT_TIMEOUT_MS)
        except TimeoutError as error:
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

        win32 = Win32()
        observed = cls._read_entry(win32, cls.pid, cls.target)
        text_after = cls._text_digest(win32, cls.pid)
        table = bridge.call_table_address if bridge is not None else 0
        if access is not None:
            access.close()

        print(
            f"\nleave_game_thread_func     = 0x{cls.target:08X}\n"
            f"ui.send_ui_message_func    = 0x{cls.call_target:08X}\n"
            f"module range               = 0x{cls.module_base:08X} + "
            f"0x{cls.module_size:X}\n"
            f"call table                 = 0x{table:08X}\n"
            f"target agent               = {cls.agent_id}\n"
            f"hook hits                  = {cls.hits}\n"
            f"entry after remove         = {observed.hex(' ')}\n"
            f"code section before        = {cls.text_before[0][:32]}... "
            f"({cls.text_before[1]} bytes)\n"
            f"code section after         = {text_after[0][:32]}... "
            f"({text_after[1]} bytes)"
        )

        if observed != DISPLACED:
            raise AssertionError(
                f"pid {cls.pid}: 0x{cls.target:08X} was left holding "
                f"{observed.hex(' ')}, not its original {DISPLACED.hex(' ')}."
            )
        if text_after != cls.text_before:
            raise AssertionError(
                f"pid {cls.pid}: the code section changed during the run: "
                f"{cls.text_before[0]} before, {text_after[0]} after."
            )

    # -- the guard, live ---------------------------------------------------

    def test_a_slot_outside_the_module_is_refused_in_the_client(self) -> None:
        """The payload's own rule, enforced inside the client, not here.

        The address is written into the table by this process, so nothing stops
        the host from asking; the client-side code is what refuses, and the
        refusal comes back through the queue.
        """

        record = self.bridge.call(SLOT_OUTSIDE, SEND_CHANGE_TARGET, self.agent_id, 0)

        self.assertEqual(record.state, CommandState.FAILED)
        self.assertEqual(record.result, -102)  # RESULT_BAD_TARGET

    def test_a_slot_past_the_table_is_refused_in_the_client(self) -> None:
        record = self.bridge.call(DESCRIPTOR_DEPTH, SEND_CHANGE_TARGET)

        self.assertEqual(record.state, CommandState.FAILED)
        self.assertEqual(record.result, -104)  # RESULT_BAD_DESCRIPTOR

    # -- the call ----------------------------------------------------------

    def test_the_call_reaches_the_client_and_completes(self) -> None:
        """``kSendChangeTarget`` for the player's own character.

        The form's function returns void, so a zero result means "it ran": the
        evidence is the completion itself, on the game thread, inside the client.
        """

        record = self.bridge.call(
            SLOT_UI_MESSAGE, SEND_CHANGE_TARGET, self.agent_id, 0
        )

        self.assertEqual(record.state, CommandState.DONE)
        self.assertEqual(record.result, 0)
        self.assertEqual(record.operation, Operation.CALL)

    def test_the_call_completed_while_the_client_ran_its_own_frame(self) -> None:
        """Nothing is paused to make this work: the hook fires as it always does."""

        before = self.bridge.hits()
        self.bridge.call(SLOT_UI_MESSAGE, SEND_CHANGE_TARGET, self.agent_id, 0)
        self.bridge.wait_for_hits(2, HIT_TIMEOUT_MS)

        self.assertGreater(self.bridge.hits(), before)

    def test_the_completion_event_carries_the_call(self) -> None:
        record = self.bridge.call(
            SLOT_UI_MESSAGE, SEND_CHANGE_TARGET, self.agent_id, 0
        )

        matching = [
            event
            for event in self.bridge.completions()
            if event.sequence == record.sequence
        ]
        self.assertTrue(matching, f"no completion event for {record.sequence}")
        event = matching[0]
        self.assertEqual(event.kind, EventKind.COMMAND_COMPLETE)
        self.assertEqual(event.arg0, Operation.CALL)
        self.assertEqual(event.arg1, CommandState.DONE)

    def test_the_client_is_still_there(self) -> None:
        pids = [int(process["pid"]) for process in py4gw.Win32().find_guild_wars()]
        self.assertIn(self.pid, pids)

    # -- resolution --------------------------------------------------------

    @staticmethod
    def _resolve(win32: Win32, pid: int, resolver: str) -> int:
        """Find one address the way every other read in this project does."""

        module = win32.get_main_module(pid)
        with ProcessMemoryReader(win32, pid) as reader:
            scanner = RemoteScanner(
                reader,
                int(module["base_address"]),
                int(module["size"]),
            )
            scanner.initialize()
            catalog = PatternCatalog.from_directory("offsets")
            result = catalog.resolve(resolver, scanner)
        if not result.ok:
            raise AssertionError(f"pid {pid}: {resolver} did not resolve: {result.message}")
        return int(result.value)

    @staticmethod
    def _read_entry(win32: Win32, pid: int, address: int) -> bytes:
        """Read the entry bytes through a fresh read-only handle."""

        with ProcessMemoryReader(win32, pid) as reader:
            return reader.read(address, len(DISPLACED))

    @staticmethod
    def _text_digest(win32: Win32, pid: int) -> tuple[str, int]:
        """Return a hash of the client's whole code section.

        The hook changes nine bytes of it for as long as it is installed, and the
        call path is not allowed to change any others. Hashing it before and after
        is what turns that into something checked.
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


class LiveObservationTests(unittest.TestCase):
    """The client's own notification, read back — so an effect is *asserted*.

    This is the pair the port needs. The client tells the world when its target
    changes (``UIMessage::kChangeTarget``), Reforged's runtime listens for exactly
    that message and keeps the target id from it, and we can listen too. So the
    test changes the target and then reads the id out of what the client itself
    said, instead of asking a person to watch a ring.
    """

    pid: int
    target: int
    call_target: int
    observe_target: int
    agent_id: int
    access: WriteAccess
    bridge: Bridge
    hits: int

    @classmethod
    def setUpClass(cls) -> None:
        win32 = Win32()
        clients = win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")
        cls.pid = int(clients[0]["pid"])
        if not win32.is_elevated():
            raise unittest.SkipTest(
                "The controller must be elevated: connecting asserts it, and the "
                "write rights are denied without it. Run this suite from an "
                "elevated shell."
            )

        module = win32.get_main_module(cls.pid)
        cls.module_base = int(module["base_address"])
        cls.module_size = int(module["size"])
        cls.target = cls._resolve(win32, cls.pid, HOOK_RESOLVER)
        cls.call_target = cls._resolve(win32, cls.pid, CHANGE_TARGET_RESOLVER)
        cls.observe_target = cls._resolve(win32, cls.pid, CALL_RESOLVER)

        if cls._read_entry(win32, cls.pid, cls.target) != DISPLACED:
            raise AssertionError(
                f"pid {cls.pid}: 0x{cls.target:08X} does not hold the entry bytes "
                "this test declares. Nothing was written."
            )
        # Eight bytes, not the ten that also cover the following ``jae``: a
        # relative branch cannot be replayed at another address, and the
        # trampoline replays these bytes verbatim.
        observed = cls._read_entry_at(win32, cls.pid, cls.observe_target, len(UI_DISPLACED))
        if observed != UI_DISPLACED:
            raise AssertionError(
                f"pid {cls.pid}: 0x{cls.observe_target:08X} holds "
                f"{observed.hex(' ')}, not the {UI_DISPLACED.hex(' ')} this test "
                "declares. Nothing was written."
            )

        cls.text_before = cls._text_digest(win32, cls.pid)
        client = py4gw.connect(clients[0], game_thread=False)  # this test hooks the client itself
        try:
            cls.agent_id = int(Player.GetAgentID())
            cls.other_agent = 0
            snapshot = client.read_agent_array()
            if snapshot is not None:
                for reference in snapshot.all:
                    if reference.is_living and reference.agent_id not in (0, cls.agent_id):
                        cls.other_agent = int(reference.agent_id)
                        break
        finally:
            py4gw.disconnect()
        if not cls.agent_id:
            raise unittest.SkipTest(
                "Log a character into a map before running this test."
            )

        try:
            cls.access = WriteAccess(cls.pid)
        except OSError as error:
            if getattr(error, "errno", None) == ACCESS_DENIED or error.args[0] == 5:
                raise unittest.SkipTest(
                    f"Windows denied write access to pid {cls.pid} with error 5."
                ) from error
            raise

        cls.bridge = Bridge(cls.access, cls.pid, timeout_ms=COMMAND_TIMEOUT_MS)
        cls.bridge.install(
            cls.target,
            DISPLACED,
            calls={
                SLOT_CHANGE_TARGET: Descriptor(
                    target=cls.call_target, form=CallForm.U32_U32
                )
            },
            module_base=cls.module_base,
            module_size=cls.module_size,
            watch=[CHANGE_TARGET_MESSAGE],
            observing=(cls.observe_target, UI_DISPLACED),
        )
        try:
            cls.hits = cls.bridge.wait_for_hits(HIT_TARGET, HIT_TIMEOUT_MS)
        except TimeoutError as error:
            cls.bridge.remove()
            cls.access.close()
            raise unittest.SkipTest(
                f"pid {cls.pid}: the hooks are placed but the game thread did not "
                f"run within {HIT_TIMEOUT_MS} ms. Be in a map. ({error})"
            ) from error

    @classmethod
    def tearDownClass(cls) -> None:
        bridge = getattr(cls, "bridge", None)
        access = getattr(cls, "access", None)
        if bridge is not None and bridge.installed:
            bridge.remove()

        win32 = Win32()
        hook_entry = cls._read_entry(win32, cls.pid, cls.target)
        observe_entry = cls._read_entry_at(
            win32, cls.pid, cls.observe_target, len(UI_DISPLACED)
        )
        text_after = cls._text_digest(win32, cls.pid)
        watch = bridge.watch_address if bridge is not None else 0
        observer = bridge.observer_address if bridge is not None else 0
        if access is not None:
            access.close()

        print(
            f"\nchange_target_func         = 0x{cls.call_target:08X}\n"
            f"ui.send_ui_message_func    = 0x{cls.observe_target:08X}\n"
            f"watch list                 = 0x{watch:08X} "
            f"[kChangeTarget 0x{CHANGE_TARGET_MESSAGE:08X}]\n"
            f"observer code              = 0x{observer:08X}\n"
            f"player agent               = {cls.agent_id}\n"
            f"hook hits                  = {cls.hits}\n"
            f"game-thread entry after    = {hook_entry.hex(' ')}\n"
            f"message entry after        = {observe_entry.hex(' ')}\n"
            f"code section before        = {cls.text_before[0][:32]}...\n"
            f"code section after         = {text_after[0][:32]}..."
        )

        if hook_entry != DISPLACED or observe_entry != UI_DISPLACED:
            raise AssertionError(
                f"pid {cls.pid}: a hooked function was left patched: "
                f"{hook_entry.hex(' ')} and {observe_entry.hex(' ')}."
            )
        if text_after != cls.text_before:
            raise AssertionError(
                f"pid {cls.pid}: the code section changed during the run."
            )

    # -- the effect, asserted ----------------------------------------------

    def change_and_watch(self, agent_id: int) -> int:
        """Change the target and return the id the client reported.

        The client reports a **change**, not a request: asking for the target it
        already has produces no notice at all, which is measured behaviour and
        recorded in ``docs/RESEARCH.md``. The target is a piece of global game
        state, so every call here first asks for the opposite of what it is about
        to ask for, and throws that notice away. Without it the tests would pass
        or fail depending on the order they ran in.
        """

        opposite = 0 if agent_id else self.other_agent
        if opposite != agent_id:
            self.bridge.call(SLOT_CHANGE_TARGET, opposite, 0)
        self.bridge.events()

        record = self.bridge.call(SLOT_CHANGE_TARGET, agent_id, 0)
        self.assertEqual(record.state, CommandState.DONE)

        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            for event in self.bridge.events():
                if (
                    event.kind == EventKind.UI_MESSAGE
                    and event.sequence == CHANGE_TARGET_MESSAGE
                ):
                    return int(event.arg0)
            time.sleep(0.01)
        self.fail(
            f"pid {self.pid}: the client did not report a target change within 2 s "
            f"after {CHANGE_TARGET_RESOLVER}({agent_id}, 0) completed."
        )

    def test_the_client_reports_the_target_it_was_given(self) -> None:
        """Target another agent, and read the id back out of the client's notice.

        Not the player's own agent: setting the target to yourself produced no
        notice at all in this client build, which is recorded in
        ``docs/RESEARCH.md`` rather than asserted, because one run cannot tell
        "the client ignores self-selection" from "it was slower than the wait".
        """

        if not self.other_agent:
            self.skipTest("no other living agent is in range to target")

        reported = self.change_and_watch(self.other_agent)

        self.assertEqual(reported, self.other_agent)

    def test_clearing_the_target_is_reported_as_no_target(self) -> None:
        """Agent id 0 clears the selection, and the client says so (``agent.cpp:119``)."""

        if not self.other_agent:
            self.skipTest("no other living agent is in range to target")

        reported = self.change_and_watch(0)

        self.assertEqual(reported, 0)

    def test_a_registered_handler_runs_when_the_events_are_pumped(self) -> None:
        """The registry over real events: register, cause one, pump, see it fire."""

        if not self.other_agent:
            self.skipTest("no other living agent is in range to target")

        callbacks = Callbacks(self.bridge)
        seen: list[EventRecord] = []
        callbacks.register(EventKind.UI_MESSAGE, seen.append)

        # Clear first, so the change that follows is one the client will report,
        # and pump the notice away through the registry itself.
        self.bridge.call(SLOT_CHANGE_TARGET, 0, 0)
        callbacks.pump()
        seen.clear()

        self.bridge.call(SLOT_CHANGE_TARGET, self.other_agent, 0)
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and not seen:
            callbacks.pump()
            time.sleep(0.01)

        self.assertTrue(seen, "the registered handler never ran")
        changes = [
            record for record in seen if record.sequence == CHANGE_TARGET_MESSAGE
        ]
        self.assertTrue(changes, [record.sequence for record in seen])
        self.assertEqual(int(changes[0].arg0), self.other_agent)

    def test_a_listener_thread_delivers_without_anyone_pumping(self) -> None:
        """The thread reads and dispatches. Nothing in this test calls pump()."""

        if not self.other_agent:
            self.skipTest("no other living agent is in range to target")

        callbacks = Callbacks(self.bridge)
        seen: list[EventRecord] = []
        callbacks.register(EventKind.UI_MESSAGE, seen.append)

        with EventListener(self.bridge, callbacks) as listener:
            self.bridge.call(SLOT_CHANGE_TARGET, 0, 0)
            self.bridge.call(SLOT_CHANGE_TARGET, self.other_agent, 0)

            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                if [
                    record
                    for record in seen
                    if record.sequence == CHANGE_TARGET_MESSAGE
                    and int(record.arg0) == self.other_agent
                ]:
                    break
                time.sleep(0.005)

        matching = [
            record
            for record in seen
            if record.sequence == CHANGE_TARGET_MESSAGE
            and int(record.arg0) == self.other_agent
        ]
        self.assertTrue(
            matching,
            f"the listener delivered nothing for agent {self.other_agent}",
        )
        self.assertGreater(listener.delivered, 0)
        self.assertFalse(listener.running)

    def test_one_watch_entry_records_one_kind_of_message(self) -> None:
        """The client sends a great many messages; only the watched one is kept."""

        self.bridge.events()
        if not self.other_agent:
            self.skipTest("no other living agent is in range to target")
        self.change_and_watch(0)

        sequences = {
            int(event.sequence)
            for event in self.bridge.events()
            if event.kind == EventKind.UI_MESSAGE
        }
        self.assertTrue(sequences <= {CHANGE_TARGET_MESSAGE}, sequences)

    def test_the_client_is_still_there(self) -> None:
        pids = [int(process["pid"]) for process in py4gw.Win32().find_guild_wars()]
        self.assertIn(self.pid, pids)

    # -- resolution --------------------------------------------------------

    @staticmethod
    def _resolve(win32: Win32, pid: int, resolver: str) -> int:
        module = win32.get_main_module(pid)
        with ProcessMemoryReader(win32, pid) as reader:
            scanner = RemoteScanner(
                reader, int(module["base_address"]), int(module["size"])
            )
            scanner.initialize()
            result = PatternCatalog.from_directory("offsets").resolve(resolver, scanner)
        if not result.ok:
            raise AssertionError(f"pid {pid}: {resolver} did not resolve: {result.message}")
        return int(result.value)

    @staticmethod
    def _read_entry(win32: Win32, pid: int, address: int) -> bytes:
        return LiveObservationTests._read_entry_at(
            win32, pid, address, len(DISPLACED)
        )

    @staticmethod
    def _read_entry_at(win32: Win32, pid: int, address: int, size: int) -> bytes:
        with ProcessMemoryReader(win32, pid) as reader:
            return reader.read(address, size)

    @staticmethod
    def _text_digest(win32: Win32, pid: int) -> tuple[str, int]:
        module = win32.get_main_module(pid)
        digest = hashlib.sha256()
        size = 0
        with ProcessMemoryReader(win32, pid) as reader:
            scanner = RemoteScanner(
                reader, int(module["base_address"]), int(module["size"])
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

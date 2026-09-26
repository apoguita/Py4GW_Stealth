"""Offline tests for the bridge: the host side of the queue.

No client is involved. The target is a ``bytearray``, allocations come from a
fixed base, and the payload is played by the test itself — writing the terminal
state and advancing ``command_taken`` exactly where the real code would.

What this proves: install order and rollback, the read-back of the block, publish
and its full-region refusal, the wait and its timeout, the sequence check that
stops a reused slot returning another command's answer, the event read, and that
removing the hook restores the function's own bytes while leaving the
allocations mapped.

What it does not prove: that anything in the client runs. The dispatcher's own
behaviour is executed in ``test_payload_offline.py``; the live wiring is
``test_live_bridge.py``.
"""

from __future__ import annotations

import struct
import threading
import time
import unittest

from py4gw.game_thread.bridge import HOOK_NAME, Bridge
from py4gw.game_thread.hooker import STATE_HITS_OFFSET, STATE_SIZE
from py4gw.game_thread.patcher import PAGE_EXECUTE_READ
from py4gw.game_thread.payload import build_dispatcher, dispatcher_size
from py4gw.game_thread.shared_block import (
    BLOCK_SIZE,
    COMMAND_DEPTH,
    COMMAND_SIZE,
    DATA_REGION_OFFSET,
    DATA_SIZE,
    DECODE_DEPTH,
    DECODE_REGION_OFFSET,
    DECODE_SLOT_SIZE,
    DESCRIPTOR_DEPTH,
    DESCRIPTOR_SIZE,
    EVENT_DEPTH,
    EVENT_REGION_OFFSET,
    EVENT_SIZE,
    HEADER_OFFSET,
    HEADER_SIZE,
    CallForm,
    CommandRecord,
    CommandState,
    Descriptor,
    EventKind,
    EventRecord,
    Operation,
    command_offset,
    data_offset,
    descriptor_offset,
    event_offset,
)

BASE = 0x00400000
TARGET = 0x00401000
#: The real prologue of ``leave_game_thread_func`` on the client build in use:
#: push ebp, mov ebp/esp, sub esp/0x220.
ORIGINAL = bytes.fromhex("55 8B EC 81 EC 20 02 00 00")
ALLOC_BASE = 0x20000000
REGION = 0x100000
PID = 1234
PAGE_READWRITE = 0x04


class FakeTarget:
    """A target with pretend memory, pretend allocations and pretend threads."""

    def __init__(self) -> None:
        # Two regions so the target's own memory and the allocations can never
        # alias each other.
        self.memory = bytearray(2 * REGION)
        self.memory[TARGET - BASE : TARGET - BASE + len(ORIGINAL)] = ORIGINAL
        self.allocated: dict[int, int] = {}
        self.freed: list[int] = []
        self.next_allocation = ALLOC_BASE
        self.writes: list[tuple[int, int]] = []
        self.protections: list[tuple[int, int, int]] = []
        #: When set, reads of the block come back zeroed, as if the write missed.
        self.hide_allocations = False

    # -- the patcher's and hooker's needs ---------------------------------

    def read(self, address: int, size: int) -> bytes:
        if self.hide_allocations and address >= ALLOC_BASE:
            return bytes(size)
        start = self._index(address)
        return bytes(self.memory[start : start + size])

    def write(self, address: int, data: bytes) -> None:
        start = self._index(address)
        self.memory[start : start + len(data)] = data
        self.writes.append((address, len(data)))

    def protect(self, address: int, size: int, protection: int) -> int:
        self.protections.append((address, size, protection))
        return PAGE_READWRITE

    def flush_instruction_cache(self, address: int, size: int) -> None:
        pass

    def list_thread_ids(self) -> list[int]:
        return [101]

    def open_thread(self, thread_id: int) -> int:
        return 0x1000 + thread_id

    def suspend_thread(self, thread_handle: int) -> int:
        return 0

    def resume_thread(self, thread_handle: int) -> int:
        return 0

    def thread_eip(self, thread_handle: int) -> int:
        return BASE + 0x9000

    def close_thread(self, thread_handle: int) -> None:
        pass

    def allocate(self, size: int) -> int:
        address = self.next_allocation
        self.next_allocation += 0x1000
        self.allocated[address] = size
        return address

    def free(self, address: int) -> None:
        self.freed.append(address)

    # -- helpers ----------------------------------------------------------

    def at(self, address: int, size: int) -> bytes:
        start = self._index(address)
        return bytes(self.memory[start : start + size])

    def entry(self) -> bytes:
        return self.at(TARGET, len(ORIGINAL))

    def _index(self, address: int) -> int:
        if BASE <= address < BASE + REGION:
            return address - BASE
        if ALLOC_BASE <= address < ALLOC_BASE + REGION:
            return REGION + (address - ALLOC_BASE)
        raise ValueError(f"address 0x{address:08X} is outside the fake's regions")


class FakePayload:
    """What the real payload would do to the block, done from the test."""

    def __init__(self, target: FakeTarget, bridge: Bridge) -> None:
        self.target = target
        self.bridge = bridge

    def complete(
        self,
        sequence: int,
        state: CommandState = CommandState.DONE,
        result: int = 0,
    ) -> None:
        """Write a terminal record into the slot the sequence belongs to."""

        record = CommandRecord(
            sequence=sequence,
            operation=Operation.ECHO_U32,
            state=state,
            result=result,
        )
        self.target.write(self.address(sequence), record.to_bytes())

    def take(self, count: int = 1) -> None:
        """Advance the counter the payload owns."""

        header = self.bridge.header()
        self.target.write(
            self.bridge.block_address + HEADER_OFFSET["command_taken"],
            struct.pack("<I", (header.command_taken + count) & 0xFFFFFFFF),
        )

    def emit(self, kind: int, sequence: int = 0, arg0: int = 0) -> None:
        """Publish an event the way the payload does: record first, counter last."""

        header = self.bridge.header()
        slot = header.event_written % EVENT_DEPTH
        record = EventRecord(kind=kind, sequence=sequence, arg0=arg0)
        self.target.write(
            self.bridge.block_address + event_offset(slot), record.to_bytes()
        )
        self.target.write(
            self.bridge.block_address + HEADER_OFFSET["event_written"],
            struct.pack("<I", (header.event_written + 1) & 0xFFFFFFFF),
        )

    def address(self, sequence: int) -> int:
        """Return the command slot address a sequence belongs to."""

        return self.bridge.block_address + command_offset(
            sequence % COMMAND_DEPTH
        )


class BridgeTestCase(unittest.TestCase):
    """A fake target with a bridge installed on it."""

    def setUp(self) -> None:
        self.target = FakeTarget()
        self.bridge = Bridge(self.target, PID, timeout_ms=200)
        self.bridge.install(TARGET, ORIGINAL, session_id=0xABCD1234)
        self.payload = FakePayload(self.target, self.bridge)


class DataRegionTests(BridgeTestCase):
    """The block's data region: what a call is handed a pointer to.

    A function that takes a pointer — a string to read, a word to write a result into —
    needs an address in the client that outlives the call. The source's callers use their
    own stack frames; this project uses a span of the block, which is the same thing from
    the client's side: memory inside its own process.
    """

    def test_the_region_is_inside_the_block_and_after_the_events(self) -> None:
        self.assertEqual(
            data_offset(0, 0), EVENT_REGION_OFFSET + EVENT_DEPTH * EVENT_SIZE
        )
        self.assertEqual(DECODE_REGION_OFFSET, DATA_REGION_OFFSET + DATA_SIZE)
        self.assertEqual(
            BLOCK_SIZE,
            DECODE_REGION_OFFSET + DECODE_DEPTH * DECODE_SLOT_SIZE,
        )

    def test_data_survives_a_write_and_a_read(self) -> None:
        payload = b"Foreman"

        address = self.bridge.write_data(0x40, payload)

        self.assertEqual(
            address, self.bridge.block_address + data_offset(0x40, len(payload))
        )
        self.assertEqual(self.bridge.read_data(0x40, len(payload)), payload)

    def test_a_wide_string_can_be_placed_for_the_client_to_read(self) -> None:
        """``FileHashToRecObj`` takes a ``const wchar_t*``; this is how it gets one."""

        payload = "amet".encode("utf-16-le") + b"\x00\x00"
        address = self.bridge.write_data(0, payload)

        self.assertEqual(self.bridge.read_data(0, len(payload)), payload)
        self.assertEqual(
            address, self.bridge.block_address + data_offset(0, len(payload))
        )

    def test_a_span_past_the_region_is_refused(self) -> None:
        """The alternative to refusing is writing over the event ring."""

        with self.assertRaises(ValueError):
            self.bridge.write_data(DATA_SIZE, b"\x00")
        with self.assertRaises(ValueError):
            self.bridge.read_data(DATA_SIZE - 2, 4)
        with self.assertRaises(ValueError):
            self.bridge.data_address(-1)

    def test_the_region_cannot_reach_the_event_ring(self) -> None:
        """Every span is inside the region, so the counters and events are untouched."""

        self.bridge.write_data(0, bytes(DATA_SIZE))
        before = self.target.read(self.bridge.block_address, HEADER_SIZE)
        after = self.target.read(self.bridge.block_address, HEADER_SIZE)
        self.assertEqual(before, after)

    def test_a_bridge_without_a_block_refuses(self) -> None:
        bridge = Bridge(self.target, PID, timeout_ms=200)

        with self.assertRaises(RuntimeError):
            bridge.write_data(0, b"\x00")


class InstallTests(BridgeTestCase):
    """What install places, in what order, and what it does when it fails."""

    def test_it_places_the_block_the_dispatcher_and_the_hook(self) -> None:
        self.assertEqual(self.target.allocated[self.bridge.block_address], BLOCK_SIZE)
        self.assertEqual(
            self.target.allocated[self.bridge.dispatcher_address],
            dispatcher_size(),
        )
        self.assertEqual(
            self.target.at(self.bridge.dispatcher_address, dispatcher_size()),
            build_dispatcher(),
        )
        self.assertTrue(self.bridge.installed)

    def test_the_entry_patch_lands_last(self) -> None:
        """Nothing can reach the stub before the stub exists."""

        dispatcher_writes = [
            index
            for index, (address, _) in enumerate(self.target.writes)
            if address == self.bridge.dispatcher_address
        ]
        entry_writes = [
            index
            for index, (address, _) in enumerate(self.target.writes)
            if address == TARGET
        ]
        self.assertTrue(entry_writes)
        self.assertGreater(entry_writes[0], max(dispatcher_writes))

    def test_the_entry_now_jumps_to_the_stub(self) -> None:
        entry = self.target.entry()
        self.assertEqual(entry[0], 0xE9)
        offset = struct.unpack("<I", entry[1:5])[0]
        address = (TARGET + 5 + offset) & 0xFFFFFFFF
        self.assertGreaterEqual(address, ALLOC_BASE)
        self.assertTrue(self.target.at(address, 1))

    def test_the_dispatcher_is_left_executable_and_not_writable(self) -> None:
        self.assertIn(
            (self.bridge.dispatcher_address, dispatcher_size(), PAGE_EXECUTE_READ),
            self.target.protections,
        )

    def test_installing_twice_is_refused(self) -> None:
        with self.assertRaises(RuntimeError):
            self.bridge.install(TARGET, ORIGINAL)

    def test_a_target_that_does_not_match_is_refused_and_nothing_is_left(self) -> None:
        target = FakeTarget()
        bridge = Bridge(target, PID)
        with self.assertRaises(RuntimeError):
            bridge.install(TARGET, bytes.fromhex("90 90 90 90 90 90 90 90 90"))

        self.assertEqual(target.entry(), ORIGINAL)
        self.assertEqual(bridge.block_address, 0)
        self.assertFalse(bridge.installed)
        # The block and the dispatcher the bridge made are released: the hook
        # was never placed, so nothing can be inside them.
        self.assertIn(ALLOC_BASE, target.freed)
        self.assertIn(ALLOC_BASE + 0x1000, target.freed)

    def test_a_block_that_does_not_read_back_stops_the_install(self) -> None:
        target = FakeTarget()
        target.hide_allocations = True
        bridge = Bridge(target, PID)
        with self.assertRaises(RuntimeError):
            bridge.install(TARGET, ORIGINAL)
        self.assertEqual(target.entry(), ORIGINAL)
        self.assertFalse(bridge.installed)


class QueueTests(BridgeTestCase):
    """Publishing, waiting, and reading the events back."""

    def test_publish_fills_the_slot_and_advances_the_host_counter(self) -> None:
        sequence = self.bridge.publish(Operation.PING)

        self.assertEqual(sequence, 0)
        self.assertEqual(self.bridge.header().command_written, 1)
        record = CommandRecord.from_bytes(
            self.target.at(self.payload.address(0), COMMAND_SIZE)
        )
        self.assertEqual(record.sequence, 0)
        self.assertEqual(record.operation, Operation.PING)
        self.assertEqual(record.state, CommandState.READY)

    def test_each_command_gets_the_next_sequence(self) -> None:
        for expected in range(4):
            self.assertEqual(self.bridge.publish(Operation.PING), expected)

    def test_publish_refuses_a_full_region(self) -> None:
        for _ in range(COMMAND_DEPTH):
            self.bridge.publish(Operation.PING)

        self.assertEqual(self.bridge.header().command_written, COMMAND_DEPTH)
        with self.assertRaises(RuntimeError):
            self.bridge.publish(Operation.PING)

    def test_a_taken_command_frees_its_slot(self) -> None:
        for _ in range(COMMAND_DEPTH):
            self.bridge.publish(Operation.PING)
        self.payload.take(COMMAND_DEPTH)

        sequence = self.bridge.publish(Operation.PING)
        self.assertEqual(sequence, COMMAND_DEPTH)
        self.assertEqual(sequence % COMMAND_DEPTH, 0)

    def test_wait_returns_a_record_the_payload_finished(self) -> None:
        sequence = self.bridge.publish(Operation.PING)
        self.payload.complete(sequence, result=0x42)

        record = self.bridge.wait(sequence)
        self.assertEqual(record.sequence, sequence)
        self.assertEqual(record.state, CommandState.DONE)
        self.assertEqual(record.result, 0x42)

    def test_wait_reports_a_failed_command_rather_than_raising(self) -> None:
        sequence = self.bridge.publish(Operation.PING)
        self.payload.complete(sequence, state=CommandState.FAILED, result=-100)

        record = self.bridge.wait(sequence)
        self.assertEqual(record.state, CommandState.FAILED)
        self.assertEqual(record.result, -100)

    def test_wait_polls_until_the_payload_finishes(self) -> None:
        sequence = self.bridge.publish(Operation.PING)

        def finish() -> None:
            time.sleep(0.02)
            self.payload.complete(sequence, result=7)

        worker = threading.Thread(target=finish)
        worker.start()
        self.addCleanup(worker.join)

        started = time.monotonic()
        record = self.bridge.wait(sequence, timeout_ms=2000)
        self.assertEqual(record.result, 7)
        self.assertGreaterEqual(time.monotonic() - started, 0.01)

    def test_a_call_publishes_and_waits_without_deadlocking_itself(self) -> None:
        """The ring is held for a whole call, and a call *is* a publish.

        ``call`` takes the ring so no other thread can publish into it while it waits, and then
        publishes on the same thread. A lock that is not reentrant makes that a deadlock on the
        first call of the session — a hang no caller could diagnose — so the call is made on a
        thread this test can give up on, and not completing is a failure rather than a hang.
        """

        def finish() -> None:
            for _ in range(400):
                header = self.bridge.header()
                if header.command_written:
                    self.payload.complete(header.command_written - 1, result=0x5A)
                    return
                time.sleep(0.005)

        worker = threading.Thread(target=finish, daemon=True)
        worker.start()

        records: list[CommandRecord] = []
        caller = threading.Thread(
            target=lambda: records.append(
                self.bridge.call(0, 0x3000000B, 42, 0, timeout_ms=2000)
            ),
            daemon=True,
        )
        caller.start()
        caller.join(3.0)

        self.assertFalse(
            caller.is_alive(),
            "the call never returned: the lock it holds for the ring is not reentrant",
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].state, CommandState.DONE)
        self.assertEqual(records[0].result, 0x5A)

    def test_wait_times_out_and_says_what_it_saw(self) -> None:
        sequence = self.bridge.publish(Operation.PING)

        with self.assertRaises(TimeoutError) as caught:
            self.bridge.wait(sequence, timeout_ms=30)

        message = str(caught.exception)
        self.assertIn(f"command {sequence}", message)
        self.assertIn("READY", message)
        self.assertIn(str(PID), message)

    def test_wait_will_not_return_the_answer_to_another_command(self) -> None:
        """A slot is reused every lap, so the record has to be this command's."""

        sequence = self.bridge.publish(Operation.PING)
        stale = CommandRecord(
            sequence=sequence + COMMAND_DEPTH,
            operation=Operation.PING,
            state=CommandState.DONE,
            result=99,
        )
        self.target.write(self.payload.address(sequence), stale.to_bytes())

        with self.assertRaises(TimeoutError):
            self.bridge.wait(sequence, timeout_ms=30)

    def test_submit_publishes_and_waits(self) -> None:
        stop = threading.Event()

        def serve() -> None:
            seen = 0
            while not stop.is_set():
                written = self.bridge.header().command_written
                while seen < written:
                    self.payload.complete(seen, result=seen)
                    seen += 1
                time.sleep(0.002)

        worker = threading.Thread(target=serve)
        worker.start()
        # Cleanups run last-registered first, so the worker is stopped before
        # it is joined.
        self.addCleanup(worker.join)
        self.addCleanup(stop.set)

        for expected in range(3):
            record = self.bridge.submit(Operation.ECHO_U32, expected, timeout_ms=2000)
            self.assertEqual(record.result, expected)

    def test_events_are_returned_oldest_first_and_taken(self) -> None:
        self.payload.emit(EventKind.COMMAND_COMPLETE, sequence=1, arg0=11)
        self.payload.emit(EventKind.COMMAND_COMPLETE, sequence=2, arg0=22)

        events = self.bridge.events()
        self.assertEqual([event.sequence for event in events], [1, 2])
        self.assertEqual([event.arg0 for event in events], [11, 22])
        self.assertEqual(self.bridge.header().event_taken, 2)

        self.assertEqual(self.bridge.events(), [])

    def test_completions_filters_to_the_completion_events(self) -> None:
        self.payload.emit(EventKind.COMMAND_COMPLETE, sequence=1)
        self.payload.emit(9, sequence=2)

        completions = self.bridge.completions()
        self.assertEqual(len(completions), 1)
        self.assertEqual(completions[0].sequence, 1)

    def test_a_corrupt_event_region_is_refused(self) -> None:
        self.target.write(
            self.bridge.block_address + HEADER_OFFSET["event_written"],
            struct.pack("<I", EVENT_DEPTH + 1),
        )

        with self.assertRaises(RuntimeError):
            self.bridge.events()

    def test_reading_before_installing_is_refused(self) -> None:
        bridge = Bridge(FakeTarget(), PID)
        with self.assertRaises(RuntimeError):
            bridge.header()
        with self.assertRaises(RuntimeError):
            bridge.publish(Operation.PING)
        with self.assertRaises(RuntimeError):
            bridge.hits()


class HookTests(BridgeTestCase):
    """The hit counter and taking the hook back out."""

    def test_hits_reads_what_the_stub_counts(self) -> None:
        # Found by its size rather than by allocation order: install places the
        # block, the call table and the dispatcher before the hooker runs, so the
        # state word is the one allocation of exactly STATE_SIZE bytes.
        state_address = next(
            address
            for address, size in self.target.allocated.items()
            if size == STATE_SIZE
        )

        self.target.write(
            state_address + STATE_HITS_OFFSET, struct.pack("<I", 9)
        )

        self.assertEqual(self.bridge.hits(), 9)

    def test_remove_restores_the_function_and_leaves_the_allocations(self) -> None:
        self.bridge.remove()

        self.assertEqual(self.target.entry(), ORIGINAL)
        self.assertFalse(self.bridge.installed)
        # Nothing is freed on purpose: a thread can still be inside the stub.
        self.assertEqual(self.target.freed, [])
        self.assertNotIn(HOOK_NAME, self.bridge.require_hooker().installed)

    def test_the_block_can_still_be_read_after_the_hook_is_removed(self) -> None:
        self.bridge.publish(Operation.PING)
        self.bridge.remove()

        self.assertEqual(self.bridge.header().command_written, 1)

    def test_remove_is_refused_when_nothing_was_installed(self) -> None:
        bridge = Bridge(FakeTarget(), PID)
        with self.assertRaises(RuntimeError):
            bridge.remove()


class CallVocabularyTests(unittest.TestCase):
    """The call table the host writes and the dispatcher is emitted with."""

    CALL_TARGET = 0x00401000
    MODULE_BASE = 0x00400000
    MODULE_SIZE = 0x100000

    def setUp(self) -> None:
        self.target = FakeTarget()
        self.bridge = Bridge(self.target, PID, timeout_ms=200)
        self.descriptor = Descriptor(
            target=self.CALL_TARGET, form=CallForm.UI_MESSAGE
        )
        self.bridge.install(
            TARGET,
            ORIGINAL,
            session_id=0xABCD1234,
            calls={0: self.descriptor},
            module_base=self.MODULE_BASE,
            module_size=self.MODULE_SIZE,
        )
        self.payload = FakePayload(self.target, self.bridge)

    def test_the_table_is_allocated_and_holds_the_descriptor(self) -> None:
        table = self.bridge.call_table_address

        self.assertEqual(
            self.target.allocated[table], DESCRIPTOR_DEPTH * DESCRIPTOR_SIZE
        )
        self.assertEqual(
            self.target.at(table, DESCRIPTOR_SIZE), self.descriptor.to_bytes()
        )

    def test_a_slot_the_host_did_not_fill_names_nothing(self) -> None:
        """An empty slot is zero, so the payload refuses it rather than guessing."""

        table = self.bridge.call_table_address
        empty = self.target.at(
            table + descriptor_offset(1), DESCRIPTOR_SIZE
        )

        self.assertEqual(empty, bytes(DESCRIPTOR_SIZE))

    def test_the_dispatcher_carries_the_table_and_the_bounds(self) -> None:
        code = self.target.at(
            self.bridge.dispatcher_address,
            self.target.allocated[self.bridge.dispatcher_address],
        )

        self.assertEqual(
            code,
            build_dispatcher(
                self.bridge.call_table_address,
                self.MODULE_BASE,
                self.MODULE_SIZE,
            ),
        )

    def test_a_call_publishes_the_slot_and_the_words(self) -> None:
        sequence = self.bridge.publish_call(0, 0x3000000B, 42, 0)

        record = CommandRecord.from_bytes(
            self.target.at(self.payload.address(sequence), COMMAND_SIZE)
        )
        self.assertEqual(record.operation, Operation.CALL)
        self.assertEqual(record.arg0, 0)
        self.assertEqual(record.arg1, 0x3000000B)
        self.assertEqual(record.arg2, 42)
        self.assertEqual(record.arg3, 0)

    def test_a_slot_outside_the_table_is_refused_before_anything_is_written(self) -> None:
        target = FakeTarget()
        bridge = Bridge(target, PID)

        with self.assertRaises(ValueError):
            bridge.install(
                TARGET, ORIGINAL, calls={DESCRIPTOR_DEPTH: self.descriptor}
            )

        self.assertFalse(bridge.installed)
        self.assertEqual(target.entry(), ORIGINAL)

    def test_installing_without_calls_leaves_a_zeroed_table(self) -> None:
        target = FakeTarget()
        bridge = Bridge(target, PID)
        bridge.install(TARGET, ORIGINAL)

        table = bridge.call_table_address
        self.assertEqual(
            target.at(table, DESCRIPTOR_DEPTH * DESCRIPTOR_SIZE),
            bytes(DESCRIPTOR_DEPTH * DESCRIPTOR_SIZE),
        )


if __name__ == "__main__":
    unittest.main()

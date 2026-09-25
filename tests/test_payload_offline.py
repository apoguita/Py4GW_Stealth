"""Offline tests for the payload: the emitted dispatcher, executed.

No client is involved. The emitted bytes are copied into executable memory in
*this* process and called against a fake block, so what is under test is the
behaviour of the exact bytes the installer would write into a client, not a
description of them.

What this proves: the header checks, one command per call, the result of each
operation, the terminal states, the completion event, the ring arithmetic on both
regions, the ``__stdcall`` contract, and that the code runs the same wherever it
is placed.

What it does not prove: that the address it is handed belongs to the client's
block. That is the installer's job and it needs a live client.
"""

from __future__ import annotations

import ctypes
import struct
import unittest
from ctypes import wintypes
from dataclasses import replace
from typing import TypedDict

from py4gw.game_thread.payload import build_dispatcher, build_observer, dispatcher_size
from py4gw.game_thread.shared_block import (
    COMMAND_DEPTH,
    DESCRIPTOR_DEPTH,
    EVENT_DEPTH,
    HEADER_OFFSET,
    HEADER_SIZE,
    MAGIC,
    PING_RESULT,
    RESULT_BAD_DESCRIPTOR,
    RESULT_BAD_TARGET,
    RESULT_NO_TARGET,
    RESULT_UNKNOWN_FORM,
    RESULT_UNKNOWN_OPERATION,
    VERSION,
    WATCH_DEPTH,
    WATCH_SIZE,
    CallForm,
    CommandRecord,
    CommandState,
    Descriptor,
    EventKind,
    Operation,
    descriptor_offset,
    empty_block,
    read_command,
    read_event,
    read_header,
    write_command,
)

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualAlloc.argtypes = (
    ctypes.c_void_p,
    ctypes.c_size_t,
    wintypes.DWORD,
    wintypes.DWORD,
)
kernel32.VirtualFree.restype = wintypes.BOOL
kernel32.VirtualFree.argtypes = (ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD)

MEM_COMMIT_RESERVE = 0x3000
MEM_RELEASE = 0x8000
PAGE_EXECUTE_READWRITE = 0x40

UINT32_MASK = 0xFFFFFFFF

SESSION_ID = 0x51E5510


class EmittedCode:
    """The emitted bytes, placed in memory this process can execute.

    The call goes through ``WINFUNCTYPE``, which is ``__stdcall``: the callee pops
    its own argument. A dispatcher that returned with a plain ``ret`` would leave
    the argument on the stack, which is exactly what the stub relies on not
    happening.
    """

    def __init__(self, code: bytes) -> None:
        self.code = code
        self.address = kernel32.VirtualAlloc(
            None, len(code), MEM_COMMIT_RESERVE, PAGE_EXECUTE_READWRITE
        )
        if not self.address:
            raise OSError(ctypes.get_last_error(), "VirtualAlloc failed.")
        ctypes.memmove(self.address, code, len(code))
        self._call = ctypes.WINFUNCTYPE(None, ctypes.c_void_p)(self.address)

    def __call__(self, block_address: int | None) -> None:
        """Run the emitted code with ``block_address`` as its only argument."""

        self._call(block_address)

    def close(self) -> None:
        """Release the executable allocation."""

        if self.address:
            kernel32.VirtualFree(self.address, 0, MEM_RELEASE)
            self.address = 0


class FakeBlock:
    """A block in this process's memory, with untouched bytes on either side.

    The block is not a buffer of its own: it sits inside a larger one so a write
    that ran off either end would land somewhere the tests can see.
    """

    #: How many untouched bytes are placed before and after the block.
    GUARD = 256

    def __init__(self, session_id: int = SESSION_ID) -> None:
        image = empty_block(session_id)
        self.size = len(image)
        self.raw = bytearray(self.GUARD + self.size + self.GUARD)
        self.raw[self.GUARD : self.GUARD + self.size] = image
        # The buffer must outlive every call: it is what the address points at.
        self.buffer = (ctypes.c_char * len(self.raw)).from_buffer(self.raw)
        self.address = ctypes.addressof(self.buffer) + self.GUARD

    # -- reading and writing the block -------------------------------------

    def read(self) -> bytearray:
        """Return a copy of the block as it is now."""

        return bytearray(self.raw[self.GUARD : self.GUARD + self.size])

    def write(self, image: bytes | bytearray) -> None:
        """Copy a block image back into the shared memory."""

        self.raw[self.GUARD : self.GUARD + self.size] = image

    def header(self):
        """Decode the header as it is now."""

        return read_header(self.read())

    def set_header(self, **changes: int) -> None:
        """Replace header counters, the way the host advances them."""

        image = self.read()
        header = replace(read_header(image), **changes)
        image[:HEADER_SIZE] = header.to_bytes()
        self.write(image)

    def corrupt(self, field: str, value: int) -> None:
        """Write a wrong value into one header field."""

        image = self.read()
        offset = HEADER_OFFSET[field]
        image[offset : offset + 4] = struct.pack("<I", value & UINT32_MASK)
        self.write(image)

    def command(self, slot: int) -> CommandRecord:
        """Decode one command record."""

        return read_command(self.read(), slot)

    def event(self, slot: int):
        """Decode one event record."""

        return read_event(self.read(), slot)

    def publish(self, record: CommandRecord) -> int:
        """Put a record in the next slot and advance the host's counter.

        This is the host's publish step in miniature: the record is filled in
        first and the counter moves afterwards, which is what makes a half-written
        record unreadable. The real queue, with its free-slot check and its
        waiting, is not this.
        """

        image = self.read()
        header = read_header(image)
        slot = header.command_written % COMMAND_DEPTH
        write_command(image, slot, record)
        image[:HEADER_SIZE] = replace(
            header, command_written=header.command_written + 1
        ).to_bytes()
        self.write(image)
        return slot

    def guards_intact(self) -> bool:
        """Return whether the bytes either side of the block are untouched."""

        empty = bytes(self.GUARD)
        return (
            bytes(self.raw[: self.GUARD]) == empty
            and bytes(self.raw[-self.GUARD :]) == empty
        )


class DispatcherTests(unittest.TestCase):
    """The emitted dispatcher, executed against a fake block."""

    dispatcher: EmittedCode

    @classmethod
    def setUpClass(cls) -> None:
        cls.code = build_dispatcher()
        cls.dispatcher = EmittedCode(cls.code)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.dispatcher.close()

    def setUp(self) -> None:
        self.block = FakeBlock()

    # -- the code itself ---------------------------------------------------

    def test_the_code_is_the_same_every_time_it_is_built(self) -> None:
        self.assertEqual(build_dispatcher(), self.code)
        self.assertEqual(dispatcher_size(), len(self.code))
        self.assertGreater(len(self.code), 0)

    def test_the_epilogue_pops_the_argument(self) -> None:
        """``popad`` then ``ret 4``: the stub has nothing to clean up."""

        self.assertEqual(self.code[-4:], bytes((0x61, 0xC2, 0x04, 0x00)))

    # -- what it refuses to touch ------------------------------------------

    def test_a_null_block_is_ignored(self) -> None:
        self.dispatcher(None)

    def test_a_block_that_fails_a_header_check_is_left_alone(self) -> None:
        for field, value in (
            ("magic", MAGIC + 1),
            ("version", VERSION + 1),
            ("header_size", HEADER_SIZE + 4),
            ("command_depth", COMMAND_DEPTH + 1),
            ("event_depth", EVENT_DEPTH + 1),
        ):
            with self.subTest(field=field):
                block = FakeBlock()
                block.publish(CommandRecord(sequence=7, operation=Operation.PING))
                block.corrupt(field, value)

                before = block.read()
                self.dispatcher(block.address)

                self.assertEqual(block.read(), before)

    def test_a_block_with_nothing_pending_is_left_alone(self) -> None:
        before = self.block.read()
        self.dispatcher(self.block.address)
        self.assertEqual(self.block.read(), before)

    def test_a_record_that_is_not_ready_is_left_alone(self) -> None:
        """Only a record the host marked ``READY`` is ours to take."""

        image = self.block.read()
        write_command(
            image,
            0,
            CommandRecord(
                sequence=3,
                operation=Operation.PING,
                state=CommandState.DONE,
                result=1234,
            ),
        )
        self.block.write(image)
        self.block.set_header(command_written=1)

        self.dispatcher(self.block.address)

        self.assertEqual(self.block.header().command_taken, 0)
        self.assertEqual(self.block.command(0).result, 1234)
        self.assertEqual(self.block.header().event_written, 0)

    # -- what it runs ------------------------------------------------------

    def test_a_nop_completes_with_no_result(self) -> None:
        self.block.publish(CommandRecord(sequence=1, operation=Operation.NOP))

        self.dispatcher(self.block.address)

        record = self.block.command(0)
        self.assertEqual(record.state, CommandState.DONE)
        self.assertEqual(record.result, 0)

    def test_ping_returns_its_constant(self) -> None:
        self.block.publish(CommandRecord(sequence=1, operation=Operation.PING))

        self.dispatcher(self.block.address)

        record = self.block.command(0)
        self.assertEqual(record.state, CommandState.DONE)
        self.assertEqual(record.result, PING_RESULT)

    def test_add_reads_both_arguments(self) -> None:
        for left, right, expected in (
            (7, 35, 42),
            (0, 0, 0),
            (UINT32_MASK, 2, 1),
        ):
            with self.subTest(left=left, right=right):
                block = FakeBlock()
                block.publish(
                    CommandRecord(
                        sequence=1,
                        operation=Operation.ADD_U32,
                        arg0=left,
                        arg1=right,
                    )
                )

                self.dispatcher(block.address)

                record = block.command(0)
                self.assertEqual(record.state, CommandState.DONE)
                self.assertEqual(record.result, expected)

    def test_echo_returns_its_first_argument(self) -> None:
        self.block.publish(
            CommandRecord(sequence=1, operation=Operation.ECHO_U32, arg0=42)
        )

        self.dispatcher(self.block.address)

        record = self.block.command(0)
        self.assertEqual(record.state, CommandState.DONE)
        self.assertEqual(record.result, 42)

    def test_an_operation_the_payload_lacks_fails(self) -> None:
        """Including the call-based ones, which wait for the call vocabulary."""

        for operation in (4, 99, UINT32_MASK):
            with self.subTest(operation=operation):
                block = FakeBlock()
                block.publish(CommandRecord(sequence=1, operation=operation))

                self.dispatcher(block.address)

                record = block.command(0)
                self.assertEqual(record.state, CommandState.FAILED)
                self.assertEqual(record.result, RESULT_UNKNOWN_OPERATION)
                self.assertEqual(block.header().command_taken, 1)

    # -- one command per call ----------------------------------------------

    def test_one_command_is_taken_per_call(self) -> None:
        self.block.publish(
            CommandRecord(sequence=1, operation=Operation.ECHO_U32, arg0=11)
        )
        self.block.publish(
            CommandRecord(sequence=2, operation=Operation.ECHO_U32, arg0=22)
        )

        self.dispatcher(self.block.address)
        self.assertEqual(self.block.header().command_taken, 1)
        self.assertEqual(self.block.command(0).result, 11)
        self.assertEqual(self.block.command(1).state, CommandState.READY)

        self.dispatcher(self.block.address)
        self.assertEqual(self.block.header().command_taken, 2)
        self.assertEqual(self.block.command(1).result, 22)

    def test_commands_are_taken_in_the_order_they_were_published(self) -> None:
        for index in range(COMMAND_DEPTH):
            self.block.publish(
                CommandRecord(
                    sequence=index, operation=Operation.ECHO_U32, arg0=index
                )
            )

        for index in range(COMMAND_DEPTH):
            self.dispatcher(self.block.address)
            record = self.block.command(index % COMMAND_DEPTH)
            self.assertEqual(record.sequence, index)
            self.assertEqual(record.result, index)

        self.assertEqual(self.block.header().command_taken, COMMAND_DEPTH)

    def test_the_command_ring_wraps(self) -> None:
        """A counter is a sequence number, and its low bits are the slot."""

        block = self.block
        block.set_header(command_written=COMMAND_DEPTH - 1, command_taken=COMMAND_DEPTH - 1)

        last = block.publish(
            CommandRecord(sequence=15, operation=Operation.ECHO_U32, arg0=15)
        )
        self.assertEqual(last, COMMAND_DEPTH - 1)
        self.dispatcher(block.address)
        self.assertEqual(block.command(COMMAND_DEPTH - 1).result, 15)

        first = block.publish(
            CommandRecord(sequence=16, operation=Operation.ECHO_U32, arg0=16)
        )
        self.assertEqual(first, 0)
        self.dispatcher(block.address)
        self.assertEqual(block.command(0).result, 16)
        self.assertEqual(block.header().command_taken, COMMAND_DEPTH + 1)

    # -- the completion event ----------------------------------------------

    def test_the_completion_event_carries_the_command(self) -> None:
        self.block.publish(CommandRecord(sequence=0x1234, operation=Operation.PING))

        self.dispatcher(self.block.address)

        event = self.block.event(0)
        self.assertEqual(event.kind, EventKind.COMMAND_COMPLETE)
        self.assertEqual(event.sequence, 0x1234)
        self.assertEqual(event.arg0, Operation.PING)
        self.assertEqual(event.arg1, CommandState.DONE)
        # The event's argument is unsigned; the command's result is signed. Both
        # carry the same 32 bits.
        self.assertEqual(event.arg2, PING_RESULT & UINT32_MASK)
        self.assertEqual(event.arg3, 0)
        self.assertEqual(event.tick, 0)
        self.assertEqual(self.block.header().event_written, 1)

    def test_a_failed_command_is_reported_as_failed(self) -> None:
        self.block.publish(CommandRecord(sequence=9, operation=99))

        self.dispatcher(self.block.address)

        event = self.block.event(0)
        self.assertEqual(event.sequence, 9)
        self.assertEqual(event.arg0, 99)
        self.assertEqual(event.arg1, CommandState.FAILED)
        self.assertEqual(event.arg2, RESULT_UNKNOWN_OPERATION & UINT32_MASK)

    def test_the_event_ring_wraps(self) -> None:
        block = self.block
        block.set_header(event_written=EVENT_DEPTH - 1, event_taken=EVENT_DEPTH - 1)

        block.publish(CommandRecord(sequence=1, operation=Operation.PING))
        self.dispatcher(block.address)
        self.assertEqual(block.event(EVENT_DEPTH - 1).kind, EventKind.COMMAND_COMPLETE)
        self.assertEqual(block.header().event_written, EVENT_DEPTH)

        block.publish(CommandRecord(sequence=2, operation=Operation.PING))
        self.dispatcher(block.address)
        self.assertEqual(block.event(0).sequence, 2)
        self.assertEqual(block.header().event_written, EVENT_DEPTH + 1)

    def test_a_full_event_region_does_not_stop_the_command(self) -> None:
        """The record is the answer; the event is a notification."""

        self.block.set_header(event_written=EVENT_DEPTH, event_taken=0)
        self.block.publish(CommandRecord(sequence=1, operation=Operation.PING))

        self.dispatcher(self.block.address)

        record = self.block.command(0)
        self.assertEqual(record.state, CommandState.DONE)
        self.assertEqual(record.result, PING_RESULT)
        self.assertEqual(self.block.header().command_taken, 1)
        self.assertEqual(self.block.header().event_written, EVENT_DEPTH)

    # -- what it is allowed to touch ---------------------------------------

    def test_nothing_outside_the_block_is_written(self) -> None:
        self.block.publish(CommandRecord(sequence=1, operation=Operation.PING))

        self.dispatcher(self.block.address)

        self.assertEqual(self.block.command(0).state, CommandState.DONE)
        self.assertTrue(self.block.guards_intact())

    def test_the_code_runs_the_same_from_any_address(self) -> None:
        """Nothing in it is an absolute address, so it needs no relocation."""

        first = EmittedCode(self.code)
        second = EmittedCode(self.code)
        self.addCleanup(first.close)
        self.addCleanup(second.close)
        self.assertNotEqual(first.address, second.address)

        for dispatcher in (first, second):
            block = FakeBlock()
            block.publish(
                CommandRecord(
                    sequence=5,
                    operation=Operation.ADD_U32,
                    arg0=40,
                    arg1=2,
                )
            )
            dispatcher(block.address)
            self.assertEqual(block.command(0).result, 42)

    def test_many_calls_leave_the_stack_where_they_found_it(self) -> None:
        """A callee that did not pop its argument would walk the stack away."""

        calls = 200
        for index in range(calls):
            self.block.publish(
                CommandRecord(
                    sequence=index, operation=Operation.ECHO_U32, arg0=index
                )
            )
            self.dispatcher(self.block.address)

        self.assertEqual(self.block.header().command_taken, calls)
        self.assertEqual(
            self.block.command((calls - 1) % COMMAND_DEPTH).result, calls - 1
        )


class WitnessRecord(TypedDict):
    """What the witness target recorded, as plain Python data."""

    message: int
    wparam: int
    lparam: int
    words: list[int]


class WitnessBuffer:
    """A buffer with a real address, plus the target code that writes into it.

    The witness is the fake callee the CALL path talks to. It records what it was
    handed — the three arguments and the first four words behind ``wparam`` — and
    a canary, so a test can tell "called with this" from "never called".
    """

    #: message, wparam, lparam, four packed words, canary.
    SIZE = 32
    CANARY = 0x00C0FFEE
    CANARY_OFFSET = 28

    def __init__(self, size: int = SIZE) -> None:
        self.raw = bytearray(size)
        self.buffer = (ctypes.c_char * size).from_buffer(self.raw)
        self.address = ctypes.addressof(self.buffer)

    def code(self, address: int) -> bytes:
        """Emit ``void __cdecl(u32 message, void* wparam, void* lparam)``.

        ``mov [absolute], eax`` (``A3``) keeps the emitter to a few forms, and a
        plain ``ret`` is the cdecl return: the caller releases the arguments, and
        the dispatcher does exactly that.
        """

        body = bytearray()
        for esp_offset, store_offset in ((4, 0), (8, 4), (12, 8)):
            # mov eax, [esp+esp_offset] ; mov [address+store_offset], eax
            body += bytes((0x8B, 0x44, 0x24, esp_offset))
            body += bytes((0xA3,)) + struct.pack("<I", address + store_offset)
        body += bytes((0x8B, 0x54, 0x24, 0x08))  # mov edx, [esp+8]  (wparam)
        for word in range(4):
            displacement = word * 4
            if displacement:
                body += bytes((0x8B, 0x42, displacement))  # mov eax, [edx+disp]
            else:
                body += bytes((0x8B, 0x02))  # mov eax, [edx]
            body += bytes((0xA3,)) + struct.pack("<I", address + 12 + displacement)
        body += bytes((0xC7, 0x05)) + struct.pack(
            "<II", address + self.CANARY_OFFSET, self.CANARY
        )
        body.append(0xC3)
        return bytes(body)

    def code_two_words(self, address: int) -> bytes:
        """Emit ``void __cdecl(u32, u32)``: record both words, then return.

        The order matters and is the whole point: a two-argument call that pushes
        its words the wrong way round still returns, and only a witness tells the
        difference between ``f(7, 9)`` and ``f(9, 7)``.
        """

        body = bytearray()
        for esp_offset, store_offset in ((4, 0), (8, 4)):
            body += bytes((0x8B, 0x44, 0x24, esp_offset))
            body += bytes((0xA3,)) + struct.pack("<I", address + store_offset)
        body += bytes((0xC7, 0x05)) + struct.pack(
            "<II", address + self.CANARY_OFFSET, self.CANARY
        )
        body.append(0xC3)
        return bytes(body)

    def write(self, offset: int, data: bytes) -> None:
        """Put bytes in the buffer, for a test that sets up a table."""

        self.raw[offset : offset + len(data)] = data

    def write_descriptor(self, slot: int, descriptor: Descriptor) -> None:
        """Put one call descriptor in its slot. Slots are not byte offsets."""

        self.write(descriptor_offset(slot), descriptor.to_bytes())

    def write_raw_descriptor(self, slot: int, target: int, form: int) -> None:
        """Write an entry the record itself would refuse.

        That is the only way to ask what the payload does with a form it does not
        know: the descriptor record rejects one before it could be written.
        """

        self.write(descriptor_offset(slot), struct.pack("<II", target, form))

    def clear(self) -> None:
        """Forget everything recorded. The address does not change."""

        self.raw[:] = bytes(len(self.raw))

    def called(self) -> bool:
        """Return whether the target was reached."""

        return (
            int.from_bytes(
                self.raw[self.CANARY_OFFSET : self.CANARY_OFFSET + 4], "little"
            )
            == self.CANARY
        )

    def snapshot(self) -> WitnessRecord:
        """Return what the target recorded."""

        def word(offset: int) -> int:
            return int.from_bytes(self.raw[offset : offset + 4], "little")

        return {
            "message": word(0),
            "wparam": word(4),
            "lparam": word(8),
            "words": [word(12 + index * 4) for index in range(4)],
        }


class CallTests(unittest.TestCase):
    """The CALL path, executed against a target function this test emits.

    The target is machine code too, and it does one thing: write down what it was
    called with. That turns "the form passes the arguments it says it does" from
    a claim about emitted bytes into something the test observes.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.witness = WitnessBuffer()
        cls.target = EmittedCode(cls.witness.code(cls.witness.address))
        cls.two_word_witness = WitnessBuffer()
        cls.two_word_target = EmittedCode(
            cls.two_word_witness.code_two_words(cls.two_word_witness.address)
        )
        # The table is allocated once, because the dispatcher has its address
        # emitted into it. Its contents are cleared for each test.
        cls.table = WitnessBuffer(DESCRIPTOR_DEPTH * 8)
        # Both witnesses stand in for client functions, so the module range the
        # dispatcher enforces is declared to contain both.
        low = min(cls.target.address, cls.two_word_target.address) & ~0xFFFF
        high = max(cls.target.address, cls.two_word_target.address) + 0x10000
        cls.module_base = low
        cls.module_size = high - low
        cls.code = build_dispatcher(
            call_table_address=cls.table.address,
            module_base=cls.module_base,
            module_size=cls.module_size,
        )
        cls.dispatcher = EmittedCode(cls.code)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.dispatcher.close()
        cls.target.close()
        cls.two_word_target.close()

    def setUp(self) -> None:
        self.block = FakeBlock()
        self.witness.clear()
        self.two_word_witness.clear()
        self.table.clear()
        self.table.write_descriptor(
            0, Descriptor(target=self.target.address, form=CallForm.UI_MESSAGE)
        )
        self.table.write_descriptor(
            4,
            Descriptor(target=self.two_word_target.address, form=CallForm.U32_U32),
        )

    def call(self, slot: int, message: int, word0: int = 0, word1: int = 0):
        """Publish one CALL command and run the dispatcher over it."""

        self.block.publish(
            CommandRecord(
                sequence=1,
                operation=Operation.CALL,
                arg0=slot,
                arg1=message,
                arg2=word0,
                arg3=word1,
            )
        )
        self.dispatcher(self.block.address)
        return self.block.command(0)

    # -- the call itself ---------------------------------------------------

    def test_the_call_reaches_the_target(self) -> None:
        self.call(0, message=0x3000000B, word0=42, word1=0)

        self.assertTrue(self.witness.called())

    def test_the_form_passes_the_arguments_the_contract_defines(self) -> None:
        self.call(0, message=0x3000000B, word0=1234, word1=0)
        seen = self.witness.snapshot()

        self.assertEqual(seen["message"], 0x3000000B)
        self.assertNotEqual(seen["wparam"], 0)
        self.assertEqual(seen["lparam"], 0, "lparam must be null")
        self.assertEqual(seen["words"][0], 1234)
        self.assertEqual(seen["words"][1], 0)
        # The payload is sixteen zeroed words: the client reads fields the
        # command never set, so the ones it does not set have to be zero.
        self.assertEqual(seen["words"][2:], [0, 0])

    def test_a_completed_call_reports_no_value(self) -> None:
        """The form's function returns void, so a zero result means "it ran"."""

        record = self.call(0, message=0x1, word0=1, word1=2)

        self.assertEqual(record.state, CommandState.DONE)
        self.assertEqual(record.result, 0)

    def test_each_call_gets_its_own_zeroed_payload(self) -> None:
        self.call(0, message=0x1, word0=7, word1=8)
        first = self.witness.snapshot()["words"]

        self.witness.clear()
        self.call(0, message=0x2, word0=9, word1=0)
        second = self.witness.snapshot()["words"]

        self.assertEqual(first[:2], [7, 8])
        self.assertEqual(second[:2], [9, 0])

    # -- what it refuses ---------------------------------------------------

    def test_a_slot_past_the_end_of_the_table_is_refused(self) -> None:
        record = self.call(DESCRIPTOR_DEPTH, message=0x1)

        self.assertEqual(record.state, CommandState.FAILED)
        self.assertEqual(record.result, RESULT_BAD_DESCRIPTOR)
        self.assertFalse(self.witness.called())

    def test_a_slot_that_names_no_function_is_refused(self) -> None:
        self.table.write_descriptor(1, Descriptor(target=0))

        record = self.call(1, message=0x1)

        self.assertEqual(record.state, CommandState.FAILED)
        self.assertEqual(record.result, RESULT_NO_TARGET)
        self.assertFalse(self.witness.called())

    # -- the two-word form -------------------------------------------------

    def test_two_words_arrive_in_the_order_the_form_says(self) -> None:
        """``f(7, 9)`` and ``f(9, 7)`` both return; only the target tells them apart."""

        self.call(4, message=7, word0=9)
        seen = self.two_word_witness.snapshot()

        self.assertEqual(seen["message"], 7)
        self.assertEqual(seen["wparam"], 9)

    def test_a_two_word_call_completes(self) -> None:
        record = self.call(4, message=0, word0=0)

        self.assertEqual(record.state, CommandState.DONE)
        self.assertEqual(record.result, 0)
        self.assertTrue(self.two_word_witness.called())

    def test_a_slot_outside_the_module_is_refused(self) -> None:
        """The rule the call path holds on its own, whatever the host resolved."""

        outside = self.module_base - 0x1000
        self.table.write_descriptor(2, Descriptor(target=outside, form=CallForm.UI_MESSAGE))

        record = self.call(2, message=0x1)

        self.assertEqual(record.state, CommandState.FAILED)
        self.assertEqual(record.result, RESULT_BAD_TARGET)
        self.assertFalse(self.witness.called())

    def test_a_form_the_payload_does_not_know_is_refused(self) -> None:
        # Written straight into the table: the record refuses an unknown form,
        # which is right, and this is about what the payload does with one.
        self.table.write_raw_descriptor(3, self.target.address, 99)

        record = self.call(3, message=0x1)

        self.assertEqual(record.state, CommandState.FAILED)
        self.assertEqual(record.result, RESULT_UNKNOWN_FORM)
        self.assertFalse(self.witness.called())

    def test_a_dispatcher_without_a_table_refuses_every_call(self) -> None:
        dispatcher = EmittedCode(build_dispatcher())
        self.addCleanup(dispatcher.close)

        self.block.publish(
            CommandRecord(sequence=1, operation=Operation.CALL, arg1=0x1)
        )
        dispatcher(self.block.address)

        record = self.block.command(0)
        self.assertEqual(record.state, CommandState.FAILED)
        self.assertEqual(record.result, RESULT_NO_TARGET)
        self.assertFalse(self.witness.called())


class ObserverTests(unittest.TestCase):
    """The observer: a client call this project did not make, recorded as an event.

    It is called here exactly as the forwarding stub calls it —
    ``(block, message_id, wparam)`` — with a message this test chose and a packet
    in this test's memory, and what it writes into the event region is the answer.
    """

    MESSAGE = 0x1000000B

    @classmethod
    def setUpClass(cls) -> None:
        cls.watch = WitnessBuffer(WATCH_DEPTH * WATCH_SIZE)
        cls.packet = WitnessBuffer(64)
        cls.code = build_observer(cls.watch.address, WATCH_DEPTH)
        cls.observer = EmittedCode(cls.code)
        cls.observer_call = ctypes.WINFUNCTYPE(
            None, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p
        )(cls.observer.address)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.observer.close()

    def setUp(self) -> None:
        self.block = FakeBlock()
        self.watch.clear()
        self.packet.clear()
        self.watch.write(0, struct.pack("<I", self.MESSAGE))

    def observe(self, message: int, packet: int | None) -> None:
        self.observer_call(self.block.address, message, packet)

    def events(self) -> list:
        header = self.block.header()
        return [self.block.event(slot) for slot in range(header.event_written)]

    def events_written(self) -> int:
        """Read the counter raw, for tests that corrupt the header on purpose."""

        image = self.block.read()
        offset = HEADER_OFFSET["event_written"]
        return int.from_bytes(image[offset : offset + 4], "little")

    # -- what it records ---------------------------------------------------

    def test_a_watched_message_becomes_an_event(self) -> None:
        self.packet.write(0, struct.pack("<4I", 0xAA, 0xBB, 0xCC, 0xDD))

        self.observe(self.MESSAGE, self.packet.address)

        events = self.events()
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.kind, EventKind.UI_MESSAGE)
        self.assertEqual(event.sequence, self.MESSAGE)
        self.assertEqual(
            [event.arg0, event.arg1, event.arg2, event.arg3],
            [0xAA, 0xBB, 0xCC, 0xDD],
        )
        self.assertEqual(self.block.header().event_written, 1)

    def test_the_client_is_not_touched_apart_from_the_event(self) -> None:
        self.observe(self.MESSAGE, self.packet.address)

        self.assertTrue(self.block.guards_intact())
        # Nothing was queued, taken or completed: observation is not a command.
        header = self.block.header()
        self.assertEqual(header.command_written, 0)
        self.assertEqual(header.command_taken, 0)

    def test_the_target_id_of_a_change_target_message_is_the_first_word(self) -> None:
        """``ChangeTargetUIMsg``: manual target at ``wparam+0`` (``ui.h:78-85``)."""

        self.packet.write(0, struct.pack("<4I", 38, 0, 7, 0))

        self.observe(self.MESSAGE, self.packet.address)

        self.assertEqual(self.events()[0].arg0, 38)

    # -- what it ignores ---------------------------------------------------

    def test_a_message_that_is_not_watched_is_ignored(self) -> None:
        self.observe(self.MESSAGE + 1, self.packet.address)

        self.assertEqual(self.events(), [])

    def test_a_null_packet_is_not_dereferenced(self) -> None:
        self.observe(self.MESSAGE, None)

        self.assertEqual(self.events(), [])

    def test_a_block_that_is_not_ours_is_ignored(self) -> None:
        self.block.corrupt("magic", MAGIC + 1)

        self.observe(self.MESSAGE, self.packet.address)

        self.assertEqual(self.events_written(), 0)

    def test_a_full_event_region_drops_the_event_without_lying(self) -> None:
        self.block.set_header(event_written=EVENT_DEPTH, event_taken=0)

        self.observe(self.MESSAGE, self.packet.address)

        self.assertEqual(self.events_written(), EVENT_DEPTH)

    def test_an_observer_without_a_watch_list_records_nothing(self) -> None:
        observer = EmittedCode(build_observer(0))
        self.addCleanup(observer.close)
        call = ctypes.WINFUNCTYPE(
            None, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p
        )(observer.address)

        call(self.block.address, self.MESSAGE, self.packet.address)

        self.assertEqual(self.events(), [])


if __name__ == "__main__":
    unittest.main()

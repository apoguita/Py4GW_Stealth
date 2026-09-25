"""Offline tests for the shared block: layout, records and queue arithmetic.

No client is involved and none is needed. The block is an ordinary ``bytearray``
here, so everything except the reads and writes into the real process can be
exercised, including the rejections.

The two properties worth guarding hardest are the ones the design rests on:

* a producer fills the record and only then advances its counter, so a consumer
  reading below that counter can never see a half-written record;
* each counter has exactly one writer, so nothing needs a lock.
"""

from __future__ import annotations

import struct
import unittest

from py4gw.game_thread import shared_block as block
from py4gw.game_thread.shared_block import (
    BLOCK_SIZE,
    COMMAND_DEPTH,
    COMMAND_SIZE,
    EVENT_DEPTH,
    EVENT_SIZE,
    MAGIC,
    VERSION,
    BlockHeader,
    CommandRecord,
    CommandState,
    EventRecord,
    command_offset,
    empty_block,
    event_offset,
    free_slots,
    pending,
    read_command,
    read_event,
    read_header,
    write_command,
    write_event,
)

SESSION = 0x1234ABCD


class LayoutTests(unittest.TestCase):
    """Pin the layout, because the payload's machine code is emitted against it."""

    def test_sizes_are_what_the_payload_expects(self) -> None:
        self.assertEqual(block.HEADER_SIZE, 64)
        self.assertEqual(COMMAND_SIZE, 32)
        self.assertEqual(EVENT_SIZE, 32)
        self.assertEqual(block.COMMAND_REGION_OFFSET, 64)
        self.assertEqual(block.EVENT_REGION_OFFSET, 64 + 16 * 32)
        self.assertEqual(BLOCK_SIZE, 64 + 16 * 32 + 64 * 32)

    def test_records_have_no_padding(self) -> None:
        """Every field is four bytes, so the struct sizes are the field sums."""

        self.assertEqual(len(CommandRecord(sequence=1, operation=2).to_bytes()), 32)
        self.assertEqual(len(EventRecord(kind=1).to_bytes()), 32)
        self.assertEqual(len(BlockHeader(session_id=1).to_bytes()), 64)

    def test_offsets_stay_inside_their_region(self) -> None:
        self.assertEqual(command_offset(0), block.COMMAND_REGION_OFFSET)
        self.assertEqual(
            command_offset(COMMAND_DEPTH - 1) + COMMAND_SIZE,
            block.EVENT_REGION_OFFSET,
        )
        self.assertEqual(event_offset(0), block.EVENT_REGION_OFFSET)
        self.assertEqual(event_offset(EVENT_DEPTH - 1) + EVENT_SIZE, BLOCK_SIZE)

    def test_slot_out_of_range_is_rejected(self) -> None:
        for bad in (-1, COMMAND_DEPTH):
            with self.subTest(slot=bad):
                with self.assertRaises(ValueError):
                    command_offset(bad)
        for bad in (-1, EVENT_DEPTH):
            with self.subTest(slot=bad):
                with self.assertRaises(ValueError):
                    event_offset(bad)

    def test_field_offsets_match_the_records(self) -> None:
        """The payload addresses these words directly, so they have to be right.

        Each field is given a value no other field has, and the offset map is
        checked against where that value actually lands in the packed bytes.
        """

        def packed_at(offsets, image, value):
            return [
                name
                for name, offset in offsets.items()
                if image[offset : offset + 4] == value.to_bytes(4, "little")
            ]

        header = BlockHeader(
            session_id=0x11111111,
            command_written=0x22222222,
            command_taken=0x2222221D,
            event_written=0x44444444,
            event_taken=0x4444443D,
        ).to_bytes()
        for name, value in (
            ("session_id", 0x11111111),
            ("command_written", 0x22222222),
            ("command_taken", 0x2222221D),
            ("event_written", 0x44444444),
            ("event_taken", 0x4444443D),
        ):
            with self.subTest(field=name):
                self.assertEqual(packed_at(block.HEADER_OFFSET, header, value), [name])

        command = CommandRecord(
            sequence=0x66666666,
            operation=0x77777777,
            arg0=0x88888888,
            arg1=0x99999999,
            arg2=0xAAAAAAAA,
            arg3=0xBBBBBBBB,
        ).to_bytes()
        for name, value in (
            ("sequence", 0x66666666),
            ("operation", 0x77777777),
            ("arg0", 0x88888888),
            ("arg1", 0x99999999),
            ("arg2", 0xAAAAAAAA),
            ("arg3", 0xBBBBBBBB),
        ):
            with self.subTest(field=name):
                self.assertEqual(packed_at(block.COMMAND_OFFSET, command, value), [name])

        event = EventRecord(
            kind=0xCCCCCCCC,
            sequence=0xDDDDDDDD,
            arg0=0xEEEEEEEE,
            arg1=0x01010101,
            arg2=0x02020202,
            arg3=0x03030303,
            tick=0x04040404,
        ).to_bytes()
        for name, value in (
            ("kind", 0xCCCCCCCC),
            ("sequence", 0xDDDDDDDD),
            ("arg0", 0xEEEEEEEE),
            ("arg1", 0x01010101),
            ("arg2", 0x02020202),
            ("arg3", 0x03030303),
            ("tick", 0x04040404),
        ):
            with self.subTest(field=name):
                self.assertEqual(packed_at(block.EVENT_OFFSET, event, value), [name])

    def test_the_state_field_sits_where_the_map_says(self) -> None:
        """The two fields the payload reads and writes by hand, pinned exactly."""

        image = CommandRecord(
            sequence=1,
            operation=2,
            state=CommandState.DONE,
            result=-100,
        ).to_bytes()
        state_offset = block.COMMAND_OFFSET["state"]
        result_offset = block.COMMAND_OFFSET["result"]
        self.assertEqual(
            int.from_bytes(image[state_offset : state_offset + 4], "little"),
            int(CommandState.DONE),
        )
        self.assertEqual(
            int.from_bytes(image[result_offset : result_offset + 4], "little", signed=True),
            -100,
        )


class EmptyBlockTests(unittest.TestCase):
    """A fresh block must be exactly the size and identity the host expects."""

    def test_empty_block_is_the_full_size_and_validates(self) -> None:
        raw = empty_block(SESSION)
        self.assertEqual(len(raw), BLOCK_SIZE)
        header = read_header(raw)
        self.assertEqual(header.session_id, SESSION)
        self.assertEqual(header.command_written, 0)
        self.assertEqual(header.command_taken, 0)
        self.assertEqual(header.event_written, 0)
        self.assertEqual(header.event_taken, 0)

    def test_regions_start_zeroed(self) -> None:
        raw = empty_block(SESSION)
        self.assertEqual(raw[block.COMMAND_REGION_OFFSET :], bytes(BLOCK_SIZE - 64))

    def test_a_zero_session_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            empty_block(0)


class HeaderValidationTests(unittest.TestCase):
    """Every mismatch must fail closed rather than be decoded."""

    def _mutate(self, offset: int, value: int) -> bytes:
        raw = bytearray(empty_block(SESSION))
        struct.pack_into("<I", raw, offset, value)
        return bytes(raw)

    def test_wrong_magic(self) -> None:
        with self.assertRaises(ValueError):
            read_header(self._mutate(0, MAGIC ^ 0xFFFFFFFF))

    def test_wrong_version(self) -> None:
        with self.assertRaises(ValueError):
            read_header(self._mutate(4, VERSION + 1))

    def test_wrong_header_size(self) -> None:
        with self.assertRaises(ValueError):
            read_header(self._mutate(8, 32))

    def test_wrong_depths(self) -> None:
        with self.assertRaises(ValueError):
            read_header(self._mutate(16, COMMAND_DEPTH + 1))
        with self.assertRaises(ValueError):
            read_header(self._mutate(20, EVENT_DEPTH + 1))

    def test_nonzero_reserved_fields(self) -> None:
        for index in range(10, 16):
            with self.subTest(field=index):
                with self.assertRaises(ValueError):
                    read_header(self._mutate(index * 4, 1))

    def test_short_image_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            read_header(bytes(63))

    def test_a_header_that_cannot_be_true_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            BlockHeader(session_id=SESSION, command_written=COMMAND_DEPTH + 1)
        with self.assertRaises(ValueError):
            BlockHeader(session_id=SESSION, event_written=EVENT_DEPTH + 1)

    def test_header_round_trips(self) -> None:
        header = BlockHeader(
            session_id=SESSION,
            command_written=5,
            command_taken=2,
            event_written=9,
            event_taken=1,
        )
        self.assertEqual(BlockHeader.from_bytes(header.to_bytes()), header)


class CommandRecordTests(unittest.TestCase):
    """Commands carry work; the payload owns their state and result."""

    def test_round_trip(self) -> None:
        record = CommandRecord(
            sequence=7, operation=4, arg0=1, arg1=2, arg2=3, arg3=0x00400000
        )
        self.assertEqual(CommandRecord.from_bytes(record.to_bytes()), record)

    def test_terminal_state_carries_a_result(self) -> None:
        record = CommandRecord(
            sequence=7,
            operation=4,
            state=CommandState.FAILED,
            result=-102,
        )
        self.assertEqual(CommandRecord.from_bytes(record.to_bytes()), record)

    def test_unknown_state_is_rejected(self) -> None:
        raw = bytearray(CommandRecord(sequence=1, operation=1).to_bytes())
        struct.pack_into("<I", raw, 24, 99)
        with self.assertRaises(ValueError):
            CommandRecord.from_bytes(bytes(raw))

    def test_wrong_size_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CommandRecord.from_bytes(bytes(COMMAND_SIZE - 1))

    def test_a_ready_command_may_not_carry_a_result(self) -> None:
        with self.assertRaises(ValueError):
            CommandRecord(sequence=1, operation=1, result=5)

    def test_fields_must_fit_their_width(self) -> None:
        with self.assertRaises(ValueError):
            CommandRecord(sequence=-1, operation=1)
        with self.assertRaises(ValueError):
            CommandRecord(sequence=1, operation=1, arg0=2**32)
        with self.assertRaises(ValueError):
            CommandRecord(sequence=1, operation=1, state=CommandState.DONE, result=2**31)

    def test_state_must_be_a_command_state(self) -> None:
        with self.assertRaises(ValueError):
            CommandRecord(sequence=1, operation=1, state=2)  # type: ignore[arg-type]


class EventRecordTests(unittest.TestCase):
    """Events carry what the payload observed."""

    def test_round_trip(self) -> None:
        record = EventRecord(kind=2, sequence=7, arg0=1, arg1=2, tick=44)
        self.assertEqual(EventRecord.from_bytes(record.to_bytes()), record)

    def test_wrong_size_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            EventRecord.from_bytes(bytes(EVENT_SIZE - 1))

    def test_nonzero_reserved_field_is_rejected(self) -> None:
        raw = bytearray(EventRecord(kind=1).to_bytes())
        struct.pack_into("<I", raw, 28, 1)
        with self.assertRaises(ValueError):
            EventRecord.from_bytes(bytes(raw))

    def test_fields_must_fit_their_width(self) -> None:
        with self.assertRaises(ValueError):
            EventRecord(kind=-1)
        with self.assertRaises(ValueError):
            EventRecord(kind=1, tick=2**32)


class QueueArithmeticTests(unittest.TestCase):
    """The counters are the lock; their arithmetic must be exact."""

    def test_pending_and_free(self) -> None:
        self.assertEqual(pending(0, 0), 0)
        self.assertEqual(free_slots(0, 0, COMMAND_DEPTH), COMMAND_DEPTH)
        self.assertEqual(pending(5, 2), 3)
        self.assertEqual(free_slots(5, 2, COMMAND_DEPTH), COMMAND_DEPTH - 3)

    def test_a_full_queue_has_no_free_slots(self) -> None:
        self.assertEqual(free_slots(COMMAND_DEPTH, 0, COMMAND_DEPTH), 0)

    def test_counters_wrap_without_losing_the_difference(self) -> None:
        """The counters are absolute, so a wrap must not look like a reset."""

        written = (2**32 - 2) & 0xFFFFFFFF
        taken = (2**32 - 4) & 0xFFFFFFFF
        self.assertEqual(pending(written, taken), 2)
        self.assertEqual(free_slots(written, taken, COMMAND_DEPTH), COMMAND_DEPTH - 2)

    def test_an_overrun_is_corruption_not_a_full_queue(self) -> None:
        with self.assertRaises(ValueError):
            free_slots(COMMAND_DEPTH + 1, 0, COMMAND_DEPTH)


class IndependentQueueTests(unittest.TestCase):
    """Simulate both sides over one image, with no client and no threads.

    The producer always writes the record before advancing its counter, and the
    consumer only reads below that counter, so the loop below is the same
    discipline the payload must follow.
    """

    def setUp(self) -> None:
        self.raw = bytearray(empty_block(SESSION))
        self.command_written = 0
        self.command_taken = 0

    def publish(self, operation: int) -> int:
        slot = self.command_written % COMMAND_DEPTH
        record = CommandRecord(sequence=self.command_written + 1, operation=operation)
        write_command(self.raw, slot, record)
        self.command_written = (self.command_written + 1) & 0xFFFFFFFF
        return slot

    def test_publish_then_consume_round_trips(self) -> None:
        for index in range(COMMAND_DEPTH):
            slot = self.publish(index)
            record = read_command(self.raw, slot)
            self.assertEqual(record.operation, index)
            self.assertEqual(record.sequence, index + 1)
            self.assertEqual(record.state, CommandState.READY)
            self.command_taken = (self.command_taken + 1) & 0xFFFFFFFF

        self.assertEqual(pending(self.command_written, self.command_taken), 0)
        self.assertEqual(
            free_slots(self.command_written, self.command_taken, COMMAND_DEPTH),
            COMMAND_DEPTH,
        )

    def test_a_consumer_never_reads_above_the_published_counter(self) -> None:
        """Whatever is beyond the counter is not a record the host may read."""

        self.publish(0)
        self.publish(1)
        # Slots 2..15 were never written, so the consumer must not look at them.
        for slot in range(2, COMMAND_DEPTH):
            record = read_command(self.raw, slot)
            self.assertEqual(record.sequence, 0)
            self.assertEqual(record.operation, 0)

    def test_the_payload_can_mark_a_command_done_in_place(self) -> None:
        slot = self.publish(4)
        running = read_command(self.raw, slot)
        write_command(
            self.raw,
            slot,
            CommandRecord(
                sequence=running.sequence,
                operation=running.operation,
                arg0=running.arg0,
                state=CommandState.DONE,
            ),
        )
        finished = read_command(self.raw, slot)
        self.assertEqual(finished.sequence, running.sequence)
        self.assertIn(finished.state, block.TERMINAL_COMMAND_STATES)

    def test_events_use_the_other_region_and_do_not_disturb_commands(self) -> None:
        command_slot = self.publish(1)
        write_event(self.raw, 0, EventRecord(kind=2, sequence=1, tick=9))

        self.assertEqual(read_event(self.raw, 0).tick, 9)
        self.assertEqual(read_command(self.raw, command_slot).operation, 1)
        self.assertEqual(read_event(self.raw, 1).kind, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

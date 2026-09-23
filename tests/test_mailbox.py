"""Offline checks for the callback mailbox wire format."""

from __future__ import annotations

import struct
import unittest

from py4gw.memory import MailboxRecord, MailboxState


class MailboxRecordTests(unittest.TestCase):
    """Check record encoding and stable-snapshot validation."""

    def _encode(
        self,
        state: int = int(MailboxState.VALID),
        address: int = 0x12345678,
        sequence: int = 8,
        session_id: int = 0xABCDEF01,
        magic: int = MailboxRecord._MAGIC,
        version: int = MailboxRecord._VERSION,
        size: int = MailboxRecord._SIZE,
    ) -> bytes:
        return struct.pack(
            "<IHHIIII",
            magic,
            version,
            size,
            session_id,
            sequence,
            state,
            address,
        )

    def _decode(self, data: bytes) -> MailboxRecord:
        """Decode identical reads for the test attachment."""

        return MailboxRecord.from_stable_reads(data, data, 0xABCDEF01)

    def test_round_trips_valid_context_pointer(self) -> None:
        """A valid record preserves the target's 32-bit address."""

        record = MailboxRecord(
            session_id=0xABCDEF01,
            sequence=8,
            state=MailboxState.VALID,
            context_address=0x12345678,
        )

        decoded = self._decode(record.to_bytes())

        self.assertEqual(decoded, record)
        self.assertEqual(len(record.to_bytes()), 24)

    def test_accepts_empty_cleared_and_stopping_records(self) -> None:
        """Non-valid states carry no pointer and decode distinctly."""

        for state in (MailboxState.EMPTY, MailboxState.CLEARED, MailboxState.STOPPING):
            with self.subTest(state=state):
                decoded = self._decode(self._encode(state=int(state), address=0))
                self.assertEqual(decoded.state, state)
                self.assertEqual(decoded.context_address, 0)

    def test_rejects_different_reads(self) -> None:
        """A changing snapshot is not treated as a stable pointer."""

        first = self._encode()
        second = self._encode(address=0x87654321)

        with self.assertRaisesRegex(ValueError, "changed between reads"):
            MailboxRecord.from_stable_reads(first, second, 0xABCDEF01)

    def test_rejects_odd_sequence(self) -> None:
        """An odd sequence means the writer was updating the record."""

        with self.assertRaisesRegex(ValueError, "in progress"):
            self._decode(self._encode(sequence=7))

    def test_rejects_wrong_attachment(self) -> None:
        """A record from a previous session cannot be accepted."""

        record = self._encode(session_id=0x11111111)

        with self.assertRaisesRegex(ValueError, "different attachment"):
            self._decode(record)

    def test_rejects_unknown_header_values(self) -> None:
        """The reader refuses unknown format identity and versions."""

        invalid_headers = (
            (self._encode(magic=0), "magic"),
            (self._encode(version=2), "version"),
            (self._encode(size=20), "size"),
        )
        for data, expected_error in invalid_headers:
            with self.subTest(expected_error=expected_error):
                with self.assertRaisesRegex(ValueError, expected_error):
                    self._decode(data)

    def test_rejects_invalid_state_and_pointer_combinations(self) -> None:
        """Unknown states and contradictory pointer fields fail closed."""

        with self.assertRaisesRegex(ValueError, "unknown mailbox state"):
            self._decode(self._encode(state=99, address=0))

        with self.assertRaisesRegex(ValueError, "nonzero address"):
            self._decode(self._encode(state=int(MailboxState.VALID), address=0))

        with self.assertRaisesRegex(ValueError, "only a valid record"):
            self._decode(self._encode(state=int(MailboxState.CLEARED)))

    def test_rejects_wrong_record_length(self) -> None:
        """Partial or oversized reads are not parsed as mailbox records."""

        with self.assertRaisesRegex(ValueError, "exactly 24 bytes"):
            self._decode(b"\x00" * 23)

    def test_rejects_unrepresentable_record_values(self) -> None:
        """Addresses and counters must fit the target's 32-bit fields."""

        with self.assertRaisesRegex(ValueError, "context_address"):
            MailboxRecord(
                session_id=1,
                sequence=2,
                state=MailboxState.VALID,
                context_address=0x1_0000_0000,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)

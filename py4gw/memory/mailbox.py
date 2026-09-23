"""The fixed-width record used to report a callback-owned context address."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum


class MailboxState(IntEnum):
    """States the callback stub can publish for the WorldMap pointer."""

    EMPTY = 0
    VALID = 1
    CLEARED = 2
    STOPPING = 3


@dataclass(frozen=True)
class MailboxRecord:
    """One validated snapshot of the 32-bit callback mailbox."""

    session_id: int
    sequence: int
    state: MailboxState
    context_address: int

    _MAGIC = 0x50593447
    _VERSION = 1
    _SIZE = 24
    _STRUCT = struct.Struct("<IHHIIII")
    _MAX_UINT32 = 0xFFFFFFFF

    def __post_init__(self) -> None:
        """Reject values that cannot be represented by the wire format."""

        for name, value in (
            ("session_id", self.session_id),
            ("sequence", self.sequence),
            ("context_address", self.context_address),
        ):
            if not 0 <= value <= self._MAX_UINT32:
                raise ValueError(f"{name} must fit in an unsigned 32-bit value")

        if self.session_id == 0:
            raise ValueError("session_id must be nonzero")
        if self.sequence % 2:
            raise ValueError("sequence must be even for a stable record")
        if self.state is MailboxState.VALID and self.context_address == 0:
            raise ValueError("a valid record must contain a nonzero address")
        if self.state is not MailboxState.VALID and self.context_address != 0:
            raise ValueError("only a valid record may contain an address")

    def to_bytes(self) -> bytes:
        """Return this snapshot in the fixed 24-byte mailbox format."""

        return self._STRUCT.pack(
            self._MAGIC,
            self._VERSION,
            self._SIZE,
            self.session_id,
            self.sequence,
            int(self.state),
            self.context_address,
        )

    @classmethod
    def from_stable_reads(
        cls,
        first_read: bytes,
        second_read: bytes,
        expected_session_id: int,
    ) -> MailboxRecord:
        """Decode two identical even-sequence reads for one attachment.

        ``first_read`` and ``second_read`` are separate reads of the same
        target address. Requiring identical bytes and an even sequence avoids
        accepting a snapshot while the target callback is updating it.
        """

        if len(first_read) != cls._SIZE or len(second_read) != cls._SIZE:
            raise ValueError(f"mailbox records must be exactly {cls._SIZE} bytes")
        if first_read != second_read:
            raise ValueError("mailbox changed between reads")

        magic, version, size, session_id, sequence, state_value, address = (
            cls._STRUCT.unpack(first_read)
        )

        if magic != cls._MAGIC:
            raise ValueError("mailbox magic does not match")
        if version != cls._VERSION:
            raise ValueError(f"unsupported mailbox version: {version}")
        if size != cls._SIZE:
            raise ValueError(f"mailbox record size does not match: {size}")
        if session_id != expected_session_id:
            raise ValueError("mailbox belongs to a different attachment")
        if sequence % 2:
            raise ValueError("mailbox update is in progress")

        try:
            state = MailboxState(state_value)
        except ValueError as error:
            raise ValueError(f"unknown mailbox state: {state_value}") from error

        return cls(
            session_id=session_id,
            sequence=sequence,
            state=state,
            context_address=address,
        )

"""The block of memory inside the client that the host and the payload share.

This is Stealth's own infrastructure, not a port. Reforged has no counterpart:
its game-thread queue is a ``std::vector`` in its own address space, which is
possible only because the code runs inside the client. This project runs outside
it, so both sides need somewhere to meet.

The block holds two queues, one per direction, and each has exactly one writer:

    commands   the host publishes work, the payload takes it
    events     the payload publishes what happened, the host takes it

Each side therefore owns its own counter and only ever *reads* the other's, which
is what removes the need for a lock. The payload is running on the game's own
thread and must never wait for us.

Two rules make a torn record impossible without any per-record marker:

* a producer fills the whole record **first**, and only then advances its counter;
* a consumer only ever reads records **below** the counter the producer published.

Layout: a fixed 64-byte header, then the command region, then the event region.
Depths and record sizes are constants of this module, so a payload and a host that
disagree fail validation instead of misreading each other.

The vocabularies of those records — command state, operation, event kind, and the
result codes — live here too, beside the fields they describe, so there is one
place to read the contract from.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum

#: 'SBLK' little-endian, so a mismatched region is rejected rather than decoded.
MAGIC = 0x4B4C4253

#: Bumped whenever the layout changes. A mismatch must fail closed.
VERSION = 1

HEADER_SIZE = 64
COMMAND_DEPTH = 16
EVENT_DEPTH = 64
COMMAND_SIZE = 32
EVENT_SIZE = 32
DESCRIPTOR_DEPTH = 16
DESCRIPTOR_SIZE = 8

#: The watch list: message ids the observer records when they go past. Flat
#: words, because an entry is one id; a kind that needs to capture a different
#: shape can grow it when something requires that.
WATCH_DEPTH = 8
WATCH_SIZE = 4

COMMAND_REGION_OFFSET = HEADER_SIZE
EVENT_REGION_OFFSET = COMMAND_REGION_OFFSET + COMMAND_DEPTH * COMMAND_SIZE
BLOCK_SIZE = EVENT_REGION_OFFSET + EVENT_DEPTH * EVENT_SIZE

_HEADER = struct.Struct("<16I")
_COMMAND = struct.Struct("<7Ii")
_EVENT = struct.Struct("<8I")
_DESCRIPTOR = struct.Struct("<2I")

_COMMAND_FIELDS = (
    "sequence",
    "operation",
    "arg0",
    "arg1",
    "arg2",
    "arg3",
    "state",
    "result",
)

_EVENT_FIELDS = (
    "kind",
    "sequence",
    "arg0",
    "arg1",
    "arg2",
    "arg3",
    "tick",
    "reserved",
)

_DESCRIPTOR_FIELDS = (
    "target",
    "form",
)

_HEADER_FIELDS = (
    "magic",
    "version",
    "header_size",
    "session_id",
    "command_depth",
    "event_depth",
    "command_written",
    "command_taken",
    "event_written",
    "event_taken",
    "reserved0",
    "reserved1",
    "reserved2",
    "reserved3",
    "reserved4",
    "reserved5",
)

#: Byte offset of every field, derived from the field order the packed structs are
#: built from. Code that addresses a record's words directly — the payload's
#: machine code, or a host reading a block without decoding it — takes its offsets
#: from here, so it cannot drift from the structs.
HEADER_OFFSET = {name: index * 4 for index, name in enumerate(_HEADER_FIELDS)}
COMMAND_OFFSET = {name: index * 4 for index, name in enumerate(_COMMAND_FIELDS)}
EVENT_OFFSET = {name: index * 4 for index, name in enumerate(_EVENT_FIELDS)}
DESCRIPTOR_OFFSET = {name: index * 4 for index, name in enumerate(_DESCRIPTOR_FIELDS)}

_UINT32_MAX = 0xFFFFFFFF

#: A block image is ``bytes`` when it is a snapshot read from the client, and
#: ``bytearray`` when it is a buffer being built or written.
BlockImage = bytes | bytearray


class CommandState(IntEnum):
    """What the payload has done with a command record.

    ``READY`` is written by the host before it publishes; ``RUNNING`` and a
    terminal state are written by the payload only.
    """

    READY = 0
    RUNNING = 1
    DONE = 2
    FAILED = 3


TERMINAL_COMMAND_STATES = (CommandState.DONE, CommandState.FAILED)


class Operation(IntEnum):
    """What a command asks the payload to do.

    The values follow this project's earlier bridge design, which is kept under
    ``external/``, so a command written against either is read the same way.

    Only operations the payload can complete on its own are here, plus ``CALL``
    for work that goes through the descriptor table. Value 4 is deliberately
    skipped: the earlier design used it for a call whose target address and
    arguments travelled in the command, which is what ``CALL`` replaces with a
    descriptor index.
    """

    NOP = 0
    PING = 1
    ADD_U32 = 2
    ECHO_U32 = 3
    CALL = 5


class CallForm(IntEnum):
    """How a command's words become one call's arguments.

    A descriptor names a function *and* a form. The form is what makes a call
    typed: it fixes how many words the command carries and where each one goes,
    so the payload never guesses and no untyped argument blob reaches the client.
    A form the payload does not know fails rather than being called anyway.
    """

    #: ``ui::SendUIMessage(message_id, wparam, lparam)``, the shape Native uses
    #: for almost every action it takes on the player's behalf: the client's
    #: message id in ``arg1``, and ``arg2``/``arg3`` packed into a zeroed
    #: sixteen-word payload that is passed as ``wparam`` with ``lparam`` null.
    #: That is ``ui_bindings.cpp:60-74``'s contract, ported.
    #:
    #: Sending a message is not the same as doing the thing, and the sources say
    #: so: Native's own handler for ``kSendChangeTarget`` *observes* it and calls
    #: ``ChangeTargetFn``, which is where the target actually changes
    #: (``agent.cpp:143-155``). The messages are the client telling the world what
    #: it did; the functions are what does it.
    UI_MESSAGE = 1

    #: ``void __cdecl(uint32_t, uint32_t)``: two words passed straight through.
    #: ``ChangeTargetFn`` is this shape, and so is ``CallTargetFn``
    #: (``agent_methods.cpp:18-22``).
    U32_U32 = 2


class EventKind(IntEnum):
    """What an event record is about.

    The numbering follows the same earlier design, which leaves the value between
    ``NONE`` and ``COMMAND_COMPLETE`` to a per-frame tick kind. Nothing produces
    one yet, so it is not declared here; the gap keeps the values from shifting
    when something does. That design's low values name specific happenings; a
    watched UI message is this project's own kind, and the message id travels in
    the record's ``sequence`` field.
    """

    NONE = 0
    COMMAND_COMPLETE = 2
    UI_MESSAGE = 63


#: What a ``PING`` completes with. Not a value the client can produce, so it can
#: only come back if our own code ran on the game thread.
#:
#: These are the same 32 bits as ``0xC0DEC0DE``, written as what a reader actually
#: gets back: a command's ``result`` is signed, because an error code has to be
#: negative, so the bit pattern reads as a negative number there. An event's
#: ``arg2`` is unsigned and reads as the positive one.
PING_RESULT = 0xC0DEC0DE - 2**32

#: What a command completes with when the payload does not know its operation.
RESULT_UNKNOWN_OPERATION = -100

#: The call path's refusals. -101 and -102 are the earlier design's values for
#: these same two cases. -103 and -104 are this project's: that design had no
#: typed forms and named no descriptor slots.
RESULT_NO_TARGET = -101
RESULT_BAD_TARGET = -102
RESULT_UNKNOWN_FORM = -103
RESULT_BAD_DESCRIPTOR = -104


def _check_uint32(name: str, value: int) -> None:
    if not 0 <= value <= _UINT32_MAX:
        raise ValueError(f"{name} must fit in an unsigned 32-bit value")


def command_offset(slot: int) -> int:
    """Return the byte offset of one command record in the block."""

    if not 0 <= slot < COMMAND_DEPTH:
        raise ValueError(f"command slot must be 0..{COMMAND_DEPTH - 1}")
    return COMMAND_REGION_OFFSET + slot * COMMAND_SIZE


def event_offset(slot: int) -> int:
    """Return the byte offset of one event record in the block."""

    if not 0 <= slot < EVENT_DEPTH:
        raise ValueError(f"event slot must be 0..{EVENT_DEPTH - 1}")
    return EVENT_REGION_OFFSET + slot * EVENT_SIZE


def descriptor_offset(slot: int) -> int:
    """Return the byte offset of one call descriptor in the call table.

    The table is a region of its own, not part of the block: its address is
    emitted into the dispatcher at install, and a command names a slot in it
    rather than an address.
    """

    if not 0 <= slot < DESCRIPTOR_DEPTH:
        raise ValueError(f"descriptor slot must be 0..{DESCRIPTOR_DEPTH - 1}")
    return slot * DESCRIPTOR_SIZE


def pending(written: int, taken: int) -> int:
    """Return how many records a consumer has not taken yet."""

    return (written - taken) & _UINT32_MAX


def free_slots(written: int, taken: int, depth: int) -> int:
    """Return how many records a producer may still publish.

    ``pending`` can exceed ``depth`` only if a producer overran, which is
    corruption rather than a full queue, so it is reported as such.
    """

    outstanding = pending(written, taken)
    if outstanding > depth:
        raise ValueError(
            f"queue is corrupt: {outstanding} records are outstanding in a "
            f"{depth}-slot region"
        )
    return depth - outstanding


@dataclass(frozen=True)
class BlockHeader:
    """The 64-byte header, validated on construction and on decode."""

    session_id: int
    command_written: int = 0
    command_taken: int = 0
    event_written: int = 0
    event_taken: int = 0

    def __post_init__(self) -> None:
        """Reject values the format cannot carry, or that cannot be true."""

        _check_uint32("session_id", self.session_id)
        if self.session_id == 0:
            raise ValueError("session_id must be nonzero")

        for name in (
            "command_written",
            "command_taken",
            "event_written",
            "event_taken",
        ):
            _check_uint32(name, getattr(self, name))

        if pending(self.command_written, self.command_taken) > COMMAND_DEPTH:
            raise ValueError("command region is corrupt: more outstanding than depth")
        if pending(self.event_written, self.event_taken) > EVENT_DEPTH:
            raise ValueError("event region is corrupt: more outstanding than depth")

    def to_bytes(self) -> bytes:
        """Return the header in its fixed 64-byte form."""

        return _HEADER.pack(
            MAGIC,
            VERSION,
            HEADER_SIZE,
            self.session_id,
            COMMAND_DEPTH,
            EVENT_DEPTH,
            self.command_written,
            self.command_taken,
            self.event_written,
            self.event_taken,
            0,
            0,
            0,
            0,
            0,
            0,
        )

    @classmethod
    def from_bytes(cls, raw: BlockImage) -> BlockHeader:
        """Decode and validate a header, failing closed on every mismatch."""

        if len(raw) != HEADER_SIZE:
            raise ValueError(f"block header must be exactly {HEADER_SIZE} bytes")

        values = dict(zip(_HEADER_FIELDS, _HEADER.unpack(raw)))

        if values["magic"] != MAGIC:
            raise ValueError("block magic does not match")
        if values["version"] != VERSION:
            raise ValueError(f"unsupported block version: {values['version']}")
        if values["header_size"] != HEADER_SIZE:
            raise ValueError(
                f"block header size does not match: {values['header_size']}"
            )
        if values["command_depth"] != COMMAND_DEPTH:
            raise ValueError(
                f"command depth does not match: {values['command_depth']}"
            )
        if values["event_depth"] != EVENT_DEPTH:
            raise ValueError(f"event depth does not match: {values['event_depth']}")
        for name in ("reserved0", "reserved1", "reserved2", "reserved3",
                     "reserved4", "reserved5"):
            if values[name] != 0:
                raise ValueError(f"{name} must be zero")

        return cls(
            session_id=values["session_id"],
            command_written=values["command_written"],
            command_taken=values["command_taken"],
            event_written=values["event_written"],
            event_taken=values["event_taken"],
        )


@dataclass(frozen=True)
class CommandRecord:
    """One unit of work for the payload to run on the game thread.

    ``operation`` selects what to do; ``arg0``..``arg3`` are the arguments.
    ``state`` and ``result`` belong to the payload.
    """

    sequence: int
    operation: int
    arg0: int = 0
    arg1: int = 0
    arg2: int = 0
    arg3: int = 0
    state: CommandState = CommandState.READY
    result: int = 0

    def __post_init__(self) -> None:
        """Reject anything the record cannot carry."""

        for name in ("sequence", "operation", "arg0", "arg1", "arg2", "arg3"):
            _check_uint32(name, getattr(self, name))
        if not -(2**31) <= self.result < 2**31:
            raise ValueError("result must fit in a signed 32-bit value")
        if not isinstance(self.state, CommandState):
            raise ValueError("state must be a CommandState")
        if self.state is CommandState.READY and self.result != 0:
            raise ValueError("a ready command cannot carry a result")

    def to_bytes(self) -> bytes:
        """Return the record in its fixed 32-byte form."""

        return _COMMAND.pack(
            self.sequence,
            self.operation,
            self.arg0,
            self.arg1,
            self.arg2,
            self.arg3,
            int(self.state),
            self.result,
        )

    @classmethod
    def from_bytes(cls, raw: BlockImage) -> CommandRecord:
        """Decode one command record, failing closed on a bad state value."""

        if len(raw) != COMMAND_SIZE:
            raise ValueError(f"command record must be exactly {COMMAND_SIZE} bytes")

        sequence, operation, arg0, arg1, arg2, arg3, state_value, result = (
            _COMMAND.unpack(raw)
        )
        try:
            state = CommandState(state_value)
        except ValueError as error:
            raise ValueError(f"unknown command state: {state_value}") from error

        return cls(
            sequence=sequence,
            operation=operation,
            arg0=arg0,
            arg1=arg1,
            arg2=arg2,
            arg3=arg3,
            state=state,
            result=result,
        )


@dataclass(frozen=True)
class EventRecord:
    """Something the payload observed and wants the host to know about."""

    kind: int
    sequence: int = 0
    arg0: int = 0
    arg1: int = 0
    arg2: int = 0
    arg3: int = 0
    tick: int = 0

    def __post_init__(self) -> None:
        """Reject anything the record cannot carry."""

        for name in ("kind", "sequence", "arg0", "arg1", "arg2", "arg3", "tick"):
            _check_uint32(name, getattr(self, name))

    def to_bytes(self) -> bytes:
        """Return the record in its fixed 32-byte form."""

        return _EVENT.pack(
            self.kind,
            self.sequence,
            self.arg0,
            self.arg1,
            self.arg2,
            self.arg3,
            self.tick,
            0,
        )

    @classmethod
    def from_bytes(cls, raw: BlockImage) -> EventRecord:
        """Decode one event record."""

        if len(raw) != EVENT_SIZE:
            raise ValueError(f"event record must be exactly {EVENT_SIZE} bytes")

        kind, sequence, arg0, arg1, arg2, arg3, tick, reserved = _EVENT.unpack(raw)
        if reserved != 0:
            raise ValueError("event reserved field must be zero")

        return cls(
            kind=kind,
            sequence=sequence,
            arg0=arg0,
            arg1=arg1,
            arg2=arg2,
            arg3=arg3,
            tick=tick,
        )


@dataclass(frozen=True)
class Descriptor:
    """One entry of the call table: what to call, and in which form.

    The host writes these into the client, resolved from the pattern catalog the
    same way every other address in this project is. A command then names a slot,
    so the queue carries an index and never an address, and the payload refuses a
    target outside the client module before it calls anything.
    """

    target: int = 0
    form: CallForm = CallForm.UI_MESSAGE

    def __post_init__(self) -> None:
        """Reject anything the entry cannot carry."""

        _check_uint32("target", self.target)
        if not isinstance(self.form, CallForm):
            raise ValueError("form must be a CallForm")

    def to_bytes(self) -> bytes:
        """Return the entry in its fixed 8-byte form."""

        return _DESCRIPTOR.pack(self.target, int(self.form))

    @classmethod
    def from_bytes(cls, raw: BlockImage) -> Descriptor:
        """Decode one descriptor, failing closed on an unknown form."""

        if len(raw) != DESCRIPTOR_SIZE:
            raise ValueError(f"descriptor must be exactly {DESCRIPTOR_SIZE} bytes")

        target, form_value = _DESCRIPTOR.unpack(raw)
        try:
            form = CallForm(form_value)
        except ValueError as error:
            raise ValueError(f"unknown call form: {form_value}") from error
        return cls(target=target, form=form)


def empty_block(session_id: int) -> bytes:
    """Return a fresh block image with both queues empty."""

    header = BlockHeader(session_id=session_id).to_bytes()
    return header + bytes(BLOCK_SIZE - HEADER_SIZE)


def read_header(raw: BlockImage) -> BlockHeader:
    """Decode the header of a whole block image."""

    if len(raw) < HEADER_SIZE:
        raise ValueError(f"block image must be at least {HEADER_SIZE} bytes")
    return BlockHeader.from_bytes(raw[:HEADER_SIZE])


def write_command(raw: bytearray, slot: int, record: CommandRecord) -> None:
    """Write one command record into a block image."""

    if len(raw) < BLOCK_SIZE:
        raise ValueError(f"block image must be at least {BLOCK_SIZE} bytes")
    offset = command_offset(slot)
    raw[offset : offset + COMMAND_SIZE] = record.to_bytes()


def read_command(raw: BlockImage, slot: int) -> CommandRecord:
    """Read one command record out of a block image."""

    offset = command_offset(slot)
    return CommandRecord.from_bytes(raw[offset : offset + COMMAND_SIZE])


def write_event(raw: bytearray, slot: int, record: EventRecord) -> None:
    """Write one event record into a block image."""

    if len(raw) < BLOCK_SIZE:
        raise ValueError(f"block image must be at least {BLOCK_SIZE} bytes")
    offset = event_offset(slot)
    raw[offset : offset + EVENT_SIZE] = record.to_bytes()


def read_event(raw: BlockImage, slot: int) -> EventRecord:
    """Read one event record out of a block image."""

    offset = event_offset(slot)
    return EventRecord.from_bytes(raw[offset : offset + EVENT_SIZE])

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
#:
#: 2: the command record gained a ``value`` word — the callee's return register, stored by
#: the emitted call path — so a command is 64 bytes and every offset after the command
#: region moved.
#:
#: 3: the command record gained ``arg4`` and ``arg5``, for the first source declaration that
#: takes five words (``OpenFileByFileId``, ``gw_dat_reader.h:42``). Both sit with the other
#: arguments, so every offset after them moved again.
#:
#: 4: the block gained the decode region — the strings an asynchronous decode is handed and
#: the text it produces — so the block is larger, and a host and a payload built from
#: different versions must refuse to work together rather than write past each other.
#:
#: 5: an event record gained a bounded copy of the string the watched message named, and the
#: watch list an entry's second word says where that string's pointer sits in the packet. The
#: copy is what makes a dialog button's label readable at all: the pointer the client announces
#: is a buffer it reuses, so the string has to be read **inside the client's own call** and
#: carried out with the event (``docs/RESEARCH.md``, 2026-09-25).
VERSION = 5

HEADER_SIZE = 64
COMMAND_DEPTH = 16
EVENT_DEPTH = 64

#: A command record's size must stay a power of two: the emitted dispatcher addresses a
#: record by shifting its slot, which is checked where the shift is derived
#: (``payload.py``). Eleven words are in use — the eight it always had, ``value``, and the
#: two the five-word call form added — and the rest of the 64 bytes is unused room rather
#: than a promise.
COMMAND_SIZE = 64
DESCRIPTOR_DEPTH = 16
DESCRIPTOR_SIZE = 8

#: The watch list: what the observer records when a message goes past. An entry is the message
#: id and the byte offset of the ``wchar_t*`` field that message carries, or zero for a message
#: that carries no string — ``DialogBodyInfo {uint32 type; uint32 agent_id; wchar_t* message_enc}``
#: is eight (``ui.h:54-58``), the client's ``DialogButtonInfo {uint32 button_icon; wchar_t*
#: message; uint32 dialog_id; uint32 skill_id}`` is four (``ui.h:60-65``), and
#: ``ChangeTargetUIMsg`` names no string (``ui.h:78-84``).
WATCH_DEPTH = 8
WATCH_SIZE = 8

#: Inside one watch entry: the message id the observer compares, and the byte offset of the
#: ``wchar_t*`` field whose string it should copy out with the event (zero for none).
WATCH_ID_OFFSET = 0
WATCH_STRING_OFFSET = 4

#: How much of a watched message's string an event carries, in wide characters. The copy is
#: taken by the emitted observer **inside the client's call**, which is the only moment the
#: string is the client's own; the bound is what stops a string without a terminator from being
#: read on for ever. Seven times the largest dialog text this project has measured (a 134-byte
#: table entry, 67 units) — a longer string is reported as unterminated rather than truncated,
#: because half a string decodes to the wrong text.
#:
#: A record's own words end at 40 and its text starts at 64, so the six words between them are
#: unused room rather than a promise, and the text's 960 bytes bring the record to the 1024 the
#: observer's shift needs.
EVENT_TEXT_WORDS = 480
EVENT_TEXT_STATE_OFFSET = 32
EVENT_TEXT_LENGTH_OFFSET = 36
EVENT_TEXT_OFFSET = 64
EVENT_TEXT_SIZE = EVENT_TEXT_WORDS * 2
EVENT_SIZE = EVENT_TEXT_OFFSET + EVENT_TEXT_SIZE

COMMAND_REGION_OFFSET = HEADER_SIZE
EVENT_REGION_OFFSET = COMMAND_REGION_OFFSET + COMMAND_DEPTH * COMMAND_SIZE

#: A scratch region inside the same allocation, for data a call has to be handed a
#: **pointer** to: a string the client reads as an argument, or a word the client writes a
#: result into. The source's own callers keep those in their stack frames; this project has
#: no frame in the client, so it keeps them here, in the client's own address space.
DATA_REGION_OFFSET = EVENT_REGION_OFFSET + EVENT_DEPTH * EVENT_SIZE
DATA_SIZE = 4096

#: The decode region: one slot per string being decoded asynchronously, holding the string the
#: client is handed and the text it writes back.
#:
#: The source hands its string to the client's decoder and gets the text back through a
#: callback into its own address space (``GW::ui::AsyncDecodeStr``, ``ui_methods.cpp:2582``
#: and ``dialog.cpp:885``). Nothing of this project's runs in that address space, so the two
#: halves of that transaction need somewhere to meet, and this is it: the host places the
#: string it wants decoded, the emitted stub the client calls copies the text it was given
#: into the same slot, and the host reads it back.
#:
#: **Each slot has exactly one writer at a time** — the host writes the string before the
#: call, the client's callback writes the text after it — so, like the two queues above, no
#: lock is needed. The state word is what orders them, and it is written **last** by whichever
#: side has finished, so a reader that sees it sees everything before it.
DECODE_DEPTH = 32

#: A slot's own words: the state, the length of the string the client decoded, and two words
#: of room that are not a promise.
DECODE_HEADER_SIZE = 16

#: The string the client is handed, in bytes. A dialog's encoded text is short — the live body
#: measured 22 code units — and this is room for 512 of them; a longer one is refused rather
#: than truncated, because half a string decodes to the wrong text.
DECODE_INPUT_SIZE = 1024

#: The text the client writes back, in wide characters. This is the bound the source does not
#: have: native's callback copies into a ``std::wstring`` that grows, and a slot here cannot.
#: A decoded string longer than this is **truncated**, and the slot's length word is the
#: string's real length, so the host can say so rather than answer with half a sentence.
DECODE_CAPACITY = 2048
DECODE_OUTPUT_SIZE = DECODE_CAPACITY * 2

DECODE_SLOT_SIZE = DECODE_HEADER_SIZE + DECODE_INPUT_SIZE + DECODE_OUTPUT_SIZE
DECODE_REGION_OFFSET = DATA_REGION_OFFSET + DATA_SIZE

#: Where each part of a slot sits **inside** it. The emitted stub is handed a slot's address
#: and addresses the state, the length, and the text relative to that, so these are the offsets
#: its machine code is built from — the one place both sides read the shape from.
DECODE_SLOT_STATE_OFFSET = 0
DECODE_SLOT_LENGTH_OFFSET = 4
DECODE_SLOT_INPUT_OFFSET = DECODE_HEADER_SIZE
DECODE_SLOT_OUTPUT_OFFSET = DECODE_HEADER_SIZE + DECODE_INPUT_SIZE

BLOCK_SIZE = DECODE_REGION_OFFSET + DECODE_DEPTH * DECODE_SLOT_SIZE

_HEADER = struct.Struct("<16I")
#: ``result`` is the one signed field: the call path's refusals are negative codes.
_COMMAND = struct.Struct("<9IiI")
#: An event's words, and then its copy of the string the watched message named
#: (``EVENT_TEXT_OFFSET``), which is code units rather than words and is written separately.
_EVENT = struct.Struct("<10I")
_DESCRIPTOR = struct.Struct("<2I")

_COMMAND_FIELDS = (
    "sequence",
    "operation",
    "arg0",
    "arg1",
    "arg2",
    "arg3",
    "arg4",
    "arg5",
    "state",
    "result",
    "value",
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
    "text_state",
    "text_length",
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
    #: (``agent_methods.cpp:19-20``).
    U32_U32 = 2

    #: ``void __cdecl(void)``: no arguments, so nothing is pushed and nothing is
    #: released. ``RemoveActiveTitleFn`` is this shape
    #: (``player_methods.cpp:39``).
    NO_ARGS = 3

    #: ``void __cdecl(uint32_t)``: one word. ``SetActiveTitleFn``
    #: (``player_methods.cpp:40``) and ``SendDialogFn`` (``agent_methods.cpp:18``)
    #: are this shape.
    U32 = 4

    #: ``void __cdecl(uint32_t, uint32_t, uint32_t)``: three words, in the
    #: source's order. ``DepositFactionFn`` (``player_methods.cpp:41``) and
    #: ``DoWorldActionFn`` (``agent_methods.cpp:22``) are this shape.
    U32_U32_U32 = 5

    #: ``void __cdecl(float*)``: one pointer to a four-float array built from the
    #: command's three words and a zero. ``MoveToFn`` is this shape, and the
    #: source fills exactly that array — ``{x, y, (float)zplane, 0.0f}``
    #: (``agent_methods.cpp:21`` and ``149-153``). The fourth float is not spare
    #: room; it is a value the client reads.
    FLOAT_PTR = 6

    #: ``RecObj* __cdecl(uint32_t, uint32_t, uint32_t, uint32_t, uint32_t*)``: five
    #: words in the source's order, which is what ``OpenFileByFileId`` declares
    #: (``gw_dat_reader.h:42``) and what the GW.dat chain's first call takes. The
    #: pointer argument travels as its word, exactly as the source passes its own
    #: ``error_out`` — the DAT reader passes null there, and the ``size_out``
    #: pointer of the call after it is an address inside the block's data region.
    U32_U32_U32_U32_U32 = 7


def float_bits(value: float) -> int:
    """Return one ``float`` as the ``uint32`` a command word carries.

    A command word is 32 bits and a ``float`` is 32 bits, so a float argument
    travels as its bit pattern and the target reads it back as a float. The
    caller does the conversion because the wire record has no float field, and
    the source's own array is ``float[4]`` regardless of how it is transported.
    """

    return struct.unpack("<I", struct.pack("<f", float(value)))[0]


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
    #: A string the client's own decoder produced, and the callback it called with it. Native
    #: has no such event because the callback is its own function, called inside the client;
    #: here the stub records it and the host reads it, so it travels the same channel every
    #: other thing the client tells this project travels — ``UI_MESSAGE``, which is this
    #: project's own kind in the same way, is the precedent. The slot the text is in travels in
    #: the record's ``sequence``, its length in ``arg0``, and ``arg1`` says whether the decode
    #: failed rather than produced an empty string.
    STRING_DECODED = 3
    UI_MESSAGE = 63


class DecodeState(IntEnum):
    """What has happened to one slot of the decode region.

    ``FREE`` and ``IN_FLIGHT`` are the host's to write — it owns the slot until the client's
    callback has filled it — and ``DONE`` and ``FAILED`` are the client's, written by the
    emitted stub. The host takes the text and puts the slot back to ``FREE``.

    There is no ``FAILED`` in the source: native's callback is handed whatever the client's
    decoder produced, and a decode that could not be made calls back with ``L""``
    (``ui_methods.cpp:2583-2598``). ``FAILED`` is this side of the boundary being honest about
    the one case native cannot have — a string with no terminator inside the bound the stub is
    allowed to scan — so a caller is told the decode did not happen instead of being handed
    the empty text a real empty string produces.
    """

    FREE = 0
    IN_FLIGHT = 1
    DONE = 2
    FAILED = 3


class EventTextState(IntEnum):
    """What the observer made of the string a watched message named.

    The source's reading of that string is ``DupWideStringSafe`` (``dialog.cpp:237-252``): a
    ``wcslen`` inside a ``__try``, no copy at all when the pointer is null, and null when the
    read faulted. Emitted code here has no ``__try``, so the copy is **bounded** instead, and
    the three outcomes the source can produce are the three declared here.

    ``ABSENT`` is the source's ``!info->message``; ``COPIED`` is a string copied whole, its
    terminator included, which is what ``wcslen + 1`` gives native; ``UNTERMINATED`` is a string
    with no terminator inside :data:`EVENT_TEXT_WORDS`, which native has no equivalent of — its
    ``wcslen`` would either find one or fault — and which this side reports rather than
    truncating, because half a string decodes to the wrong text.
    """

    ABSENT = 0
    COPIED = 1
    UNTERMINATED = 2


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


def _check_uint16(name: str, value: int) -> None:
    if not 0 <= value <= 0xFFFF:
        raise ValueError(f"{name} must fit in a wide character")


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


def data_offset(offset: int, size: int = 0) -> int:
    """Return the byte offset of one span inside the block's data region.

    The region is bounded here rather than by the caller: an offset that would run past it
    is refused, because the alternative is writing over the event ring or past the end of
    the client's allocation.
    """

    if offset < 0 or size < 0 or offset + size > DATA_SIZE:
        raise ValueError(
            f"data span {offset}..{offset + size} does not fit in {DATA_SIZE} bytes"
        )
    return DATA_REGION_OFFSET + offset


def descriptor_offset(slot: int) -> int:
    """Return the byte offset of one call descriptor in the call table.

    The table is a region of its own, not part of the block: its address is
    emitted into the dispatcher at install, and a command names a slot in it
    rather than an address.
    """

    if not 0 <= slot < DESCRIPTOR_DEPTH:
        raise ValueError(f"descriptor slot must be 0..{DESCRIPTOR_DEPTH - 1}")
    return slot * DESCRIPTOR_SIZE


def decode_slot_offset(slot: int) -> int:
    """Return the byte offset of one decode slot in the block."""

    if not 0 <= slot < DECODE_DEPTH:
        raise ValueError(f"decode slot must be 0..{DECODE_DEPTH - 1}")
    return DECODE_REGION_OFFSET + slot * DECODE_SLOT_SIZE


def decode_input_offset(slot: int) -> int:
    """Return the byte offset of the string the client is handed for one slot."""

    return decode_slot_offset(slot) + DECODE_SLOT_INPUT_OFFSET


def decode_output_offset(slot: int) -> int:
    """Return the byte offset of the text the client writes back for one slot."""

    return decode_slot_offset(slot) + DECODE_SLOT_OUTPUT_OFFSET


def decode_slot_image(slot: int, encoded: bytes) -> bytes:
    """Return the bytes of one slot carrying a request: the string, then the in-flight state.

    This is what a host writes into a slot before it asks the client to decode, and the shape
    the state word's ordering is about — everything first, the state last — so a callback that
    somehow ran early would find the slot still in flight rather than read half a string. The
    room the string does not use is cleared, so nothing a previous request left in the slot can
    be read as part of this one.
    """

    if len(encoded) > DECODE_INPUT_SIZE:
        raise ValueError(
            f"the string to decode is {len(encoded)} bytes, and a decode slot holds "
            f"{DECODE_INPUT_SIZE}. A longer one is refused rather than cut short: half a "
            f"string decodes to the wrong text."
        )

    image = bytearray(DECODE_SLOT_SIZE)
    start = DECODE_SLOT_INPUT_OFFSET
    image[start : start + len(encoded)] = encoded
    struct.pack_into("<I", image, DECODE_SLOT_LENGTH_OFFSET, 0)
    struct.pack_into("<I", image, DECODE_SLOT_STATE_OFFSET, int(DecodeState.IN_FLIGHT))
    return bytes(image)


def write_decode_request(raw: bytearray, slot: int, encoded: bytes) -> None:
    """Place one encoded string for the client to decode, and mark the slot in flight."""

    if len(raw) < BLOCK_SIZE:
        raise ValueError(f"block image must be at least {BLOCK_SIZE} bytes")
    start = decode_slot_offset(slot)
    raw[start : start + DECODE_SLOT_SIZE] = decode_slot_image(slot, encoded)


def decode_state_from_word(value: int) -> DecodeState:
    """Read a slot's state from its own word, failing closed on a value the format lacks."""

    try:
        return DecodeState(value)
    except ValueError as error:
        raise ValueError(f"unknown decode state: {value}") from error


def decode_text_from_bytes(payload: BlockImage, length: int) -> tuple[str, bool]:
    """Read a decoded string out of the bytes of a slot's output area.

    The length is the decoded string's **real** length — the stub counts past the room it had
    to store it — so a string longer than the slot reports itself as truncated instead of
    quietly answering with the part that fitted.
    """

    stored = min(int(length), DECODE_CAPACITY)
    return payload[: stored * 2].decode("utf-16-le", "replace"), int(length) > DECODE_CAPACITY


def read_decode_state(raw: BlockImage, slot: int) -> DecodeState:
    """Read one slot's state out of a whole block image."""

    (value,) = struct.unpack_from("<I", raw, decode_slot_offset(slot))
    return decode_state_from_word(value)


def read_decode_result(raw: BlockImage, slot: int) -> tuple[str, bool]:
    """Read the text the client decoded into one slot of a whole block image."""

    if read_decode_state(raw, slot) is not DecodeState.DONE:
        return "", False
    (length,) = struct.unpack_from(
        "<I", raw, decode_slot_offset(slot) + DECODE_SLOT_LENGTH_OFFSET
    )
    start = decode_output_offset(slot)
    return decode_text_from_bytes(
        raw[start : start + DECODE_OUTPUT_SIZE], length
    )


def clear_decode_slot(raw: bytearray, slot: int) -> None:
    """Put one decode slot back to free, once its text has been read."""

    start = decode_slot_offset(slot)
    struct.pack_into("<I", raw, start + DECODE_SLOT_LENGTH_OFFSET, 0)
    struct.pack_into("<I", raw, start + DECODE_SLOT_STATE_OFFSET, int(DecodeState.FREE))


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

    ``operation`` selects what to do; ``arg0``..``arg5`` are the arguments. The first of them
    is the call table slot for a ``CALL``, so a call carries five words. ``state``, ``result``
    and ``value`` belong to the payload: ``result`` is the status code, and ``value`` is the
    callee's return register for a ``CALL`` — the port of the return type the source's own
    prototype table carries. A target declared ``void`` leaves whatever the callee left in
    that register, so ``value`` is read only for a target whose return the caller wants.
    """

    sequence: int
    operation: int
    arg0: int = 0
    arg1: int = 0
    arg2: int = 0
    arg3: int = 0
    arg4: int = 0
    arg5: int = 0
    state: CommandState = CommandState.READY
    result: int = 0
    value: int = 0

    def __post_init__(self) -> None:
        """Reject anything the record cannot carry."""

        for name in (
            "sequence",
            "operation",
            "arg0",
            "arg1",
            "arg2",
            "arg3",
            "arg4",
            "arg5",
            "value",
        ):
            _check_uint32(name, getattr(self, name))
        if not -(2**31) <= self.result < 2**31:
            raise ValueError("result must fit in a signed 32-bit value")
        if not isinstance(self.state, CommandState):
            raise ValueError("state must be a CommandState")
        if self.state is CommandState.READY and self.result != 0:
            raise ValueError("a ready command cannot carry a result")

    def to_bytes(self) -> bytes:
        """Return the record in its fixed-width form, padded to the slot.

        The fields are eleven words and the slot is 64 bytes, so the rest of the record is
        written as zeros: the payload addresses records by slot, and a slot is one record's
        worth of bytes.
        """

        return _COMMAND.pack(
            self.sequence,
            self.operation,
            self.arg0,
            self.arg1,
            self.arg2,
            self.arg3,
            self.arg4,
            self.arg5,
            int(self.state),
            self.result,
            self.value,
        ) + bytes(COMMAND_SIZE - _COMMAND.size)

    @classmethod
    def from_bytes(cls, raw: BlockImage) -> CommandRecord:
        """Decode one command record, failing closed on a bad state value."""

        if len(raw) != COMMAND_SIZE:
            raise ValueError(f"command record must be exactly {COMMAND_SIZE} bytes")

        (
            sequence,
            operation,
            arg0,
            arg1,
            arg2,
            arg3,
            arg4,
            arg5,
            state_value,
            result,
            value,
        ) = _COMMAND.unpack_from(raw, 0)
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
            arg4=arg4,
            arg5=arg5,
            state=state,
            result=result,
            value=value,
        )


@dataclass(frozen=True)
class EventRecord:
    """Something the payload observed and wants the host to know about.

    ``text`` is the copy the observer took of the string a watched message named — the wide
    characters as the client had them, terminator included, which is what native's
    ``DupWideStringSafe`` hands its own callers (``dialog.cpp:237-252``). It is empty when the
    message names no string or names a null one, and ``text_state`` says which of the three
    outcomes it was (:class:`EventTextState`); a caller that needs the difference between "no
    string" and "a string with no terminator inside the bound" reads that word.
    """

    kind: int
    sequence: int = 0
    arg0: int = 0
    arg1: int = 0
    arg2: int = 0
    arg3: int = 0
    tick: int = 0
    text_state: int = EventTextState.ABSENT
    text: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        """Reject anything the record cannot carry."""

        for name in ("kind", "sequence", "arg0", "arg1", "arg2", "arg3", "tick"):
            _check_uint32(name, getattr(self, name))
        if self.text_state not in tuple(EventTextState):
            raise ValueError(f"event text_state {self.text_state} is not a state")
        if len(self.text) > EVENT_TEXT_WORDS:
            raise ValueError(
                f"an event carries at most {EVENT_TEXT_WORDS} code units; "
                f"{len(self.text)} were given"
            )
        for unit in self.text:
            _check_uint16("text unit", unit)
        if self.text_state is EventTextState.ABSENT and self.text:
            raise ValueError("an event with no string cannot carry text")

    def to_bytes(self) -> bytes:
        """Return the record in its fixed ``EVENT_SIZE``-byte form."""

        words = _EVENT.pack(
            self.kind,
            self.sequence,
            self.arg0,
            self.arg1,
            self.arg2,
            self.arg3,
            self.tick,
            0,
            int(self.text_state),
            len(self.text),
        )
        text = b"".join(struct.pack("<H", unit) for unit in self.text)
        return (
            words
            + bytes(EVENT_TEXT_OFFSET - _EVENT.size)
            + text
            + bytes(EVENT_TEXT_SIZE - len(text))
        )

    @classmethod
    def from_bytes(cls, raw: BlockImage) -> EventRecord:
        """Decode one event record."""

        if len(raw) != EVENT_SIZE:
            raise ValueError(f"event record must be exactly {EVENT_SIZE} bytes")

        (
            kind,
            sequence,
            arg0,
            arg1,
            arg2,
            arg3,
            tick,
            reserved,
            text_state,
            text_length,
        ) = _EVENT.unpack(raw[: _EVENT.size])
        if reserved != 0:
            raise ValueError("event reserved field must be zero")
        if text_length > EVENT_TEXT_WORDS:
            raise ValueError(
                f"event text length {text_length} is past the {EVENT_TEXT_WORDS} "
                "code units a record carries"
            )

        text = tuple(
            struct.unpack_from("<H", raw, EVENT_TEXT_OFFSET + index * 2)[0]
            for index in range(text_length)
        )
        return cls(
            kind=kind,
            sequence=sequence,
            arg0=arg0,
            arg1=arg1,
            arg2=arg2,
            arg3=arg3,
            tick=tick,
            text_state=text_state,
            text=text,
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

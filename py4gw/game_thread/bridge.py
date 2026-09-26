"""The host side of the game-thread bridge: publish work, read what came back.

A bridge owns three things in one client:

    the block        allocated here, filled with ``empty_block``, read back to
                     confirm it landed where it was written
    the dispatcher   the emitted machine code, written and left executable
    the hook         installed on the function whose thread should run the work

The block and the dispatcher are placed first and the hook is installed **last**,
so a failure at any earlier step can release everything it made: nothing can reach
our code until the entry patch lands.

What the bridge does not own is the transport. The caller opened it and the caller
closes it. What the bridge also does not do is release its allocations when the
hook is removed — see :meth:`Bridge.remove`.

One command is one round trip: :meth:`Bridge.publish` fills the next slot and
advances the host's counter; :meth:`Bridge.wait` reads the record until the
payload has finished with it. Nothing waits on a lock, because there is no lock:
each side owns exactly one counter in each region and only reads the other's.
"""

from __future__ import annotations

import os
import struct
import threading
import time
from collections.abc import Mapping, Sequence

from .hooker import Hooker, WritableTarget
from .patcher import PAGE_EXECUTE_READ
from .payload import build_decoder_stub, build_dispatcher, build_observer
from .shared_block import (
    BLOCK_SIZE,
    COMMAND_DEPTH,
    COMMAND_SIZE,
    DECODE_DEPTH,
    DECODE_OUTPUT_SIZE,
    DECODE_SLOT_LENGTH_OFFSET,
    DECODE_SLOT_STATE_OFFSET,
    DESCRIPTOR_DEPTH,
    DESCRIPTOR_SIZE,
    EVENT_DEPTH,
    EVENT_SIZE,
    HEADER_OFFSET,
    HEADER_SIZE,
    TERMINAL_COMMAND_STATES,
    WATCH_DEPTH,
    WATCH_SIZE,
    BlockHeader,
    CommandRecord,
    DecodeState,
    Descriptor,
    EventKind,
    EventRecord,
    Operation,
    command_offset,
    data_offset,
    decode_input_offset,
    decode_output_offset,
    decode_slot_image,
    decode_slot_offset,
    decode_state_from_word,
    decode_text_from_bytes,
    descriptor_offset,
    empty_block,
    event_offset,
    free_slots,
    pending,
    read_header,
)

#: What the bridge calls the one hook it installs.
HOOK_NAME = "game_thread"

#: What it calls the observing hook, when the caller asks for one.
OBSERVER_NAME = "observe"

#: The observer's stub forwards the hooked function's first two arguments, which
#: are the message id and its packet. Its payload pops the block and those two,
#: so this number and the observer's epilogue have to agree.
OBSERVER_ARGUMENTS = 2

#: The observer is placed in its **post-call** form: what it records is read where the
#: source reads it, after the client's own send has run and before its caller gets
#: control back (``SendUIMessage`` runs the altitude-``0x1`` callbacks after the
#: original returns, ``ui_methods.cpp:1390-1404``; the dialog registers at that
#: altitude, ``dialog.cpp:1273-1292``). The entry form is the dispatcher's.
OBSERVER_AFTER = True

#: How long a command gets to complete, for callers that do not say.
DEFAULT_TIMEOUT_MS = 2000

#: How long to wait between reads of a record or of the hit counter.
POLL_SECONDS = 0.001

_UINT32_MAX = 0xFFFFFFFF


def _new_session_id() -> int:
    """Return a nonzero session id for one attach.

    The block carries it so a host can tell one attach from another; the payload
    does not read it, because it decides nothing about addressing.
    """

    return int.from_bytes(os.urandom(4), "little") or 1


class Bridge:
    """Publish commands to one client's game thread and read what came back."""

    def __init__(
        self,
        access: WritableTarget,
        pid: int,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> None:
        """Create a bridge over an already-open transport."""

        if pid <= 0:
            raise ValueError("pid must be positive.")
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive.")

        self._access = access
        self._pid = pid
        self._timeout_ms = timeout_ms
        self._block_address = 0
        self._call_table_address = 0
        self._watch_address = 0
        self._dispatcher_address = 0
        self._observer_address = 0
        self._decoder_address = 0
        self._hooker: Hooker | None = None
        self._observer_hooker: Hooker | None = None
        #: One use of the command ring at a time. Every publish goes through :meth:`publish`,
        #: and a call holds this across its wait as well, so two threads cannot interleave
        #: their publishes. It is **reentrant** because a call *is* a publish: ``call`` takes
        #: the ring and then publishes into it on the same thread. The payload is not party to
        #: any of this — the lock is the host's, held for the length of a call.
        self._call_lock = threading.RLock()
        #: The decode slots in flight, and the ones whose completion has already been handed to
        #: the host. Both threads touch these — a caller starts a decode, the listener reports
        #: what finished — so they are behind the one lock this side owns. Nothing in the client
        #: takes it: it is the host's own bookkeeping, not the transport's.
        self._decode_lock = threading.Lock()
        self._decode_slots: dict[int, bool] = {}

    # -- what it is --------------------------------------------------------

    @property
    def pid(self) -> int:
        """Return the process this bridge works in."""

        return self._pid

    @property
    def timeout_ms(self) -> int:
        """Return how long a command gets by default."""

        return self._timeout_ms

    @property
    def installed(self) -> bool:
        """Return whether the hook is currently placed."""

        return self._hooker is not None and HOOK_NAME in self._hooker.installed

    @property
    def observing(self) -> bool:
        """Return whether an observing hook is currently placed."""

        return (
            self._observer_hooker is not None
            and OBSERVER_NAME in self._observer_hooker.installed
        )

    @property
    def watch_address(self) -> int:
        """Return where the watch list is, or zero when there is none."""

        return self._watch_address

    @property
    def observer_address(self) -> int:
        """Return where the observer's code is, or zero when there is none."""

        return self._observer_address

    @property
    def block_address(self) -> int:
        """Return where the shared block is, or zero before it is placed."""

        return self._block_address

    @property
    def call_table_address(self) -> int:
        """Return where the call table is, or zero before it is placed."""

        return self._call_table_address

    @property
    def dispatcher_address(self) -> int:
        """Return where the dispatcher is, or zero before it is placed."""

        return self._dispatcher_address

    @property
    def decoder_address(self) -> int:
        """Return where the decoder stub is, or zero before it is placed.

        This is the address the client's decoder calls with the text it produced, so it is what
        a decode call is handed as its callback — the port of the ``DecodeStr_Callback`` native
        passes to ``AsyncDecodeStr``.
        """

        return self._decoder_address

    # -- placing and taking back -------------------------------------------

    def install(
        self,
        target: int,
        displaced: bytes,
        session_id: int | None = None,
        calls: Mapping[int, Descriptor] | None = None,
        module_base: int = 0,
        module_size: int = 0,
        watch: Sequence[tuple[int, int]] = (),
        observing: tuple[int, bytes] | None = None,
    ) -> None:
        """Place the block, the call table, the dispatcher and the hook.

        ``target`` is the function whose thread should run the work, and
        ``displaced`` the whole instructions the entry patch replaces. The bytes
        at ``target`` have to match ``displaced`` or the installer refuses: that
        is what catches a wrong address or a client that changed underneath us.

        ``calls`` fills the call table the dispatcher reads: slot to descriptor,
        which the caller resolved. ``module_base``/``module_size`` bound what may
        be called, and without them the dispatcher refuses every call — a call is
        the one thing this bridge does that the client did not ask for, so it
        happens only inside a declared range.

        ``watch`` is a list of ``(message id, string offset)`` entries and ``observing`` is the
        function to watch them on as ``(target, displaced)``. With those, that function gets a
        second hook whose payload records a watched call as an event, **and copies the string the
        message names** — read there because that is the only moment it is the client's own.
        """

        if self._hooker is not None:
            raise RuntimeError(f"pid {self._pid}: the bridge is already installed.")

        session = _new_session_id() if session_id is None else session_id
        block_address = self._access.allocate(BLOCK_SIZE)
        table_address = 0
        watch_address = 0
        observer_address = 0
        dispatcher_address = 0
        decoder_address = 0
        try:
            self._place_block(block_address, session)
            table_address = self._place_call_table(calls or {})

            code = build_dispatcher(table_address, module_base, module_size)
            dispatcher_address = self._access.allocate(len(code))
            self._access.write(dispatcher_address, code)
            self._access.protect(dispatcher_address, len(code), PAGE_EXECUTE_READ)
            self._access.flush_instruction_cache(dispatcher_address, len(code))

            # The decoder stub is placed whether or not this install observes anything: it is
            # the callback a decode is handed, and a decode is something a *caller* asks for
            # later, not something this install knows about yet. Native's equivalent is compiled
            # into its runtime and always there.
            decoder = build_decoder_stub()
            decoder_address = self._access.allocate(len(decoder))
            self._access.write(decoder_address, decoder)
            self._access.protect(decoder_address, len(decoder), PAGE_EXECUTE_READ)
            self._access.flush_instruction_cache(decoder_address, len(decoder))

            hooker = Hooker(
                self._access,
                self._pid,
                block_address,
                dispatcher_address,
                self._timeout_ms,
            )
            hooker.install(HOOK_NAME, target, displaced)

            observer_hooker: Hooker | None = None
            if observing is not None:
                watch_address = self._place_watch_list(watch)
                observer = build_observer(watch_address, WATCH_DEPTH)
                observer_address = self._access.allocate(len(observer))
                self._access.write(observer_address, observer)
                self._access.protect(
                    observer_address, len(observer), PAGE_EXECUTE_READ
                )
                self._access.flush_instruction_cache(
                    observer_address, len(observer)
                )
                observer_hooker = Hooker(
                    self._access,
                    self._pid,
                    block_address,
                    observer_address,
                    self._timeout_ms,
                )
                observe_target, observe_displaced = observing
                observer_hooker.install(
                    OBSERVER_NAME,
                    observe_target,
                    observe_displaced,
                    forwarded_arguments=OBSERVER_ARGUMENTS,
                    after=OBSERVER_AFTER,
                )
        except BaseException:
            # The entry patches are the last steps and they did not complete, so
            # nothing can be running our code and what this made can go back.
            for address in (
                observer_address,
                watch_address,
                decoder_address,
                dispatcher_address,
                table_address,
                block_address,
            ):
                if address:
                    self._access.free(address)
            raise

        self._block_address = block_address
        self._call_table_address = table_address
        self._watch_address = watch_address
        self._dispatcher_address = dispatcher_address
        self._observer_address = observer_address
        self._decoder_address = decoder_address
        self._hooker = hooker
        self._observer_hooker = observer_hooker

    def remove(self, free_allocations: bool = False) -> None:
        """Disable dispatch and restore both hooked functions' own bytes.

        Both hooks come out, the observing one first: it is the one on a function
        the client calls constantly, so it is the one worth removing soonest.

        ``free_allocations`` releases everything this bridge placed — the block,
        the call table, the watch list, the dispatcher, the observer, the decoder stub and the
        hooker's own generated code. A caller that connects and disconnects as a
        routine asks for it, so connecting does not accumulate memory in a client
        that outlives the controller. The default leaves everything mapped, which
        is what a one-off install wants and what the hooker's reasoning describes.

        **A decode still in flight is refused here, not freed underneath.** The decoder stub is
        the callback the client will call, and freeing it while the client still holds its
        address is how a controller takes the client down with it; the caller drains first
        (``ConnectedClient.close`` does, through the dialog module's own shutdown).
        """

        if self._observer_hooker is not None and self.observing:
            self._observer_hooker.remove(OBSERVER_NAME, free_code=free_allocations)
        self.require_hooker().remove(HOOK_NAME, free_code=free_allocations)

        if free_allocations:
            in_flight = self.decodes_in_flight()
            if in_flight:
                raise RuntimeError(
                    f"pid {self._pid}: {in_flight} string decodes are still in flight, and "
                    "the decoder stub the client will call cannot be freed while they are. "
                    "Drain them before removing the bridge."
                )
            for address in (
                self._observer_address,
                self._watch_address,
                self._decoder_address,
                self._dispatcher_address,
                self._call_table_address,
                self._block_address,
            ):
                if address:
                    self._access.free(address)
            self._observer_address = 0
            self._watch_address = 0
            self._decoder_address = 0
            self._dispatcher_address = 0
            self._call_table_address = 0
            self._block_address = 0

    # -- the queue ---------------------------------------------------------

    def header(self) -> BlockHeader:
        """Read and validate the block's header as it is now."""

        self._require_block()
        raw = self._access.read(self._block_address, HEADER_SIZE)
        try:
            return read_header(raw)
        except ValueError as error:
            raise RuntimeError(
                f"pid {self._pid}: the block at 0x{self._block_address:08X} no "
                f"longer decodes: {error}"
            ) from error

    def publish(
        self,
        operation: Operation | int,
        arg0: int = 0,
        arg1: int = 0,
        arg2: int = 0,
        arg3: int = 0,
        arg4: int = 0,
        arg5: int = 0,
    ) -> int:
        """Publish one command and return the sequence number it was given.

        The record is filled in first and the host's counter moves afterwards,
        so a payload reading below that counter can never see a half-written
        command. A command's sequence number *is* that counter, which is why its
        slot is the sequence's low bits.

        The six words are the record's whole argument area. A ``CALL``'s ``arg0`` is the
        call table slot, so a call carries five words — which is the widest source
        declaration the vocabulary covers today.

        The publish itself is serialised with every other use of the ring (see ``call``); the
        wait that follows a bare publish is the caller's own, and reads only its own record.
        """

        with self._call_lock:
            header = self.header()
            if free_slots(
                header.command_written, header.command_taken, COMMAND_DEPTH
            ) < 1:
                raise RuntimeError(
                    f"pid {self._pid}: all {COMMAND_DEPTH} command slots are "
                    "outstanding; the payload has not taken what it was given."
                )

            sequence = header.command_written
            record = CommandRecord(
                sequence=sequence,
                operation=int(operation),
                arg0=arg0,
                arg1=arg1,
                arg2=arg2,
                arg3=arg3,
                arg4=arg4,
                arg5=arg5,
            )
            self._access.write(
                self._block_address + command_offset(sequence % COMMAND_DEPTH),
                record.to_bytes(),
            )
            self._write_uint32(
                HEADER_OFFSET["command_written"], header.command_written + 1
            )
            return sequence

    def wait(self, sequence: int, timeout_ms: int | None = None) -> CommandRecord:
        """Return the record for ``sequence``, once the payload is finished.

        The record's own sequence number has to match: a slot is reused every
        lap of the ring, and returning another command's result would be worse
        than returning nothing.
        """

        self._require_block()
        timeout = self._timeout_ms if timeout_ms is None else timeout_ms
        address = self._block_address + command_offset(sequence % COMMAND_DEPTH)
        deadline = time.monotonic() + timeout / 1000.0
        while True:
            record = CommandRecord.from_bytes(
                self._access.read(address, COMMAND_SIZE)
            )
            if (
                record.sequence == sequence
                and record.state in TERMINAL_COMMAND_STATES
            ):
                return record
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"pid {self._pid}: command {sequence} did not complete within "
                    f"{timeout} ms. Slot {sequence % COMMAND_DEPTH} holds sequence "
                    f"{record.sequence} in state {record.state.name}."
                )
            time.sleep(POLL_SECONDS)

    def submit(
        self,
        operation: Operation | int,
        arg0: int = 0,
        arg1: int = 0,
        arg2: int = 0,
        arg3: int = 0,
        arg4: int = 0,
        arg5: int = 0,
        timeout_ms: int | None = None,
    ) -> CommandRecord:
        """Publish one command and wait for its result.

        Held across both, for the same reason ``call`` is: the pair is one use of the ring, and
        a second publisher slipping in between would take the next slot while this one waits.
        """

        with self._call_lock:
            return self.wait(
                self.publish(operation, arg0, arg1, arg2, arg3, arg4, arg5), timeout_ms
            )

    def publish_call(
        self,
        slot: int,
        arg1: int = 0,
        arg2: int = 0,
        arg3: int = 0,
        arg4: int = 0,
        arg5: int = 0,
    ) -> int:
        """Publish a call to one table slot and return its sequence number.

        ``slot`` names the descriptor, and the five words are the form's: the
        descriptor says what they mean, so the same words are a message id and two
        packed fields for one form and something else for the next.

        The sequence is the ``command_written`` counter's value **before** it
        advances, so the first command published through a block is sequence
        ``0``. Anything waiting on a completion event has to allow for that.
        """

        return self.publish(Operation.CALL, slot, arg1, arg2, arg3, arg4, arg5)

    def call(
        self,
        slot: int,
        arg1: int = 0,
        arg2: int = 0,
        arg3: int = 0,
        arg4: int = 0,
        arg5: int = 0,
        timeout_ms: int | None = None,
    ) -> CommandRecord:
        """Call through one table slot and wait for the call to complete.

        Held for the whole publish-and-wait, because the command ring carries one call at a
        time: the dialog's body decode is issued from the listener thread while a caller may be
        calling something else, and two publishes into that ring would interleave.
        """

        with self._call_lock:
            return self.wait(
                self.publish_call(slot, arg1, arg2, arg3, arg4, arg5), timeout_ms
            )

    def events(self) -> list[EventRecord]:
        """Return the events published since the last call, oldest first.

        Reading them is what advances the host's counter, so a caller that never
        calls this leaves the payload's event region filling up — at which point
        the payload drops events rather than waiting.

        What the payload's own machine code recorded comes first, and then whatever string
        decodes the client has finished since the last read (``_decode_events``). Both are
        events the client produced; the second kind is read out of its slot rather than the
        event ring, because the code that fills it is the client's callback and not this
        project's payload.
        """

        header = self.header()
        count = pending(header.event_written, header.event_taken)
        if count > EVENT_DEPTH:
            raise RuntimeError(
                f"pid {self._pid}: the event region is corrupt: {count} records "
                f"are outstanding in {EVENT_DEPTH} slots."
            )

        records = []
        for index in range(count):
            slot = (header.event_taken + index) % EVENT_DEPTH
            records.append(
                EventRecord.from_bytes(
                    self._access.read(
                        self._block_address + event_offset(slot), EVENT_SIZE
                    )
                )
            )
        if count:
            self._write_uint32(HEADER_OFFSET["event_taken"], header.event_taken + count)
        records.extend(self._decode_events())
        return records

    def completions(self) -> list[EventRecord]:
        """Return the completion events among the events read."""

        return [
            event
            for event in self.events()
            if event.kind == EventKind.COMMAND_COMPLETE
        ]

    # -- the hook ----------------------------------------------------------

    def require_hooker(self) -> Hooker:
        """Return the hooker, or refuse if the bridge was never installed."""

        if self._hooker is None:
            raise RuntimeError(
                f"pid {self._pid}: the bridge has never been installed."
            )
        return self._hooker

    def hits(self) -> int:
        """Return how many times the hooked function has reached our stub."""

        return self.require_hooker().hits(HOOK_NAME)

    def wait_for_hits(
        self, minimum_delta: int = 1, timeout_ms: int | None = None
    ) -> int:
        """Wait until the hooked function has run at least ``minimum_delta`` times."""

        return self.require_hooker().wait_for_hits(
            HOOK_NAME,
            minimum_delta,
            self._timeout_ms if timeout_ms is None else timeout_ms,
        )

    # -- internals ---------------------------------------------------------

    def _place_watch_list(self, watch: Sequence[tuple[int, int]]) -> int:
        """Write the watch entries the observer compares and copies by, and return their address.

        An entry is a message id and the byte offset of the ``wchar_t*`` field that message
        carries, or zero for a message that carries no string — the observer copies that string
        out with the event, because the moment it runs is the only moment the string is the
        client's own. The list lives in the client and its address is emitted into the observer,
        so neither word travels through the queue. More entries than the list holds is refused
        rather than silently truncated.
        """

        if len(watch) > WATCH_DEPTH:
            raise ValueError(
                f"a watch list holds {WATCH_DEPTH} entries; {len(watch)} were given."
            )

        address = self._access.allocate(WATCH_DEPTH * WATCH_SIZE)
        self._access.write(address, bytes(WATCH_DEPTH * WATCH_SIZE))
        for index, (message, string_offset) in enumerate(watch):
            self._access.write(
                address + index * WATCH_SIZE,
                struct.pack(
                    "<II", message & _UINT32_MAX, string_offset & _UINT32_MAX
                ),
            )
        return address

    def _place_call_table(self, calls: Mapping[int, Descriptor]) -> int:
        """Write the call table, zeroed first so an unused slot names nothing.

        The table holds addresses, and it lives in the client. That is the point
        of it: a command names a slot, so no address ever travels through the
        queue, and a slot the host did not fill stays a zero entry the payload
        refuses rather than an address anyone chose.
        """

        for slot in calls:
            if not 0 <= slot < DESCRIPTOR_DEPTH:
                raise ValueError(f"call slot must be 0..{DESCRIPTOR_DEPTH - 1}")

        address = self._access.allocate(DESCRIPTOR_DEPTH * DESCRIPTOR_SIZE)
        self._access.write(address, bytes(DESCRIPTOR_DEPTH * DESCRIPTOR_SIZE))
        for slot, descriptor in calls.items():
            self._access.write(
                address + descriptor_offset(slot), descriptor.to_bytes()
            )
        return address

    def _place_block(self, address: int, session_id: int) -> None:
        """Write a fresh block and read it back before anything trusts it."""

        self._access.write(address, empty_block(session_id))
        raw = self._access.read(address, HEADER_SIZE)
        try:
            header = read_header(raw)
        except ValueError as error:
            raise RuntimeError(
                f"pid {self._pid}: the block written at 0x{address:08X} does not "
                f"decode: {error}"
            ) from error
        if header.session_id != session_id:
            raise RuntimeError(
                f"pid {self._pid}: the block at 0x{address:08X} read back with "
                f"session {header.session_id}, not {session_id}."
            )

    def _write_uint32(self, offset: int, value: int) -> None:
        """Write one counter in the header."""

        self._access.write(
            self._block_address + offset,
            struct.pack("<I", value & _UINT32_MAX),
        )

    # -- the data region ---------------------------------------------------

    def data_address(self, offset: int, size: int = 0) -> int:
        """Return the client address of a span inside the block's data region.

        A caller needs the address itself when a function it calls takes a **pointer**: the
        source's own callers hand over the address of one of their stack variables, and this
        project's equivalent is a span of the block, because the block is memory inside the
        client. The span is bounds-checked against the region, so a mistake here is a
        refusal rather than a write over the event ring.
        """

        self._require_block()
        return self._block_address + data_offset(offset, size)

    def write_data(self, offset: int, payload: bytes) -> int:
        """Write bytes into the data region, and return their address in the client."""

        address = self.data_address(offset, len(payload))
        self._access.write(address, payload)
        return address

    def read_data(self, offset: int, size: int) -> bytes:
        """Read a span back out of the data region."""

        return self._access.read(self.data_address(offset, size), size)

    def _require_block(self) -> None:
        """Refuse to read a block that was never placed."""

        if not self._block_address:
            raise RuntimeError(
                f"pid {self._pid}: the bridge has no block; install it first."
            )

    # -- strings the client decodes ----------------------------------------

    def begin_decode(self, encoded: bytes) -> int:
        """Place one encoded string for the client to decode, and return its slot.

        This is the half of native's ``AsyncDecodeStr`` this side can do: the string is put
        where the client can read it, and the slot it went into is the ``param`` the client's
        callback will be handed. The call itself belongs to the caller, because it needs the
        resolved address of the client's decoder — a catalog name this bridge does not know.

        Every slot busy is a refusal, and it is the same refusal native makes with its own cap
        on pending labels (``kMaxDecodedButtonLabelPending``, ``dialog.cpp:674``): a caller is
        told nothing was queued rather than handed a request that will never complete.
        """

        self._require_block()
        with self._decode_lock:
            free = [
                slot for slot in range(DECODE_DEPTH) if slot not in self._decode_slots
            ]
            if not free:
                raise RuntimeError(
                    f"pid {self._pid}: all {DECODE_DEPTH} decode slots are in flight, so "
                    f"this string was not queued."
                )
            slot = free[0]
            self._decode_slots[slot] = False
        self._access.write(
            self._block_address + decode_slot_offset(slot),
            decode_slot_image(slot, encoded),
        )
        return slot

    def decode_input_address(self, slot: int) -> int:
        """Return the client address of the string one slot is holding."""

        self._require_block()
        return self._block_address + decode_input_offset(slot)

    def decode_slot_address(self, slot: int) -> int:
        """Return the client address of a slot, which is the ``param`` its callback is given."""

        self._require_block()
        return self._block_address + decode_slot_offset(slot)

    def complete_decode(self, slot: int, text: str) -> None:
        """Write a decode's answer into its slot without a call having been made.

        Three of the client's decoder's own refusals answer the callback themselves
        (``ui_methods.cpp:2583-2598``: no decoder, not an encoded string, no text parser). Here
        that answer is written where the callback would have written it, so a caller reads one
        kind of completion whichever way the decode ended — and the completion is delivered as
        an event like any other, because the slot is still marked unreported.
        """

        self._require_block()
        payload = text.encode("utf-16-le")
        if len(payload) > DECODE_OUTPUT_SIZE:
            raise ValueError(
                f"a decode answer of {len(payload)} bytes does not fit a "
                f"{DECODE_OUTPUT_SIZE}-byte slot."
            )
        start = self._block_address + decode_slot_offset(slot)
        self._access.write(self._block_address + decode_output_offset(slot), payload)
        self._access.write(
            start + DECODE_SLOT_LENGTH_OFFSET, struct.pack("<I", len(text))
        )
        self._access.write(
            start + DECODE_SLOT_STATE_OFFSET, struct.pack("<I", DecodeState.DONE)
        )

    def release_decode(self, slot: int) -> None:
        """Give a slot back when the decode it was holding will never happen.

        ``SafeAsyncDecodeStr``'s false, on this side of the boundary: nothing was asked of the
        client, so nothing will call back, and the slot must not be left in flight.
        """

        self._require_block()
        start = self._block_address + decode_slot_offset(slot)
        self._access.write(
            start + DECODE_SLOT_STATE_OFFSET, struct.pack("<I", DecodeState.FREE)
        )
        with self._decode_lock:
            self._decode_slots.pop(slot, None)

    def decode_state(self, slot: int) -> DecodeState:
        """Return what has happened to one decode slot, without taking anything from it."""

        self._require_block()
        raw = self._access.read(
            self._block_address + decode_slot_offset(slot) + DECODE_SLOT_STATE_OFFSET, 4
        )
        return decode_state_from_word(struct.unpack("<I", raw)[0])

    def take_decoded_string(self, slot: int) -> tuple[str, bool]:
        """Read the text the client decoded, and put the slot back to free.

        Called once per completion, which is what native's ``Release...DecodeRequest`` is: the
        request is finished with as soon as its answer has been taken.
        """

        self._require_block()
        start = self._block_address + decode_slot_offset(slot)
        (length,) = struct.unpack(
            "<I",
            self._access.read(start + DECODE_SLOT_LENGTH_OFFSET, 4),
        )
        payload = self._access.read(
            self._block_address + decode_output_offset(slot), DECODE_OUTPUT_SIZE
        )
        text, truncated = decode_text_from_bytes(payload, length)
        self._access.write(start + DECODE_SLOT_STATE_OFFSET, struct.pack("<I", DecodeState.FREE))
        self._access.write(start + DECODE_SLOT_LENGTH_OFFSET, struct.pack("<I", 0))
        with self._decode_lock:
            self._decode_slots.pop(slot, None)
        return text, truncated

    def decodes_in_flight(self) -> int:
        """Return how many decodes have been asked for and not yet taken."""

        with self._decode_lock:
            return len(self._decode_slots)

    def _decode_events(self) -> list[EventRecord]:
        """Return one completion event for every decode the client has finished.

        Native is told by the client calling back; this side is told by reading the slot the
        callback wrote. The event is reported **once** — a report is not the same as taking the
        text, which the handler does through :meth:`take_decoded_string` — so a poll that sees
        the same finished slot twice does not deliver the same callback twice.
        """

        with self._decode_lock:
            outstanding = list(self._decode_slots.items())

        events: list[EventRecord] = []
        for slot, reported in outstanding:
            if reported:
                continue
            raw = self._access.read(
                self._block_address + decode_slot_offset(slot) + DECODE_SLOT_STATE_OFFSET,
                4,
            )
            state = decode_state_from_word(struct.unpack("<I", raw)[0])
            if state is DecodeState.FREE or state is DecodeState.IN_FLIGHT:
                continue
            (length,) = struct.unpack(
                "<I",
                self._access.read(
                    self._block_address
                    + decode_slot_offset(slot)
                    + DECODE_SLOT_LENGTH_OFFSET,
                    4,
                ),
            )
            events.append(
                EventRecord(
                    kind=EventKind.STRING_DECODED,
                    sequence=slot,
                    arg0=length,
                    arg1=1 if state is DecodeState.FAILED else 0,
                )
            )
            with self._decode_lock:
                self._decode_slots[slot] = True
        return events

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
import time
from collections.abc import Mapping, Sequence

from .hooker import Hooker, WritableTarget
from .patcher import PAGE_EXECUTE_READ
from .payload import build_dispatcher, build_observer
from .shared_block import (
    BLOCK_SIZE,
    COMMAND_DEPTH,
    COMMAND_SIZE,
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
    Descriptor,
    EventKind,
    EventRecord,
    Operation,
    command_offset,
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
        self._hooker: Hooker | None = None
        self._observer_hooker: Hooker | None = None

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

    # -- placing and taking back -------------------------------------------

    def install(
        self,
        target: int,
        displaced: bytes,
        session_id: int | None = None,
        calls: Mapping[int, Descriptor] | None = None,
        module_base: int = 0,
        module_size: int = 0,
        watch: Sequence[int] = (),
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

        ``watch`` is a list of message ids, and ``observing`` is the function to
        watch them on as ``(target, displaced)``. With those, that function gets a
        second hook whose payload records a watched call as an event — which is
        how this project reads something the client only ever says once.
        """

        if self._hooker is not None:
            raise RuntimeError(f"pid {self._pid}: the bridge is already installed.")

        session = _new_session_id() if session_id is None else session_id
        block_address = self._access.allocate(BLOCK_SIZE)
        table_address = 0
        watch_address = 0
        observer_address = 0
        dispatcher_address = 0
        try:
            self._place_block(block_address, session)
            table_address = self._place_call_table(calls or {})

            code = build_dispatcher(table_address, module_base, module_size)
            dispatcher_address = self._access.allocate(len(code))
            self._access.write(dispatcher_address, code)
            self._access.protect(dispatcher_address, len(code), PAGE_EXECUTE_READ)
            self._access.flush_instruction_cache(dispatcher_address, len(code))

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
                )
        except BaseException:
            # The entry patches are the last steps and they did not complete, so
            # nothing can be running our code and what this made can go back.
            for address in (
                observer_address,
                watch_address,
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
        self._hooker = hooker
        self._observer_hooker = observer_hooker

    def remove(self, free_allocations: bool = False) -> None:
        """Disable dispatch and restore both hooked functions' own bytes.

        Both hooks come out, the observing one first: it is the one on a function
        the client calls constantly, so it is the one worth removing soonest.

        ``free_allocations`` releases everything this bridge placed — the block,
        the call table, the watch list, the dispatcher, the observer and the
        hooker's own generated code. A caller that connects and disconnects as a
        routine asks for it, so connecting does not accumulate memory in a client
        that outlives the controller. The default leaves everything mapped, which
        is what a one-off install wants and what the hooker's reasoning describes.
        """

        if self._observer_hooker is not None and self.observing:
            self._observer_hooker.remove(OBSERVER_NAME, free_code=free_allocations)
        self.require_hooker().remove(HOOK_NAME, free_code=free_allocations)

        if free_allocations:
            for address in (
                self._observer_address,
                self._watch_address,
                self._dispatcher_address,
                self._call_table_address,
                self._block_address,
            ):
                if address:
                    self._access.free(address)
            self._observer_address = 0
            self._watch_address = 0
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
    ) -> int:
        """Publish one command and return the sequence number it was given.

        The record is filled in first and the host's counter moves afterwards,
        so a payload reading below that counter can never see a half-written
        command. A command's sequence number *is* that counter, which is why its
        slot is the sequence's low bits.
        """

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
        timeout_ms: int | None = None,
    ) -> CommandRecord:
        """Publish one command and wait for its result."""

        return self.wait(
            self.publish(operation, arg0, arg1, arg2, arg3), timeout_ms
        )

    def publish_call(
        self, slot: int, arg1: int = 0, arg2: int = 0, arg3: int = 0
    ) -> int:
        """Publish a call to one table slot and return its sequence number.

        ``slot`` names the descriptor, and the three words are the form's: the
        descriptor says what they mean, so the same three words are a message id
        and two packed fields for one form and something else for the next.
        """

        return self.publish(Operation.CALL, slot, arg1, arg2, arg3)

    def call(
        self,
        slot: int,
        arg1: int = 0,
        arg2: int = 0,
        arg3: int = 0,
        timeout_ms: int | None = None,
    ) -> CommandRecord:
        """Call through one table slot and wait for the call to complete."""

        return self.wait(
            self.publish_call(slot, arg1, arg2, arg3), timeout_ms
        )

    def events(self) -> list[EventRecord]:
        """Return the events published since the last call, oldest first.

        Reading them is what advances the host's counter, so a caller that never
        calls this leaves the payload's event region filling up — at which point
        the payload drops events rather than waiting.
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

    def _place_watch_list(self, messages: Sequence[int]) -> int:
        """Write the message ids the observer records, and return their address.

        The list lives in the client and its address is emitted into the observer,
        so no message id travels through the queue either. More ids than the list
        holds is refused rather than silently truncated.
        """

        if len(messages) > WATCH_DEPTH:
            raise ValueError(
                f"a watch list holds {WATCH_DEPTH} message ids; "
                f"{len(messages)} were given."
            )

        address = self._access.allocate(WATCH_DEPTH * WATCH_SIZE)
        self._access.write(address, bytes(WATCH_DEPTH * WATCH_SIZE))
        for index, message in enumerate(messages):
            self._access.write(
                address + index * WATCH_SIZE,
                struct.pack("<I", message & _UINT32_MAX),
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

    def _require_block(self) -> None:
        """Refuse to read a block that was never placed."""

        if not self._block_address:
            raise RuntimeError(
                f"pid {self._pid}: the bridge has no block; install it first."
            )

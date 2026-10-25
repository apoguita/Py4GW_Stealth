"""The client's StoC handler array, and replacing one header's handler with emitted code.

**This is not a hook on a function.** Native takes a packet callback by *replacing the client's own
handler* for that header and keeping the original to chain to:

```c
if (g_game_server_handlers && g_game_server_handlers->size() > header) {
    g_game_server_handlers->at(header).handler_func = &StoCHandler_Func;   // stoc_methods.cpp:55-57
    success = true;
}
```

and it snapshots the whole array first, so `DisableHooks` can put every entry back
(``stoc.cpp:118-140``). This module is that: the walk to the array, the replacement, and the
restore. The emitted stub that goes into the entry is ``payload.build_packet_stub``.

**The walk is native's own.** ``stoc.handler_table_addr`` resolves to the address of the
``GameServer*`` **variable** — native casts it to ``GameServer**`` and dereferences it before reading
``gs_codec`` (``stoc_patterns.cpp:43-50``), which is what the port's resolver's ``deref_ptr`` step
produces. ``gs_codec`` sits at ``+0x8`` of the game server and ``handlers`` at ``+0x2C`` of the codec
(``stoc.cpp:26-41``: ``h0000[12]``, the ``ls_codec`` pointer, ``h0010[12]``, ``client_codec_array[4]``,
then ``handlers``). Read-only against the running client, this project's probe measured the whole
chain and every merchant header (``tests/probe_stoc_handlers.py``, ``tests/live_reports/stoc_handlers.json``):
the server at ``0x1D6BC90``, the codec at ``0x1D63388``, 487 entries of which the five this port wants
are all in range and hold real code.

**One stub per header, and why.** Native shares one ``StoCHandler_Func`` across every header because
its callbacks are compiled C++ that read each packet's own struct; emitted code cannot, so a stub
carries the header and the number of words its listener reads as immediates
(``payload.build_packet_stub``). Everything else is the source's: the entry is replaced only for a
header in range, the client's own handler is saved first, the stub chains to it, and the restore puts
the saved pointers back.

**The write goes through the game thread.** The new pointer is placed in the block's data region and
copied into the client's entry by the payload's ``WRITE_MEMORY`` operation, which runs inside the
hooked client function — the same route every other client-state write in this project takes
(``camera.py``, ``ui/preferences.py``, ``frame.py``). Native writes it under its own critical section
from whichever thread registered the callback; here the write is serialised with the client's own
dispatch instead of with a lock this side cannot take, and the entry is read back afterwards, because
a write that did not land is the one thing this must not assume.
"""

from __future__ import annotations

import struct
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import IntEnum
from typing import Protocol

from .hooker import FREE_WAIT_SECONDS, HIT_POLL_SECONDS, WritableTarget
from .patcher import PAGE_EXECUTE_READ
from .payload import build_packet_stub
from .shared_block import (
    CommandRecord,
    CommandState,
    DATA_REGION_OFFSET,
    K_MAX_COMPUTED_PACKET_BYTES,
    Operation,
    PACKET_BASE_SIZE,
    PacketCapture,
)


class PacketBridge(Protocol):
    """What these hooks need from a bridge: the block, the transport, and the write path.

    A protocol rather than the class itself, because the bridge is what installs these hooks — the
    same reason ``hooker.py`` takes ``TargetAccess`` (``hooker.py:49-53``) instead of the patcher
    that owns it.
    """

    @property
    def block_address(self) -> int: ...

    @property
    def access(self) -> WritableTarget: ...

    @property
    def module_range(self) -> tuple[int, int]: ...

    @property
    def loaded_modules(self) -> Sequence[tuple[int, int]]: ...

    def write_data(self, offset: int, payload: bytes) -> int: ...

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
    ) -> CommandRecord: ...


#: Where ``GameServer.gs_codec`` sits (``stoc.cpp:26-41``). The server structure's own head is
#: eight bytes and the codec pointer follows it.
GAME_SERVER_CODEC_OFFSET = 0x8

#: Where ``handlers`` sits inside the codec: ``h0000[12]``, the ``ls_codec`` pointer, ``h0010[12]``,
#: ``client_codec_array[4]``, then the array.
CODEC_HANDLERS_OFFSET = 0x2C

#: ``GW::GWArray<T>`` — the buffer, the capacity, the size, then a word the class keeps unused
#: (``GW/common/gw_array.h:61-64``). Only the first three are read.
ARRAY_BUFFER_OFFSET = 0x0
ARRAY_CAPACITY_OFFSET = 0x4
ARRAY_SIZE_OFFSET = 0x8
ARRAY_SIZE = 0x10

#: One ``StoCHandler``: the template pointer, how many descriptors it has, and the handler
#: (``stoc_patterns.cpp:9-13``). Only the handler is touched.
ENTRY_TEMPLATE_OFFSET = 0x0
ENTRY_FIELD_COUNT_OFFSET = 0x4
ENTRY_HANDLER_OFFSET = 0x8
ENTRY_SIZE = 0xC

#: Where the two things this module keeps in the block's data region sit, above the ``Map`` family's
#: last span (``map._UI_STATE_OFFSET`` ends at ``0xF44``) and below the region's ``0x1000`` bound. The
#: pointer being written is staged in the first so ``WRITE_MEMORY`` has a source; the second is the
#: count of stubs running right now, which is what :meth:`PacketHooks.remove` waits on.
PACKET_POINTER_OFFSET = 0xF50
PACKET_INFLIGHT_OFFSET = 0xF54


def is_live_code(
    address: int,
    module_base: int,
    module_size: int,
    loaded_modules: Sequence[tuple[int, int]] = (),
) -> bool:
    """Whether a pointer is inside code that is loaded **right now**.

    The client's own module is the ordinary answer. Another runtime's compiled handler is the other one: it
    lives inside that runtime's own module image, which is what a loaded module's range covers — measured
    live on 2026-10-01, header 132's handler was ``0x578F1ED3`` inside ``Py4GW.dll``.

    What is **not** live is memory no module covers: that is where a controller that has died leaves its
    own generated stub, and chaining to one means jumping into memory nobody owns, on the client's own
    thread. The two are told apart by asking the module list, not by guessing from the address.
    """

    if module_base <= address < module_base + module_size:
        return True
    return any(base <= address < base + size for base, size in loaded_modules)


def _read_uint32(access: WritableTarget, address: int) -> int:
    """Read one word from the client."""

    return int(struct.unpack("<I", access.read(address, 4))[0])


@dataclass(frozen=True)
class HandlerTable:
    """The client's handler array, as one read of it found it."""

    #: The address of the ``GWArray`` itself, which is what a caller holds on to.
    address: int
    #: Where the entries are.
    buffer: int
    capacity: int
    size: int

    def entry(self, header: int) -> int:
        """Return the address of one header's entry, refusing one the array does not hold."""

        if not 0 <= header < self.size:
            raise ValueError(
                f"the client's handler array holds {self.size} entries; header "
                f"{header} is not one of them."
            )
        return self.buffer + header * ENTRY_SIZE

    def handler(self, header: int) -> int:
        """Return the handler one header currently runs."""

        return self.entry(header) + ENTRY_HANDLER_OFFSET


def read_handler_table(access: WritableTarget, table_address: int) -> HandlerTable:
    """Follow native's walk from the resolved table address to the client's handler array.

    ``ResolveGameServerHandlers`` refuses a server, a codec or an array it cannot reach
    (``stoc_patterns.cpp:43-50``); each of those is a different failure here, and each names what was
    missing rather than returning an array with nothing in it.
    """

    if not table_address:
        raise ValueError("stoc.handler_table_addr resolved to nothing.")

    game_server = _read_uint32(access, table_address)
    if not game_server:
        raise RuntimeError(
            f"the game server pointer at 0x{table_address:08X} is null: the client has not "
            "built its codec yet."
        )

    codec = _read_uint32(access, game_server + GAME_SERVER_CODEC_OFFSET)
    if not codec:
        raise RuntimeError(
            f"the game server at 0x{game_server:08X} has no codec, so it has no handler array."
        )

    address = codec + CODEC_HANDLERS_OFFSET
    raw = access.read(address, ARRAY_SIZE)
    buffer = int(struct.unpack_from("<I", raw, ARRAY_BUFFER_OFFSET)[0])
    capacity = int(struct.unpack_from("<I", raw, ARRAY_CAPACITY_OFFSET)[0])
    size = int(struct.unpack_from("<I", raw, ARRAY_SIZE_OFFSET)[0])
    if not buffer:
        raise RuntimeError(
            f"the handler array at 0x{address:08X} has no entries buffer."
        )
    if size > capacity:
        raise RuntimeError(
            f"the handler array at 0x{address:08X} says {size} entries in {capacity} slots, "
            "which is not an array."
        )
    return HandlerTable(address=address, buffer=buffer, capacity=capacity, size=size)


def _covers(stub: PacketStub, words: int, capture: PacketCapture | None) -> bool:
    """Whether an already placed stub already records what a new registration asks for."""

    if stub.words < words:
        return False
    if capture is None:
        return True
    return stub.capture is not None


#: ``kMaxStoCPacketBuffer`` (``packet_sniffer.h:28``): how much of an inbound packet the sniffer
#: keeps, whatever its walked size says.
K_MAX_STOC_PACKET_BUFFER = 512


class FieldKind(IntEnum):
    """The kinds of field one template descriptor can describe (``stoc_methods.cpp:118-132``).

    A descriptor is ``type`` in bits 0-3, ``size`` in bits 4-7 and ``count`` in bits 8-23
    (``:114-116``). The widths below are wire widths, which is what the walk sums.
    """

    AgentId = 0
    Float = 1
    Vect2 = 2
    Vect3 = 3
    #: ``Byte``, ``Word`` and ``Dword`` are all serialized as a four-byte value (``:142-144``).
    Fixed4 = 4
    Blob = 5
    #: Template bookkeeping entries (e.g. array-end markers); no wire bytes at all.
    Ignore = 6
    String16 = 7
    Array8 = 8
    Array16 = 9
    Array32 = 10
    #: ``GW`` always places at most one nested struct, and always last (``:225``).
    NestedStruct = 11
    Unknown = 12


def decode_field_kind(descriptor: int) -> FieldKind:
    """Port of ``DecodeFieldKind`` (``stoc_methods.cpp:134-165``): one descriptor's kind."""

    field_type = descriptor & 0xF
    field_size = (descriptor >> 4) & 0xF
    if field_type == 0:
        return FieldKind.AgentId
    if field_type == 1:
        return FieldKind.Float
    if field_type == 2:
        return FieldKind.Vect2
    if field_type == 3:
        return FieldKind.Vect3
    if field_type in (4, 8):
        return FieldKind.Fixed4
    if field_type in (5, 9):
        return FieldKind.Blob
    if field_type in (6, 10):
        return FieldKind.Ignore
    if field_type == 7:
        return FieldKind.String16
    if field_type == 11:
        if field_size == 1:
            return FieldKind.Array8
        if field_size == 2:
            return FieldKind.Array16
        if field_size == 4:
            return FieldKind.Array32
        return FieldKind.Unknown
    if field_type == 12:
        return FieldKind.NestedStruct
    return FieldKind.Unknown


def _field_width(kind: FieldKind, count: int) -> int:
    """Return one field's wire width, which is what the walk adds (``stoc_methods.cpp:181-235``)."""

    if kind in (FieldKind.AgentId, FieldKind.Float, FieldKind.Fixed4):
        return 4
    if kind is FieldKind.Vect2:
        return 8
    if kind is FieldKind.Vect3:
        return 12
    if kind in (FieldKind.Blob, FieldKind.Array8):
        return count
    if kind in (FieldKind.String16, FieldKind.Array16):
        return count * 2
    if kind is FieldKind.Array32:
        return count * 4
    return 0


def read_template(access: WritableTarget, entry: int) -> tuple[tuple[int, ...], int]:
    """Read one handler's own field template: its descriptors and its declared count.

    Native's ``StoCHandler`` is ``{uint32_t* packet_template; uint32_t field_count; handler_func}``
    (``stoc_methods.cpp:9-13``), so the first two words of a live entry are what the size walk reads.
    ``field_count`` counts **uint32_t descriptors and is not a byte size** — that distinction is the
    whole reason the walk exists (``stoc.cpp:20``).
    """

    template, field_count = struct.unpack("<II", access.read(entry, 8))
    if not template or not field_count:
        return (), 0
    if field_count > K_MAX_COMPUTED_PACKET_BYTES // 4:
        raise ValueError(
            f"the handler at 0x{entry:08X} declares {field_count} template descriptors, which is "
            "past any template a packet can have."
        )
    raw = access.read(template, field_count * 4)
    return struct.unpack(f"<{field_count}I", raw), field_count


def describe_template(descriptors: Sequence[int], cap: int = K_MAX_STOC_PACKET_BUFFER) -> PacketCapture:
    """Return the capture a stub needs to carry one header's packet, from its template alone.

    This is the template-only half of ``GW::StoC::GetPacketSize``'s walk (``stoc_methods.cpp:181-235``):
    every descriptor contributes its wire width, starting **past** field 0, which describes the header
    word the packet pointer already accounts for (``:246-248``). When the template ends in a nested
    struct, the walk's data-dependent part is handed to the stub instead — the repeat count is read
    out of the packet (``:212-217``) — so what comes back is a :class:`PacketCapture` rather than a
    size: the fixed width, then the nested stride and where the count sits.

    A nested struct **inside** the nested part is refused by name: native's walk returns after the
    first nested struct because GW never places a second one (``:225-226``), so a template with one
    has no width this can state. It is a template no packet of this client uses; a refusal says so
    instead of copying a size nobody computed.
    """

    offset = PACKET_BASE_SIZE
    for index in range(1, len(descriptors)):
        descriptor = descriptors[index]
        count = (descriptor >> 8) & 0xFFFF
        kind = decode_field_kind(descriptor)

        if kind is FieldKind.NestedStruct:
            stride = 0
            for nested in descriptors[index + 1 :]:
                nested_kind = decode_field_kind(nested)
                if nested_kind is FieldKind.NestedStruct:
                    raise ValueError(
                        "the template nests a struct inside a nested struct, which no packet of "
                        "this client has and which native's walk refuses to walk ("
                        "stoc_methods.cpp:225-226)."
                    )
                stride += _field_width(nested_kind, (nested >> 8) & 0xFFFF)
            return PacketCapture(
                fixed_bytes=offset, nested_stride=stride, repeat_offset=offset, cap=cap
            )

        offset += _field_width(kind, count)
        if offset > K_MAX_COMPUTED_PACKET_BYTES:
            return PacketCapture(fixed_bytes=offset, cap=cap)

    return PacketCapture(fixed_bytes=offset, cap=cap)


@dataclass(frozen=True)
class PacketStub:
    """One header's replacement: what it copies, where it came from, and where it now lives."""

    header: int
    #: How many of the packet's words the stub copies into the record, for a listener that reads
    #: fields off the packet rather than keeping its bytes.
    words: int
    address: int
    original: int
    entry: int
    #: The orphaned stub an original was recovered from, when the entry held one from a controller
    #: that died. Zero when the entry held the client's own handler.
    repaired_from: int = 0
    #: What the stub copies of the packet's **bytes**, when this header is one the sniffer keeps.
    #: ``None`` for a stub placed only for a listener, which records words and no capture.
    capture: PacketCapture | None = None


#: The stub's opening: ``pushad`` then ``inc dword [imm32]``, the in-flight count taken on entry —
#: what ``payload.build_packet_stub`` emits first, and what tells this project's own code from
#: anything else that could be sitting in an entry.
_STUB_OPENING = bytes((0x60, 0xFF, 0x05))

#: ``mov eax, imm32`` and ``call eax``: the chain to the original, and the only place the handler an
#: entry held before it was replaced is still written down.
_CHAIN_MOV = 0xB8
_CHAIN_CALL = bytes((0xFF, 0xD0))

#: How much of a stub to read when looking for that immediate. One is about 220 bytes with eighteen
#: packet words; this is that and more, and it is bounded so a wild pointer cannot read far.
_STUB_READ = 512


def original_from_stub(
    access: WritableTarget, stub: int, module_base: int, module_size: int
) -> int | None:
    """Return the handler one of this project's orphaned stubs chains to, or ``None``.

    **This is the port's own recovery, and it exists because a controller can be killed.** Nothing
    runs on the way out then, so the client's entries keep pointing at stubs whose block and whose
    owning process are gone — and the originals were only in that process's memory, exactly as
    native's ``g_original_functions`` lives in its own. The one copy that belongs to the client being
    repaired is **inside the stub itself**: it was emitted with the handler it replaced baked in as
    the immediate of the ``mov eax`` it calls through (``payload.build_packet_stub``).

    The answer is only accepted when it lands inside the client module **and** the bytes there look
    like a function's entry, which is what keeps a misread from being written back as a handler. A
    stub that is not this project's, or one whose immediates cannot be read, answers ``None`` and the
    caller refuses rather than guessing.
    """

    if module_base <= stub < module_base + module_size:
        return None

    try:
        code = access.read(stub, _STUB_READ)
        head = code[:3]
    except OSError:
        return None

    if head != _STUB_OPENING:
        return None

    for index in range(len(code) - 6):
        if code[index] != _CHAIN_MOV or code[index + 5 : index + 7] != _CHAIN_CALL:
            continue
        candidate = int.from_bytes(code[index + 1 : index + 5], "little")
        if not module_base <= candidate < module_base + module_size:
            continue
        try:
            entry = access.read(candidate, 2)
        except OSError:
            continue
        if entry == b"\x55\x8b":
            return candidate
    return None


class PacketHooks:
    """Replace the client's handler for the headers a listener wants, and put them back.

    One instance per client: it holds the addresses it placed and every original it saved, which is
    what the restore writes back.
    """

    def __init__(self, bridge: PacketBridge) -> None:
        """Create the hooks over a bridge that has already placed its block and hook.

        The bridge is what carries the transport: the client reads for the array, the data region the
        pointer being written is staged in, and the ``WRITE_MEMORY`` command that lands it.
        """

        self._bridge = bridge
        self._table: HandlerTable | None = None
        self._stubs: dict[int, PacketStub] = {}
        self._pointer_address = 0
        self._inflight_address = 0

    # -- what it is --------------------------------------------------------

    @property
    def table(self) -> HandlerTable | None:
        """Return the array this replaced entries in, or ``None`` before it is read."""

        return self._table

    @property
    def headers(self) -> tuple[int, ...]:
        """Return the headers whose handlers are this project's code right now."""

        return tuple(sorted(self._stubs))

    def in_flight(self) -> int:
        """Return how many stubs are running right now."""

        if not self._inflight_address:
            return 0
        return _read_uint32(self._access(), self._inflight_address)

    def stub(self, header: int) -> PacketStub:
        """Return one header's stub, refusing a header this is not replacing."""

        try:
            return self._stubs[header]
        except KeyError as error:
            raise ValueError(
                f"header {header} is not one of the {len(self._stubs)} this project replaced."
            ) from error

    # -- placing and removing ----------------------------------------------

    def install(
        self,
        table_address: int,
        wanted: Mapping[int, int],
        captures: Mapping[int, PacketCapture] | None = None,
    ) -> tuple[PacketStub, ...]:
        """Read the client's array, place one stub per wanted header, and point the entries at them.

        ``wanted`` maps a header to how many of that packet's words its listener reads, which is what
        the stub copies. ``captures`` maps a header to a :class:`~.shared_block.PacketCapture` — how
        much of the packet's **bytes** the stub keeps — and is what the packet sniffer asks for. Both
        may name the same header: native runs one callback per registration on the same packet
        (``g_packet_entries[header]``, ``stoc.cpp:80-99``), and here the single stub a header gets
        carries what all of them need, because one record is what the host dispatches.

        **This is additive, as native's registration is.** ``RegisterPacketCallback`` removes that
        entry's own old registration and inserts the new one (``stoc_methods.cpp:41-53``); it never
        refuses because a header is already watched, and neither does a second listener's arrival —
        which is the arrangement native itself creates, because its packet sniffer registers every
        header (``packet_sniffer.cpp:129-135``) and the merchant listener registers five of the same
        ones (``listeners.cpp:96-128``). A header this project already replaced is left alone when
        the stub it has already covers what is now asked, and re-placed when it does not; the stub
        it replaces is left mapped rather than freed, because freeing code the client may be inside
        is how a client is taken down — the same reason :meth:`remove` waits on the in-flight count.

        A header the client's array does not hold is refused before anything is replaced, so a
        partly applied install cannot happen: native checks the same bound before it writes
        (``stoc_methods.cpp:55``).

        The order is the source's: read the array, save each original, place the code, then replace
        the entry (``EnableHooks``, ``stoc.cpp:118-128``). Each entry is read back after the write,
        because a replacement that did not land would leave the client running its own handler while
        this side believes it is watching.

        **A handler has to be live code — the client's own, or another runtime's inside a loaded module —
        and anything else is refused, or recovered when it is this project's own.** Native snapshots
        whatever the array holds and chains to it, which is safe in a runtime that injected itself into a
        fresh process; a controller here can connect to a client that outlived a previous controller, and a
        handler pointer left in memory no module covers is a jump into freed memory — taken on the client's
        own thread, on the next packet of that header. So each wanted header's handler is checked before
        anything is placed: inside the client's module is the ordinary case, and inside **a loaded module**
        is another runtime's compiled handler, which is chaining the same way the entry hooks chain.

        Measured live on 2026-10-01 with Reforged injected: header 132's entry held ``0x578F1ED3``, inside
        ``Py4GW.dll`` (``0x578F0000 + 0xF94000``). Reforged's packet sniffer registers **all 488** headers
        (``packet_sniffer.cpp:129-135``), so every header this project wants is one of its callbacks, and
        refusing those entries would have made the merchant listener impossible on the very arrangement the
        owner needs. A pointer that is **one of this project's own orphaned stubs** is repaired instead: the
        original is read back out of the stub's own chained-original immediate
        (:func:`original_from_stub`), the entry is put back, and the install carries on — which is the same
        recovery ``ConnectedClient._prepare_target`` performs on a stale entry patch, applied to the other
        kind of pointer this project replaces. Anything else is refused by name.
        """

        captures = {} if captures is None else dict(captures)
        if not wanted and not captures:
            raise ValueError("no header was asked for.")

        access = self._access()
        table = read_handler_table(access, table_address)
        every = sorted(set(wanted) | set(captures))
        for header in every:
            table.entry(header)

        bridge = self._require_bridge()
        module_base, module_size = bridge.module_range
        loaded_modules = bridge.loaded_modules
        self._pointer_address = bridge.write_data(PACKET_POINTER_OFFSET, bytes(4))
        self._inflight_address = bridge.write_data(PACKET_INFLIGHT_OFFSET, bytes(4))
        self._table = table

        placed: list[PacketStub] = []
        try:
            for header in every:
                words = wanted.get(header, 0)
                capture = captures.get(header)
                existing = self._stubs.get(header)
                if existing is not None and _covers(existing, words, capture):
                    continue

                entry = table.entry(header)
                # A header already replaced keeps chaining to the original this project saved, and
                # never re-reads its own stub off the entry: the entry holds this project's code now.
                original = (
                    existing.original
                    if existing is not None
                    else _read_uint32(access, entry + ENTRY_HANDLER_OFFSET)
                )
                repaired_from = 0
                # **A null handler is not a reason to refuse.** Native snapshots whatever the entry
                # holds and registers anyway (``stoc_methods.cpp:41-61``): the array has an entry for
                # every header in range, and a header the client itself never dispatches has no
                # handler at all. Nothing chains to it because nothing ever calls it — and the stub
                # is built to chain to nothing, which is the ``original == 0`` form
                # (``payload.build_packet_stub``). Measured live on 2026-10-24: header 79's entry
                # held a zero handler, and refusing it aborted the whole install over a header that
                # carries no traffic.
                if original and existing is None and not is_live_code(
                    original, module_base, module_size, loaded_modules
                ):
                    recovered = original_from_stub(access, original, module_base, module_size)
                    if not recovered:
                        raise RuntimeError(
                            f"header {header}'s entry at 0x{entry:08X} holds the handler "
                            f"0x{original:08X}, which is in memory no loaded module covers "
                            f"(the client is 0x{module_base:08X}..0x{module_base + module_size:08X}, and "
                            f"{len(loaded_modules)} other module(s) were checked), and it is not one of "
                            "this project's own stubs either, so the handler it replaced cannot be read "
                            "back out of it. A controller that died leaves its stubs in exactly that "
                            "memory, and chaining to one would jump into memory it no longer owns. "
                            "Nothing was replaced. `tools/restore_stoc_handlers.py` reports what it can "
                            "prove about those entries; restarting the client is the other way."
                        )
                    repaired_from = original
                    self._write_handler(
                        entry + ENTRY_HANDLER_OFFSET, recovered, header
                    )
                    original = recovered

                code = build_packet_stub(
                    bridge.block_address,
                    header,
                    words,
                    original,
                    inflight_address=self._inflight_address,
                    capture=capture,
                )
                address = access.allocate(len(code))
                access.write(address, code)
                access.protect(address, len(code), PAGE_EXECUTE_READ)
                access.flush_instruction_cache(address, len(code))

                stub = PacketStub(
                    header=header,
                    words=words,
                    address=address,
                    original=original,
                    entry=entry + ENTRY_HANDLER_OFFSET,
                    repaired_from=repaired_from,
                    capture=capture,
                )
                placed.append(stub)
                self._stubs[header] = stub
                self._write_handler(stub.entry, address, header)
        except BaseException:
            # An install that could not finish leaves nothing behind: every entry it already
            # replaced goes back, and the code goes with it. The install is what failed, not the
            # restore, so a restore that also failed is reported beside it rather than instead.
            try:
                self.remove(free_code=True)
            except BaseException as restore_error:  # noqa: BLE001 - reported with the first failure
                raise RuntimeError(
                    f"installing the packet hooks failed, and putting the client's handlers back "
                    f"failed too: {restore_error}"
                ) from restore_error
            raise

        return tuple(placed)

    def remove(self, free_code: bool = False) -> tuple[int, ...]:
        """Put every replaced entry back, and free the stubs' code only when nothing is inside it.

        The restore is the source's: ``DisableHooks`` writes the saved pointers back for every header
        it took (``stoc.cpp:130-140``), unconditionally — a client that replaced one of them itself
        in the meantime has its own handler overwritten by what was there before this project ran,
        which is exactly what native does and is not this side's decision to make.

        **The entries go back before anything is freed**, and that order is not cosmetic: the write
        runs on the game thread through the payload, so it needs the block and the hook this bridge
        placed, and a stub whose code was freed while the client still points at it is how a client is
        taken down.

        **Every entry is attempted even when one write fails.** Native's loop restores all of them
        (``stoc.cpp:134-138``); a restore that stopped at the first refusal would leave the client
        dispatching some headers into code this is about to release, which is the one outcome worth
        more than reporting the failure early. The failures are collected and raised together, and
        the headers that did go back are reported in the message.

        ``free_code`` waits for the in-flight count to reach zero first, because a packet handler can
        run on a thread this controller never sees; a count that does not drain is reported rather
        than slept off, and nothing is freed (``Hooker.remove``, ``hooker.py:783-805``).
        """

        if not self._stubs:
            return ()

        restored: list[int] = []
        failures: list[str] = []
        for header in sorted(self._stubs):
            stub = self._stubs[header]
            try:
                self._write_handler(stub.entry, stub.original, header)
            except BaseException as error:  # noqa: BLE001 - collected, then raised together
                failures.append(f"header {header}: {error}")
            else:
                restored.append(header)

        if failures:
            raise RuntimeError(
                "; ".join(failures)
                + f". {len(restored)} of {len(self._stubs)} entries were restored"
                + (f" ({restored})" if restored else "")
                + "; nothing was freed."
            )

        if free_code:
            deadline = time.monotonic() + FREE_WAIT_SECONDS
            while True:
                inside = self.in_flight()
                if not inside:
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        f"{inside} packet stub(s) were still running {FREE_WAIT_SECONDS} s after "
                        "every entry was restored. Nothing was freed: the generated code stays "
                        "mapped, because unmapping code under a live instruction pointer is how a "
                        "client is taken down."
                    )
                time.sleep(HIT_POLL_SECONDS)
            access = self._access()
            for stub in self._stubs.values():
                access.free(stub.address)

        self._stubs.clear()
        self._table = None
        return tuple(restored)

    # -- internals ---------------------------------------------------------

    def _write_handler(self, entry: int, handler: int, header: int) -> None:
        """Place a handler pointer in one of the client's entries, on the game thread.

        The pointer is written into the block's data region first — ``WRITE_MEMORY`` copies *from*
        there — and the command's completion is checked, because this is the one operation whose
        silent failure would leave the client dispatching a packet into code that is not there.
        The entry is read back afterwards.
        """

        bridge = self._require_bridge()
        bridge.write_data(PACKET_POINTER_OFFSET, struct.pack("<I", handler))
        record = bridge.submit(
            Operation.WRITE_MEMORY,
            entry,
            PACKET_POINTER_OFFSET,
            4,
            0,
            0,
            0,
        )
        if record.state is not CommandState.DONE:
            raise RuntimeError(
                f"header {header}: writing 0x{handler:08X} into the entry at 0x{entry:08X} did "
                f"not complete (state {record.state!r}, result {record.result})."
            )
        landed = _read_uint32(self._bridge.access, entry)
        if landed != handler:
            raise RuntimeError(
                f"header {header}: the entry at 0x{entry:08X} reads 0x{landed:08X} after writing "
                f"0x{handler:08X}."
            )

    # -- internals ---------------------------------------------------------

    def _access(self) -> WritableTarget:
        """Return the transport this bridge reads the client through."""

        return self._bridge.access

    def _require_bridge(self) -> PacketBridge:
        """Return the bridge, refusing one that has not placed a block."""

        if not self._bridge.block_address:
            raise RuntimeError("the bridge has not placed its block yet.")
        return self._bridge

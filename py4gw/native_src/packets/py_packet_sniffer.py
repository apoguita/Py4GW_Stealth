"""Port of Native's ``PyPacketSniffer`` module over ``GW::packet_sniffer``.

**Sources.** ``src/GW/packet_sniffer/packet_sniffer_bindings.cpp`` (the module: ``PacketDirection``,
``PacketLogEntry`` and the 12-member ``PacketSniffer`` facade, ``:46-91``), ``packet_sniffer.h`` (the
namespace's own surface: three bounds, ``LogPacket``/``GetLogs*``/``ClearLogs*``, the lifecycle pair
per direction, ``SendPacketFn`` and ``ResolveCToSSendTarget``), ``packet_sniffer.cpp`` (the two
capture paths) and ``packet_sniffer_methods.cpp`` (the log under its mutex). ``stubs/PyPacketSniffer.pyi``
is the same surface in stub form, and it is what Reforged's Python imports.

**Why this is a module of its own, and why it is not the class.** In both sources ``PyPacketSniffer``
*is* a module: native's embedded binding, and the stub Reforged imports
(``Py4GWCoreLib/PacketSniffer.py:7``). Its facade is a class of that module named
``PacketSniffer`` — and Reforged's own file also declares a class of that name. The two cannot share
a Python module, so the module is ported where the sources put it, as a module, and Reforged's class
sits over it in ``py4gw/packet_sniffer.py`` exactly as it sits over the import in
``Py4GWCoreLib/PacketSniffer.py``.

**What the two capture paths are here, and they are different mechanisms.**

- **StoC** replaces the client's own handler for a header with this project's code
  (``game_thread/packets.py``), which is the one mechanism this project has that changes how the
  client dispatches its own packets. Native does the same thing
  (``g_game_server_handlers->at(header).handler_func = &StoCHandler_Func``,
  ``stoc_methods.cpp:55-57``) and registers **every** header (``packet_sniffer.cpp:129-135``), so
  the loop below is the source's own: ``header < kStoCHeaderCount``. Native refuses a header the
  live array does not hold by returning ``false`` from the registration and carrying on
  (``stoc_methods.cpp:55-60``, whose return ``InitializeStoC`` ignores) — and the live array held
  **487** entries when this project last read it (``tests/live_reports/stoc_handlers.json``), so the
  last header of the source's loop is exactly that case. The port skips a header past the array's
  size for the same reason and in the same place.
- **CToS** is an entry hook on the client's send wrapper (``packet_sniffer.cpp:156-194``), placed by
  :meth:`~py4gw.client.ConnectedClient.install_send_capture` and recorded by
  ``payload.build_send_capture_stub``.

**How the records reach this side.** Native's callbacks append to ``std::vector<PacketLogEntry>``
under a mutex inside its own process (``packet_sniffer_methods.cpp:13-56``). Here the emitted stub
writes one ``PACKET`` event per packet — header, direction, size, and a bounded copy of the bytes —
and the host drains it through the connection's callback registry. So ``LogPacket`` is the port of
the append, including the cap: ``while (g_logs.size() > kMaxLogs) g_logs.erase(g_logs.begin())``
(``:19-21``) drops the **oldest** entry, which is what :func:`LogPacket` does.

**The one thing that is not the source's, and it is the transport's.** ``entry.tick`` is
``PY4GW::System::GetTickCount64()`` taken inside the client at capture time (``:84``, ``:137``).
Nothing emits a tick in this project's block — every stub writes zero — so the tick is taken from
the **same Windows function** when the host reads the record. ``GetTickCount64`` is a machine-wide
millisecond clock, so the value is the same clock the source reads, later by however long the record
waited for the drain. It is recorded here rather than smoothed over.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass, field
from enum import IntEnum

from ...client import require_client
from ...game_thread.packets import (
    K_MAX_STOC_PACKET_BUFFER,
    describe_template,
    read_template,
)
from ...game_thread.shared_block import (
    EventKind,
    EventRecord,
    PacketCapture,
    PACKET_DIRECTION_CTOS,
    PACKET_DIRECTION_STOC,
)

#: ``kStoCHeaderCount`` (``stoc.h:24``): how many headers native's StoC loop walks. It is the
#: source's constant and not the live array's size; the array is asked about each header.
K_STOC_HEADER_COUNT = 0x1E8

#: ``kMaxLogs`` (``packet_sniffer.h:30``): the cap on the log, whose oldest entry is dropped first.
K_MAX_LOGS = 10000

#: ``kMaxReasonableCToSPacketSize`` (``packet_sniffer.h:29``): what the send capture's guard allows,
#: and the reason a longer packet is dropped rather than clipped (``packet_sniffer.cpp:52-55``).
K_MAX_REASONABLE_CTOS_PACKET_SIZE = 4096

#: The log the ports of ``LogPacket`` and the ``Get*Logs`` functions read, and the two lifecycle flags
#: ``g_stoc_initialized``/``g_ctos_initialized`` (``packet_sniffer.cpp:109-110``).
_logs: list[PacketLogEntry] = []
_stoc_initialized = False
_ctos_initialized = False
#: Whether the log is subscribed to the event channel. One subscription serves both directions.
_handler_registered = False
#: The captures each registered StoC header needs, kept so the module knows which headers it took — the
#: record's own word already carries the size the stub computed, so nothing is re-walked when a record
#: arrives; this is only what :meth:`PacketSniffer.initialize_stoc` installed.
_stoc_captures: dict[int, PacketCapture] = {}

_kernel32 = getattr(ctypes, "windll", None)
_kernel32 = None if _kernel32 is None else _kernel32.kernel32


def GetTickCount64() -> int:
    """Return ``PY4GW::System::GetTickCount64()``, the clock native stamps a record with.

    A machine-wide millisecond clock, so it is the same value the source reads inside the client,
    taken when this side reads the record instead of when the packet arrived (see the module note).
    """

    if _kernel32 is None:  # not on Windows: there is no such clock
        return 0
    return int(_kernel32.GetTickCount64())


class PacketDirection(IntEnum):
    """``py::enum_<PacketDirection>`` (``packet_sniffer_bindings.cpp:56-59``), ``StoC = 0, CToS = 1``."""

    StoC = 0
    CToS = 1


@dataclass(frozen=True, slots=True)
class PacketLogEntry:
    """``PacketLogEntry`` (``packet_sniffer.h:19-25``; bound at ``packet_sniffer_bindings.cpp:61-75``).

    ``tick``, ``direction``, ``header``, ``size`` and ``data``, in the source's order. ``data`` is the
    bytes the capture kept: the binding exposes a ``vector<uint8_t>`` as a list of ints and
    Reforged's ``_convert_entry`` reads it with ``bytes(entry.data)`` (``PacketSniffer.py:395``), so
    those bytes are what both of them see.
    """

    tick: int = 0
    direction: PacketDirection = PacketDirection.StoC
    header: int = 0
    size: int = 0
    data: bytes = field(default=b"")

    def __repr__(self) -> str:
        """The binding's own repr (``packet_sniffer_bindings.cpp:68-75``)."""

        direction = "StoC" if self.direction == PacketDirection.StoC else "CToS"
        return (
            f"<Packet direction={direction} header=0x{self.header:04X} "
            f"size={self.size}>"
        )


# -- the log, which is ``g_logs`` under ``g_mutex`` --------------------------


def LogPacket(entry: PacketLogEntry) -> None:
    """``LogPacket`` (``packet_sniffer_methods.cpp:16-22``): append, dropping the oldest past the cap."""

    _logs.append(entry)
    while len(_logs) > K_MAX_LOGS:
        _logs.pop(0)


def GetLogs() -> list[PacketLogEntry]:
    """``GetLogs`` (``:24-27``): a copy of the whole log, oldest first."""

    return list(_logs)


def GetLogsByDirection(direction: PacketDirection) -> list[PacketLogEntry]:
    """``GetLogsByDirection`` (``:29-39``): the entries of one direction, in log order."""

    return [entry for entry in _logs if entry.direction == direction]


def ClearLogs() -> None:
    """``ClearLogs`` (``:41-44``)."""

    _logs.clear()


def ClearLogsByDirection(direction: PacketDirection) -> None:
    """``ClearLogsByDirection`` (``:46-56``): remove one direction's entries, keeping the order of the rest."""

    _logs[:] = [entry for entry in _logs if entry.direction != direction]


# -- the StoC capture -------------------------------------------------------


def _capture_record(event: EventRecord) -> None:
    """Append one ``PACKET`` event to the log, as the two capture paths produce them here.

    Native's StoC callback and its CToS detour both end in ``LogPacket`` (``packet_sniffer.cpp:90``,
    ``:146``), and this is the host-side half of that: the record the stub wrote becomes the entry the
    log holds.

    ``arg1`` is the **size** the record carries, and for an inbound packet it is the walk the stub
    computed inside the client — the same number ``GetPacketSize`` would have answered, which is why
    nothing is re-walked here. ``capture`` is the bytes, clipped by the stub to the direction's own
    bound exactly as native clips them, so a capture shorter than the size is a clipped packet and not
    a missing one.
    """

    direction = (
        PacketDirection.CToS
        if int(event.arg0) == PACKET_DIRECTION_CTOS
        else PacketDirection.StoC
    )
    LogPacket(
        PacketLogEntry(
            tick=GetTickCount64(),
            direction=direction,
            header=int(event.sequence),
            size=int(event.arg1),
            data=bytes(event.capture),
        )
    )


def InitializeStoC() -> bool:
    """``InitializeStoC`` (``packet_sniffer.cpp:123-154``): replace every header's handler.

    Idempotent (``g_stoc_initialized``, ``:125-127``), one capture per header described from that
    header's own field template — which is what native's ``GetPacketSize`` reads when a packet
    arrives, resolved here once instead (``stoc_methods.cpp:239-262``) — and the host handler
    registered (see :func:`_register_handler`), because the records all arrive on the one event
    channel.

    Answers ``True`` once the entries are placed. A client that has not built its handler array yet
    refuses inside the walk and nothing is replaced, which is the same answer native gives when
    ``ResolveGameServerHandlers`` fails (``stoc_patterns.cpp:43-50``).
    """

    global _stoc_initialized

    if _stoc_initialized:
        return True

    client = require_client()
    table_address = client._resolve("stoc.handler_table_addr")
    bridge = client.bridge
    table = bridge.read_packet_table(table_address)

    captures: dict[int, PacketCapture] = {}
    for header in range(K_STOC_HEADER_COUNT):
        # Native's own bound check: a header the live array does not hold is not registered
        # (``stoc_methods.cpp:55``), and its registration answers ``false`` without stopping the loop.
        if header >= table.size:
            continue
        descriptors, _field_count = read_template(bridge.access, table.entry(header))
        captures[header] = describe_template(descriptors, K_MAX_STOC_PACKET_BUFFER)

    bridge.install_packets(table_address, {}, captures)
    _register_handler()
    _stoc_captures.update(captures)
    _stoc_initialized = True
    return True


def _register_handler() -> None:
    """Subscribe the log to the event channel, once, whichever half is started first.

    Native has no such step: its two capture paths call ``LogPacket`` themselves, in its own process
    (``packet_sniffer.cpp:90``, ``:146``). Here the records travel to the host through the connection's
    registry, and **both directions end in the same handler** — the record's ``arg0`` says which — so
    a direction started on its own has to register it too. Measured 2026-10-24: ``initialize_ctos``
    without this registered nothing, and the events were drained and dropped by the caller's own pump,
    which looks exactly like a client that sent no packets.
    """

    global _handler_registered

    if _handler_registered:
        return
    require_client().callbacks.register(EventKind.PACKET, _capture_record)
    _handler_registered = True


def _unregister_handler_if_idle() -> None:
    """Drop the subscription once neither half is capturing any more."""

    global _handler_registered

    if not _handler_registered or _stoc_initialized or _ctos_initialized:
        return
    require_client().callbacks.unregister(EventKind.PACKET, _capture_record)
    _handler_registered = False


def TerminateStoC() -> None:
    """``TerminateStoC`` (``:201-212``): put every handler back and forget the captures.

    Native removes one callback per header and clears its flag; here every entry goes back in one
    step, because they were placed in one step (``game_thread/packets.py``). The subscription goes
    only when the outbound half is not capturing either, because the two share it.
    """

    global _stoc_initialized

    if not _stoc_initialized:
        return

    client = require_client()
    client.bridge.remove_packets()
    _stoc_captures.clear()
    _stoc_initialized = False
    _unregister_handler_if_idle()


# -- the CToS capture -------------------------------------------------------


def ResolveCToSSendTarget() -> int:
    """``ResolveCToSSendTarget`` (``packet_sniffer_patterns.cpp:10-19``): the send wrapper, or zero.

    Native resolves ``packet_sniffer.ctos_send_target`` and leaves ``*out_target`` at zero when no
    attempt resolves; that is what this answers, and what :func:`InitializeCToS` tests.
    """

    client = require_client()
    if not client.resolves("packet_sniffer.ctos_send_target"):
        return 0
    return client._resolve("packet_sniffer.ctos_send_target")


def InitializeCToS() -> bool:
    """``InitializeCToS`` (``packet_sniffer.cpp:156-194``): hook the send wrapper, once.

    Idempotent (``:158-161``). A target that does not resolve answers ``False`` and leaves the StoC
    half alone, which is what native's aborted initialization does (``:163-166``).

    **The first version of this killed the client twice on 2026-10-24, and the fault was here.** The
    entry span the hook replaces was worked out as **5** bytes over ``55 8B EC 83 EC 50``, which cuts
    ``sub esp, 0x50`` (three bytes) in half: the trampoline replayed a ``sub esp`` that took the first
    byte of this project's jump as its frame size and resumed mid-``push``, so every send ran on a
    wrecked frame. ``ConnectedClient._entry_span`` now answers the **6** bytes the instructions occupy
    (and ``9`` for the ``sub esp, imm32`` form), ``payload.send_capture_arguments`` forwards the
    wrapper's **three** words — ``(ctx, size, packet)`` — instead of two, and this half subscribes to
    the event channel like the inbound one does (:func:`_register_handler`). All three are
    offline-verified and **live-verified**: measured 2026-10-24 on build 39112, ``CToS 0x0039`` with
    12 bytes captured, and the hook removed afterwards with the client alive.
    """

    global _ctos_initialized

    if _ctos_initialized:
        return True

    if not ResolveCToSSendTarget():
        return False

    client = require_client()
    client.install_send_capture()
    _register_handler()
    _ctos_initialized = True
    return True


def TerminateCToS() -> None:
    """``TerminateCToS`` (``:214-227``)."""

    global _ctos_initialized

    if not _ctos_initialized:
        return

    require_client().remove_send_capture()
    _ctos_initialized = False
    _unregister_handler_if_idle()


# -- the unified pair -------------------------------------------------------


def Initialize() -> bool:
    """``Initialize`` (``:112-121``): StoC first, then CToS, and their conjunction.

    Native logs which half failed and answers ``stoc_ok && ctos_ok``; the answer is the whole of it
    here, and neither half is undone when the other fails — the source leaves the StoC half in place
    when the CToS target does not resolve (``:163-166``), and so does this.
    """

    stoc_ok = InitializeStoC()
    ctos_ok = InitializeCToS()
    return stoc_ok and ctos_ok


def Terminate() -> None:
    """``Terminate`` (``:196-199``): **CToS first, then StoC** — the source's own order."""

    TerminateCToS()
    TerminateStoC()


# -- the facade the binding exposes ----------------------------------------


class PacketSniffer:
    """``PacketSnifferFacade`` (``packet_sniffer_bindings.cpp:15-42``), bound as ``PyPacketSniffer.PacketSniffer``.

    Twelve members, each a forward to one of this module's functions — the source's own shape
    (``:77-90``). ``instance()`` is the binding's function-local static (``:16-19``).
    """

    _instance: 'PacketSniffer | None' = None

    @staticmethod
    def instance() -> 'PacketSniffer':
        """``PacketSnifferFacade::Instance`` (``:16-19``)."""

        if PacketSniffer._instance is None:
            PacketSniffer._instance = PacketSniffer()
        return PacketSniffer._instance

    def initialize(self) -> bool:
        """``:79``."""

        return Initialize()

    def initialize_stoc(self) -> bool:
        """``:80``."""

        return InitializeStoC()

    def initialize_ctos(self) -> bool:
        """``:81``."""

        return InitializeCToS()

    def terminate(self) -> None:
        """``:82``."""

        Terminate()

    def terminate_stoc(self) -> None:
        """``:83``."""

        TerminateStoC()

    def terminate_ctos(self) -> None:
        """``:84``."""

        TerminateCToS()

    def get_logs(self) -> list[PacketLogEntry]:
        """``:85``."""

        return GetLogs()

    def get_stoc_logs(self) -> list[PacketLogEntry]:
        """``:86``."""

        return GetLogsByDirection(PacketDirection.StoC)

    def get_ctos_logs(self) -> list[PacketLogEntry]:
        """``:87``."""

        return GetLogsByDirection(PacketDirection.CToS)

    def clear_logs(self) -> None:
        """``:88``."""

        ClearLogs()

    def clear_stoc_logs(self) -> None:
        """``:89``."""

        ClearLogsByDirection(PacketDirection.StoC)

    def clear_ctos_logs(self) -> None:
        """``:90``."""

        ClearLogsByDirection(PacketDirection.CToS)


__all__ = [
    "GetLogs",
    "GetLogsByDirection",
    "GetTickCount64",
    "Initialize",
    "InitializeCToS",
    "InitializeStoC",
    "K_MAX_LOGS",
    "K_MAX_REASONABLE_CTOS_PACKET_SIZE",
    "K_STOC_HEADER_COUNT",
    "LogPacket",
    "PacketDirection",
    "PacketLogEntry",
    "PacketSniffer",
    "ResolveCToSSendTarget",
    "Terminate",
    "TerminateCToS",
    "TerminateStoC",
]

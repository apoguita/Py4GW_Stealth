"""Prove the external map-readiness gate and measure what it costs.

Reforged never reads a map-scoped value without first asking whether the map is
ready::

    Map.IsMapReady() -> IsMapDataLoaded() and not IsObservingMatch() and not IsMapLoading()

Every ingredient of that predicate is a plain context read, so an external
controller can evaluate it too.  The interesting part is *how* the third
ingredient has to be read.

``map.instance_info_addr`` resolves scan -> dereference, so it yields the
``InstanceInfo*`` struct pointer for the map that was loaded when the scan ran.
The native runtime resolves that one once, at startup, into ``g_instance_info``
and then deliberately does *not* use it for live data::

    Context::g_instance_info_ptr = 0;
    return Patterns::Resolve("map.instance_info_addr", &g_instance_info) &&
           Patterns::Resolve("map.instance_info_ptr_ref", &g_instance_info_ptr);

``GetInstanceType()`` uses the second one, the *address of the pointer*, and
dereferences it on every call::

    const auto instance_info_ptr = Context::GetInstanceInfoPtr();
    auto* info = instance_info_ptr ? *reinterpret_cast<InstanceInfo**>(instance_info_ptr) : nullptr;
    return info ? info->instance_type : InstanceType::Loading;

So the runtime caches the stable half (a module-global slot address) and
re-dereferences the volatile half (the map-scoped pointer) per read.  This
preflight does the same through ``map.instance_info_ptr_ref`` and reports the
difference against Stealth's cached-struct-pointer route, then times a full gate
evaluation so the cost of gating every read is known rather than assumed.

This script writes NOTHING into ``Gw.exe``.  It has no hook, no payload, no
patch, no remote allocation, and no remote thread.  It only reads memory.

How to use it::

    python tests/preflight_readiness_gate.py --pid <PID>

While the client is logged in, change maps (zone, enter/leave an outpost) and
watch the ``instance_type`` column.  A ready map reads 0 (Outpost) or 1
(Explorable); ``Loading``, 2, means the gate is closed and no map-scoped value
should be fetched.
"""

from __future__ import annotations

import argparse
import time
from typing import Any

from py4gw import PatternCatalog, ProcessMemoryReader, RemoteScanner, Win32
from py4gw.client import ConnectedClient, connect

#: Resolver that returns the *address of* the InstanceInfo pointer.  This is the
#: half the native runtime caches; the value stored there is map-scoped.
SLOT_RESOLVER = "map.instance_info_ptr_ref"

#: Resolver that returns the dereferenced, map-scoped ``InstanceInfo*``.  This is
#: the half Stealth's ``InstanceInfo`` currently caches and re-reads forever.
STRUCT_RESOLVER = "map.instance_info_addr"

#: ``InstanceInfo::instance_type`` follows the first pointer field.
INSTANCE_TYPE_OFFSET = 4

OUTPOST = 0
EXPLORABLE = 1
LOADING = 2

#: What the gate accepts as "the map is loaded and playable".
PLAYABLE_TYPES = (OUTPOST, EXPLORABLE)


class InstanceInfoSlot:
    """Resolve the InstanceInfo slot once, then dereference it per read."""

    def __init__(
        self,
        reader: ProcessMemoryReader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
    ) -> None:
        """Create a reader for one process and its offset catalog."""

        self._reader = reader
        self._scanner = scanner
        self._patterns = patterns
        self._slot: int | None = None
        self._resolve_ms: float | None = None

    def build(self) -> int:
        """Scan once for the slot address and cache it."""

        start = time.perf_counter()
        result = self._patterns.resolve(SLOT_RESOLVER, self._scanner)
        self._resolve_ms = (time.perf_counter() - start) * 1000.0
        if not result.ok:
            detail = result.message or "the resolver returned no address"
            raise RuntimeError(f"{SLOT_RESOLVER} failed: {detail}")
        self._slot = result.value
        return self._slot

    @property
    def slot(self) -> int:
        """Return the cached slot address, which is stable for the process."""

        if self._slot is None:
            raise RuntimeError("InstanceInfoSlot.build() has not been called.")
        return self._slot

    @property
    def resolve_ms(self) -> float | None:
        """Return the one-time scan cost in milliseconds."""

        return self._resolve_ms

    def pointer(self) -> int:
        """Dereference the slot and return the current InstanceInfo address."""

        return self._scanner.read_uint32(self.slot)

    def struct_pointer_scan(self) -> int:
        """Resolve the cached-struct route for comparison with ``pointer()``."""

        result = self._patterns.resolve(STRUCT_RESOLVER, self._scanner)
        return result.value if result.ok else 0

    def instance_type(self) -> int:
        """Read ``instance_type`` through a fresh dereference of the slot."""

        pointer = self.pointer()
        if not pointer:
            return LOADING
        raw = self._reader.read(pointer + INSTANCE_TYPE_OFFSET, 4)
        return int.from_bytes(raw, "little")


class GateReport:
    """One evaluated readiness verdict with every ingredient visible."""

    def __init__(
        self,
        map_context: bool,
        char_context: bool,
        instance_info: bool,
        world_context: bool,
        agent_context: bool,
        instance_type: int,
        current_map_id: int | None,
        observe_map_id: int | None,
        player_number: int | None,
        elapsed_ms: float,
    ) -> None:
        """Capture one gate evaluation."""

        self.map_context = map_context
        self.char_context = char_context
        self.instance_info = instance_info
        self.world_context = world_context
        self.agent_context = agent_context
        self.instance_type = instance_type
        self.current_map_id = current_map_id
        self.observe_map_id = observe_map_id
        self.player_number = player_number
        self.elapsed_ms = elapsed_ms

    @property
    def data_loaded(self) -> bool:
        """Reforged ``Map.IsMapDataLoaded``."""

        return all(
            (
                self.map_context,
                self.char_context,
                self.instance_info,
                self.world_context,
            )
        )

    @property
    def observing(self) -> bool:
        """Reforged ``Map.IsObservingMatch``: the character observes another map."""

        return self.current_map_id != self.observe_map_id

    @property
    def map_loading(self) -> bool:
        """Reforged ``Map.IsMapLoading``."""

        return self.instance_type not in PLAYABLE_TYPES

    @property
    def ready(self) -> bool:
        """Reforged ``Map.IsMapReady`` plus this project's agent-context gate."""

        return (
            self.data_loaded
            and self.agent_context
            and not self.observing
            and not self.map_loading
        )

    def line(self) -> str:
        """Return a one-line human-readable verdict."""

        state = "READY  " if self.ready else "NOTREADY"
        return (
            f"{state} "
            f"type={self.instance_type} "
            f"map={self.current_map_id} observe={self.observe_map_id} "
            f"player={self.player_number} "
            f"loaded={int(self.data_loaded)} "
            f"ctx(m/c/i/w/a)="
            f"{int(self.map_context)}/{int(self.char_context)}/{int(self.instance_info)}"
            f"/{int(self.world_context)}/{int(self.agent_context)} "
            f"{self.elapsed_ms:7.3f} ms"
        )

    def as_dict(self) -> dict[str, Any]:
        """Return the report as a JSON-serializable mapping."""

        return {
            "ready": self.ready,
            "data_loaded": self.data_loaded,
            "observing": self.observing,
            "map_loading": self.map_loading,
            "instance_type": self.instance_type,
            "current_map_id": self.current_map_id,
            "observe_map_id": self.observe_map_id,
            "player_number": self.player_number,
            "map_context": self.map_context,
            "char_context": self.char_context,
            "instance_info": self.instance_info,
            "world_context": self.world_context,
            "agent_context": self.agent_context,
            "elapsed_ms": self.elapsed_ms,
        }


def evaluate_gate(client: ConnectedClient, slot: InstanceInfoSlot) -> GateReport:
    """Evaluate the readiness predicate and time the whole evaluation."""

    start = time.perf_counter()
    try:
        instance_type = slot.instance_type()
    except (OSError, RuntimeError):
        instance_type = LOADING

    try:
        char_context = client.read_char_context()
    except (OSError, RuntimeError):
        char_context = None

    map_context = _try(client.read_map_context)
    world_context = _try(client.read_world_context)
    agent_context = _try(client.read_acc_agent_context)
    instance_info = _try(client.read_instance_info)

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return GateReport(
        map_context=map_context is not None,
        char_context=char_context is not None,
        instance_info=instance_info is not None,
        world_context=world_context is not None,
        agent_context=agent_context is not None,
        instance_type=instance_type,
        current_map_id=int(char_context.current_map_id) if char_context else None,
        observe_map_id=int(char_context.observe_map_id) if char_context else None,
        player_number=int(char_context.player_number) if char_context else None,
        elapsed_ms=elapsed_ms,
    )


def _try(operation: Any) -> Any:
    """Run one context read and report a failure as ``None``."""

    try:
        return operation()
    except (OSError, RuntimeError):
        return None


def parse_arguments() -> argparse.Namespace:
    """Read optional PID, watch, interval, and sample-count arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pid",
        type=int,
        help="Guild Wars PID to inspect (defaults to the first discovered client).",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Poll until interrupted, printing only when the verdict changes.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.25,
        help="Seconds between polls in watch mode (default: 0.25).",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=50,
        help="Gate evaluations used for the timing summary (default: 50).",
    )
    arguments = parser.parse_args()
    if arguments.interval <= 0:
        parser.error("--interval must be positive")
    if arguments.samples <= 0:
        parser.error("--samples must be positive")
    return arguments


def pick_process(win32: Win32, pid: int | None) -> dict[str, Any]:
    """Return the requested Guild Wars process, or the first one found."""

    clients = win32.find_guild_wars()
    if not clients:
        raise SystemExit("No Guild Wars clients are currently running.")
    if pid is None:
        return clients[0]
    process = next((c for c in clients if int(c["pid"]) == pid), None)
    if process is None:
        raise SystemExit(f"Guild Wars PID {pid} was not found.")
    return process


def main() -> int:
    """Resolve the slot, report the cached-route difference, and time the gate."""

    arguments = parse_arguments()
    win32 = Win32()
    process = pick_process(win32, arguments.pid)
    pid = int(process["pid"])
    module = win32.get_main_module(pid)
    print(f"PID: {pid}")
    print(f"Path: {process.get('path') or '-'}")
    print()

    with ProcessMemoryReader(win32, pid) as reader:
        scanner = RemoteScanner(
            reader, int(module["base_address"]), int(module["size"])
        )
        scanner.initialize()
        patterns = PatternCatalog.from_directory("offsets")
        slot = InstanceInfoSlot(reader, scanner, patterns)
        slot.build()
        print(f"{SLOT_RESOLVER:<32} slot=0x{slot.slot:08X}  "
              f"one-time scan={slot.resolve_ms:.3f} ms")

        fresh = slot.pointer()
        cached = slot.struct_pointer_scan()
        agree = "AGREE" if fresh == cached else "DIFFER"
        print(f"fresh deref of slot              = 0x{fresh:08X}")
        print(f"{STRUCT_RESOLVER:<32} = 0x{cached:08X}  {agree}")
        print()

        with connect(process) as client:
            if not arguments.watch:
                return _report_once(client, slot, arguments.samples)
            return _watch(client, slot, arguments.interval)
    return 0


def _report_once(
    client: ConnectedClient,
    slot: InstanceInfoSlot,
    samples: int,
) -> int:
    """Print one verdict plus a timing summary over ``samples`` evaluations."""

    report = evaluate_gate(client, slot)
    print(report.line())
    print()

    durations: list[float] = []
    for _ in range(samples):
        start = time.perf_counter()
        evaluate_gate(client, slot)
        durations.append((time.perf_counter() - start) * 1000.0)

    durations.sort()
    print(f"gate evaluation over {samples} samples")
    print(f"  min={durations[0]:.3f} ms  "
          f"p50={durations[len(durations) // 2]:.3f} ms  "
          f"max={durations[-1]:.3f} ms")
    print()
    print("Compare with the one-time scan cost above: the gate re-dereferences")
    print("the slot chain every time, and that chain is what stays fresh.")
    return 0 if report.ready else 2


def _watch(
    client: ConnectedClient,
    slot: InstanceInfoSlot,
    interval: float,
) -> int:
    """Poll the gate and print a line whenever the verdict or type changes."""

    print("Watching. Change maps in game and watch instance_type. Ctrl+C to stop.")
    print()
    previous: tuple[bool, int, int | None] | None = None
    while True:
        report = evaluate_gate(client, slot)
        state = (report.ready, report.instance_type, report.current_map_id)
        if state != previous:
            stamp = time.strftime("%H:%M:%S")
            print(f"[{stamp}] {report.line()}")
            previous = state
            if report.ready:
                print()
        time.sleep(interval)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        raise SystemExit(130) from None

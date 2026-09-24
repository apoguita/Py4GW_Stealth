# Py4GW Stealth

Py4GW Stealth is an independent external-host project for reading Guild Wars
data and, eventually, executing source-backed work on the game's thread.
Reforged source projects are research references, not runtime dependencies.
The current implementation is read-only. The selected architecture for
source-backed callbacks and game-thread work is an external controller with a
Stealth-owned in-process payload or patch, without a conventional injected
DLL. This modifies `Gw.exe` and is injection. That payload is not implemented
yet, because the first pointer it was needed for now has a read-only route:
`WorldMapContext` is acquired by walking the client's UI frame array, which
writes nothing to the client. See
[`docs/UI_FRAME_TREE.md`](docs/UI_FRAME_TREE.md). “No DLL” describes the
chosen delivery approach; it does not mean the target is unmodified or that the
payload is undetectable. See
[`docs/NATIVE_EXECUTION_PLAN.md`](docs/NATIVE_EXECUTION_PLAN.md)
for the inventory and resumable plan.

The project is being developed one capability at a time. **Full source/API
parity has been achieved for no context.** A mechanical sweep of every source
context struct with data fields (`include/GW/context/*.h` plus
`include/GW/ui/ui.h`) counts **1803 declared fields across 205 structs**: 70
structs are fully represented, 47 are present with fields still unmatched, and
88 have no Stealth declaration — of which **64 are UI-message/packet structs**
(217 fields) and 24 are other data structs (152 fields). That UI-message block
is the largest single body of unported declared data. Method, calibration, and
the naming caveat are in
[`docs/CONTEXT_PARITY_AUDIT.md`](docs/CONTEXT_PARITY_AUDIT.md).

Two map contexts were live-verified open **and** closed through the read-only
frame route: `MissionMapContext` (frame 1591, direct callback registration) and
`WorldMapContext` (frame 3698, registered through a `jmp` thunk). No hook,
payload, or write was involved. `SalvageSessionInfo` is captured by a hook in
the source project but is **not used by either reference project**, and salvage
is driven through UI frames and client-to-server packets, so it is not a
pointer-acquisition gap.

The current library
provides read-only `Gw.exe` discovery, a reusable x86 pattern scanner, and
external readers for Reforged's maintained `CharContext`, `GameContext`,
`PreGameContext`, `Cinematic`, `GameplayContext`, `ServerRegion`,
`InstanceInfo`, `TextParser`, `AvailableCharacterArray`, `PartyContext`,
`GuildContext`, `AccAgentContext`, `Camera`, `FriendList`, `ChatBuffer`,
`WorldContext`, `TradeContext`, `ItemContext`, `AccountContext`, and
`GadgetContext`, plus the read-only `MapContext` pathing, props, snapshots,
travel-portal helpers, and per-client pathing cache. `MissionMapContext` and
`WorldMapContext` structures and data readers are also ported, plus the native
`SalvageSessionInfo` record. All three acquire their root address the same
read-only way: by walking the client's UI frame array to the frame that
registered the relevant callback. Resolution and array structure are confirmed
on one live client; the callback handoff itself is still pending an open/close
test. See
[`docs/CALLBACK_POINTER_RESEARCH.md`](docs/CALLBACK_POINTER_RESEARCH.md) for the
callback-route status and [`docs/UI_FRAME_TREE.md`](docs/UI_FRAME_TREE.md) for
the frame-tree route and its test scripts. Any target-side payload or patch is
still injection, even without a DLL.
A small NiceGUI window exercises the
client-selection and read-only connection surface.
The library also has a bounded AgentArray reader with native category
classification, lazy agent-record reads, and explicit living-agent snapshots
for frequent queries. Living effects, visible effects, equipment, and tags are
available from those records.

The existence of a reader does not imply complete parity with the source
projects. The current field/helper inventory and every recorded gap are in
[`docs/CONTEXT_PARITY_AUDIT.md`](docs/CONTEXT_PARITY_AUDIT.md).
Contexts are certified one at a time using a binary source-port checklist;
runtime limitations are recorded separately and never substitute for parity.
Pathing is a first-class MapContext surface; its current status and migration
boundary are recorded in [`docs/PATHING_MIGRATION_PLAN.md`](docs/PATHING_MIGRATION_PLAN.md).
The correction between external read slices and full source/API parity is in
[`docs/PARITY_STATUS_CORRECTION.md`](docs/PARITY_STATUS_CORRECTION.md).

## Install

From the project directory:

```text
python -m pip install -e .
```

This installs the package and its Python dependencies, including NiceGUI's
native-window support. The editable install keeps Python connected to the
working source tree.

Run scripts through the selected Python interpreter:

```text
python path\to\script.py
```

This is preferred over typing `script.py` by itself, because Windows may use a
different interpreter for the `.py` file association.

## Example

```python
from py4gw import Win32

win32 = Win32()
print(win32.format_processes(win32.find_guild_wars()))
```

For a selected PID, the read-only scanner path is:

```python
from py4gw import ProcessMemoryReader, RemoteScanner, Win32

win32 = Win32()
pid = 1234  # choose a PID returned by find_guild_wars()
module = win32.get_main_module(pid)

with ProcessMemoryReader(win32, pid) as reader:
    scanner = RemoteScanner(
        reader,
        module_base=module["base_address"],
        module_size=module["size"],
    )
    scanner.initialize()
    print(scanner.get_section_range("text"))
```

This opens the selected process with read-only access and returns section
addresses. It does not write to or execute code in the process. The scanner
and the context readers have been verified against one live client build.
Compatibility with other builds is not established.

## Caching and readiness

The library follows one rule: **cache what the pattern scan produced, because
that is stable; never cache a dereferenced pointer, because that is map-scoped.**
Guild Wars moves its context pointers on every map load, so a cached final value
belongs to whichever map was loaded when the scan ran.

There is no time-to-live cache. A full readiness gate costs about 0.073 ms while
the one-time scan it depends on costs 4.6-27.6 ms, so the expensive half is the
scan (already cached because it never changes) and the volatile half is cheap to
re-read. The gate is therefore re-evaluated per read, and a map change is noticed
because the client is re-asked rather than because a timer expired:

```python
from py4gw import Map

client = py4gw.connect(pid)

if Map.IsMapReady():
    instance = client.read_instance_info()
else:
    print(Map.GetInstanceTypeName())   # e.g. "Loading"
```

`Map.IsMapReady()` is that predicate, ported member for member from Reforged's
`Map.py` lines 40-118. See [`docs/READINESS_GATE.md`](docs/READINESS_GATE.md) for
the members and the source lines, and
[`docs/PORTING_RULES.md`](docs/PORTING_RULES.md) before adding anything.

## Wrapper classes

The Reforged wrapper classes are being ported one at a time, keeping every member
name and signature. Each member either returns a real value from a readable game
context or refuses with `NotImplementedError` naming the mechanism it would need;
nothing is silently wrong, and nothing writes to the client.

```python
import py4gw
from py4gw.player import Player

py4gw.connect(py4gw.win32.list_processes()[0])
print(Player.GetName(), Player.GetLevel(), Player.GetXY())
```

`Player` is the first ported wrapper: 70 Reforged members, 46 of them working
externally and 24 refusing. See [`docs/PLAYER_PORT.md`](docs/PLAYER_PORT.md) for
the per-member table.

## Main UI

Run the current test surface from the project directory:

```text
python main.py
```

The first tab lists every running Guild Wars client, shows its live character
name when available, labels clients at the selection menus, and lets you
refresh and connect to a selected PID. After connecting, the `Client data`
tab becomes available; its context subtabs display the live structure fields:
`Cinematic`, `Camera`, `FriendList`, `ChatBuffer`, `WorldContext`, `GameplayContext`, `ServerRegion`, `InstanceInfo`, `TextParser`,
`AvailableCharacters`, `PartyContext`, `GuildContext`, `AccAgentContext`,
`AccountContext`, `GadgetContext`, `TradeContext`, `ItemContext`,
`MapContext` (root, pathing arrays/links, props, snapshots, and travel portals),
`PreGameContext`, `GameContext`, and `CharContext`. The migration order for
these readers is `CharContext`, `GameContext`, `PreGameContext`, `Cinematic`,
`GameplayContext`, `ServerRegion`, `InstanceInfo`, `TextParser`,
`AvailableCharacterArray`, `PartyContext`, `GuildContext`, then
`AccAgentContext`, `Camera`, `FriendList`, `ChatBuffer`, then the verified
read-only `WorldContext` root and its source-backed child records (including
party, map-agent, player, NPC, hero, pet, skillbar, quest, title, morale, and
mission-map records), followed by `TradeContext`, `ItemContext`,
AccountContext, and GadgetContext. Item records are read through the bounded
`ItemContext -> Bag -> Item` path, plus the cached source item-global tables
for formulas, composite models, storage state, and PvP metadata; modifier
pointers are read lazily as bounded native modifier words and expose the
native bit/helper rules; the higher-level semantic modifier catalog remains
separate.
`PreGameContext` reports when the client is outside the selection menus.
The context tables support sorting by their
headers, pagination, filtering, row selection, and wrapped values for long
fields.
The context status lines show the latest refresh state.

For a detailed live breakdown of resolver, structure, and pointer/array costs,
run the direct performance harness while Guild Wars is running:

```text
python tests/perf_context.py
```

Use `--samples N` to change the repeated sample count or `--pid PID` to select
a specific client. The harness reports elapsed time, percentiles, remote-read
counts, and requested byte counts for each stage.

The UI is a presentation and testing surface. The `Win32` class remains the
owner of all Windows process operations.

For scripts, the same client-selection path is available through a small
facade:

```python
import py4gw

clients = py4gw.win32.list_processes()
selected_client = clients[0]
client = py4gw.connect(selected_client)
print("attached:", client.is_connected)

char_context = py4gw.context.charcontext.get()
if char_context is not None and char_context.is_logged_in:
    print(char_context.player_name_str or "in selection menus")

game_context = py4gw.context.gamecontext.get()
if game_context is not None:
    print(f"CharContext address: 0x{game_context.char_context:08X}")

gameplay_context = py4gw.context.gameplaycontext.get()
if gameplay_context is not None:
    print(f"Mission-map zoom: {gameplay_context.mission_map_zoom:.3f}")

instance_info = py4gw.context.instanceinfo.get()
if instance_info is not None and instance_info.current_map_info is not None:
    print(f"Map file id: {instance_info.current_map_info.file_id}")

text_parser = py4gw.context.textparser.get()
if text_parser is not None:
    print(f"Text language: {text_parser.language_id}")

available_characters = py4gw.context.availablecharacters.get()
if available_characters is not None:
    print([entry.player_name_str for entry in available_characters.characters])

party = py4gw.context.partycontext.get()
if party is not None:
    print(f"Party leader: {party.is_party_leader}")

py4gw.disconnect()
```

`py4gw.connect` opens the selected process for read-only access and owns the
handle until `py4gw.disconnect()` is called. Connection performs the one-time
signature scan and caches its stable pointer location; later context reads do
not rescan the module.

Controller-side execution timing is available through `PerfCounter`, the
port of Reforged Native's `PyProfiler`:

```python
import py4gw
from py4gw import PerfCounter

perf = PerfCounter()
perf.start("context.read")
try:
    context = py4gw.context.charcontext.get()
finally:
    perf.end("context.read")

print(perf.calculate_report("context.read").avg)
```

This measures Python/controller work only; it does not measure code executing
inside Guild Wars.

## Documentation

- [Scope](docs/SCOPE.md) — what the project is and is not
- [Installation guide](INSTALL.md) — setup and usage details
- [Design contract](docs/DESIGN.md) — current implementation rules
- [Performance](docs/PERFORMANCE.md) — timing, resolver caching, and the live harness
- [Porting rules](docs/PORTING_RULES.md) — read before adding any API: this project ports Reforged and Native, it does not invent
- [Readiness gate](docs/READINESS_GATE.md) — the ported `Map` gate that decides when map data may be read
- [Player port](docs/PLAYER_PORT.md) — the ported Reforged `Player` class, its adaptations, and its disabled members
- [Context inventory](docs/CONTEXT_INVENTORY.md) — native/Reforged context mapping and Stealth status
- [Parity certification checklist](docs/PARITY_CERTIFICATION_CHECKLIST.md) — the one-context-at-a-time binary parity gate
- [Context parity audit](docs/CONTEXT_PARITY_AUDIT.md) — source-backed fields, helpers, and explicit gaps for every migrated reader
- [Target-side work](docs/DEFERRED_INJECTION.md) — planned features that require code, writes, hooks, or patches in the client
- [Native execution plan](docs/NATIVE_EXECUTION_PLAN.md) — source inventory and phased, extensible plan for hooks, callbacks, and game-thread execution
- [Callback pointer research](docs/CALLBACK_POINTER_RESEARCH.md) — the self-sufficient pointer acquisition direction and research steps
- [UI frame tree](docs/UI_FRAME_TREE.md) — the `py4gw/ui/` package and the read-only frame-array route to frame-published contexts
- [Programming style](docs/STYLE.md) — naming and coding conventions
- [Research record](docs/RESEARCH.md) — detailed source analysis and history

## Current boundary

The current implementation only performs read-only operations. It can
discover processes and scan/read selected process memory, but it does not write
to a process, inject code, create remote threads, or install hooks. This
describes what exists now, not a requirement that the final project remain
pure external. The UI frame-tree route is read-only: it reads the client's
frame array, the frame that registered a context's callback, and the context
that frame publishes. It writes nothing and is not a hook or a payload. It
covers `WorldMapContext`, `MissionMapContext`, and `SalvageSessionInfo`;
`GwDxContext` still needs target-side code.

Features that require those mechanisms are not implemented yet and are tracked
in [`docs/DEFERRED_INJECTION.md`](docs/DEFERRED_INJECTION.md) and the phased
[`docs/NATIVE_EXECUTION_PLAN.md`](docs/NATIVE_EXECUTION_PLAN.md).

The selected plan includes game-thread execution through a reusable
Stealth-owned payload/patch bridge rather than a conventional DLL. The
mechanism remains unimplemented, is technically injection, and must preserve
the source-backed behavior documented in the execution plan.

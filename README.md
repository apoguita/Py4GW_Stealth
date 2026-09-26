# Py4GW Stealth

Py4GW Stealth is an independent external-host project for reading Guild Wars data
and for executing source-backed work on the game's own thread. Reforged source
projects are research references, not runtime dependencies.
The reads are read-only and **connecting is a write**. Every context, `Map`,
`Player` and `Party` member only reads. `py4gw.connect()` installs the capability
layer: hooks on two of the client's own functions, an emitted dispatcher that makes
typed calls on the game's thread, and a listener thread that delivers events to
registered callbacks. `disconnect()` stops the listener, restores both functions'
own bytes and frees everything it placed. That modifies `Gw.exe` and is injection
by this project's own definition, so the project is no longer pure external;
`connect(..., game_thread=False)` is the read-only connection. The callback-owned map
contexts still have a read-only route rather than a hook — `WorldMapContext` and
`MissionMapContext` are acquired by walking
the client's UI frame array, which writes nothing to the client. See
[`docs/UI_FRAME_TREE.md`](docs/UI_FRAME_TREE.md). “No DLL” describes the
chosen delivery approach; it does not mean the target is unmodified or that the
payload is undetectable. See
[`docs/NATIVE_EXECUTION_PLAN.md`](docs/NATIVE_EXECUTION_PLAN.md)
for the inventory and resumable plan.

## Status and strategy

**Reforged and Reforged Native are complete, working libraries.** They ship and
they run in production. Stealth is a *port* of them — not a parallel design, not
a reimplementation with different ideas — and the port is past its early stage:
the contexts load and read, five accessor classes are ported, and what is left is
breadth of porting, named member by member in each class's port doc.

**The ported library is read-only; `py4gw/game_thread` is not.** Every path that
reads the client — the contexts, `Map`, `Player`, `Party`, `Client` — only reads.
The separate capability layer in `py4gw/game_thread/` can place code in the client:
a shared block, a fail-closed patch sequence, entry hooks, a dispatcher emitted as
machine code from Python that runs on the game's own thread, and an observer that
reports the client's own messages. All three capabilities are live-verified against
the running client, and the layer puts both functions' original bytes back when a
connection closes: **hooks**, **execution** (typed calls into the client's own
functions, with the effect asserted from what the client itself reported), and
**callbacks** (a registry keyed by event kind, plus a listener thread that delivers
an event as it arrives). What is thin is **breadth, not capability** — six typed call
forms where the sources need more, and a callback kind per hooked function — and no
ported context is wired to either yet, so a context member that needs them is not
ported yet. Eleven `Player` actions are the first members ported onto the call path, and
the callback layer has its first consumers: the connection registers the dialog
module's handler and the target capture against the client's own UI messages, which is
how `Player.GetTargetID` and `Dialog.get_active_dialog()` read what the client reported
rather than polling for it.

**The structure comes first.** Every member of a ported class is declared now, in
the source's own shape and nesting, including the members whose bodies are not
ported yet. That is deliberate: when remote execution, hooks or callbacks are added,
the functionality is ported into a slot that already exists, instead of the class
having to be redesigned around a capability that arrived later. A member that is not
yet ported in this library is therefore not an unknown quantity — it is a placeholder
that carries its own name, its source location, and exactly what it still needs.

Read [`docs/PORTING_RULES.md`](docs/PORTING_RULES.md) before adding anything.

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
provides read-only `Gw.exe` discovery, a reusable x86 pattern scanner, external
readers for Reforged's maintained `CharContext`, `GameContext`,
`PreGameContext`, `Cinematic`, `GameplayContext`, `ServerRegion`,
`InstanceInfo`, `TextParser`, `AvailableCharacterArray`, `PartyContext`,
`GuildContext`, `AccAgentContext`, `Camera`, `FriendList`, `ChatBuffer`,
`WorldContext`, `TradeContext`, `ItemContext`, `AccountContext`, and
`GadgetContext`, plus the read-only `MapContext` pathing, props, snapshots,
travel-portal helpers, and per-client pathing cache. `MissionMapContext` and
`WorldMapContext` structures and data readers are also ported, plus the native
`SalvageSessionInfo` record. All three acquire their root address the same
read-only way: by walking the client's UI frame array to the frame that
registered the relevant callback. `MissionMapContext` and `WorldMapContext` are
live-verified open and closed through that route;
`SalvageSessionInfo` is resolved but its open/close handoff has not been tested.
See
[`docs/CALLBACK_POINTER_RESEARCH.md`](docs/CALLBACK_POINTER_RESEARCH.md) for the
callback-route status and [`docs/UI_FRAME_TREE.md`](docs/UI_FRAME_TREE.md) for
the frame-tree route and its test scripts. Any target-side payload or patch is
still injection, even without a DLL.
A small NiceGUI window exercises the
client-selection and connection surface. It opens the client list read-only and
patches nothing; a selected connection installs the game-thread layer.
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

Reforged's `@frame_cache` decorator is **not ported, and nothing replaces it**.
It memoises a call for the duration of one game frame and is cleared by an
in-process tick (`PyCallback.Phase.PreUpdate`). Stealth is not run every frame and
is not throttled; it reads the client on demand, so a ported decorator would never
invalidate and would pin map-scoped values for the life of the process. This is a
settled decision, not a gap — Reforged decorates 36 of `Map`'s 178 members alone,
so expect it on every ported file. The rule and its reasoning are in
[`docs/PORTING_RULES.md`](docs/PORTING_RULES.md); caching is still allowed for
large structures whose contents are expensive to re-read, just never as a
frame-throttle.

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
context, or is not ported yet and raises `NotImplementedError` naming the mechanism
it still needs; nothing is silently wrong, and nothing writes to the client.

```python
import py4gw
from py4gw.player import Player

py4gw.connect(py4gw.win32.list_processes()[0])
print(Player.GetName(), Player.GetLevel(), Player.GetXY())
```

`Map`, `Player`, `Party`, `Scanner` and `Dialog` are ported, and each one carries a
verdict in [`docs/CLASS_PORT_MAP.md`](docs/CLASS_PORT_MAP.md): **FULL** when every member
works, **INCOMPLETE** with the remaining members named. `Scanner` is FULL. `Player` has 71
Reforged members: 51 that read, 18 that act by calling the client's own function on its own
thread, and 1 that refuses — `player_instance`, an artifact of the port that is no longer valid for
anything: it returned Reforged's in-process `PyPlayer` object, this project has no player object,
and every value it provided is answered by the class's own members. The chat-history trio is ported and the
history is kept **live**: the connection watches the client's own `kWriteToChatLog` message and
decodes each announced line as it arrives, so `Player.GetChatHistory()` answers after the fact
without anyone calling `RequestChatHistory` first — which still does the source's own
walk-and-replace when it is called. `Party` declares all five of its
namespaces, with its 30 action members still to port; `Dialog` declares all 32 of `PyDialog`'s
bound methods and **all of them answer** — the state from the client's own messages, the five
metadata columns, the frame-by-hash read, the catalog decode queue, both journals, and the
lifecycle. A button's caption **is** produced: the port reads the string where the source reads it
— inside the client's own call — and the client's own decoder renders it (live, 2026-09-25). One
work item is left in the class, and it is porting work: this build's `DialogLoader_GetText`, so a
catalog dialog's `content` is empty for now — the client function the source calls through has not
been identified on this build, and the 2026-09-26 pass over `Gw.exe` itself shows why the usual
routes come up empty (this client inlines the text path into its dialog window). **The sources are
complete and working, so the function is there to find**; the method and the evidence are in
[`docs/RESEARCH.md`](docs/RESEARCH.md) and [`docs/DIALOG_PORT.md`](docs/DIALOG_PORT.md). What is not
missing is the decode: the string the client announces is handed straight back to the client's own
`AsyncDecodeStr`, and the text returns through a callback the port places inside the client
(`docs/RESEARCH.md`). `Agent` (148 members), `Utils` (40 members), `Skill` (87 members) and `SkillBar` (18 members) are
ported and INCOMPLETE too, each with its remaining members named — `Skill`'s record readers and name
tables all work, `Utils.BalthazarSkillIdToDialogId` runs the source's PvP remap over one of them,
`Utils.GenerateSkillbarTemplate` composes a template from the skillbar the `SkillBar` port reads, and
`SkillBar`'s three skill presses name the control-action mechanism they still need. See
[`docs/PLAYER_PORT.md`](docs/PLAYER_PORT.md), [`docs/PARTY_PORT.md`](docs/PARTY_PORT.md),
[`docs/UTILS_PORT.md`](docs/UTILS_PORT.md), [`docs/SKILL_PORT.md`](docs/SKILL_PORT.md),
[`docs/SKILLBAR_PORT.md`](docs/SKILLBAR_PORT.md) and
[`docs/CLASS_PORT_MAP.md`](docs/CLASS_PORT_MAP.md) for the per-member tables.

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

`py4gw.connect` opens the selected process and owns the handle until
`py4gw.disconnect()` is called. Connection performs the one-time signature scan and
caches its stable pointer location; later context reads do not rescan the module.

**Connect requires an elevated shell.** A process cannot elevate itself — its token
is fixed when it is created and no API raises it — so the shell has to be elevated
before the script starts. `connect` therefore asserts elevation once, up front,
through `Win32.is_elevated()`, and raises a `RuntimeError` naming the pid and what
to do about it, rather than letting a bare `error 5` surface later from whichever
operation needed it. Run scripts and the test suite from an elevated shell.

The four rights this library needs beyond reading (`PROCESS_VM_WRITE`,
`PROCESS_VM_OPERATION`, `PROCESS_CREATE_THREAD`, `PROCESS_SUSPEND_RESUME`) are
refused to an unelevated controller with error 5 on this machine even though the
client's own DACL grants our user SID `PROCESS_ALL_ACCESS`; what actually refuses
them is recorded in [`docs/RESEARCH.md`](docs/RESEARCH.md).

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
- [Porting rules](docs/PORTING_RULES.md) — read before adding any API: port what can be ported, name what each unported member still needs, never redesign or invent
- [Readiness gate](docs/READINESS_GATE.md) — the ported `Map` gate that decides when map data may be read
- [Player port](docs/PLAYER_PORT.md) — the ported Reforged `Player` class, its adaptations, its eighteen action members, and what is still to port
- [Utils port](docs/UTILS_PORT.md) — the ported `py4gwcorelib_src/Utils.py` and its `Color`: 36 of 40 members working, the four members it unblocked in `Player` and `Agent`, and the four that name what they still need
- [Skill port](docs/SKILL_PORT.md) — the ported `Skill` class over the client's skill constant table: 79 of 87 members working, native's three generated name tables, and the offline byte-level verification of the record
- [Skillbar port](docs/SKILLBAR_PORT.md) — the ported `SkillBar` class: every read working over the client's skillbar array and tooltip, the control-action members that name their mechanism, and the tooltip indirection measured against the running client
- [Party port](docs/PARTY_PORT.md) — the complete `Party` surface and the four members that can only return a constant
- [Dialog port](docs/DIALOG_PORT.md) — the whole `Dialog` class and the state behind it: all 32 of `PyDialog`'s members answering, the button caption produced where the source produces it, both journals, and the one recorded build divergence
- [Dialog migration plan](docs/DIALOG_MIGRATION_PLAN.md) — the seven features to port first, in dependency order, and what each unblocks beyond `Dialog`
- [Agent port](docs/AGENT_PORT.md) — the queue for Reforged's 147-member `Agent`, prepared ahead of the point it is reached at: `Player.GetInstanceUptime` delegates to it
- [Map port](docs/MAP_PORT.md) — the staged plan for the 178-member `Map` surface, and its progress record
- [Context inventory](docs/CONTEXT_INVENTORY.md) — native/Reforged context mapping and Stealth status
- [Class port map](docs/CLASS_PORT_MAP.md) — which Reforged classes exist, which are ported, what each depends on, and the order the dependencies allow
- [Parity certification checklist](docs/PARITY_CERTIFICATION_CHECKLIST.md) — the one-context-at-a-time binary parity gate
- [Context parity audit](docs/CONTEXT_PARITY_AUDIT.md) — source-backed fields, helpers, and explicit gaps for every migrated reader
- [Target-side work](docs/TARGET_SIDE_WORK.md) — planned features that require code, writes, hooks, or patches in the client
- [Native execution plan](docs/NATIVE_EXECUTION_PLAN.md) — source inventory and phased, extensible plan for hooks, callbacks, and game-thread execution
- [Callback pointer research](docs/CALLBACK_POINTER_RESEARCH.md) — the self-sufficient pointer acquisition direction and research steps
- [UI frame tree](docs/UI_FRAME_TREE.md) — the `py4gw/ui/` package and the read-only frame-array route to frame-published contexts
- [Programming style](docs/STYLE.md) — naming and coding conventions
- [Research record](docs/RESEARCH.md) — detailed source analysis and history

## Current boundary

The project is no longer pure external. Every ported read path — process discovery,
the scanner, the contexts, `Map`, `Player`, `Party` — only reads, and no read has
ever patched a client. On top of those reads, `py4gw/game_thread/` places code in
the client, and **`py4gw.connect()` installs it**:

- `py4gw/win32/write_access.py` opens a second handle with the rights writing needs,
  allocates, writes, reprotects pages and suspends threads;
- `patcher.py` writes a nine-byte entry patch into `leave_game_thread_func` and an
  eight-byte one into `ui.send_ui_message_func`, after checking the bytes it would
  displace and refusing when they differ;
- `hooker.py` places a stub, a trampoline, the emitted dispatcher and the observer in
  memory allocated inside the client;
- a daemon listener thread in the controller reads the event region and delivers
  events to registered handlers.

The dispatcher is **emitted as machine code from Python** and executed by the
client's own thread, so there is no compiler, no build step and no checked-in binary
anywhere in it. `py4gw.disconnect()` stops the listener, restores both functions'
own bytes, waits for the detour to drain and frees everything it placed; a controller
that died mid-install is recovered from instead, by repairing a stale patch of ours
and counting any client threads still suspended. Two full connect/disconnect cycles
have been verified live: the block and the watch list were reused rather than
leaked, both entry byte sequences came back, and the client's code-section hash was
unchanged. `connect(..., game_thread=False)` skips all of it and is the read-only
connection.

This is **payload injection** by the project's own definition — an external
controller writes code and a patch into the client without loading a DLL. It is
bounded: the only client code written is the entry patches at those two addresses,
every other byte lives in memory the connection allocated, and the live tests hash
the whole code section before and after to show it came back byte-identical. Windows
denies the four rights this needs to an unelevated caller with error 5, so it runs
from an elevated shell.

The UI frame-tree route below is read-only: it reads the client's
frame array, the frame that registered a context's callback, and the context
that frame publishes. It writes nothing and is not a hook or a payload. It
covers `WorldMapContext`, `MissionMapContext`, and `SalvageSessionInfo`; both map
contexts are live-verified, and `GwDxContext` still needs target-side code.

Capabilities that are still missing are tracked in
[`docs/TARGET_SIDE_WORK.md`](docs/TARGET_SIDE_WORK.md) and the phased
[`docs/NATIVE_EXECUTION_PLAN.md`](docs/NATIVE_EXECUTION_PLAN.md): the call vocabulary
covers six typed forms where the sources need more — pointer and string arguments
are still the gap — the callback kinds cover what the
two hooks report, and no ported context consumes either yet — which is why a member
needing its source's callback is not ported yet rather than returning a value.


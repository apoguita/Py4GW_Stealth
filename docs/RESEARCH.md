# Py4GW Stealth Research Record

This document contains the detailed research history and source comparisons
that were intentionally kept out of the GitHub front page. It is not the
project's short description or installation guide.

Status: current active research project. The library reads, and since 2026-09-24
`py4gw/game_thread/` writes: two entry hooks, an emitted dispatcher that makes typed
calls on the client's own thread, and a callback listener. `py4gw.connect()` installs
that layer and `disconnect()` removes it and frees what it placed.
Scope: establish what an external Guild Wars controller can read, write, execute, and observe before expanding capabilities.
Authority: inspected current Py4GW Reforged and Py4GW Reforged Native sources; inspected the GwAu3 source checkout; and verified multiple external read slices against a live client. The exact per-context source comparison and remaining gaps are in [`CONTEXT_PARITY_AUDIT.md`](CONTEXT_PARITY_AUDIT.md). Do not treat these live slices as full parity.

## Intent

Py4GW Stealth is an independent external-host project intended to recreate
selected useful Guild Wars data capabilities. It must be self-sufficient: the
Reforged DLL, embedded Python runtime, and Reforged-owned shared-memory block
are source references, not runtime dependencies. The reads are read-only; the
capability layer writes, so the project is no longer pure external and does not
claim to be.

The project is capability-by-capability research. It does not assume that
every in-process Reforged feature can be reproduced externally, and it does
not promise a complete replacement before each capability has been tested.

The immediate purpose is to reproduce the source-backed pointer paths without
depending on Reforged's runtime. **Architecture decision (2026-09-23):** the
external Stealth controller will install Stealth-owned payload/patch code in
`Gw.exe` where Native requires callbacks or game-thread execution. No
conventional injected DLL or Reforged runtime is part of this design. This is
payload injection, not pure-external operation; “no DLL” does not mean the
target is unmodified or that the payload is undetectable. The payload is **built
and live-verified** in `py4gw/game_thread/` and installed by `py4gw.connect()`;
the WorldMap callback pointer it was first aimed at turned out to be reachable
through the client's UI frame array without a hook. See
[`CALLBACK_POINTER_RESEARCH.md`](CALLBACK_POINTER_RESEARCH.md) and
[`NATIVE_EXECUTION_PLAN.md`](NATIVE_EXECUTION_PLAN.md).

## Live result: the game-thread bridge works, but only elevated (2026-09-23)

Target throughout: `F:\GW\GW1\Gw.exe`, PID 29520, SHA-256
`44FBD68767A8D02B5DD4FB1A8A09B684A86B24716731327EE64905DD698FE124`,
10493120 bytes, file version `1, 0, 0, 1`, ArenaNet "Guild Wars Game Client",
main window "Guild Wars Reforged".

### First attempt failed on the process token, not on the client

An unelevated controller cannot obtain a write/execute handle. `OpenProcess`
was probed one right at a time (read-only probe; handles opened and closed
immediately):

| Access right | Unelevated | Elevated |
| --- | --- | --- |
| `PROCESS_QUERY_INFORMATION` (0x0400) | allowed | allowed |
| `PROCESS_VM_READ` (0x0010) | allowed | allowed |
| `PROCESS_TERMINATE` (0x0001) | allowed | allowed |
| `SYNCHRONIZE` (0x00100000) | allowed | allowed |
| `PROCESS_VM_WRITE` (0x0020) | **denied, error 5** | **allowed** |
| `PROCESS_VM_OPERATION` (0x0008) | **denied, error 5** | **allowed** |
| `PROCESS_CREATE_THREAD` (0x0002) | **denied, error 5** | **allowed** |
| `PROCESS_SUSPEND_RESUME` (0x0800) | **denied, error 5** | **allowed** |

### What actually denies those rights (measured 2026-09-24)

The table above is right: unelevated, four rights are refused with error 5, and
elevating the same controller grants them. **The explanation recorded under it was
wrong**, and it was wrong in a way worth writing down, because it named the wrong
mechanism and stopped the question.

Measured directly, all read-only:

```text
client process owner        = S-1-5-21-2318337067-689748385-3951430353-1001   (our own user)
client DACL                 = 3 ALLOW ACEs, no DENY ACE
    ALLOW  PROCESS_ALL_ACCESS        -> our own user SID
    ALLOW  PROCESS_ALL_ACCESS        -> S-1-5-18 (SYSTEM)
    ALLOW  TERMINATE,VM_READ,QUERY*  -> S-1-5-5-1-2886058493 (logon session)
client token                = Medium integrity (S-1-16-8192), elevation type 3 (Limited)
controller token            = Medium integrity (S-1-16-8192), elevation type 3 (Limited)

unelevated rights on pid 15380
    granted  PROCESS_TERMINATE, PROCESS_VM_READ, PROCESS_QUERY_INFORMATION,
             PROCESS_QUERY_LIMITED_INFORMATION, READ_CONTROL, SYNCHRONIZE
    error 5  PROCESS_VM_WRITE, PROCESS_VM_OPERATION, PROCESS_CREATE_THREAD,
             PROCESS_SUSPEND_RESUME, WRITE_DAC, WRITE_OWNER
```

So the client's DACL **grants our own user SID `PROCESS_ALL_ACCESS`**, including
`VM_WRITE`, and both tokens are the same integrity level. Neither the DACL nor
mandatory integrity control can explain the refusal: an access check against that
DACL succeeds for the token we hold. `WRITE_DAC` and `WRITE_OWNER` are refused too,
so there is no unelevated way to change the answer — the DACL cannot be rewritten
and the object cannot be taken over.

What distinguishes the two runs is not a Windows policy. `RTCore64.sys` — RivaTuner
Statistics Server's kernel driver — is loaded (enumerated with `EnumDeviceDrivers`,
which needs no elevation), and the earlier live record on this machine lists
`RTSSHooks.dll` among the client's 99 loaded modules. RTSS registers an
object-handle filter to protect the processes it hooks, and a filter of that kind
refuses write-class rights to callers it does not trust while leaving reads alone,
which is also why an elevated caller is accepted. That is **inferred**, not proven:
it is the only explanation left that fits every measurement, but the driver itself
was not inspected.

**What this changes.** Not the operational rule — target-side work on this client
needs an elevated controller, measured both ways. What changes is why, and what
would make it untrue: the elevation requirement is *this machine's filter*, not a
property of `Gw.exe`. On a machine without RTSS, the DACL above says an unelevated
controller would be granted `VM_WRITE`, and the bridge would not need elevation at
all. **Unresolved:** whether stopping RTSS and re-probing lifts the denial. That is
the experiment that settles it, and it has not been run.

The earlier note here said "ordinary UAC token splitting". It described the
observable behaviour correctly and the mechanism incorrectly: the two tokens do
differ, but not in anything the client's DACL checks.

Consequence for the project: target-side work on this client requires an
elevated controller today. That is a real operational constraint and a change in
the trust boundary — the controller holds administrator rights over the machine,
not merely over the game.

### Live verification (elevated controller)

The hardened bridge (bridge version 2, 612-byte header, 382-byte guarded
dispatcher) was installed against the live client and driven end to end.

Hook install and queue round trip (`tools/test_game_thread_bridge.py`):

```text
leave_game_thread_func   = 0x011F5880
client module range      = 0x00FC0000 + 0xF49000
saved target prologue    = 55 8b ec 81 ec 20 02 00 00
installed entry patch    = e9 7b a7 cf 02 90 90 90 90
published module bounds  = 0x00FC0000 + 0xF49000
hook hits                = 0 -> 3
dispatcher heartbeat     = 0 -> 3
game-thread PING         = state=DONE result=0xC0DEC0DE
```

First live call into a Guild Wars function (`tools/test_move_10.py --move`):

```text
player agent id           = 25
current position          = (1023.807, -640.257, plane=0)
requested target          = (1033.807, -640.257, plane=0)
OP_MOVE                   = state=DONE result=0
observed position         = (1033.807, -640.257, plane=0)
max observed displacement = 10.000 GW units
distance to target        = 0.000
```

Displacement and target distance are exact. The move ABI was cross-checked
against `Py4GW_Reforged_Native/src/GW/agent/agent_methods.cpp:145-155`
(`void __cdecl(float* pos)`, `arg = {x, y, (float)zplane, 0}`) and against the
real callee at static VA `0x00536E80`, whose prologue reads no `[ebp+8]` and
ends in a plain `ret` — one argument, caller-cleaned, matching the dispatcher.

Call-site phase also matches the source project:
`src/GW/game_thread/game_thread.cpp:63-68` runs queued work and *then* calls the
original; the Stealth detour runs its queue and then replays the stolen
prologue, i.e. the same point in the same frame on the same thread.

Both runs restored the original bytes (`Hook restored and remote bridge
allocations freed`), and the client remained responsive, connected, and
logged in afterwards on the same PID. No client was restarted to recover.

### One defect found by the live run

The first elevated attempt was refused by the bridge's own patch gate:

```text
Thread 45648 reported an implausible 32-bit EIP 0x77E1320C,
outside the declared code range 0x00FC0000-0x01F09000.
```

The gate was correct to refuse and wrong to be that narrow. The client has
**99 loaded modules** (including `RTSSHooks.dll` from RivaTuner and
`steam_api.dll`), and a thread suspended for a patch is routinely parked in a
system DLL such as `ntdll`. Trusting only the main image rejected a normal
thread. The gate now accepts any address inside any loaded module
(`Win32.enumerate_modules`, `RemoteExecutionTransport(executable_regions=...)`)
and still fails closed when the address is in none of them. Re-running after
the fix installed the hook on the first attempt.

### Status of the three target-side capabilities

- **Hooks — verified live.** Entry detour installed, fired, and restored.
- **Game-thread code execution — verified live.** The payload ran inside the
  client and the game thread serviced the queue.
- **Call to a real Guild Wars function — verified live.** `agent.move_to_func`
  called on the game thread with the source-backed argument layout.
- **Callbacks — verified live** (added after this section was written). A registry
  keyed by event kind, `py4gw/game_thread/callbacks.py`, and an `EventListener`
  thread that reads the event region and delivers each event as it arrives; a
  handler fired from a real client message with no `pump()` call. What is thin is
  the number of kinds — one per hooked function.

See [`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md) and
[`NATIVE_EXECUTION_PLAN.md`](NATIVE_EXECUTION_PLAN.md).

## Live observation: the first writes from this project (2026-09-24)

Separate from the reference bridge above: this is Stealth's **own** code — the
installer its own hooks will be built with — exercised against the live client
for the first time.

**Target.** `F:\GW\GW1\Gw.exe`, PID 15380, SHA-256
`44FBD68767A8D02B5DD4FB1A8A09B684A86B24716731327EE64905DD698FE124`, 10493120
bytes (`0xA01CC0`), file version `1, 0, 0, 1`, product "Guild Wars", main window
"Guild Wars Reforged". The file is byte-identical to the one in the game-thread
bridge record above; only the PID and the load base (`0x00610000`, ASLR) differ.

**Input.** `python -m unittest tests.test_write_access -v`, from an elevated shell.
Unelevated, the same suite skips itself with its reason recorded — `Windows
denied write access to pid 15380 with error 5` — which was observed first.

**Changed since that run.** `py4gw.connect()` now asserts elevation itself, once,
through `Win32.is_elevated()` (the documented `TokenElevation` query on this
process's own token), and raises a `RuntimeError` naming the pid, the four denied
rights and what to do about it. So the refusal above is no longer something a
caller meets on its first write: it is what connecting reports. The read-only
check in that run used `Win32` and `ProcessMemoryReader` directly rather than
`connect`, which is why it still passed unelevated at the time.

**Expected.** The suite drives the transport and the fail-closed patch sequence:
open the process with the invasive rights, allocate inside it, write, read back,
overwrite, confirm the allocation lies outside the client module, enumerate the
client's threads, read a thread's instruction pointer, patch and restore those
bytes, then refuse a second patch and refuse a restore whose bytes are no longer
ours.

**Observed.** `Ran 10 tests ... OK`. The client was suspended and resumed
repeatedly, its threads were enumerated, a thread context was read, page
protection was changed and restored, and every byte written read back identical.

**Scope of the writes.** Every write targeted memory this test allocated with
`VirtualAllocEx`, asserted to lie outside the client module. Nothing was written
to the client's own code or data; no hook was installed; no remote thread was
created. Each allocation was freed in a `finally` and the transport closed.

**Cleanup verified.** The client was still `Responding=True` on the same PID
afterwards, no temporary files were left behind, the offline suite is 409 tests
green, and `pyright` reports no errors.

**A finding for the module-bound trust anchor.** The same module reports two
different sizes depending on which API answers:

| Source | `Gw.exe` size |
| --- | --- |
| Toolhelp `MODULEENTRY32W.modBaseSize` — the preferred path, elevated only | `0x0F48000` |
| PSAPI `GetModuleInformation().SizeOfImage` — the unelevated fallback | `0x0F49000` |
| PE header `SizeOfImage`, read from the live image | `0x0F49000` |

`CreateToolhelp32Snapshot(TH32CS_SNAPMODULE)` returns `-1` / error 5 to an
unelevated controller (measured directly), so `Win32.get_main_module`
(`py4gw/win32/win32.py:222-266`) falls back to PSAPI — meaning **which number it
returns depends on whether the controller is elevated**, and every target-side
operation requires elevation. Toolhelp's figure is one page short of both the PE
header and PSAPI. The failure mode is in the safe direction: a trust anchor built
from the smaller number can only refuse a legitimate target inside that last page,
never accept an illegitimate one. Which field should carry `module_size` across
the wire is **unresolved**; it is recorded in
[`NATIVE_EXECUTION_PLAN.md`](NATIVE_EXECUTION_PLAN.md).

## Live observation: nine `Player` actions, and the effect read from the client (2026-09-24)

The first time this project has made the client do things and *read back* what it
did, for a whole family of members rather than one call. Every action member of
`py4gw/player.py` that is ported was exercised through the member — `Player.Move`,
not `agent.move_to_func` — and each effect came out of a report the client itself
produces, not out of a call completing.

**Target.** `F:\GW\GW1\Gw.exe`, PID 20192, module base `0x00610000`, size
`0x0F49000`. **Input.** `python -m unittest tests.test_live_player`, elevated, in a
map. Result: 9 tests, 9 passing. `tests/test_player.py` passed alongside it, 49
tests between the two runs.

**The three reports used, and why only those three.**

| Report | Packet | Used for |
| --- | --- | --- |
| `kChangeTarget` (`0x10000020`) | `ChangeTargetUIMsg`, manual target id first | the target a `ChangeTarget` call produced |
| `kDialogBody` (`0x100000A6`) | `DialogBodyInfo`, agent id second | the dialog an interaction opened |
| the client's own world/player records | — | position after `Move`, title tier after `RemoveActiveTitle`, friend-list status after `SetPlayerStatus` |

The observer dereferences each watched message's `wparam`, so **only messages whose
`wparam` is a packet pointer may be watched.** `kSendAgentDialog` is the counter-example
in the sources — its `wparam` *is* the dialog id (`agent.cpp:138-141`) — and no
`kSend*` message is watched, because reading four words from a small integer on the
game thread is a wild read in the client.

**What the run established.**

- `Player.ChangeTarget(agent)` → the client's own notice carried that agent id back.
- `Player.ChangeTarget(0)` → published **no call at all**: the source's binding
  refuses a zero id before it calls (`player_bindings.cpp:237-239`). The client
  function *does* accept zero — the suite uses it to clear — so the member and the
  function are not the same thing, and this is the run that shows it.
- `Player.Move(x, y)` → the character walked and the suite walked it back. The +X
  attempt moved nothing (geometry) and the −X attempt worked: 4.61 units, measured by
  the client's own position.
- `Player.Interact(agent)` → **the client reported a dialog for that agent.** This is
  the strongest evidence in the run: an interaction the client acknowledged in its own
  message stream.
- `Player.CallTarget(agent)` → completed on the game thread, taking the world-action
  branch that a non-enemy is routed to (`agent_methods.cpp:219-224`).
- `Player.RemoveActiveTitle()` → the client's active title tier went from `182` to `0`.
- `Player.SetActiveTitle(id)` → put tier `182` back on title `1`, and switching to
  title `0` moved the client to tier `6`: a *different* title, read back from the
  client's own record. A round trip that removes a title and restores the same one
  proves less than it looks like — a function that does nothing passes it — so the
  switch is the assertion that matters, and the character was left on title `1`.
- `Player.SetPlayerStatus(current)` → completed, and the client's own field still
  agreed; `SetPlayerStatus(9)` published no call, because the source validates first.

Rollback: both hooked functions read back as their own bytes, and the whole code
section hashed identically before and after (`33984c4c...`, 5,473,792 bytes).

**A bug this run found, in code that was already ported and already "verified".**
`Player.GetActiveTitleID` had dropped native's `!player->active_title_tier` check
(`player_methods.cpp:159-161`). A tier index of `0` is what "no title displayed"
*is*, and without the check the title search matched the first title whose tier index
was also `0` and reported a title the player was not displaying. `RemoveActiveTitle()`
had been working correctly; the reader was wrong about what it produced. The existing
live test (`tests/test_player.py::test_active_title_matches_the_player_tier`) had
encoded the same mistake in its assertion, and was split on the same condition. This
is the argument for reading an effect out of the client rather than out of a member:
the member that lies is the one being used to check the member that works.

**A fact the suite's first version got wrong, recorded so it is not re-learned.**
Command sequences start at **zero**: a command's sequence is the `command_written`
counter's value *before* it advances. A test waiting for "a sequence greater than the
last one seen", initialised to `0`, waits forever for a completion event it has
already been handed. Recorded in `Bridge.publish_call`'s docstring.

**And the same mistake a second time, in a different place — which is why it is
written down twice.** The helper that picks a second title to switch to returned `0`
for "none found", and **title index `0` is "Hero", a real title**: `TitleID` starts at
`Hero` and puts `None` at `0xff` (`constants/constants.h:250-267`). For one run the
suite reported that a character with progress in **forty titles** had no second title
to switch to. Two different sentinels in one suite, both colliding with a real `0`.
The rule the suite now follows: a "nothing found" value is `None`, never `0`, unless
`0` is genuinely not a value of that type (an agent id, which starts at `1`, is the
one place `0` is still safe).

**What was not run.** `DepositFaction` (needs 5000 faction and an ambassador), and
the enemy branch of `CallTarget` — a real call-target is a party broadcast and the
suite will not choose a party's target. Interacting with an enemy is never done: it
starts a fight. A dialog an interaction opens is not yet closed by this project —
that needs the Escape key, which is the next work item there; the suite says so and
runs that check last.

## Live observation: the hook, the payload and the queue (2026-09-24)

Stealth's own hook, its own emitted dispatcher and its own host-side queue, run
together against the live client. This is the first time this project has placed
code in `Gw.exe`, and the first time a command published by this process was run
by the client's own game thread. Everything above this section is read-only work;
this one is not, and it is `payload injection` by the definition in `AGENTS.md`.

**Target.** `F:\GW\GW1\Gw.exe`, PID 15380, SHA-256
`44FBD68767A8D02B5DD4FB1A8A09B684A86B24716731327EE64905DD698FE124`, module base
`0x00610000`, size `0x0F49000`.

**Input.** `python -m unittest tests.test_live_bridge`, from an elevated shell. A
read-only preflight ran first, confirming the resolver and the entry bytes before
anything was written.

**Resolved first, read-only:**

```text
game_thread.leave_game_thread_func = 0x00845880
entry bytes                        = 55 8b ec 81 ec 20 02 00 00
bytes after them                   = a1 80 74 e0 00 33 c5   (mov eax,[0x00E07480]; xor eax,esp)
```

The nine bytes the test declares as displaced end exactly where that next
instruction begins, so the cut is at an instruction boundary and not through the
middle of one. The offset inside the module is `0x235880`, which is the same offset
the earlier bridge record resolved on a different load base (`0x011F5880` with base
`0x00FC0000`). Two independent runs, two ASLR bases, the same function.

**Expected.** The hook is placed on that function, with its entry bytes checked
against the declared ones before anything is written; it fires on the client's
timeline; work published by this process is taken and completed by the game thread;
the completion event comes back; the original bytes are restored at the end.

**Observed.** `Ran 10 tests ... OK`.

```text
leave_game_thread_func     = 0x00845880
displaced entry bytes      = 55 8b ec 81 ec 20 02 00 00
hook hits                  = 2
entry after remove         = 55 8b ec 81 ec 20 02 00 00
code section before        = 33984c4c6a98d23ec43b00798f9f2a11... (5473792 bytes)
code section after         = 33984c4c6a98d23ec43b00798f9f2a11... (5473792 bytes)
left mapped (on purpose)   = block 0x09540000, dispatcher 0x09550000
```

- `PING` completed `DONE` with `0xC0DEC0DE`; `ECHO_U32` returned its argument;
  `ADD_U32` returned the sum; `NOP` completed with no result; and an operation the
  payload does not know completed `FAILED` with `-100`. Every one of those was
  computed **inside the client, on the client's own thread**.
- The completion event arrived carrying the command's sequence, operation, terminal
  state and result.
- The command ring was driven past its depth — 17 commands in one test, across a
  lap boundary — with every command completing and nothing left outstanding.
- The hooked function kept running after the round trips: the hit counter advanced
  again, which is the trampoline replaying the displaced prologue and the client
  carrying on with its own work.
- The client stayed alive and responsive on the same PID for the whole run.

**Cleanup verified, and this is the strongest statement the project can make about
its own writes.** The entry bytes read back as the original nine. Beyond that, the
client's whole `.text` section — 5,473,792 bytes — was hashed before the hook was
installed and after it was removed, and the two digests are identical
(`33984c4c...`). The entry patch is the only client code this project writes, so
that is evidence rather than assertion: the client's code section came back exactly
as it was found.

**What is deliberately left mapped.** The block and the dispatcher stay allocated
inside the client, about 3 KB per run, because a thread can be inside the stub at
the moment of removal and about to call the dispatcher. That is the same reasoning
the hooker already records for the stub itself, and it is the concrete cost behind
the owner-loss question in the plan. The runs so far have left three such pairs;
the client reclaims them when it exits.


The Native project remains the source authority for pointer ownership and
acquisition. Its direct signatures and callback-published pointers are
different cases; Stealth will reproduce the relevant Native callback path
rather than consume Reforged's shared-memory publication. The read-only
context-parity roadmap continues as a separate track and does not gate the
selected WorldMap callback implementation.

This document does not promise a botting surface. The payload architecture and
first callback target are selected; the callback's implementation, review,
and live verification remain unfinished.

The current implementation is intentionally narrower than the long-term
research question: it is a project-owned `Win32` boundary, a reusable
read-only scanner consuming the copied offsets definitions, and a small
NiceGUI window for exercising process discovery. The UI does not expand the
library's process or memory capabilities.

The current source inventory for the native and Reforged context surfaces is
maintained in [CONTEXT_INVENTORY.md](CONTEXT_INVENTORY.md). It records the
native root accessors, the Reforged Python modules, their many-to-one mapping,
and which surfaces Stealth has actually implemented. That inventory is
comparative source evidence; it is not evidence that every context has been
externally validated.

## Live result: the effect asserted from the client's own report (2026-09-24)

The target is not yet read from a context — checked in both projects, not assumed:

```cpp
// Py4GW_Reforged/Py4GWCoreLib/Player.py:229-235
return Player.player_instance().target_id;

// Py4GW_Reforged_Native/src/GW/player/player_bindings.cpp:159   (what fills it)
target_id = static_cast<int>(GW::agent::GetTargetId());

// src/GW/agent/agent_methods.cpp:65-66
uint32_t GetTargetId() { return g_current_target_id; }

// src/GW/agent/agent.cpp:60 and 161-165   (the only writer)
uint32_t g_current_target_id = 0;
case ui::UIMessage::kChangeTarget:
    g_current_target_id = msg ? msg->manual_target_id : 0;
```

`ChangeTargetUIMsg` and `ChangeTargetPacket` (`include/GW/context/ui.h:78-85, 198-205`)
are message payloads, not contexts. So the target is **only** available the way
Reforged gets it: by listening to the client's own `kChangeTarget` message. Nothing
else holds it, which is why `Player.GetTargetID` is not yet ported here.

**So this project now listens too.** `tests/test_live_call.py` installs a second
hook on `ui.send_ui_message_func` (resolved as `0x008441A0`), with a watch list of
one message id (`kChangeTarget = 0x10000020`), and the observer records a matching
call as an event carrying the packet's first four words. Then it asserts the effect
rather than trusting a completion:

```text
change_target_func         = 0x009F6F60
ui.send_ui_message_func    = 0x008441A0
watch list                 = 0x0AFA0000 [kChangeTarget 0x10000020]
observer code              = 0x0AFB0000
game-thread entry after    = 55 8b ec 81 ec 20 02 00 00
message entry after        = 55 8b ec 8b 45 08 83 f8 56
code section before        = 33984c4c6a98d23ec43b00798f9f2a11...
code section after         = 33984c4c6a98d23ec43b00798f9f2a11...
```

`Ran 4 tests ... OK`: the target was set to another agent, and the id that came back
out of the client's own notice was **that agent**. Clearing it reported zero. Only
the watched message was recorded — the client sends a great many others on the same
function — and both entry patches were restored with the code section unchanged.

**Two things measured that the tests now depend on.**

- **The client reports changes, not requests.** Setting the target it already has
  produces no notice at all. This failed two runs before it was understood: the
  first because the same target was set twice, the second because an earlier test
  had already set it. The tests now ask for the opposite target first and discard
  that notice, so they do not depend on the order they run in.
- **Setting the target to the player's own agent produced no notice** in this build.
  Recorded rather than asserted: one run cannot separate "the client ignores
  self-selection" from "it was slower than the two-second wait". The assertion uses
  another living agent instead.

**The entry cut is eight bytes, not ten.** The first ten bytes of
`ui.send_ui_message_func` are `push ebp; mov ebp,esp; mov eax,[ebp+8]; cmp eax,0x56;
jae +0x16` — and the `jae` is a **relative branch**. The trampoline replays the
displaced bytes verbatim at a different address, so displacing a branch would send
it somewhere else entirely. Eight bytes ends on a whole instruction before it. This
is the sharpest edge the hooker's "the caller declares the displaced bytes" rule
exists for: the bytes match either way, and only the *cut* is wrong.

**What this unlocks.** `Player.GetTargetID` can now be implemented the way Reforged
implements it — from the client's own notification, maintained by the host — instead
of leaving the member unported. **Done**: the connection watches `kChangeTarget` and keeps the packet's
first word, and a live run had the client announce target `16` with the member reading
`16` back (`docs/PLAYER_PORT.md`). Any future action can be verified the same way: call
the function, watch the client say what it did.

## Live result: the target changed, and why the message did not (2026-09-24)

The first live call was on the wrong side of the mechanism, and both source projects
say so once you follow the path end to end.

**Reforged Python's path** (`Py4GWCoreLib/Player.py:705-715` →
`native_src/methods/PlayerMethods.py:102-111`):

```python
Player.ChangeTarget(agent_id)
    -> ActionQueueManager().AddAction("ACTION", _do_action)      # game thread
    -> Player.player_instance().ChangeTarget(agent_id)
    -> PyGameThread.enqueue(_action)                            # game thread again
    -> UIManager.SendUIMessage(UIMessage.kSendChangeTarget, [target.agent_id])
```

So the action, in Reforged, is **sending a message** — which is why sending one
looked like the right move. But nothing in the client acts on `kSendChangeTarget`:
what acts on it is Reforged's own injected handler (`agent.cpp:143-155`), which sees
the message and calls the real function:

```cpp
case ui::UIMessage::kSendChangeTarget:
    if (g_change_target_original) {
        const auto* packet = static_cast<ui::packet::kSendChangeTarget*>(wparam);
        g_change_target_original(packet->target_id, packet->auto_target_id);
    }
```

`g_change_target_original` is the original code of the function Native resolved
(`agent.change_target_func`, hooked at `agent.cpp:230-236`). **The message is how
Reforged's own runtime is told; the function is what changes the target.** With no
runtime inside the client, our message had no listener, and the target did not move.

**Called the function instead, and it moved.** `tests/probe_live_target.py`
resolved `agent.change_target_func` to `0x009F6F60` and alternated
`(player_agent_id, 0)` with `(0, 0)` — target self, then clear, which is what
Native's `ManagerCanFindAgent` documents id `0` as doing (`agent.cpp:119`). Observed
by the person at the keyboard: **the target ring appeared and cleared, repeatedly**.
That is the first time this project has changed the state of a running game.

**A mistake in the probe, recorded so it is not repeated.** It was run with 20
rounds, holding the target for about a minute. That was far more than the question
needed and it was uncomfortable to watch. The defaults are now 3 rounds — six target
changes, about nine seconds — with a ceiling on the arguments and a "finished" line
at the end, because an operator watching a live client needs to know it will stop.

**The client was left clean**, checked afterwards rather than assumed:

```text
python processes        = none
entry @ 0x00845880      = 55 8b ec 81 ec 20 02 00 00   (its own bytes, not a patch)
.text sha256            = 33984c4c6a98d23e...          identical to the baseline
```

**What this changes for the port.** A Native action is not one thing but two: the
message the runtime broadcasts and the function the runtime calls in response. Only
the second is ours to make. That is the rule for porting any action from here —
follow the message to the handler, and call what the handler calls.

**And the limit that remained, and how it was closed.** The effect is real and
observable by a person, but at the time it was not readable by this process: the
current target is `g_current_target_id`, fed from the `kChangeTarget` message
(`agent.cpp:161-165`), and no context holds it — which is why `Player.GetTargetID`
was not yet ported. Both directions were then built. Observing the notification is the
observer hook in `py4gw/game_thread/`: `client.watch(message)` records a message id
in the client's own watch list and the listener delivers it to a registered
handler. Reading the value is `offsets/gwau3_leads.json`, a copied GwAu3 lead whose
resolver lands on the address operand at `0x0129A174`; it was confirmed
differentially rather than assumed — the target was set to the player's own agent,
a gadget and two living agents of different allegiances, and the address followed
every one, each checked against the client's own change notice. `Player.GetTargetID`
is still not ported: the value is reachable, and porting the member onto that
route is the next work item.

## Live observation: the first call into the client (2026-09-24)

This project made a Guild Wars client **do** something for the first time. Until
now every live run either read the client or ran our own code inside it; this one
called one of the client's own functions, on the client's own thread, with
arguments this process chose.

**Target.** `F:\GW\GW1\Gw.exe`, PID 15380, module `0x00610000 + 0xF49000`.

**Input.** `python -m unittest tests.test_live_call`, from an elevated shell, in a
map.

**Resolved first, read-only, through the pattern catalog:**

```text
game_thread.leave_game_thread_func = 0x00845880   55 8b ec 81 ec 20 02 00 00 a1 80 74 ...
ui.send_ui_message_func            = 0x008441a0   55 8b ec 8b 45 08 83 f8 56 73 16 68 ...
```

The second one is worth reading as a contract check, not just an address:

```asm
55            push ebp
8b ec         mov  ebp, esp
8b 45 08      mov  eax, [ebp+8]     ; the first argument, a cdecl argument
83 f8 56      cmp  eax, 0x56        ; bounded against the message-id count
73 16         jae  +0x16
68 ...        push <something>      ; then dispatch
```

A function that reads its first argument from `[ebp+8]` and bounds-checks it
against `0x56` is a `void __cdecl(uint32 message_id, ...)` dispatcher, which is
what `SendUIMessageFn` says it is (`ui_patterns.cpp:31`). The ABI was checked
against the client before a single byte was written.

**The call.** `ui::SendUIMessage(kSendChangeTarget, &packet{agent_id, 0}, nullptr)`,
resolved to `0x008441A0` and named by call-table slot 0, with the player's own
agent id (38) as the target. That is `agent_methods.cpp:132-135`'s call, made from
outside the process.

**Observed.** `Ran 6 tests ... OK`:

```text
leave_game_thread_func     = 0x00845880
ui.send_ui_message_func    = 0x008441A0
module range               = 0x00610000 + 0xF49000
call table                 = 0x03690000
target agent               = 38
hook hits                  = 2
entry after remove         = 55 8b ec 81 ec 20 02 00 00
code section before        = 33984c4c6a98d23ec43b00798f9f2a11... (5473792 bytes)
code section after         = 33984c4c6a98d23ec43b00798f9f2a11... (5473792 bytes)
```

- The call completed `DONE` — taken off the queue by the game thread and run there,
  while the client kept running its own frame. The hook fired again afterwards,
  which is the trampoline still replaying the prologue.
- **Two refusals were exercised live, inside the client**, not in a fake target: a
  slot naming `0x1000`, outside the module, came back `RESULT_BAD_TARGET` (−102)
  without being called, and a slot past the end of the table came back
  `RESULT_BAD_DESCRIPTOR` (−104). That is the "no arbitrary remote call" rule
  answering in the only place it counts.
- The completion event arrived carrying the operation and the terminal state.
- The client stayed alive and responsive on the same PID.
- The entry bytes were restored, and the client's whole `.text` section hashed
  identically before and after (`33984c4c...`), so the only code written was the
  nine-byte entry patch.

**What it does not prove.** That the game changed *in this run*. The player's
current target is `g_current_target_id`, which Native maintains from a
`kChangeTarget` UI-message hook (`agent.cpp:60,143-145`) and which no readable
context holds — the reason `Player.GetTargetID` is not yet ported in this library. This run
proves the call reached the client's own function on the client's thread and the
client survived it. The effect itself was shown separately, by calling
`agent.change_target_func` directly from a probe and watching the target ring
appear and clear, and it is now also readable through the current-target resolver
recorded above.

## The call vocabulary as the sources define it (2026-09-24)

Read before writing any of it, because what the sources say changed what the first
slice had to be.

`Py4GW_Reforged_Native` declares each call's ABI as a typedef next to the code that
uses it (`src/GW/agent/agent_methods.cpp:18-22`):

```cpp
using SendDialogFn    = void(__cdecl*)(uint32_t dialog_id);
using ChangeTargetFn  = void(__cdecl*)(uint32_t agent_id, uint32_t auto_target_id);
using CallTargetFn    = void(__cdecl*)(Constants::CallTargetType type, uint32_t agent_id);
using MoveToFn        = void(__cdecl*)(float* pos);
using DoWorldActionFn = void(__cdecl*)(Constants::WorldActionId action_id, uint32_t agent_id, bool suppress_call_target);
```

But the actions barely use those. Almost everything routes through **one**
function, declared in `ui_patterns.cpp:31` and `ui_methods.cpp:19`:

```cpp
using SendUIMessageFn = void(__cdecl*)(UIMessage message_id, void* wparam, void* lparam);
```

`agent.ChangeTarget` (`agent_methods.cpp:132-135`) sends `kSendChangeTarget` with a
two-word packet; `InteractAgent` sends `kSendWorldAction`; `CallTarget` sends
`kSendCallTarget`; the party-search, tick, invite, travel, difficulty and
hero add/kick paths are the same shape. The packet contract is documented in
`ui_bindings.cpp:60-74`: a **zeroed sixteen-word POD**, values packed into the
front, passed as `wparam`, `lparam` null.

Two consequences for this project:

1. **The first callable operation is that one function**, not a per-action
   function. One form covers a family, which is why the first slice is a form and
   not an operation per action.
2. **Its address is already in our catalog.** Native resolves it with
   `PY4GW::Patterns::Resolve("ui.send_ui_message_func", ...)` (`ui.cpp:722`), and
   our copied `offsets/ui.json` carries `send_ui_message_func` with the same
   `send_ui_message` pattern and a `to_function_start` step — one of the 29 offset
   files that are byte-identical to Native's. Nothing new was needed to resolve a
   callable target.

**A not-yet-ported member this explains.** `Player.GetTargetID` is not yet ported because the current
target is `g_current_target_id`, which Native maintains from a `kChangeTarget`
UI-message **hook** (`agent.cpp:60` and `143-145`), not from any context, so the
source's own accessor is still to port as written. Both halves of that gap now have
a route in Stealth — the notification through the observer hook, and the value
through the current-target resolver — but the member is still declared and not yet
ported; porting it onto either route is the next work item.

## Terminology

`External host` means the primary logic runs outside `Gw.exe`. It does not, by itself, mean that the game process is unmodified.

`Self-sufficient` means Stealth owns its required pointer-acquisition and data
transport paths; it does not require the Reforged DLL or shared-memory block.
It does not imply pure external operation.

`Pure external` means the tool does not allocate executable remote memory, write code into `Gw.exe`, or patch its code. Process-memory reads and writes may still occur.

`Payload injection` means an external program writes a small executable payload and/or code patch into `Gw.exe`, without loading a conventional DLL. It is still injection in the technical sense.

`DLL injection` means an in-process DLL owns a substantial runtime. Current Py4GW Reforged uses this model.

“Non-injected” is shorthand for the pure-external model above. If a future
experiment places a payload, executable code, or a patch in `Gw.exe`, it is
technically injection and must not be described as non-injected.

## Relationship to Py4GW Reforged

Py4GW Reforged is a Python automation and scripting library for Guild Wars. It
provides tools for in-game interaction, from single-character helpers to
multi-account bots. Python does not run as a standalone interpreter in that
model: the launcher injects `Py4GW.dll` into the game, and the DLL embeds the
Python runtime inside `Gw.exe`.

Reforged reaches the game through two connected paths:

- `Py*` bindings such as `PyAgent`, `PyPlayer`, `PyImGui`, and `PySystem`, with
  wrapper classes in `Py4GWCoreLib`;
- shared memory containing live game state such as agent positions, health,
  map state, and world context.

The native companion project builds the injected `Py4GW.dll`:
<https://github.com/apoguita/Py4GW_Reforged_Native>

Stealth is intended to investigate how selected Reforged capabilities could be
recreated from an external Python process. It is not currently a replacement
for the complete Reforged library, and each capability must be designed and
validated separately.

## Current Implementation

Status: verified from the current source, Pyright run, and focused tests.

The current project surface is:

```text
main.py                 NiceGUI native test window
py4gw/                  project package
  win32/win32.py        Win32 process-discovery class
  memory/memory.py      Read-only process-memory transport
  scanner/scanner.py    Offline pattern scanner core
  scanner/remote.py     PE sections and remote scanner
  scanner/patterns.py   Offset definitions and resolver chains
  context/char_context.py  Reforged CharContext layout, reader, and accessor
  context/game_context.py External GameContext layout, resolver, and reader
  context/pre_game_context.py External PreGameContext layout, resolver, and reader
  context/cinematic_context.py External Cinematic layout and reader
  context/gameplay_context.py External GameplayContext layout and reader
  context/server_region_context.py External ServerRegion layout, resolver, and reader
  context/instance_info_context.py External InstanceInfo layout, resolver, and reader
  context/text_parser_context.py External TextParser layout and GameContext reader
  context/available_character_context.py External account-roster array reader
  context/party_context.py External PartyContext hierarchy and list readers
  context/guild_context.py External GuildContext hierarchy and guild readers
  context/acc_agent_context.py External AgentContext summary and movement readers
tests/test_win32.py     focused process tests
tests/test_scanner.py   offline scanner tests
tests/test_remote_scanner.py  synthetic PE scanner tests
tests/test_patterns.py  offsets/resolver tests
tests/test_cinematic_context.py live Cinematic integration test
tests/test_gameplay_context.py live GameplayContext integration test
tests/test_server_region_context.py live ServerRegion integration test
tests/test_instance_info_context.py live InstanceInfo integration test
tests/test_text_parser_context.py live TextParser integration test
tests/test_available_character_context.py live AvailableCharacterArray integration test
tests/test_party_context.py live PartyContext integration test
tests/test_guild_context.py live GuildContext integration test
tests/test_acc_agent_context.py live AccAgentContext integration test
tests/test_context.py   live CharContext integration test
tests/nicegui_probe.py  manual NiceGUI dependency check
```

The `Win32` class currently provides `list_processes`,
`find_guild_wars`, and `format_processes`. `find_guild_wars` matches the
executable filename `Gw.exe` case-insensitively and reports the PID, name,
path, and path error when applicable.

The `Scanner` class scans a local byte snapshot. It supports the
Reforged escaped pattern literals, masks, signed result offsets, bounded
ranges, first/all/nth matches, and the native C-string compatibility behavior
used by the copied offsets definitions. It is deliberately independent of
Windows handles.

The `ProcessMemoryReader` and `RemoteScanner` add the read-only external path:
they open a selected process, parse its x86 PE section ranges, scan those
ranges in bounded chunks, and execute the copied `Patterns` resolver
operations. Their section and resolver path, plus the `CharContext`,
`GameContext`, `PreGameContext`, `Cinematic`, `GameplayContext`,
`ServerRegion`, `InstanceInfo`, and `TextParser` readers have been implemented
and verified. `AvailableCharacterArray`, `PartyContext`, `GuildContext`, and
`AccAgentContext`, the read-only `Camera` context, `FriendList`, and
`ChatBuffer` have also been implemented and verified
against one live client build. This does not establish compatibility with
other builds.

The root `main.py` window has a client-selection tab and read-only context
tabs for a connected client. NiceGUI is a presentation
dependency only; it does not own Windows API declarations, process handles,
memory operations, or Guild Wars-specific rules.

The project enforces this code boundary with `pyrightconfig.json`: Pyright
checks `main.py`, `py4gw/`, and `tests/`, while excluding the local research
checkouts under `external/`. The selected Pyright/Pylance interpreter must be
the same interpreter where NiceGUI and the editable project are installed.

## Confirmed Research

### Current Py4GW Reforged

- The Python repository describes `Py4GW.dll` as embedding Python inside Guild Wars. The external bridge communicates with an injected bridge widget; it does not replace the injected runtime.
- The native repository identifies itself as a Windows-only, 32-bit injected DLL. Its runtime creates hooks and runs frame/callback work in process. Relevant owners include `src/Py4GW.cpp`, `src/dllmain.cpp`, `src/base/hooker.cpp`, and `include/callback/callback.h`.
- The native code uses MinHook through `HookBase`. Its game- and render-driven callbacks are therefore in-process behavior, not an externally delivered callback mechanism.

Conclusion: the existing `Py*` modules and Python callback system are not yet ported to Stealth — an ordinary external Python interpreter does not import them directly, so reproducing that surface here is outstanding work. They exist because the DLL has embedded a Python runtime inside `Gw.exe`.

### GwAu3

GwAu3's AutoIt application is external, but its command execution mechanism is not pure external memory access.

- `API/Core/GwAu3_Core_Assembler.au3`, `Assembler_ModifyMemory()`, allocates executable memory in `Gw.exe` with `VirtualAllocEx`, writes generated assembly, and installs detours including `MainStart -> MainProc`.
- Its generated `MainProc` checks a remote command queue and transfers execution to the queued command when the game reaches the detoured main path.
- `API/Core/GwAu3_Core.au3`, `Core_Enqueue()`, uses `WriteProcessMemory` to place externally-built command records in that queue.
- `API/Core/GwAu3_Core_Scanner.au3` also uses a remotely created thread for its scan procedure.

Conclusion: GwAu3 demonstrates that an external controller can gain broad game-thread execution capabilities without an injected DLL or embedded scripting runtime. It does so by injecting a smaller executable payload and patching game code. AutoIt is not the special capability; a 32-bit Python process with appropriate Windows interop could use the same operating-system primitives.

### GwAu3 character-name discovery

Status: verified by source inspection of the checked-out GwAu3 revision. This
is not yet verified against a live Guild Wars client from Stealth.

GwAu3 uses the character name to make a list of `Gw.exe` candidates useful for
human selection. Its character-name path is:

1. Enumerate processes whose executable name is `gw.exe`.
2. Open one candidate process and discover its main module base address.
3. Read the module's PE headers and record the virtual ranges of sections such
   as `.text`.
4. Read the `.text` section and search for the x86 byte pattern
   `8B 03 83 C4 10 A3`.
5. From the match, read a 32-bit pointer at the pattern-relative offset used
   by GwAu3 (`match + 6 - 0xF`).
6. Read a fixed-size UTF-16/wchar character-name value from that pointer.
7. When the caller supplied a character name, compare the trimmed result and
   keep the matching PID/window. When scanning all clients, return the name
   associated with each candidate.

The relevant source paths are `API/Core/GwAu3_Core.au3`,
`API/Core/GwAu3_Core_Scanner.au3`, `API/Modules/Data/GwAu3_Data_Player.au3`,
and `API/Core/GwAu3_Core_Memory.au3`. `Scanner_ScanGW` does not check the
character-pattern result before calling `Player_GetCharName`, which is a
source-level weakness rather than evidence that every candidate is identified.

This mechanism is a read-only pattern scan and pointer dereference. GwAu3
opens the process with an all-access mask (`0x1F0FFF`), but Stealth should not
copy that privilege choice for a read-only identity probe. The pattern and
offset are historical comparative evidence, not a current-build guarantee.
They must be revalidated against the target build and treated as a target-
specific adapter rather than hidden inside generic Win32 process code.

### Implemented capability: reusable read-only scanner

The implemented scanner is reusable, not character-specific. Its job is to
search validated byte ranges in a selected process and report matches without
knowing what those matches mean. Guild Wars character-name discovery will be a
consumer of this scanner, not part of the scanner engine itself. The current
consumers are the maintained `CharContext`, `GameContext`, `PreGameContext`,
`Cinematic`, `GameplayContext`, `ServerRegion`, `InstanceInfo`, `TextParser`,
`AvailableCharacterArray`, `PartyContext`, `GuildContext`, and
`AccAgentContext` readers.

The scanner foundation should provide:

- bounded reads from a selected process and address range;
- exact byte patterns and explicitly represented wildcard bytes;
- correct handling of matches that cross read-chunk boundaries;
- zero, one, or many match results with their target addresses;
- validation of requested ranges and target pointer width;
- distinct outcomes for unreadable ranges, incomplete reads, and no matches;
- explicit ownership and closing of process handles; and
- deterministic offline tests that do not require a live Guild Wars client.

The implementation was staged as offline matching, bounded process-memory
transport, section/range selection, remote helper operations, and finally the
offsets resolver. A target-specific signature, pointer offset, or
text-decoding rule must not be hidden inside the reusable scanner.

## Capability Boundary So Far

| Capability | Pure external process | External host plus remote payload | Current Py4GW DLL |
|---|---|---|---|
| Read process memory | Yes | Yes | Yes |
| Write process memory | Yes | Yes | Yes |
| Run controller logic outside the game | Yes | Yes | Bridge/client split only |
| Reliably execute code on a known game path | Not established | Yes, as GwAu3 demonstrates | Yes |
| Hook internal functions / receive internal callbacks | No normal detour callback path | Yes | Yes |
| Use Py4GW `Py*` modules | No | Not yet ported: they need to be recreated here | Yes |
| In-game D3D/ImGui overlay | No | Not yet ported: it needs in-process overlay code | Yes |

Important distinction: an external process can ask Windows to start code in another process, but that does not prove that a particular Guild Wars function is safe on that thread. Thread affinity, calling convention, object lifetime, and game state must be established per function.

## Remaining Research Questions

1. Which useful Guild Wars state can be read externally with stable, validated pointer chains?
2. Which game-owned command, UI-message, or packet paths can be driven by external writes alone, without a new payload?
3. For each desired internal function, what are its x86 ABI, argument lifetime, required state, and thread-affinity constraints?
4. Which Native-backed operations, beyond the selected WorldMap callback
   capture, require game-thread execution?
5. How should installation, version mismatch, shutdown, and recovery for the
   selected payload be verified and made observable?

## Current Project Boundary

The first read-only runtime exists in the `py4gw` package. It lists Windows
processes, finds `Gw.exe` candidates by executable filename, opens a selected
process for query/VM-read access, and scans validated x86 module sections.
The root NiceGUI window is only a test and presentation surface over process
discovery; it does not own the memory path, and its own client-list refresh does
not modify any process. A selected connection installs the game-thread layer
unless it is asked not to with `game_thread=False`.

Claims about GwAu3 and Reforged behavior are source-based. The Stealth
CharContext, GameContext, PreGameContext, Cinematic, GameplayContext,
ServerRegion, InstanceInfo, process reader, and scanner observations marked as
live below were reproduced against one client build. None of these
observations establish compatibility with other builds or with the remaining
contexts.

## Initial Deliverable: Generic Process-Scanning Library

The first deliverable is a project-owned Windows library plus a small test
surface that can:

1. enumerate running processes and present a useful list;
2. find every process whose executable filename is `Gw.exe`; and
3. open a selected process read-only and scan its validated x86 module ranges;
4. load the copied `offsets/` definitions and execute reusable resolver chains.

The implemented part is generic Windows process handling, a bounded memory
reader, PE section discovery, a reusable pattern scanner, an offsets resolver,
and selected Guild Wars structure readers. Their exact parity and pointer
availability are recorded in `CONTEXT_PARITY_AUDIT.md`. The callback-owned map
contexts are read through their own readers, and Stealth reaches their root
addresses through the client's UI frame array rather than a hook. Command paths and behavior
interpretation are not implemented. The root UI exposes the read surfaces without
adding a second process layer.

Those readers remain read-only. The payload architecture and its WorldMap callback
target were selected early, and the payload has since been built, extended and
verified on a live client in `py4gw/game_thread/` — entry hooks, an emitted
dispatcher that runs typed calls on the client's own thread, and an observer that
reports the client's messages to registered callbacks, all installed by
`py4gw.connect()` and removed by `py4gw.disconnect()`. Memory scanning is read-only
and is part of the implemented foundation. See
[`CALLBACK_POINTER_RESEARCH.md`](CALLBACK_POINTER_RESEARCH.md) and
[`NATIVE_EXECUTION_PLAN.md`](NATIVE_EXECUTION_PLAN.md) for the implementation
record.

### Design order for this deliverable

- [x] Define the public vocabulary and data returned when processes are
  listed: the minimum process summary, unavailable metadata, and errors.
- [x] Define how a caller selects a process: explicit PID input and the
  lifetime of the resulting library object.
- [x] Define exactly what “scan” means for version one: validated module
  sections, masked patterns, bounded ranges, and target addresses.
- [x] Define the library boundary versus a presentation layer. The library
  returns structured data; `main.py` renders it without becoming the library
  API.
- [x] Choose the narrowest Windows APIs and Python implementation needed for
  the current read-only capability.

### Current design decision

The current direction is: keep the generic process-scanning library in small
project-owned pieces, progressing one public capability at a time. The
NiceGUI window remains deliberately limited to testing and presenting
capabilities that already exist in the library.

### First concrete capability: Guild Wars process discovery

The first capability is discovery of running Guild Wars processes so a caller
can locate them. A process is a Guild Wars *candidate* when its executable
filename is `Gw.exe`, compared case-insensitively. This is process discovery
only, not proof of a supported client build or of the scanner's compatibility
with that build.

Discovery returns every candidate, not just the first one. Each result should
at minimum preserve:

- PID (the value used to select a specific process later);
- executable filename used for the match; and
- executable path when Windows makes it available, with an explicit
  unavailable/error status when it does not.

The console API and the NiceGUI table may render those records, but the
records remain structured library data. No process is opened for modification
and no process memory is scanned in this capability.

The implementation rules and object responsibilities for this first slice are
the active [process-discovery design contract](docs/DESIGN.md).

The project-wide naming and Python conventions are in the [programming style
guide](docs/STYLE.md).

## MemLib Context

MemLib has been fetched as an external source checkout at `external/MemLib`, pinned by the checkout currently present at commit `d044a4f8ab5f12121501650e648c9895f8f14eb0`.

The fetched source describes MemLib as a Windows-only Python package that provides Win32 process/module/thread wrappers, remote memory operations, binary scanners, FASM assembly helpers, simple inline jump hooks, and shared-memory utilities. It is a candidate mechanism library for future experiments, not a selected runtime dependency or a statement of supported project behavior.

Important limits established from its own README and source:

- `Hook` is an inline jump helper, not a complete detour engine or a proof that a chosen patch point is safe.
- MemLib can provide process and transport mechanisms, but it does not supply Guild Wars signatures, function ABIs, thread-affinity facts, data layouts, or lifecycle policy.
- No MemLib method has been called against Guild Wars for this project.

## GwAu3 Source Availability

GwAu3 is available locally for historical and comparative source inspection at
`external/GwAu3`, fetched from
`https://github.com/GwAu3-Projects/GwAu3.git` and currently pinned at commit
`f5af99dc3004c81dfdeb119c6fa1e41edb23ddc1`.

This checkout is research context only and is not a Stealth dependency. The
existing GwAu3 conclusions in this document were recorded from the previously
isolated checkout named under Sources Consulted; this fresh revision has not
yet been re-inspected or used to revise those conclusions.

The user-provided `BUILDING_WITH_MEMLIB.md` was reviewed as technical reference material. It contains design proposals and examples; it is not treated as an instruction source or as verification of MemLib/Guild Wars behavior. Any later adoption decision must be supported by the fetched MemLib source, project-specific investigation, and targeted tests.

## Local Ownership Decision

Py4GW Stealth will not depend on or import MemLib for its initial work. The fetched checkout remains research context only.

The current implementation is a small, project-owned set of boundaries:

```text
py4gw/
    win32/
        win32.py      Win32 class: process listing and Gw.exe discovery
    memory/
        memory.py     read-only process-memory transport
    scanner/
        scanner.py    offline pattern matching
        remote.py     PE section and remote scanning
        patterns.py   offsets and resolver chains
```

This is not authorization to copy MemLib wholesale. Reimplement the small
required surface against documented Windows behavior. If a later change
deliberately borrows actual MemLib source, preserve its MIT license notice and
record exact file-level provenance in the project documentation.

The read surface described above is pure external and read-only. Target-side work
started with the WorldMap callback payload, and that plan was superseded: the same
pointer is reached read-only through the frame array. What was built instead is the
game-thread layer in `py4gw/game_thread/`, live-verified. See
[`CALLBACK_POINTER_RESEARCH.md`](CALLBACK_POINTER_RESEARCH.md) and
[`NATIVE_EXECUTION_PLAN.md`](NATIVE_EXECUTION_PLAN.md).

## Native scanner migration plan

The current `Py4GW_Reforged_Native` scanner is useful comparative design
material, but it is not one class with one responsibility. It has two layers:

1. `Scanner`/`FileScanner` provide section discovery, masked byte-pattern
   searches, range searches, address/string-use searches, near-call and
   function-start helpers, and section pointer validation.
2. `Patterns` loads pattern definitions and resolver chains, then combines scan,
   dereference, integer-read, arithmetic, section-validation, and fallback
   steps while preserving a resolution trace and failure policy.

The native implementation runs inside the target module. It can inspect mapped
module bytes directly and also map the module file from disk. Stealth runs
outside `Gw.exe`, so the Python version must replace those assumptions with
read-only `ReadProcessMemory` calls against a selected PID, explicit module
and section ranges, fixed-width x86 fields, and bounded reads. This is a
behavioral migration, not a line-by-line translation.

`ReadProcessMemory` does not introduce another signature set. It is only the
external transport used to obtain bytes from `Gw.exe`. The pattern bytes,
masks, offsets, section names, and resolver descriptions remain the same data
used by Reforged Native. The current Stealth repository now contains a copied
`offsets/` directory; future updates can be copied from Reforged into that
directory without maintaining a second Python translation of the signatures.
The Python loader must consume this JSON schema directly and every scan should
record the offsets source revision/build it used.

The offsets locate addresses and describe resolution steps; they do not by
themselves describe the fields of every object at those addresses. Those
layouts already exist as maintained context definitions in Reforged Native's
`GW::Context` headers and Reforged's Python `ctypes.Structure` declarations.
Stealth's structure reader should reuse or deliberately port those definitions
instead of inventing a competing model. The injected Python version can cast a
pointer and access `.contents` because it runs in the game process; the
external version must read the target bytes first and decode them, while
treating embedded pointers as target addresses that require explicit follow-up
reads.

The migration is intentionally staged:

1. **Parity inventory.** Record the native public operations and their exact
   success/failure behavior. Keep scanner mechanics separate from Guild Wars
   signatures and meanings.
2. **Offline pattern engine.** Implement typed byte patterns and masks, input
   validation, first/all/nth match behavior, offsets, and deterministic tests
   over ordinary byte buffers. No process access is involved.
3. **External memory reader.** Extend the existing Win32 boundary with a
   selected-process, read-only handle and bounded reads that preserve Windows
   error context. Add explicit close/context-manager ownership.
4. **Remote module sections.** Read and validate the target PE headers, expose
   `.text`, `.rdata`, and `.data` ranges, and reject invalid or unreadable
   ranges before scanning.
5. **Remote scanner.** Scan section/range data in chunks with overlap so a
   pattern crossing a chunk boundary is found. Return structured match and
   diagnostic results rather than a bare zero address.
6. **Scanner helpers.** Add the reusable native-style helpers one at a time:
   address uses, string uses, near-call resolution, function-start search, and
   section pointer validation. Each helper gets offline tests before any live
   process test.
7. **Pattern definitions and resolvers.** Only after the scanner core is
   stable, add a Python representation for pattern records and resolver chains,
   including fallback attempts, step traces, and continue/halt policies.
8. **Guild Wars consumers.** Add target-specific adapters, beginning with the
   maintained context readers. These adapters own signatures, pointer offsets,
   decoding, and semantic validation; the reusable scanner remains target
   agnostic.

Steps 1 through 8 now have project-owned implementations and focused tests.
The first Guild Wars-specific consumers are the externally read
`CharContext`, `GameContext`, `PreGameContext`, `Cinematic`,
`GameplayContext`, `ServerRegion`, and `InstanceInfo`, in that migration
order. All seven have been validated against one live client build.
Additional contexts remain separate future consumers and must be validated
independently.

## CharContext implementation and resolution

Status: source-verified and verified against one live client build.

The maintained Reforged definitions agree on the relevant layout:

- `CharContext` is `0x448` bytes;
- `CharContext.player_name` is an inline UTF-16/wchar field at offset `0x74`,
  with 20 code units;
- `GameContext.character` is a 32-bit target pointer at offset `0x44`.

The native context code obtains `GameContext` through the resolved
`context.base_ptr`: dereference that global to a base-context table, read the
entry at table offset `0x18` (index `6`), then read `GameContext + 0x44` to get
the `CharContext` address. Stealth uses the same target addresses with
explicit `ReadProcessMemory` calls; it does not cast remote pointers locally.

The copied `offsets/context.json` provides the `context.base_ptr` resolver.
`GameContext.initialize()` executes that resolver once and caches the
module-global pointer location for the lifetime of the connection.
`CharContext` reuses that initialized reader and follows the dynamic
character pointer for each read because the base, game, and character context
objects may change during client state transitions.

## GameContext implementation and resolution

Status: source-verified and verified against one live client build.

The external `GameContextStruct` follows the native and Reforged layout:

- it is `0x5C` bytes;
- `agent_context` is at `0x08`;
- `map_context` is at `0x14`;
- `char_context` is at `0x44`;
- `party_context` is at `0x4C`; and
- `trade_context` is at `0x58`.

All pointer fields are represented as fixed-width 32-bit target addresses.
The reader resolves `context.base_ptr` from the copied JSON definitions,
reads the base-context table, selects its `+0x18` entry, and decodes the
resulting `GameContext` bytes. The resolver location is cached for the
connection, while the base table and current context pointer are re-read for
each snapshot.

An earlier live test observed `GameContext` at `0x024D9018`. The latest focused
run on 2026-09-22 observed `GameContext` at `0x00A94398`, with
`char_context=0x00ADDD98` and `world_context=0x00AD3A40`. These are read-only
observations for individual client runs, not cross-build guarantees.

## PreGameContext implementation and resolution

Status: source-verified and verified against one live client build.

The external `PreGameContextStruct` is `0x100` bytes and the nested
`LoginCharacter` record is `0x78` bytes, matching the native and Reforged
definitions. Its `chars_array` is read as a contiguous value array through the
existing external `GWBaseArray`/`GWArrayValueView` boundary. Pointer fields are
fixed-width target addresses, including the login-character item buffer and
model pointer.

The native context initializer resolves `context.pregame_context_addr` as a
stable global-pointer location. The external reader caches that location and
re-reads the pointed-to value for each snapshot. The pointed-to context is
allowed to be null: that is the expected state while the client is outside the
selection menus, so `read()` returns `None` rather than treating it as a
resolver failure.

An earlier live test resolved the global pointer at `0x015EA2EC`. The latest
focused run on 2026-09-22 resolved it at `0x017CA2EC`. During that run the
pointed-to value was null because the client was already in-game; the reader
reported the inactive pre-game state correctly.

## Cinematic implementation and resolution

Status: source-verified and verified against one live client build.

The native `Cinematic` record is an `0x08`-byte pair of fixed-width `uint32`
fields (`h0000` and `h0004`). It is owned by `GameContext` at offset `0x30`.
The external reader reuses the connection's initialized `GameContext` resolver,
reads that pointer for each snapshot, and returns `None` when the pointer is
null. This keeps the context optional while preserving the native pointer
relationship; it does not add a second signature scan.

An earlier live test resolved `Cinematic` at `0x025065D8`. The latest focused
run on 2026-09-22 resolved it at `0x00ABF730` and read both fields as
`0x00000000`. The address and values are observations for one client build,
not cross-build guarantees.

## GameplayContext implementation and resolution

Status: source-verified and verified against one live client build.

The native and Reforged definitions agree on a fixed `0x78`-byte structure:

- `h0000` contains 19 `uint32` values;
- `mission_map_zoom` is a `float` at offset `0x4C`; and
- `unk` contains 10 trailing `uint32` values.

The native context layer resolves `context.gameplay_context_addr` as a stable
global-pointer location. The external reader caches that resolver during
connection, re-reads the pointed-to gameplay context for each snapshot, and
returns `None` when the target pointer is null. It uses the copied JSON
resolver and does not add a second signature definition.

An earlier live test resolved the global pointer at `0x015EAAB8` and the
`GameplayContext` at `0x02421248`, with `mission_map_zoom` equal to `1.500`.
The latest focused run on 2026-09-22 resolved the global pointer at
`0x017CAAB8`, the current context at `0x0A211370`, and read
`mission_map_zoom` as `1.000`. These addresses and values are observations for
one client build, not cross-build guarantees.

## ServerRegion implementation and resolution

Status: source-verified and verified against one live client build.

The native and Reforged definitions agree that `ServerRegion` is a single
signed 32-bit value, not a pointer to a larger context structure. Reforged's
`ServerRegionStruct` contains one `c_int32 region_id` field, and the native
enum uses `-2` for International, `0` for America, then the named regional
values, with `0xff` reserved for Unknown.

The native resolver stores the address of that value in
`Context::g_region_id_addr`. Its JSON-backed resolver is
`map.region_id_addr`: it scans the `region_id_ref` pattern and applies the
native dereference step. Stealth therefore resolves that address once during
connection, caches the resolver result, and reads four bytes for each
snapshot. It does not introduce a hard-coded field offset or scan the pattern
again for every read.

The focused test is `tests/test_server_region_context.py`. It checks the
fixed-width layout, resolver address, and signed value when a client is
running. The recorded run resolved the value at `0x017C63A8` and read region
ID `0` (America). These are observations for one client build, not
cross-build guarantees.

## InstanceInfo implementation and resolution

Status: source-verified and verified against one live client build.

The native and Reforged definitions agree on these fixed-width layouts:

- `MapDimensionsStruct` is `0x18` bytes;
- `AreaInfoStruct` is `0x7C` bytes; and
- `InstanceInfoStruct` is `0x14` bytes, with target pointers at offsets
  `0x00`, `0x08`, and `0x10`.

The native map resolver exposes `map.instance_info_addr`, which resolves the
current `InstanceInfo` structure address from the copied `instance_info_ref`
signature. Stealth caches that resolved address during connection and reads
the root structure on demand. Its nested `terrain_info1`, `current_map_info`,
and `terrain_info2` properties follow their target-process pointers through
`ReadProcessMemory`; they never dereference those addresses as local Python
pointers. The `AreaInfoStruct` flag and file-ID properties are ported from the
Reforged source.

An earlier live test resolved `InstanceInfo` at `0x01C4A150`, read instance
type `0`, and observed campaign `1`, region `0`, and file ID `0`. The latest
focused run on 2026-09-22 resolved the same address and read instance type
`0`, campaign `3`, region `15`, and file ID `0`. These values and addresses are
observations for one client build.

## TextParser implementation and resolution

Status: source-verified and verified against one live client build.

The native `TextParser` pointer is a field of the already-resolved
`GameContext`, at offset `+0x18`. Stealth follows that field for each read; it
does not add a second signature scan or invent a global pointer resolver. The
native root layout is `0x1D4` bytes, with the `TextCache*` field at `+0x30`,
the auxiliary structure pointer at `+0x180`, and `language_id` at `+0x1D0`.
Those pointer fields are followed through the external memory reader when the
corresponding properties are requested.

An earlier live test read `TextParser` at `0x0257E9E0` and observed language
ID `0`. The latest focused run on 2026-09-22 read `TextParser` at
`0x07453C38` and observed language ID `0`. These addresses and values are
observations for one client build.

## AvailableCharacterArray implementation and resolution

Status: source-verified and verified against one live client build.

The native account roster is a global `GWArray<AvailableCharacterInfo>`
resolved by `player.available_characters_addr`. It is distinct from the
`PreGameContext::chars_buffer` preview array. Stealth caches the resolved
`GWArray` address, rereads its header for each snapshot, and follows the array
buffer through the external memory reader. Each entry is `0x84` bytes and
includes the fixed UTF-16 name plus packed map, profession, campaign, level,
and PvP properties.

The latest focused run on 2026-09-22 resolved the roster array at
`0x017AF28C`, read 14 entries, and observed `Fezzik The Untamed` as the first
entry (level 20, map 449). These values and the address are observations for
one client build.

## PartyContext implementation and resolution

Status: source-verified and verified against one live client build.

The native party accessor follows `GameContext.party`; no separate signature
or callback is required. The root structure is `0xD0` bytes and contains
remote `GWArray` headers for parties and searches plus intrusive request and
sending lists. Stealth reads those arrays and traverses `GwList` links with
fixed-width x86 addresses and a bounded loop guard.

The live test resolved `PartyContext` at `0x00A07388`, observed one party,
68 party-search entries, and a party-leader state. These values and the address
are observations for one client build. The focused parity tests also verify all
source field offsets, fixed sizes, flag/text properties, record aliases, and
the declared facade cache. Callback registration is not ported: the source
registers an in-process callback, and nothing consumes Stealth's own callback
layer yet.

At the time of this observation, `WorldMapContext` had not yet been ported.
Its source-matched structure and supplied-address reader have since been added
and offline-checked, and its root is now live-verified through the client's UI
frame array rather than the source's injected UI callback, so no guessed pattern
was added.

## Live Observation: Gw.exe Discovery

Status: verified from a user-provided run of the current package.

The same read-only command was run with the Guild Wars client open and closed:

```text
python -c "from py4gw import Win32; win32=Win32(); print(win32.format_processes(win32.find_guild_wars()))"
```

With the client open, the observed result was:

```text
PID   | Name   | Path
39212 | Gw.exe | F:\GW\GW1\Gw.exe
```

With the client closed, the observed result was:

```text
No Gw.exe candidates are currently running.
```

This verifies the current filename-based process discovery behavior across
those two states. The Guild Wars build/version and exact observation timestamp
were not recorded in the report. The operation was read-only and performed no
cleanup or target modification.

## Live Observation: Remote scanner initialization

Status: verified from a user-provided read-only run against a live `Gw.exe`.

The external scanner opened PID `47852`, identified the main module as
`F:\GW\GW1\Gw.exe`, and successfully parsed these sections:

```text
.text  14553088 - 20026880
.rdata 20029440 - 22866432
.data  22867968 - 28505400
.rsrc  28508160 - 30277632
.reloc 30277632 - 30573056
```

The reported module base was `14548992` and its image size was `16027648`.
This verifies process opening, main-module discovery, PE parsing, and section
range initialization against that live client. The later CharContext
observation records the separate verification of a copied Guild Wars resolver
and its target pointer chain.

## Live Observation: Remote byte scan

Status: verified from a user-provided read-only run against the same live
client.

The scanner read 16 bytes at the beginning of `.text`, built a pattern from
the first four bytes, and searched the remote `.text` range. The observed
addresses were:

```text
text start:  0x00DE1000
scan result: 0x00DE1000
```

This verifies the complete read-and-search path against live Guild Wars
memory. It is a transport and scanner check only; it does not validate a
Guild Wars-specific signature or resolver definition.

## Live Observation: CharContext resolver and name read

Status: verified from a user-provided read-only run against the same live
client.

The `context.base_ptr` resolver succeeded with this trace:

```text
scan_ref       0x00E6CE4B
deref_ptr      0x015E6170
validate_ptr   success in .data
```

Following the documented target layout produced:

```text
base_context   0x0251C348
game_context   0x024D9018
char_context   0x0251DA70
player_name    non-empty UTF-16 name decoded successfully
```

The name was read from `CharContext + 0x74` as a fixed 20-code-unit
UTF-16LE field. The latest focused run on 2026-09-22 observed
`CharContext=0x00ADDD98`, decoded `Fezzik The Untamed`, and read
`GW_Array.h0014=0` with `observer_matches=0`. This verifies the initial
target-specific read path: a copied resolver, explicit 32-bit pointer reads,
and a structure field decode. The same path is now exposed by
`py4gw.context.CharContext`; the observation does not prove that the same
offsets work across other client builds.

The context port also includes the Reforged `GW_Array` header and its two
array-view behaviors. `GWArrayValueView` reads contiguous values from a
remote buffer, while `GWArrayView` reads target pointers and then the remote
structures they reference. This is an external adaptation of the Reforged
behavior: those pointers are never dereferenced as local Python pointers.

## Live Observation: Context performance breakdown

Status: verified by `tests/perf_context.py` against the same running client;
the Guild Wars build and host load were not recorded.

Before resolver caching, one five-sample run measured the following
approximate averages:

```text
resolver.pattern_scan       4.664 ms, 9 reads, 589,878 bytes
resolver.pointer_chain      0.030 ms, 4 reads, 16 bytes
context.read                4.739 ms, 14 reads, 590,990 bytes
context.read.cached_address 0.009 ms, 1 read, 1,096 bytes
```

This separates the repeated `.text` signature scan from structure decoding:
the scan dominates `CharContext.read`, while decoding a structure at an
already-resolved address is negligible. The UI's derived array views are a
separate cost; in this run `h00EC_ptrs` performed 520 remote reads and took
about 2.7 ms. These numbers are one live observation, not a cross-build or
cross-machine benchmark.

The resolver is now initialized during `ConnectedClient` construction and its
stable module-global pointer location is cached. A follow-up five-sample run
measured approximately `0.012 ms` for cached address resolution and
`0.026 ms` for `context.read`, with four remote reads for the dynamic pointer
chain plus the 0x448-byte structure. The one-time connection initialization
still took approximately `3.766 ms`, which is the intended location for the
signature scan cost.

This cache boundary matches Reforged Native. `GW::Context::Initialize()`
resolves `context.base_ptr` once and is guarded by `g_initialized`. Its
`GetGameContext()` then re-reads the pointer stored at `g_base_ptr` and selects
the game-context slot at `+0x18`; `GetCharContext()` re-reads the character
pointer at `GameContext + 0x44`. Therefore the external reader caches the
resolver's stable pointer location but does not cache the dynamic context
object addresses.

## Live Observation: GuildContext

Status: verified against the same running client build with
`tests/test_guild_context.py`.

`GuildContext` is reached directly from the current `GameContext` at the
maintained `guild_context` field. No new signature scan or callback bridge is
needed. The reader follows that pointer, reads the complete maintained
0x368-byte field surface, and follows its remote `GW_Array` members through
the external memory reader. The native header contains an older `0x3BC` size
comment, but its explicit field offsets end at the 0x368-byte roster array;
the Python layout follows those concrete offsets.

The live test resolved `GuildContext` at `0x00AD42A0` and observed player
`Fezzik The Untamed`, 243 guild records, 42 roster entries, and 20 history
entries. Offline parity tests also cover the source aliases, `GHKey.from_hex`,
the native `GHKey.k` view, and empty-array `None` semantics. These values are
one observation and are not assumed stable across client builds or account
state.

## Live Observation: AccAgentContext

Status: verified against the same running client build with
`tests/test_acc_agent_context.py`.

The Reforged Python module calls this surface `AccAgentContext`; the native
project defines the same root as `GW::Context::AgentContext`. It is reached
directly through `GameContext.agent` at `+0x08`. The external reader follows
that pointer and reads the maintained 0x1B0-byte root, including summary,
pointer, and movement arrays. Nested pointers are read through the external
memory reader and are never treated as local Python pointers. The Reforged
array properties return empty lists for ordinary empty arrays, while the
movement property returns `None` when its header is empty; Stealth preserves
those results. Native field spellings are exposed as aliases beside the
Reforged `*_array` fields.

The native header also declares `AgentInfo` and `AgentInfoArray`. The structure
is represented in Stealth, but it is not a field in `AgentContext` and the
inspected native context methods expose no getter for its array. Its runtime
pointer source is therefore unresolved; no relationship to a nearby field has
been inferred.

The live test resolved `AgentContext` at `0x07453460` and observed 2,002
summary entries, 2,002 movement entries, 104 non-null movement IDs, and
instance timer `1805937958`. These values are one observation and are not
assumed stable across client builds or account state.

## Live Observation: Camera

Status: verified against the same running client build with
`tests/test_camera.py`.

The native camera pointer is resolved by `camera.camera_ptr`, which follows
the assertion anchor, finds the nearby pointer reference, dereferences it,
and validates the resulting object in the module data section. Unlike the
context-base resolvers, this resolver returns the camera object address
itself. Stealth therefore caches that address for the connection and reads
the maintained `0x120` bytes on each snapshot.

The live test resolved Camera at `0x017CAC10` and observed look-at agent
`605`, yaw `-1.702`, pitch `0.421`, and distance `900.0`. These values are one
observation and are not assumed stable across client builds or camera state.

## Live Observation: FriendList

Status: verified against the same running client build with
`tests/test_friend_list.py`.

The native friend list is a standalone `FriendList` object resolved by
`friend_list.friend_list_addr`; it is not published through the Reforged
shared-memory pointer snapshot. Stealth reads the fixed `0xA4` root, validates
the `GWArray` header, and bounds friend-pointer traversal at 512 records. Each
friend record is decoded as the native `0x70` x86 layout, including UTF-16
alias and character-name fields.

The live test resolved FriendList at `0x01C4AE78` and observed 59 friend-array
entries, zero ignores, and player status `online`. These values are one
observation and are not assumed stable across client builds or account state.

## Live Observation: ChatBuffer

Status: verified against the same running client build with
`tests/test_chat_buffer.py`.

The native chat accessor exposes a pointer slot (`ChatBuffer**`), not a direct
object address. Stealth caches the slot resolved by `chat.chat_buffer_addr`,
re-reads the current buffer pointer for each snapshot, and reads the fixed
`0x80C` root containing 512 message pointers. Each non-null message header is
the fixed `0x10` prefix; its UTF-16 payload is decoded only when requested and
is bounded to 512 characters. The typing state is read from the separate
`chat.is_typing_frame_id` slot.

The live test observed buffer address `0x26FA73D8`, all 512 ring slots
populated, next index `268`, and typing state `False`. These values are one
observation and are not assumed stable across client builds or chat activity.

The remaining parity gap is the decoded-history helper. Reforged's
`Player.GetChatHistory()` queues native `AsyncDecodeStr` work on the Guild
Wars game thread and returns injected-runtime state; it is not equivalent to
reading the ring bytes. A read-only probe against the same running client
could open `Gw.dat` only for metadata: requesting `GENERIC_READ` failed with
Windows sharing-violation error 32. This is why the Reforged `PyDatReader`
is not yet reusable by Stealth while the client is running. The raw
encoded messages remain available; decoded-history parity is not yet ported —
it needs the decode queued on the client's own game thread, which is the next
piece of work for this module. A follow-up attempt
to duplicate the client's existing file handle remained read-only but could
not obtain `PROCESS_DUP_HANDLE` access (Windows error 5), so that route is not
currently a verified capability either.

The checked-out GwAu3 source confirms the same boundary rather than providing
an external decoder: `Utils_DecodeEncStringAsync` copies the encoded string
into a command buffer and queues an assembly payload that calls the client's
`ValidateAsyncDecodeStr` function. That is process injection/code execution,
not a pure external read. GwAu3 therefore supplies comparative evidence for
what the decoded result needs here: the same queued call into the client's own
function, which is the outstanding piece for decoded history.

## Live Observation: WorldContext root

Status: verified against the same running client build with
`tests/test_world_context.py`.

The native world pointer is already present in the maintained `GameContext`
layout at `GameContext + 0x2C`; no second signature scan is needed. Stealth
reads the complete fixed `0x854`-byte root and exposes its scalar progression
fields, party-flag coordinates, and `GWArray` headers. Child arrays are read in
full from their advertised size after validating the buffer, capacity, x86
address extent, and a 16 MiB per-array byte ceiling. Requests above that ceiling
fail explicitly rather than returning a truncated prefix.

The live test resolved `WorldContext` at `0x02572A78` and observed player
number `37`, level `20`, experience `12511518`, and `101` player records in
the advertised array header. The same live read observed one party-attribute
block with 11 populated attributes and one party-effects block with one active
effect and no buffs. These values are one observation and are not assumed
stable across client builds or account state.

Party attributes use the native `0x43C` inline record with 54 attributes.
Party effects use the native `0x24` record and follow its complete buff/effect
arrays only when requested. The root read itself does not materialize those
child arrays.

Player records use the native `0x50` layout and NPC model records use the
native `0x30` layout. Names and NPC model-file lists are indirect reads and are
only followed when requested, not during the root read. On 2026-09-22, live
array sizes and materialized counts matched for every implemented source
array accessor checked: 2,009 map agents, 9,271 NPC models, 101 players,
2,009 agent-name records, and 369 title tiers, among the other arrays. The
native root declares `vanquished_areas_array`, but Reforged Python's
`vanquished_areas` property currently returns `None` unconditionally; Stealth
preserves this source behavior rather than reading that array through the
property. Indirect UTF-16 strings are read
through their terminator up to the external reader's 32,768-character ceiling;
an over-limit or unterminated value fails instead of returning a clipped string.

Hero flags use the native `0x24` record, hero information uses `0x78`, and
pet records use `0x1C`. Their complete advertised arrays are returned. The
live observation contained 23 hero-information records and no active hero
flags or pet records.

## Live Observation: MapContext root

Status: verified against the same running client build with
`tests/test_map_context.py`.

`MapContext` is reached through the maintained `GameContext.map_context` field
at `GameContext + 0x14`; it does not require a second root signature scan.
Stealth reads the fixed `0x138` Reforged root and follows the three native
spawn arrays only through bounded lazy reads. The live test resolved
`MapContext` at `0x267A47C8`, observed map ID `449`, map type `0`, spawn counts
of `7`, `22`, and `16`, and a non-null path pointer at `0x273553C8`. The live
read then found `PathContext` at `0x273553C8`, its static-data root at
`0x271BBBC0`, and all 39 `PathingMap` records.

The native header names the first five words as `map_boundaries`, while the
Reforged Python structure uses the same bytes for `map_type`, `start_pos`, and
`end_pos`. Both views are exposed so this source difference is explicit.
Pathing child arrays and the reachable props records are read externally;
terrain and zones remain raw pointers. Source pathing snapshots, facade
helpers, and PID-scoped map-ID caches are implemented. Automatic in-client
callback registration is not yet ported; it next needs a callback kind for the map
hooks. See
[`PATHING_MIGRATION_PLAN.md`](PATHING_MIGRATION_PLAN.md).

On 2026-09-22, the live read found 1,270 trapezoids, 1,270 sink nodes, 4,271 X
nodes, 1,980 Y nodes, 164 portals, and 27 blocking props. `PropsContext`
contained 16 groups with 23 `PropByType` records, 1 model, and 516 map props.
Trapezoid, X/Y-node, and portal links were readable. The raw live check found
all 1,270 SinkNode field values pointing to aligned records in their owning
map's trapezoid arrays. This observation conflicts with the pointer-to-pointer,
null-terminated list in Reforged runtime `.py` and native C++; the Reforged
`.pyi` types those fields as single pointers instead. Stealth ports the runtime
Python/native pointer-list behavior and tests it offline. A live check also
confirmed that interpreting the observed field as the source pointer-to-pointer
produces a small trapezoid ID, which the bounded reader rejects as an implausible
address; source-shaped behavior is therefore incompatible with this client
build. Subsequent source-usage review found the Reforged snapshot explicitly
leaves `sink_nodes` empty and found no active consumer of the SinkNode helper
properties in the searched source tree. Treat this as an unused helper/live
layout discrepancy, not as a blocker for active MapContext data reading. The source
snapshot pass materialized 1,270 trapezoids and 164 portals and resolved all
164 portal pair indices; the travel-portal helper returned 7 entries.

Skillbar slots use the native `0x14` slot and `0xBC` skillbar layouts. The
root's learnable, unlocked, and duplicate-skill arrays are returned in full.
The live observation contained one skillbar, 108 unlocked values, one
duplicate-skill record, and no learnable values.

Quest and mission-objective records use the native `0x34` and `0x0C` layouts.
Title and title-tier records use the native `0x2C` and `0x0C` layouts. Their
arrays are returned in full and indirect text is read only when requested.
The live observation contained 23 quests, 47 titles, and 369 title tiers; no
mission objectives were present.

`TradeContext` uses the direct `GameContext.trade_context` pointer and the
native `0x38` root, `0x14` side, and `0x08` item layouts. The live client had
an allocated trade root with zero offered items on both sides. Its four native
state constants and three flag helpers are represented. Offer reads now cover
the complete advertised `GWArray` instead of silently stopping at 64; requests
above 16 MiB fail explicitly. Stealth only reads state; it does not initiate,
offer, accept, or cancel trades.

`ItemContext` uses the direct `GameContext.item_context` pointer and the
native fixed `0x10C` root. The live client exposed 22 bag entries and a raw
`item_array.m_size` of 26,354 in one observation. That header value is not
treated as an inventory-item count: Reforged's public `ItemArray` path walks
selected bags through `PyInventory.Bag.GetItems()`. Stealth now follows the
native `ItemContext` bag array, each `Bag.items` array, and bounded `Item`
records; the global array is not required for that path. One live read
traversed 22 bags and 340 item records.

The native `Item` layout also contains `mod_struct` at `+0x10` and
`mod_struct_size` at `+0x14`. These are an indirect array of `ItemModifier`
records, each a `0x4`-byte raw modifier word. Stealth now reads those words
lazily with a 64-entry safety bound and exposes the native identifier/argument
bit rules plus the native uses, tome/kit, and rare-material helpers. A separate
semantic layer may later adopt the Reforged `mods_types.py`/`mods_core.py`
effect catalog; that catalog is not needed to read the native context itself.

## AgentArray traversal and materialization

### Verified in Py4GW Reforged Native

The native agent array is a `GWArray<Agent*>` resolved through the
`agent.agent_array_addr` signature. `Context::GetAgentArray()` returns that
array when its header is valid. `GetAgentByID()` performs the bounds and
non-null pointer checks, then applies the stale-agent gate:

```text
agent_movement.size() > agent_id
and agent_movement[agent_id] != nullptr
```

The native code then uses the existing in-process `Agent*`. It does not copy a
full `Agent` structure for each traversal.

The native shared-memory updater does traverse the populated array each frame.
For every valid pointer it reads the common `Agent` fields needed for
classification: type flags at `Agent + 0x9C`, and, for living agents,
allegiance at `AgentLiving + 0x1B5` and the related living flags. It publishes
only the agent pointer, agent ID, and categorized ID/index references. The
shared-memory cap is 300 entries.

The updater also refuses to publish an array while the map is not ready, while
the client is observing, or during loading. This is a state-validity gate in
addition to the pointer and movement-array checks.

### Verified in Reforged Python

The public `AgentArray.Get*Array()` methods first consume the native shared
memory wrapper. They return IDs from the already-classified arrays: enemy,
ally, neutral, living, item, gadget, and so on. This path does not
materialize a full ctypes agent for every entry.

`AgentArray.GetAgentByID()` materializes one requested `AgentStruct` from the
published pointer. Filters and sorts then operate on IDs and call methods such
as `Agent.GetAllegiance`, `Agent.IsAlive`, and `Agent.GetXY`; those calls
materialize or access the selected agent as needed.

The direct `AgentArrayStruct.raw_agents` path can materialize every pointer and
classify the entire array in Python, but its recurring cache-update callback is
disabled in the inspected source. It is therefore not the normal public
agent-array path.

### Consequence for Stealth

The agent array is populated, and allegiance is a required classification
field. A Stealth traversal that must produce enemy/ally/living categories must
read enough of every valid candidate to inspect at least the common type and,
for living records, the allegiance field. That work cannot be eliminated.

It can still avoid full object materialization. The proposed external design
is:

1. Read the bounded pointer table once and capture `(agent_id, address)`
   references.
2. Apply the movement-array stale-agent check.
3. Read a small classification projection containing the common type, item
   owner, living allegiance, and living effects needed for category views.
4. Build ID/reference lists for all, ally, enemy, dead ally, dead enemy,
   owned item, living, item, gadget, and other categories.
5. Materialize the complete `Agent`, `AgentLiving`, `AgentItem`, or
   `AgentGadget` structure only for callers that request detailed data.

This preserves the native/Reforged separation: classification traverses the
populated array, while detailed structures remain on demand. The cost should
be measured as remote-read calls, bytes transferred, and Python object count;
the number of agents alone is not enough to identify the bottleneck.

### Verified Stealth first milestone

`py4gw.context.agent_array.AgentArray` now resolves the JSON
`agent.agent_array_addr` result once per connection, bulk-reads the pointer
table, reads only each candidate's `agent_id` at `Agent + 0x2C`, and applies
the movement-pointer validity gate. It returns lightweight references and does
not materialize complete agent structures during ordinary refreshes.

The live test observed a table of 2,217 entries with capacity 2,304 and
58–70 accepted current references across recent samples. The table was scanned without
reaching the 4,096-slot safety limit or the 300-reference output limit. Basic
living, item, gadget, and allegiance categories are now available. A selected
reference can also be read as a complete common, living, item, or gadget
record. Before that complete read, Stealth now rechecks the reference's
current pointer-table slot and movement entry, then verifies the record ID
again after reading it. This narrows, but does not eliminate, the race window
between remote reads. The complete living record now exposes the native effect
bit properties and bounded visible-effect list, and optional equipment/tag
records are readable through their target pointers. The reference snapshot
also publishes owned-item, dead-ally, and dead-enemy categories.

The live AgentArray check now records the resolver and steady-state stages
with `PerfCounter`. One observed client reported about 130.9 ms for the
one-time AgentArray resolver scan and about 2.1 ms for the full bounded
refresh: 0.45 ms for the pointer table, 0.40 ms for the movement table, and
1.19 ms for classification. Reading one selected complete record took about
0.045 ms for the final validity check and 0.032 ms for the record read. The
resolver remains a one-time connection operation and is not repeated during
refreshes. Offline checks separately cover impossible
headers, null buffers, truncation, and fixed-width x86 pointer decoding.

Stealth now also provides an explicit complete living-agent refresh. It reads
the full native `0x1C4` `AgentLivingStruct` for each current living reference,
retains the effects bitmap and all other fields, and serves repeated queries
from one local snapshot until the caller refreshes it. A live sample captured
56 living records in about 3.7 ms, with zero stale or unreadable records. This
is a refresh boundary, not an atomic target snapshot; each record is still
validated as it is read.

A ten-refresh harness run later measured 58 living records at an average of
4.05 ms per complete refresh (p95 4.53 ms), with average AgentArray reference
refreshes at 1.80 ms. Nested reads remained small and bounded: visible effects
averaged 0.005 ms, equipment 0.011 ms, and tags 0.006 ms for the selected
record. The one-time resolver scan was 128.0 ms in that run.

### Latest AgentContext/AgentArray parity check

On 2026-09-22, `tests/test_agent_array.py` passed against PID 29520
(`F:\GW\GW1\Gw.exe`, file version 1.0.0.1). The latest sample reported an
array size of 1,945 with capacity 2,048; 104 references passed the current-agent
gate, with zero stale, unreadable, or truncated entries. The type projection
classified 101 living agents and 3 gadgets. A complete living refresh captured
101 records with zero stale or unreadable records. The measured refresh took
6.651 ms, including 0.781 ms for the pointer table, 0.433 ms for the movement
table, and 3.481 ms for classification. The source-shaped context cache build
took 6.644 ms; resolver initialization took 136.156 ms once. These values
describe one client state, not a stable count or performance guarantee.

This live read does not certify full source/API parity. The record structs,
value dataclasses, and snapshot conversions have since been ported and checked
against Reforged Python and native C++ layouts. Offline tests assert the native
record sizes and key offsets. Two source differences are kept explicit:
Reforged Python's packed `ItemDataStruct` is 0x13 bytes with a 32-bit `type`,
while native `ItemData` is 0x10 bytes with a 1-byte type. This expands the
Python equipment union/record to 0xAB/0xF3, compared with the native
0x90/0xD8. Separate `Reforged*` structure views preserve those Python layouts;
live reads use native layouts. Reforged Python's packed living record is
0x1C2 bytes while native `AgentLiving` is 0x1C4. The `.pyi` snapshot return
annotations disagree with some runtime implementations; behavior follows the
`.py` source. Full AgentArray parity
remains incomplete: `AgentArrayStruct` cache helpers now check the matching
external context readers and materialize accepted records through remote reads.
Reforged's `SystemShaMemMgr` lookup fallback is not ported; the process-wide
callback facade is not yet ported (next: a callback kind per hooked function),
and the wider `Agent.py` helper surface
is unaudited. The external
facade uses per-client ownership; `enable()` reports that the callback
runtime is not yet ported. The native `AgentContext` root itself is the same
`GameContext.agent` root documented under AccAgentContext; the array pointer is
a separate global resolver. See the certification record for remaining gaps.

## Account and gadget roots

The native `GameContext` contains direct pointers for both `AccountContext`
(`+0x28`) and `GadgetContext` (`+0x38`). Stealth now follows those existing
parent pointers; no new signature or callback source is needed.

`AccountContext` is read as its fixed `0x138`-byte x86 root and reports the
six maintained `GWArray` headers without traversing account-wide unlock data.
`GadgetContext` is read as its fixed `0x10`-byte root. Its default
`GadgetInfo` reader materializes the entire advertised value array in one
contiguous external read. A smaller sample can be requested explicitly; an
unbounded full read above the 16 MiB safety ceiling fails instead of silently
returning a prefix. The latest live check (2026-09-22) resolved gadget root
`0x00AC41D8` and read all 9,500 advertised entries. That address and count are
observations for the running client, not constants.

This completes the remaining small direct-pointer root readers identified in
the current inventory at their implemented read boundary. It does not claim
source parity for every nested helper: the field and API gaps are recorded in
`docs/CONTEXT_PARITY_AUDIT.md`. Item child records now have a live-verified
bag-based access path; render, salvage, and callback-owned map contexts are not yet
ported onto an external object-pointer source.

## Live JSON resolver sweep — 2026-09-22

**Target:** PID `29520`, `F:\GW\GW1\Gw.exe`; one Guild Wars process was
detected. Windows file metadata reports file/product version `1.0.0.1`, which
does not provide a useful client-build identifier, so this result is tied to
the observed executable path and should not be generalized to other builds.

**Input and expected result:** Stealth's complete `offsets/` catalog; execute
each loaded named resolver once using the read-only process reader and PE
scanner. Each resolver should return a successful nonzero result.

**Observed:** all 29 JSON files in the Native offsets directory were present
in Stealth with identical contents; Stealth has one additional local file,
`agent_recolor.json`. The catalog loaded 219 patterns and 233 resolver chains.
All 233 returned successful results against this running client; none failed.
The sweep took about 9.0 seconds. The full suite also passed: 280 tests in
about 2.7 seconds, including the existing live context and pointer tests.
Both map UI callback-function resolvers returned addresses, but this does not
capture or validate the callback-published `MissionMapContext` or
`WorldMapContext` pointers.

**Safety and cleanup:** these checks only enumerated the process, read module
bytes and target memory, and resolved addresses; they did not invoke resolved
functions or write to the client. The process-memory reader was closed. This
verifies signature-chain resolution on one observed client, not the semantic
correctness of all 233 results or compatibility with every client build.

### WorldMap callback preflight — 2026-09-23

**Target:** the only running `Gw.exe` candidate at the time, PID `29520`,
`F:\GW\GW1\Gw.exe`. The user stated that this is the only client running;
re-enumerate and revalidate the PID and build immediately before any later
live test, since either may change after a restart. The executable's SHA-256 was
`44FBD68767A8D02B5DD4FB1A8A09B684A86B24716731327EE64905DD698FE124`;
file/product metadata reports `1.0.0.1`, not a useful game-build identifier.

**Read-only result:** `map.world_map_ui_callback_func` resolved to
`0x0110B5A0` inside `.text`; the signature match was at `0x0110B5C4`. The
first 16 bytes at the resolved address were
`55 8B EC 83 EC 54 8B 45 08 56 8B 48 08 8B 40 04`.

This confirms that the current JSON resolver succeeds and the address can be
read in this one process. No map interaction occurred, no callback was
observed executing, no instruction-boundary/hook-safety analysis was done,
and no bytes were written. PID and address must be rechecked after any restart.

### UI frame-array route to the map contexts — 2026-09-23

**Source finding; no live client was used for this entry.** The
`Py4GW_Reforged_Native` source was re-inventoried for this decision. Exactly
four pointers in the project are obtained only through a hook or callback:

| Pointer | Capture | Source |
| --- | --- | --- |
| `g_world_map_context` | `OnWorldMap_UICallback` | `src/GW/map/map.cpp:82-90` |
| `g_mission_map_context` | `OnMissionMap_UICallback` | `src/GW/map/map.cpp:95-103` |
| `g_salvage_context` | `OnSalvagePopup_UICallback` | `src/GW/item/item.cpp:211-225` |
| `g_dx_context` | `OnEndScene` / `OnReset` | `src/GW/render/render.cpp:75-111` |

Every other context pointer in the project comes from a pattern or pointer
chain that an external reader can replicate. The two map pointers are stored
only in the injected DLL's own globals (`src/GW/context/context.cpp:41-42`) and
are written only by those callbacks, so no game global holds them.
`ui.world_map_state_addr` is a visibility flag, not the pointer.

**Read-only route found.** `Gw.exe` does keep the owning UI frame, and the
frame keeps its registered context pointer. `include/GW/ui/ui.h:448` places
`frame_callbacks` at `Frame+0xA8`; entries are 12 bytes
(`{callback, uictl_context, h0008}`, `ui.h:321-325`);
`src/GW/ui/ui_methods.cpp:758-773` returns the last non-null `uictl_context` as
the frame's context. The map callbacks dereference `message->wParam`
(`map.cpp:85`), which is a `void**`, so the published context is one
dereference from the frame's own callback entry. `WorldMapContextStruct.frame_id`
is at `+0x0` and `MissionMapContextStruct.frame_id` at `+0x14`, giving an
independent cross-check, and the frame array itself is addressed by the
resolver Stealth already ships (`ui.frame_array_addr`, `offsets/ui.json:373`).

**Implementation result (offline only).** `py4gw/ui/` now holds the UI frame
primitives, the `FrameTree` walk, and the frame-id cross-check. Three contexts
acquire their root through it: `WorldMapContext` (frame-id offset `0x0`),
`MissionMapContext` (`0x14`), and `SalvageSessionInfo` (`0x4`, newly ported from
`include/GW/context/item.h:240-251`). `tests/test_ui_frame_offline.py` passes 42
synthetic-memory tests, including the four cross-check outcomes, each route end
to end, and three routes coexisting in one frame array. The whole offline suite
(29 files) passes, and `pyright` reports no new errors.

**Live read-only observations, PID 29520 (`F:\GW\GW1\Gw.exe`), 2026-09-23.**
The window was not open for any of the three surfaces, so this run measured
resolution and array structure, not the callback handoff:

- `ui.frame_array_addr` resolved to `0x017B896C`. The header there read as a
  valid `GWArray` with **5082 slots and capacity 5120**. This is the strongest
  single result: it confirms the resolver works on this build and that the
  global is an inline array header, which had been an interpretation.
- 521 of the 5082 slots hold a valid frame pointer; the remainder are null or
  the deleted sentinel.
- All three callbacks resolved inside `.text`: `WorldMapContext` `0x0110B5A0`
  (matching the earlier preflight), `MissionMapContext` `0x011084D0`,
  `SalvageSessionInfo` `0x014A4980`.
- `ui.world_map_state_addr` read `0x0000D511`, whose `0x80000` bit is clear,
  consistent with the world map being closed.
- No frame registered any of the three callbacks, which is the expected
  reading while the surfaces are closed.
- Measured walk cost on this client: about 45 ms per full callback search over
  521 frames before batching; the batched read path reduces the per-sample
  read count substantially.

**Live frame survey, PID 29520, 2026-09-23 (`tests/probe_live_frame_contexts.py`).**
This reads every live frame's callback entries with no window open. 548 frames
were valid and **547 registered at least one callback**, across 773 entries and
110 distinct callback addresses, all inside `.text`. Two measurements matter:

- `uictl_context` was **never** equal to its `h0008` neighbour (0 of the 540
  entries where both were non-null) and **never** equal to the frame's user
  param field. Both had been open alternatives for the slot `message->wParam`
  points at; live data eliminates them.
- Of 177 catalog `*_func` resolvers, **14 produced an address actually
  registered on a live frame** — for example `ui.ctl_button_proc_callback_func`
  resolves to `0x011D4600`, registered on 30 frames, and
  `ui.text_label_frame_callback_func` resolves to `0x011D5D60`, registered on
  16. This confirms live that a resolved UI-callback address is the same
  address the client stores in `Frame.frame_callbacks`, which is the premise
  the route rests on.
- Most `uictl_context` values point to objects whose first dword is a pointer
  into `.rdata`, consistent with vtable-bearing client objects.

**`MissionMapContext` VERIFIED live, PID 29520, 2026-09-23.** Read-only, with
the mission map open; nothing was written.

- `map.mission_map_ui_callback_func` resolved to `0x011084D0` in `.text`.
- Frame **1591** (address `0x634931E8`, `frame_state=0x00004904`, visible and
  created, parent frame 2511) registers that exact callback as `callback[0]`
  with `uictl_context = 0x26404750`.
- The frame-id cross-check passed: the context reports `frame_id = 1591`, equal
  to the frame's own array index.
- The structure read back self-consistently. Root `size = (387.0, 372.0)`, and
  the raw bytes at the context start are `00 80 c1 43 00 00 ba 43`, which are
  `387.0f` and `372.0f`. Root `frame_id` is `37 06 00 00` = `1591` at `+0x14`.
  Root `player_mission_map_pos = (2181.24, 3226.39)` matches the raw floats
  `d5 53 08 45` / `38 a6 49 45` at that offset.
- `h003c = 0x2726A308` points to a `MissionMapSubContext2` whose
  `mission_map_size = (387.0, 372.0)` equals the root's `size`, and whose
  `player_mission_map_pos`, `mission_map_pan_offset`, and
  `mission_map_pan_offset2` all equal the root's `player_mission_map_pos`.
  `h0020` is a valid `GWArray` with size 2, capacity 2.
- The frame also registers a second callback `0x0143C8B0` whose
  `uictl_context` is **null**. The `GetFrameContext` selection order correctly
  skipped it and returned index 0's context — the first live confirmation that
  the ported selection order matches the native behaviour.

This resolves the inferred hop for the mission map: the frame that registers
the callback publishes exactly the address that reads back as a valid,
internally consistent `MissionMapContext`.

**`MissionMapContext` CLEARED transition, same session.** The operator closed
the mission map and the client was re-sampled:

| Observation | Open | Closed |
| --- | --- | --- |
| Slot `[1591]` | `0x634931E8` | `0x5DDBACF0` (different frame; slot reused) |
| Live frames registering `0x011084D0` | frame 1591 | none |
| Live frames publishing `0x26404750` | frame 1591 | none |
| Old frame at `0x634931E8` | valid `Frame` | freed and reused |
| Old context at `0x26404750` | valid `MissionMapContext` | freed and reused; bytes now decode as UTF-16 text |
| Old child at `0x2726A308` | valid `MissionMapContext2` | freed and reused |
| Valid frames in the array | 548 | 582 |

The route reported "no frame registers this callback" rather than returning the
previous address. Because the walk re-derives the answer from the live frame
array on every read, it cannot hand out a cached or stale pointer — a
structural advantage over a hook that has to observe the destroy message to
clear its own stored copy.

The mission map route is therefore **verified open and closed**.

**`WorldMapContext` VERIFIED live, PID 29520, 2026-09-23.** With the full-screen
world map open. `ui.world_map_state_addr` read `0x0008D511` with bit `0x80000`
set, independently confirming the map was showing.

- Frame **3698** at `0x2630DF10` (`frame_state=0x00000944`, created and visible,
  parent 2511, 17 children) registers `callback[0] = 0x0110C340` with
  `uictl_context = 0x4526A578`.
- The frame-id cross-check passed: the context reports `frame_id = 3698`.
- Read-back: `zoom = 1.0000`, `top_left = (1462.24, 2640.10)`,
  `bottom_right = (2900.24, 3812.67)`; raw leading bytes `72 0e 00 00` = 3698.
- Cross-validation: the context's `(2181.24, 3226.39)` pair equals the
  `player_mission_map_pos` read from the separate `MissionMapContext` earlier in
  the session.

**Discovery: the registered callback is a jump thunk.** The first attempt
failed because no frame registered the resolved `0x0110B5A0`. The world-map
frame registers `0x0110C340`, whose bytes are `e9 5b f2 ff ff`, a five-byte
`jmp` whose `rel32` resolves to exactly `0x0110B5A0`. The client stores a thunk;
the maintained signature finds the handler. Reforged Native is unaffected
because `HookBase::CreateHook` follows a near call or jump before installing its
detour. Stealth's `FrameTree.frames_using_callback` now matches either the
direct address or the address reached through
`RemoteScanner.function_from_near_call`. `MissionMapContext` matched directly
(frame 1591 registered `0x011084D0` itself), which is why it worked first.

**`WorldMapContext` CLEARED transition, same session.** The operator closed the
world map:

| Observation | Open | Closed |
| --- | --- | --- |
| `ui.world_map_state_addr` | `0x0008D511` (bit `0x80000` set) | `0x0000D511` (bit clear) |
| Slot `[3698]` | `0x2630DF10` | `0x00000000` (nulled; frame destroyed) |
| Live frames registering the thunk or handler | frame 3698 | none |
| Live frames publishing `0x4526A578` | frame 3698 | none |
| Old frame at `0x2630DF10` | valid `Frame` | freed and reused |
| Old context at `0x4526A578` | valid `WorldMapContext` | freed and reused; bytes now decode as the UTF-16 registry path `\REGISTRY\US...` |
| Thunk at `0x0110C340` | `e9 5b f2 ff ff` | unchanged (static code) |
| Valid frames in the array | 582 | 575 |

Both map routes are therefore **verified open and closed**. The two close
transitions differ in mechanism — the mission-map slot was reused by another
frame, the world-map slot was nulled — and both are handled.

**`SalvageSessionInfo` is not yet read on the read-only frame route, PID 29520, 2026-09-23.**
With the operator's lesser-kit salvage window open, four measurements settled
it:

- `item.salvage_popup_uicallback_func` resolved to `0x014A4980` in `.text`
  (real prologue; `mov esi,[ebp+8]; mov eax,[esi+4]; cmp eax,7` — an
  `InteractionMessage` dispatch), with the `InvSalvage.cpp` / `m_toolId`
  assertion `-0x105` inside the same function.
- The open window was frame 1718, `child_offset_id = 111`
  (`ScreenFrame.C6.LesserSalvageWindow`), visible. It registers `0x0145EBA0`
  (thunk to `0x0145E8F0`) and `0x0145F100` (thunk to `0x0145ECC0`) — neither is
  the resolved handler.
- The resolved handler is registered as a frame callback on **zero** frames.
- The resolved handler occurs **nowhere** in the `0x1C8` bytes of any of 1141
  scanned frame records.

The cause is a distinction the Native source cannot show on its own. Hooking a
function only requires that it is *called*; reading a pointer out of a frame
requires the address to be *stored* in a frame. Native hooks by function
address and never depends on that. Live data shows the split: `MissionMapContext`
is registered directly, `WorldMapContext` through a `jmp` thunk, and
`SalvageSessionInfo`'s handler is never stored in a frame at all.

Salvage is also not a single window: Reforged's registry maps
`LesserSalvageWindow` (111), `ExpertSalvageUnidentifiedItem` (112),
`SalvageMaterialsDialog` (113), and the top-level `SalvageWindow` (children 1
and 2 as CancelButton and Button, which match `SalvageSessionCancel` and
`SalvageMaterials`). `SalvageSessionInfo` is the options window only, and
Reforged drives the other flows by frame navigation rather than by any context.

**Consequence:** `SalvageSessionInfo` is not yet ported, and it needs target-side
code: the selected mechanism is a Stealth-owned detour on `0x014A4980`
mirroring `OnSalvagePopup_UICallback`. It has **not** been implemented; the
install/rollback contract has to be written and reviewed, which is the next work
item here, and installing it is a target-modifying operation needing explicit scope.

**What salvage exposes without a hook.** Follow-up source analysis narrowed the
hook's value considerably:

- `GetSalvageSessionId()` is `WorldContext->salvage_session_id`
  (`include/GW/context/world.h:226`, `+h0690`) — a plain context field.
  Stealth already declares it (`world_context.py:1493`), and it read **29** on
  PID 29520 while the lesser-kit window was open (frame 1718,
  `child_offset_id = 111`). So "which salvage session is active" is answerable
  read-only today. Whether the field zeroes when the window closes is not yet
  measured.
- Every salvage operation is a resolvable, callable game function:
  `salvage_start_func` `0x01407F00` (`void __cdecl(kit_id, session_id,
  item_id)`, `item_methods.cpp:299`), and zero-argument
  `salvage_session_complete_func` `0x0140CAD0`,
  `salvage_session_cancel_func` `0x0140CB00`, `salvage_materials_func`
  `0x0140CB30`. The three zero-argument functions are 32-byte near-identical
  wrappers that differ only in the UI message id they dispatch: `0x78`
  complete, `0x79` cancel, `0x7A` materials.
- `SalvageStart` shows the real flow (`item_methods.cpp:292-301`): send
  `kPreStartSalvage` with `{item_id, kit_id}`, then call the function with the
  WorldContext-derived session id.
- Native resolves `salvage_materials_func` and `salvage_session_cancel_func`
  but **never calls them**; it implements materials and cancel by mutating the
  context and clicking child frames 2 and 1. Only
  `salvage_session_complete_func` is called.

So the hook buys exactly one thing: the full options record
(`item_id`, `salvagable_1/2/3`, `chosen_salvagable`, `kit_id`). Session
identity and the actions themselves do not need it. A simpler hook target, if
one is wanted for inputs rather than options, is `salvage_start_func`
`0x01407F00` — a normal three-argument `__cdecl` function with no
`InteractionMessage` dereference and no frame semantics.

**GwAu3 salvage analysis — 2026-09-23.** Read-only source review of
`external/GwAu3`. It does **not** avoid target-side code and does **not**
reveal a read-only salvage pointer, which independently confirms the
conclusion above from a second project:

- It `VirtualAllocEx`es assembled machine code into `Gw.exe`, patches the
  engine loop with `E9` detours, and runs the game's own `Salvage` function on
  the game thread through a `MainProc` hook plus a shared command queue
  (`GwAu3_Core_Assembler.au3:2387-2404`, `:1949-2029`;
  `GwAu3_Core_Memory.au3:119-121`).
- It has **no** `SalvageSessionInfo`, no salvage-window detection, and no
  frame lookup. It reads salvage state only as the session id dword at
  `[[[BasePointer]+0x18]+0x2C]+0x690` — the same `WorldContext +0x690` field.
- `SalvageGlobal` (pattern `8B4A04538945F8B4208`) is a static global used
  **only as a write target** (itemID `+0`, kitItemID `+4`) before the call, and
  is never read back for state.
- Option selection is done by **client-to-server packets**, not struct writes
  or UI clicks: `0x7A` materials, `0x7B` upgrade with slot `0`/`1`/`2` for
  prefix/suffix/inscription. Headers are `0x77` open, `0x78` cancel, `0x79`
  done, `0x7A` materials, `0x7B` upgrade.
- It has no completion or failure detection: fixed `Sleep(ping + ms)` waits
  only, and `Item_SalvageItem` returns `True` unconditionally.

`0x7A` agrees with Stealth's own reading of the three 32-byte wrapper
functions in `Gw.exe`: each builds a 4-byte buffer containing the header and
sends it, so `salvage_materials_func` (`0x0140CB30`) is a **packet sender**,
not a session mutator. That cross-validates the interpretation from two
independent sources.

**Two contradictions that must be resolved live before any salvage is
performed:**

| Question | Reforged Native | GwAu3 |
| --- | --- | --- |
| `Salvage()` argument order | `(kit_id, session_id, item_id)` | pushes `itemID, kitItemID, sessionID` → `(sessionID, kitID, itemID)` under cdecl |
| Header `0x78` | session **complete** | **CANCEL** |
| Header `0x79` | session **cancel** | DONE |
| Header `0x7A` | materials | materials — **agrees** |

A wrong argument order would salvage the wrong item, and a wrong
cancel/complete mapping would do the opposite of what the caller intended.
Neither can be settled from source; both need a live, user-present test.

**Recorded salvage-session wrappers in `Gw.exe` (PID 29520).** All resolve
live in `.text` and are 32 bytes apart with identical prologues differing only
in the dispatched header:

| Resolver | Address | Header |
| --- | --- | --- |
| `item.salvage_session_complete_func` | `0x0140CAD0` | `0x78` |
| `item.salvage_session_cancel_func` | `0x0140CB00` | `0x79` |
| `item.salvage_materials_func` | `0x0140CB30` | `0x7A` |

`item.salvage_start_func` (`0x01407F00`) is the three-argument `Salvage`
entry point; `item.salvage_popup_uicallback_func` (`0x014A4980`) is the popup
message handler that is never registered as a frame callback.

**Not established.** Whether `salvage_session_id` returns to zero when the
salvage window closes. The operator's window remained open across repeated
samples (`salvage_session_id` read `29` each time with frame 1718 visible), so
the field is confirmed readable but its idle value is unmeasured. Neither
reference project depends on that: both read it immediately before starting a
salvage.

## Live: the GW.dat read and the text it decodes to — 2026-09-25

**Target:** PID `39188`, `F:\GW\GW1\Gw.exe`, module `0x00610000` + `0xF49000`
(image base), file/product version `1.0.0.1` (no useful build identifier, as
before). The character was in a map. Test: `tests/test_live_dat.py`, which
connects — installing the capability layer — reads one string-table file, then
interacts with the closest NPC and decodes the dialog body the client reports.

**This is the first live run of the call path's value-returning forms and of the
block's data region.** The block layout changed for it (version 3: the command
record gained `arg4`/`arg5`, because `OpenFileByFileId` takes five words), and
the version-2 layout was never installed live, so this run is also the first
live exercise of the current block.

**Read-only preflight, before anything was written:** both hooked functions'
entry bytes were the ones the tests declare
(`55 8B EC 81 EC 20 02 00 00` at `leave_game_thread_func`, `0x00845880`, and
`55 8B EC 8B 45 08 83 F8 56` at `ui.send_ui_message_func`, `0x008441A0`), and
the whole `.text` section hashed to
`33984c4c6a98d23ec43b00798f9f2a11…` over 5,473,792 bytes.

**Input and expected result:** resolve the five `gw_dat_reader` functions;
convert the first `TextParser` file slot's hash with the ported
`FileHashToFileId`; read that file through the ported chain
(`OpenFileByFileId` → `ReadFileBuffer` → copy → `FreeFileBuffer` →
`CloseRecObj`); parse its entries; then interact with the closest NPC and render
the dialog body the client announces. Each step should answer what the sources
say it answers, and the client should be unchanged afterwards.

**Observed, the read:**

| Fact | Value |
| --- | --- |
| the five resolvers | all present: `open_file_by_file_id_func`, `file_hash_to_rec_obj_func`, `read_file_buffer_func`, `free_file_buffer_func`, `close_rec_obj_func` |
| `TextParser` | `language_id` 0, `entries_per_file` 1024, 11 languages × 99 file slots |
| slot 0's hash | code units `[13485, 256]` → file id 13230 |
| slot 0's range | entries 0..1024 — the stride `entries_per_file` the source indexes with |
| bytes read | 91,114, through the client's own `ReadFileBuffer` |
| entries parsed | 1024 |
| decoded with no key | 1022, of which **944 printable** (e.g. `'[null]'`, `'%num1%'`, `'<pg>[b]'`, `'%str1%'`) |

**Observed, the text:** interacting with agent 17 at `(-5430.6, -4763.3)` opened
its dialog 0.2 s later (one body, two buttons). The body's encoded pointer
`0x09D74058` held 22 codepoints starting `0x8103, 0x0A66, 0xDAA8, 0xA948, …` —
the same first four codepoints this project measured for a dialog body by an
independent route earlier (`03 81 66 0a a8 da 48 a9 …`). `_parse_codepoints`
named table index **99942** with key `0x1610C5A3EA63`; that index lives in file
slot 97, which was read through the same chain (1024 entries, 111,447 bytes), and
its 105-byte entry decrypted and unpacked to:

```text
I bring good tidings and announcements of exciting events! Right this very
moment, you could be taking part in...
```

**Observed, and unresolved: the button labels.** Both of the dialog's buttons
(ids 4484 and 6020) announced the **same** label pointer, whose five codepoints
were `0x953C, 0xC037, 0x0A92, 0x4006, 0x0000`. Parsed as an encoded reference
those name index `5475942290066`, which is far outside the table's 101,376
entries, so **the button label pointer does not carry a table reference**. The run
was repeated after a code change and saw the same dialog again: same two ids, same
shared pointer, and five codepoints whose **first two units differed**
(`0xFDF5, 0xC03B, 0x0A92, 0x4006, 0x0000`) while the last three were identical. The
earlier probe's observation of this dialog (`0x39B1, 0xC019, 0x0A92, 0x4006,
0x4A23, 0x0000`) fits the same pattern: a head that changes between runs, a tail
that does not.

Three readings of that, in the order the evidence supports them:

1. **The pointer is right and the memory behind it is not stable.** The first two
   units look like a 32-bit value written into that allocation (`0xC03BFDF5`,
   `0xC037953C`, `0xC01939B1` as little-endian pairs), which is what a reused or
   freed buffer looks like. The body's pointer, read the same way in the same runs,
   was **identical every time** (and its codepoints matched what this project had
   measured for a body before), so the mechanism works when the pointed-to memory
   is stable.
2. **A consequence for the port** *(proposed, not tested)*: a dialog member that
   needs a **button's** text cannot rely on reading the event's pointer later. It
   has either to copy the codepoints where they are live — inside the client, which
   is what the observer could be made to do — or to ask the client to decode
   (Route B), or to read the label from `DialogLoader_GetText` by dialog id. The
   body does not have this problem, which is why `Dialog`'s text still has a route
   that needs nothing new.
3. **Alternatively the button's word 1 is not the text pointer at all** for this
   message. Native's own handler treats it as one (`DialogButtonInfo.message`,
   `context/ui.h`), so this reading needs evidence before it is preferred.

What is **verified** is only what was read: the pointer, the codepoints at it, and
that they changed between runs while the body's did not.

**Safety and cleanup:** the run connected (two entry hooks, a block, a
dispatcher, a listener) and called five of the client's own file functions on
the client's own thread — the first time this project has called anything that
reads the archive. It sent nothing else: the only game action was the
interaction the test declares. Afterwards both hooked functions held their
original bytes again and the `.text` section hashed to the same
`33984c4c6a98d23ec43b00798f9f2a11…`, so the patch window is the only client code
that was ever written. The dialog the interaction opened is still up: closing it
needs the Escape key, and this project does not synthesise keyboard input.

**Not established:** that the whole table loads (99 files per language were
walked by the source, one file per read here); that the compressed path
(`UnpackGWDat`) is ever needed for these files — nothing in the chain this test
ran decompresses, and the bytes it read parsed as a string table directly; and
whether a dialog whose body is not a table reference exists (the buttons are
already one case).

## Live: the first client crash, and what it proved about the dialog table — 2026-09-25

**This is the first time this project crashed the client. It had two causes: a rebase bug in this
port, and a stale constant in the sources' table. Both are recorded here in full, and the
corrected comparison with Reforged is at the end of the entry.**

**Target:** PID `39188`, `F:\GW\GW1\Gw.exe`, module base `0x00610000`, module size
`0xF49000`. The client reported its own crash: `Exception: c0000005`, *"Memory at address
00000000 could not be read"*, `App: Gw.exe`, `BaseAddr: 00610000`, **`Build: 38888`**, at
`9/25/2026 11:30:35`, with a `Crash.dmp` written beside the client.

**What the port was doing.** `tests/test_live_dialog_text.py` — the first live run of the five
`PyDialog` text members — connected (installing the capability layer), asked
`enumerate_available_dialogs()` for the catalog, and for each available dialog id queued a
decode. The queue's second step is the client's own `DialogLoader_GetText`, which the sources
reach through a **hardcoded client virtual address**: `DialogMemory::DIALOG_LOADER_GETTEXT =
0x0079EEF0` (`dialog.h:96`), rebased onto the module by `ResolveDialogLoaderGetText`
(`dialog_patterns.cpp:261-269`) and called **without anything being read at it first**.

**What the crash dump shows, and it is unambiguous:**

```text
eip=0079eef0  eax=00000000  ebx=017c0000  esi=017c0040     (the block, at its magic)
0079EEE0  0000e8c9 310a0056 8bf8e8b1 d4edff83
0079EEF0  c41083f8 0176146a 0068e0da 79006a00
Stack: 065BF868  017e0156 00000000 0169dc64 0a5779f0
```

Three things follow from those bytes and that context:

1. **`0x0079EEF0` is not a function entry.** The instruction that ends at `0x0079EEF1` is
   `83 C4 10` (`add esp, 0x10`) — a return sequence — so the address the port called is the
   **middle of another function**. Executing from there, `C4 10` is `LES edx, [eax]` with
   `eax = 0`: *"Memory at address 00000000 could not be read"* is that instruction faulting,
   which is why the fault address is `eip` itself and not inside the loader.
2. **The call path did exactly what it was told.** The dump's `ebx` is the block
   (`4b4c4253` = `SBLK`, version 3), `esi` is command slot 0 (`operation 5` = `CALL`), and
   `esp+0`/`esp+4` are this project's dispatcher (`0x017E0156`) and the one argument, `0` — the
   first dialog id `enumerate_available_dialogs()` asks about. Nothing about the block, the
   dispatcher or the argument passing was wrong; the **address** was.

**The address was wrong for two separate reasons, and the first one was this port's bug.**

**1. The rebase was a no-op.** `ToRuntimeAddress` (``dialog_patterns.cpp:23-31``) is

```cpp
static uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
return base + (va - kGwImageBase);          // kGwImageBase = 0x00400000
```

The port rebased with the module's own ``OptionalHeader.ImageBase`` instead — an invention, on
the theory that the header would be the link-time base. **It is not, on this client**: measured
read-only (`tests/probe_dialog_loader_address.py`), the live mapped header reads
``ImageBase = 0x610000`` (the address the image was loaded at, rewritten by the client's own
loader) while the file on disk reads ``0x400000``. So the port computed
``0x610000 + (0x79EEF0 - 0x610000) = 0x79EEF0`` — the constant, unrebased — where Reforged
computes ``0x610000 + (0x79EEF0 - 0x400000) = 0x9AEEF0``. **Fixed:** ``RemoteScanner`` now uses
the sources' constant, with a regression test (`tests/test_remote_scanner.py`) that loads a
synthetic image away from its link base and requires the rebase to move by the load delta.

**2. The constant is stale on this build as well.** With the correct rebase the address is
``0x9AEEF0``, and that is **inside a function too** — one that starts at ``0x9AEEB0``:

```text
9AEEB0  55 8b ec 83 ec 18 a1 80 74 e0 00 33 c5 89 45 fc 53 8b 5d 08 56 57 8b 3b ...
        push ebp; mov ebp,esp; sub esp,18; mov eax,[E07480]; xor eax,ebp; mov [ebp-4],eax;
        push ebx; mov ebx,[ebp+8]; push esi; push edi; mov edi,[ebx]; ...
9AEEF0  89 45 ec 89 55 f4 83 e1 01 ...        ← the sources' constant, rebased, lands here
```

`sources: 0x0079EEF0 → ToRuntimeAddress → 0x9AEEF0 → to_function_start → 0x9AEEB0` — and that
function **dereferences its first argument** (`mov ebx,[ebp+8]` then `mov edi,[ebx]`) and reads
a second one (`cmp esi,[ebp+0xc]`): it is a two-pointer container search, not
``DialogLoader_GetText(uint32_t)``. So the dialog *data* addresses are not the only stale ones in
that table — the code address is stale by at least this much, which is consistent with the
table's own shape having changed (see the row probe above).

**Why this matters for the comparison with Reforged:** on this build Reforged computes the same
``0x9AEEF0`` and calls it inside ``SafeCallDialogLoader_GetText``'s ``__try``. The fault is
caught, the function answers null, and the queue caches **empty text for every dialog** — so
Reforged's *catalog text* is silently empty here too, while everything that comes from the
client's own messages (dialog body, buttons, state) keeps working. That is the difference that
made this a crash in the port and a silent empty string in Reforged: the sources wrap the call
in SEH and this project's emitted dispatcher cannot (`docs/DIALOG_MIGRATION_PLAN.md`, adaptation
2).

**The fix in the port, and what it does *not* claim.** `DialogTables.resolve_loader_get_text`
confirms the candidate's bytes before handing the address out — a prologue (`55 8B EC`, or
`8B FF 55 8B EC`) or a `jmp rel32` thunk to one inside `.text` — and answers `0` otherwise, which
is the sources' own "no loader" path (``dialog.cpp:1166-1177``: cache empty text, clear pending).
**An entry check is not identification**, and the measurement above is why: `to_function_start`
would resolve `0x9AEEF0` to the real entry `0x9AEEB0`, which the check would *accept*, and
calling that with a dialog id would dereference a small integer. So the resolver deliberately
does **not** walk back to a function start, and the loader stays refused until it is identified by
a signature rather than by an address from a stale table.

**Verified live after the fix** (`tests/test_live_dialog_text.py`, PID `18928`, 2026-09-25):
the tables resolve, **56 dialogs are available**, the loader is **refused**, the members answer
the source's empty text, **0 commands were published** — nothing was called at all — and both
hooked functions held their original bytes with the `.text` section hashing to `33984c4c…` as
before.


**What one row of the table actually holds on this build** (a read-only probe,
`tests/probe_dialog_rows.py`, run after the client was restarted; new PID `18928`, same module
`0x00610000`): the rows are `0x24` bytes and the five columns the sources name sit where they
expect them, but the field the sources call the *frame type* is **a pointer to the dialog's
name**:

```text
id 0  0xB5CF08:  event_handler 0x0070B8D0  [+0x04] 0x00B5D918 -> "AgentCommander0"
                 flags 0x563  content_id 0x20  property_id 0x1
id 7  0xB5D004:  event_handler 0x007103C0  [+0x04] 0x00B5D9F8 -> "Announcement"
                 flags 0x159  content_id 0x20  property_id 0x0
```

So this build's table is a different shape from the one the sources describe, which is
consistent with the code address being wrong too. The `event_handler` values (`0x0070B8D0`,
`0x007103C0`) are real client functions whose first bytes are `55 8B EC` (`push ebp` /
`mov ebp, esp`) — which is what the entry confirmation below is built on.

**The fix, and it is a check the source does not have.** `DialogTables.resolve_loader_get_text`
now confirms the candidate before it hands the address out: the bytes at it must begin like a
function (`55 8B EC`, or `8B FF 55 8B EC` with the hot-patch padding the same functions carry).
A candidate that does not is answered as `0`, and `QueueDialogTextDecode` already has the
source's own behaviour for a missing loader — cache empty text, clear the pending flag
(`dialog.cpp:1166-1177`) — so no dialog member ever calls an unconfirmed address.

**Verified live after the fix** (`tests/test_live_dialog_text.py`, PID `18928`, 2026-09-25):
the tables resolve, **56 dialogs are available**, the loader is **refused** with the reason
printed, the members answer the source's empty text, **0 commands were published** — nothing
was called at all — and both hooked functions held their original bytes with the `.text`
section hashing to `33984c4c…` as before. The text half of those five members therefore cannot
be exercised on this build, and what it needs is a **resolver for this build's
`DialogLoader_GetText`** — a work item with a name, not a stub.

**Not established:** where this build's `DialogLoader_GetText` is. **Four probes have now
looked, and what they rule out is the useful result** — it stops the next attempt repeating them.
The method named above was taken (`tests/probe_dialog_loader_candidates.py`, 2026-09-25): every
dialog anchor, and then **every one of the 937 `P:\Code\` paths the client carries**, resolved to
the code that references it, `to_function_start` for the function.

- **The dialog anchors are other dialogs.** `P:\Code\Gw\Ui\Dialog\DlgKey.cpp` is the **key-binding**
  screen (its asserts are `s_currKey < arrsize(s_keys)`, `actionSelected`, and its code walks a
  117-entry key table); `DlgCustomize`, `DlgDevSound`, `DlgNetCancel`, `DlgOptGeneral`, `DlgOptGr`
  and `DlgTimeout` are those dialogs' UI; and `dialog < DIALOGS` belongs to the **login screen** —
  it is referenced by one function, `0xa6daa0`, which indexes a 7-entry table at `0xdaa648` and
  asserts `!FrameGetChild(frame, code)` from `ActFrLogin.cpp`. `DIALOGS` is 7 there, not 58.
- **`P:\Code\Engine\Dialog\DlgMsg.cpp` is the dialog *message* module.** Exactly two functions
  reference it: `0x838760`, whose body dispatches a 0x5c-case jump table on `[wparam+4] - 4`
  (the packet's message kind), and `0x838c30`, which registers a callback and asserts on a null
  argument. Neither takes a dialog id and returns text.
- **The 58-row table has one reader.** `s_floatingDialogs` is 58 rows of `0x24` bytes at
  `0xb5cf08` (the assert `dialog < arrsize(s_floatingDialogs)` sits in the reader, whose bound is
  `cmp edi,0x3a`), and the only function in `.text` whose immediates land on the table's own
  addresses is **`0x6f2300`** — the dialog *window*, which indexes rows by `id*0x24` and reads the
  five fields the sources name **and the four words after them**. So no loader reads this table.
- **The row's four unnamed words are not the text.** `DialogInfo.content` comes from the loader,
  and the four words move together per dialog (`0x187ca 0xdc 0x11 0x37` for id 0,
  `0x187ca 0xdd 0x11 0x38` for id 1, `0x337 0x12a 0x11 0x6a` for id 7), which looks exactly like
  an `(index, key)` pair — so `tests/probe_dialog_row_text.py` decoded every packing of them
  through the game's own string table. **All of them are nonsense or refuse**: they are not a
  text reference.
- **Nothing is laid out as a text table either.** A run of dwords in the band every measured
  dialog text index falls in (99942, 99994, 99946) would be a table of references; there is none
  in `.rdata` or `.data`.
- **The row stride is scaled by 17 functions in the whole `.text`**, and none of them has the
  loader's shape: the only one in the dialog region is `0x79a180` (right after the templates
  dialog, `0x79a000`), and it **dereferences** its argument (`mov ecx,[ebp+8]; mov eax,[ecx+4]`)
  — calling it with a dialog id would dereference a small integer, which is how the 2026-09-25
  crash happened. The rest take their object in `ecx` (a `thiscall` member) or two arguments.
- The client carries no `DialogLoader`-like name: the only dialog-named symbols in its data are
  `GetDialog` (used by one login-module function) and `DialogGetFrame`.

What remains is not another static pass: the identification needs a function **tested for what it
returns**, and that means calling candidates from the game thread. Every call this project makes
goes through the dispatcher, which has no `__try` — a candidate that is not the loader does not
fail safely, and the one that was tried with a stale address killed the client. That is a decision
about accepting that risk, not a search that has not been run.

The loader's own consequence is narrow, which is worth stating plainly: `get_dialog_text_decoded`
and the `content` field of `get_dialog_info` are its only consumers, and the *button caption*
fallback can only reach ids 0..57 (`MAX_DIALOG_ID = 0x39`) — which real buttons (4484, 6020) are
not. The live dialog flow this class exists for works without it.

**The two earlier attempts, kept because two of their results are still load-bearing.**
`tests/probe_dialog_loader.py` read the 58 handler pointers out of the resolved table (41
distinct handlers), read the first `0x800` bytes of each, and collected every `call rel32`
  target inside `.text`: **481 candidates**, the busiest of which are called 100–372 times
  (`0x00697BC0`, `0x008420B0`, `0x008410B0`) — utility functions, not a loader. Frequency alone
  does not identify it, and ranking the same 481 by **how many distinct handlers** call them
  (6, 5, 4 …) only surfaces UI functions. The same probe found something that matters for any
  entry check:
  **most handler pointers are ``jmp rel32`` thunks** (`0x0070B8D0` → `0x0070B940`), so a
  legitimate function pointer in this client need not begin with a prologue. The port's
  confirmation accepts both shapes because of it.
- `tests/probe_dialog_strings.py` read the whole data section for dialog strings and the whole
  code section for `push imm32` references to them. The client carries its **own source paths
  and assertion messages**, which is the anchor style the offsets catalog already uses:
  ``P:\Code\Gw\Ui\Dialog\DlgNetCancel.cpp``, ``DlgDevSound.cpp``, ``DlgCustomize.cpp``,
  ``DlgOptGeneral.cpp``, ``DlgOptGr.cpp``, ``DlgKey.cpp``, ``P:\Code\Gw\Ui\Game\GmAgentDialogue.cpp``,
  ``dialog < DIALOGS``, ``DialogGetFrame(frame, dialog)``, ``dialog < GM_INT_TEMPLATES_DIALOGS``,
  ``dialog < arrsize(s_floatingDialogs)``, ``ArenaNet_Dialog_Class``. **None of them is
  referenced by a `push imm32`** — the code loads those addresses another way — which is what
  the `find_use_of_string` pass above then did, and what it came back with is the list of
  ruled-out things.

## The loader, hunted from the file — 2026-09-26

**The method changed, and that is this pass's first result: the client is a file.** Every earlier
attempt read a *running* client — hooks, the game thread, an elevated shell, a UAC prompt, and a
crash when an address that was not the loader got called. `Gw.exe` is on disk
(`F:\GW\GW1\Gw.exe`, 10,493,120 bytes, build 38888 — the image the live pid runs), and a file needs
none of that: the headers give the sections, the sections give the bytes, and a virtual address the
sources quote (`0x0079EEF0`, `0x00913920`) is an offset into it. Read-only, offline, repeatable.

**The tools** (all in `tools/`, documented in their own files, none of them touching a client):

| tool | what it answers |
| --- | --- |
| `pe_image.py` | sections, `ImageBase`, and virtual address ↔ file offset. Refuses a range the file does not hold rather than padding zeros |
| `gw_scan.py` | this *client's* shapes: function entries (`55 8B EC`, or the `8B FF` hot-patch padding), encoded strings via the port's own `is_valid_enc_str`, where a value is referenced in code or in data |
| `dialog_loader_hunt.py` | the hunt's questions: `constants` (do Native's two dialog constants describe this file?), `rows` (the metadata table, dumped by **the port's own** `ResolveFlagsBase` over the file), `table-users` (who names the table in code, and is its address held in data), `immediates` (who holds a value), `strings` (encoded strings and the tables of them) |
| `ghidra_scripts/*.java` | `DecompileAt`, `DialogTableReaders`, `ListModuleFunctions` — run by Ghidra 12.0.4 headless over the same file (project `.ghidra/gw38888`, gitignored; Ghidra's settings directory is redirected into the workspace, which the sandbox requires) |
| `resolve_offline.py` | **every resolver in `offsets/*.json`, run against the file** — the port's own `PatternCatalog` over a reader that answers virtual addresses out of the PE, with each answer's bytes and whether they begin like a function. It never connects, never calls and never writes |

**And the same file answers the resolver question — 2026-09-26, and it was the port's own bug.**
A resolver is a claim about a build and the engine that evaluates it is pure, so
`tools/resolve_offline.py` runs all of them offline. The first sweep found **15 of 143 function
resolvers** answering with something that does not begin like a function, and the worst of them was
the crash of 2026-09-25: `chat.send_chat_func` answered `0x0082D64F` from a pattern match at
`0x0082D65E`. **The pattern was never stale.** The walk back to the function start was this port's:
`to_function_start` had grown a second candidate — a `jmp` whose destination leaves the module,
treated as a patched function entry — and took whichever candidate was nearest, so an `e9` byte
*inside the instruction before the match site* won against the real prologue at `0x0082D620`. The
source has no such candidate: `Scanner::ToFunctionStart` is three lines that scan backward for
`55 8B EC` (`scanner.cpp:205-210`). The member is the source's again; the recovery that inference was
for now lives in `py4gw/client.py` (`_stale_patch_before`, verified against the bytes it expects) and
the regression is pinned in `tests/test_remote_scanner.py`. After the fix the same sweep reports
**4 of 143** — `map.cancel_enter_challenge_mission_func`, `memory.gw_version_func`,
`ui.set_game_renderer_mode_func`, `ui.trigger_terrain_rerender_func` — and
`chat.send_chat_func` answers `0x0082D620`, the client's chat send, decompiled to the source's own
`(wchar_t* message, uint32_t agent_id)` shape. The finding is in [`CHAT_PORT.md`](CHAT_PORT.md) and
[`PLAYER_PORT.md`](PLAYER_PORT.md); the four that remain are the open list.

**The port's own scan reproduces the live result.** `rows` over the file finds the flags column at
file VA `0x0094CF10` — live `0x00B5CF10`, `0x210000` apart, which is the module's relocation on this
client — and every row matches the live reading (id 0: `0x004FB8D0` handler, flags `0x563`,
content `0x20`, property `0x1`; that handler is live `0x0070B8D0`). The file *is* the binary the port
has been reading, so everything below is about the build the port runs against.

**What the client does with a row**, decompiled (`FUN_004e2300` = live `0x006F2300`, which is
`IUi::Game::DialogShow` — it ends `FUN_006342a0(frame, L"GmView-Dialog")`, and the native repository's
own RE notes name that same function: `docs/RE/ui_frame_identity_reverse_engineering.md` §3):

| row | the port's model (`dialog.h:89-99`) | the client's own use |
| --- | --- | --- |
| `+0x00` | `event_handler` | the `FrameCreate` **proc** argument |
| `+0x04` | `frame_type` | the `FrameCreate` **name** argument — a `wchar_t` literal (`"AgentCommander0"`) |
| `+0x08` | `flags` | the window's **style word**: `FUN_00634250(frame, FUN_0087c8b0, word)`, with bits `0x100`, `0x08`, `0x04` read |
| `+0x0C` | `content_id` | the `FrameCreate` **flags** argument (`0x20`, or `0x30` for ids 22/41/57) |
| `+0x10` | `property_id` | the **availability word**: tested `& 1`, `& 2`, `& 4`, `& 8` |
| `+0x14` | — | a **text id**: `if (id < 0x187CA) FUN_007c9860(id)` — the dialog's text |
| `+0x18` | — | a second id: `if (id != 0x12A) FUN_00633540(id, …)` → `FUN_005a9cd0` → text |
| `+0x1C` | — | a value compared with `0x11` |
| `+0x20` | — | a value compared with `0x6A` |

Two things follow, and both are build facts rather than port defects. The source's five columns are
the five the port reads (the scan's handler column is the proc pointer, so `flags_base - 8` is
`+0x00` and `flags_base` is `+0x08`), but on this build the word the *client* treats as
"available" is `+0x10`: `IsDialogAvailable`'s `flags & 1` lands on the style word at `+0x08`, which
is odd for 56 of the 58 rows, while the client's own window manager
(`FUN_004e8240`) tests `(&DAT_0094CF18)[id*9] & 1`. The port reads the columns the source names;
what those columns *mean* is the build's business, and it is recorded here so the next reader does
not re-derive it.

**The loader is not a reader of this table.** Ghidra's reference analysis finds **exactly one**
reference to the table's start `0x0094CF08`: `0x4E23A8`, inside `DialogShow`. The byte scan over
every dword boundary of the table's `0x828` bytes agrees — the functions that name any of its
addresses are `DialogShow` (`+0x00`…`+0x20` of row 0), `FUN_004e8240` (the window *manager*, which
walks all 58 rows and reads `+0x10`, `+0x1C`, `+0x20`), and nothing else of substance — and the
data sections hold **no pointer to it at all** (checked for its start, its `+4`, and its last row),
so there is no global through which a reader could reach it either. The earlier live probe's five
"table users" are readers of a *different* array: they name `0xB5D730`, one past the table's end,
which is where the next structure begins.

**The client inlines the text path, and its text module is identified.** The only code that reads a
dialog's text id is `DialogShow` itself (`row+0x14 < 0x187CA` → `FUN_007c9860`), and the per-column
check says it column by column: `+0x14` has **one** reader in the whole module (`DialogShow`, at
`0xE246D`), `+0x1C` one (the window manager), `+0x18` two and `+0x20` four — every reader already
named above. That function, and the encoder behind it, decompile to:

```c
/* FUN_007c9860 (file VA 0x007C9860) */            /* FUN_007c9880: the body */
void FUN_007c9860(id) { FUN_007c9880(id, 0); }     buf = FUN_007ca070();          /* shared buffer */
                                                   FUN_007cbbb0(buf, id, arg, va);  /* encode */
                                                   return buf->base;                /* wchar_t* */
```

`FUN_007cbbb0`'s numeric branch is **the port's own encoding, constant for constant**:
`WORD_VALUE_RANGE = 0x7F00`, `WORD_VALUE_BASE = 0x100`, the `MORE` bit on every digit but the last,
and `CONCAT_CODED`/`TERM_INTERMEDIATE` between segments — the arithmetic of
`py4gw/ui/encoded_str.py`. It refuses to encode a string whose security bit is set
(`"Text: Encoding encrypted string (%u). Check this string's security field."`), which is the
`ConstGetTextStrEncryptedBitmask()` the WASM symbol list carries. Two consequences, one of them an
old measurement explained:

- the pointer a dialog announces is **that shared buffer**, which is what this port measured on
  2026-09-25 (both buttons of one dialog announcing the same pointer, holding nineteen contents in
  two seconds) — the finding that moved the label read *inside* the client;
- the codepoints the port's observer copies (`8103 0a66 …`, index 99942) are this function's
  output, which is why the client's own decoder accepts them and why the port's observer had to be
  placed where it is.

**Native's own constant is stale, and here it lands in asset code.** `0x0079EEF0` rebases to
`0x9AEEF0` on this client; the function containing it is `FUN_0079EEB0`, decompiled here: a
**packet/record deserializer** — fixed `0x15`/`0x14`-byte records copied through an `alloca` probe,
asserts `0x7e7`/`0x7e4`/`0x171`, a security cookie, and counts written at `+0x40`/`+0x44`. The
port's refusal to call it is therefore correct on evidence rather than on caution. The same is true
of the five data constants: `dialog_loader_hunt.py constants` checks RVA `0x513920` in every
`Gw.exe` on this machine (the live build, the 2026-07 build under `Gw2Launcher\10`, and the 2024
build in the recycle bin) and **none of them is the dialog table** — Native's constants describe a
build that is not on this disk. The native repository says the same from the other side: its own RE
notes place `s_floatingDialog` at VA `0x0094bee8` and `FrameCreate` at `0x00630c90` in "the live
build", while `dialog.h` still carries `0x00913918` and `0x0079EEF0`, and
`ResolveDialogLoaderGetText` (`dialog_patterns.cpp:261-269`) rebases that value without verifying
anything.

**Where this leaves the item.** `class Dialog` stays INCOMPLETE on one work item: this build's
`DialogLoader_GetText`. **The sources are complete and 100% functional** — `Reforged Native` resolves
that function and calls it — so the function exists here too, and what the pass above establishes is
what it is *not* and where to look next: it is not the stale hardcoded address (`0x0079EEF0` rebases
into a packet deserializer), and it is not a reader of `s_floatingDialogs` (the client's own dialog
window is the table's only reader on this build, and it inlines the text path a loader would wrap).
Until it is identified, `resolve_loader_get_text` answers `0` and `QueueDialogTextDecode` takes the
source's own missing-loader path (empty text cached, pending cleared — `dialog.cpp:1166-1177`), which
is one of the source's cases rather than a substitute for one. The two routes left are named and
both are work with a method: a **witness** — hook the confirmed text encoder (`FUN_007c9880`, live
`0x9D9880`, 659 call sites) and drive an interaction, which names the code that builds a dialog's
codepoints — and the client's announce path read statically from `DialogShow`'s callers
(`FUN_0082D3E0`-style chat-side callers were found exactly this way for the chat send).

## Live: the client's own decoder, and the assertion it makes on a button's label — 2026-09-25

The dialog class's text was the one thing this port rendered **itself**: `QueueDialogTextDecode`
and the body's decode were ported onto a host-side render with the game's string table (Route A),
because native's `AsyncDecodeStr` hands the string to the client and gets a callback into **its
own address space**, which nothing of this project's occupies. That substitution is what this
session replaced, and the protocol itself is now ported:

- `shared_block.py`: a **decode region** — `DECODE_DEPTH = 32` slots, each holding the string the
  client is handed (1024 bytes) and the text it writes back (2048 wide characters). Each slot has
  one writer at a time (the host writes the string, the client's callback writes the text), and
  the state word is written **last**, so the block's lock-free rule holds. `VERSION = 4`.
- `payload.build_decoder_stub()`: the emitted stub the client calls — native's
  `DecodeStr_Callback`, `void(__cdecl*)(void* param, const wchar_t* s)` (`ui.h:299`) — which
  copies the text into the slot `param` names and publishes the string's real length. It is
  `__cdecl` (the client cleans the stack), it scans bounded (this side has no SEH where native
  has `wcslen` inside `__try`), and it touches nothing but its own slot.
- `py4gw/ui/async_decode.py`: the port of `AsyncDecodeStr` (`ui_methods.cpp:2582-2607`) with
  `SafeAsyncDecodeStr`'s wrapper (`dialog.cpp:264-274`), including the wrapper's three refusals
  and the empty answer each gives — no decoder, no string, `L""`; not an encoded string,
  `L"!!!"`; no text parser, `L""`.
- `dialog.py`: `_on_body` makes the copy and calls the client; `_on_string_decoded` is
  `OnDialogBodyDecoded`, `OnDialogButtonDecoded` and `OnDialogTextDecoded` behind one event
  kind, dispatching on the request the slot belongs to. The host render, the string-table load
  and the deferred "point of use" queue are deleted.

**Verified live** (`tests/test_live_dat.py`, pid 18928 and later 30560): the resolver
`ui.validate_async_decode_str_func` is there, the body's text comes back through the client's own
decoder — `'I bring good tidings and announcements of exciting events! … Northern Support bonus
week / Guild versus Guild bonus week'` — the same text Route A rendered independently, so the two
decoders agree; the journal's `recv_body` row and `get_active_dialog().raw_message` carry it, and
the client is restored (both entries original, `.text` digest unchanged).

### The crash: `IsParam(data)`, and a hole in the source's own guard

Extending the same protocol to the third text path — a **button label** — killed the client, and
the crash report named it exactly:

```text
Assertion: IsParam(data)
P:\Code\Engine\Text\TextParser.cpp(724)
App: Gw.exe   Build: 38888   When: 9/25/2026 15:02:06
...
(2) Text parser data string:
(2) 4481 c02f 0a92 4006 4a23 0000
```

The trace's `Pc:09bc0176` and `Pc:0aef001b` are outside `Gw.exe`'s module — this project's
allocations — so the decode call was on the stack when the client's parser asserted, and this
build makes an assertion **fatal**. The string in the log is a button's announced label: the same
shape the live runs print for buttons 4484 and 6020, with the first words varying between reads
and the tail `0a92 4006 4a23 0000` constant.

**Verified live** (`tests/probe_dialog_label_fill.py`, 2026-09-25): **the announced pointer is a
buffer the client reuses, not the label.** Both buttons of one dialog announced the *same* pointer
(`0x266CF190`), and reading it repeatedly for two seconds returned 19 distinct contents for one
button and 24 for the other — heap-pointer heads, small numbers, and at one moment UTF-16
loading-screen tip text (`y Know Nothing`). The module's caption for those buttons,
`継쀩\u0a92䀆䨣`, is one of those contents, and the varying head of every read on record is a heap
pointer (`0xC02F4481`, `0xC143455B`, `0xC0301DD4`, `0xC0297D99`) — memory that holds a pointer is
not a wide string that has been written yet. What the four (index, key) parses decode to is
therefore not evidence about labels at all: read through the ported chain, the entries at 17499,
17281 and 7380 all render as non-text (`tests/probe_dialog_label_indices.py`), because the index
they were parsed from was never that buffer's content.

**Why native reads something else: its callback runs *after* the client's own send returns.** The
dialog registers its four handlers at altitude `0x1` (`GW::ui::RegisterUIMessageCallback(...,
0x1)`, `dialog.cpp:1273-1292`), and `SendUIMessage` runs the callbacks with `altitude > 0`
**after** `RawSendUiMessage` — the original function — has returned (`ui_methods.cpp:1390-1404`).
So `DupWideStringSafe(info->message)` (`dialog.cpp:639`) copies the string *inside the client's own
call*, after the client's handlers have filled it, and the buffer is still its own at that moment.
This port observes the message at the sender's **entry** — the observer sits on
`ui.send_ui_message_func` and its stub runs before the function's body (`py4gw/game_thread`) — and
dereferences `label_pointer` later still, on the listener thread (`dialog._on_button`). Both are
moments outside the window the label exists in.

**It is not a weak imitation of the source's check.** `py4gw/ui/encoded_str.py` already carries
`EncStrValidate`, `EncStrValidateWord`, `EncStrValidateSingleWord`,
`EncStrValidateTerminatedLiteral` and the character classes as a faithful port of
`ui_methods.cpp:260-362`, and the logged string **passes** it — the port's own validator says so of
the very string in the crash report. That was read at the time as "the client's check is stricter
than the source's", with a button's label named as the one string Reforged decodes that is not a
real table reference. **The measurement below corrects that reading.**

### The label is a real table reference, and the port was reading the wrong buffer

**Verified live**, 2026-09-25, the same day and the same client: the observer was moved to the
source's moment and made to **copy the string inside the client's own call** (``post_payload``
hooks plus the copy in ``payload.build_observer``; the copy travels in the event record). What it
copies is the label:

| what was read | words | parses to | renders to |
| --- | --- | --- | --- |
| the body, copied inside the call | `8103 0a66 daa8 a948 3363 0002` | index 99942 | "I bring good tidings and announcements of exciting events! …" |
| the body, read from the host a second later | *identical* | *identical* | *identical* |
| button 4484, copied inside the call | `8103 0a9a ecfb c982 63f6 0000` | index 99994 | **"Would you tell me more about the Northern Support bonus?"** |
| button 6020, copied inside the call | `8103 0a6a 9c12 91f1 4a23 0000` | index 99946 | **"Would you tell me more about the Guild versus Guild bonus?"** |
| the same announced pointer, read from the host | `fdf5 c03b 0a92 4006` | nothing | nothing |

So a button's announced pointer **does** carry a table reference, and the host's read of it is the
problem: the buffer is reused between the client's call and any read made from outside it. The
crash of 2026-09-25 was this port handing the client's decoder a string that was never the label —
not a check the client makes and the source does not. The body's row in that table is the control:
a string that does not move gives the same answer either way, which is why the body always worked
and the label never did.

**It is not a weak imitation of the source's check.** `py4gw/ui/encoded_str.py` already carries
`EncStrValidate`, `EncStrValidateWord`, `EncStrValidateSingleWord`,
`EncStrValidateTerminatedLiteral` and the character classes as a faithful port of
`ui_methods.cpp:260-362`, and tracing the logged string through it by hand, it **passes**: two
words and a terminator, `data == term`. What the source's guard accepted was a buffer's contents
that happened to be shaped like an encoded string, which is why it passed a check that only looks
at the shape.

**What the port does about it:** the label is **handed over**, and the branch is the source's
(`dialog.cpp:641-708`): the copy above is its `encoded_copy`, so the port runs the source's own
check, its own "the label is the text" branch, and otherwise the request, the pending map with its
cap, the handover and the release path. Live, 2026-09-25, the module answers the dialog's two
buttons with `'Would you tell me more about the Northern Support bonus?'` and
`'Would you tell me more about the Guild versus Guild bonus?'` — the client's own decoder's text —
and both `recv_choice` rows carry it.

**What is missing is one capability, and it is the source's own order: reading the packet after
the client has finished with it.** The source's read is inside its callback at altitude `0x1`, and
this port's hook form has no such moment — its stub runs the payload before the hooked function's
body and never sees the return (`byte ... jmp trampoline`, `py4gw/game_thread/hooker.py`).

**That capability is now built and live-verified, and it moved the window without closing it.**
`build_stub(..., post_payload=True)` / `Hooker.install(..., after=True)` take the hooked function's
return address off the stack, `call` the trampoline so the body still returns into this project's
code, run the payload there, and return to the client's caller with the body's value and the stack
exactly as the caller left them — both calling conventions, because the transfer back pushes the
saved address and consumes it with `ret` rather than restoring a stack pointer. A frame stack
(`POST_DEPTH = 8`) makes a re-entrant send safe, and a call that finds every level in use is passed
through untouched rather than waited on. `tests/test_hooker_offline.py` **executes** it against a
synthetic function patched with the real entry patch — the payload runs after the body and sees the
arguments, the return value and esp are unchanged, a payload that sends the message again nests,
and a disabled hook or a full stack passes through — and the observer hook is installed in that
form (`bridge.OBSERVER_AFTER`). Live, 2026-09-25: `tests/test_live_dat.py` is 10/10, the client is
the same pid afterwards, both entry patches are back to their original bytes and the `.text`
digest is unchanged.

**It is not enough on its own, and the fix for that is in.** The observer now fires inside the
client's own call, but a string read from *this* side is still read after the stub has returned —
outside the window — so the observer's emitted code **copies the string itself**, at the offset
each watched message declares (`DialogButtonInfo.message` is four, `ui.h:60-65`;
`DialogBodyInfo.message_enc` is eight, `ui.h:54-58`), into the event record the host reads
(`EVENT_TEXT_WORDS`, bounded, with the terminator included as native's `wcslen + 1` gives it). It
is the same shape as the decoder stub copying the text the client hands it, and the same reason:
the client's own call is the only place the string is the client's. The live run of 2026-09-25
(10/10, client restored, the body's copy word-for-word equal to the host's own read of it) is what
established the table above.

The harness itself needed one fix to report any of this: the live suite's evidence is printed, and
`run_live_dat.cmd` redirects stdout to a file, so on 2026-09-25 the two `test_z_...` tests failed
with `UnicodeEncodeError: 'charmap' codec` while printing the module's caption — a cp1252 stdout,
not a port defect, and the buffered write took the rest of their evidence with it. The wrapper now
sets `PYTHONIOENCODING=utf-8`, as `run_probe_text.cmd` already did, and the suite is 10/10 with the
client restored.

### The second crash: an address that is not code, and the hole that let it through — 2026-09-25

`py4gw/chat.py` was written to close the four `Player` chat senders — the source's `SendChat`
builds a `wchar_t buffer[140]` and hands its address to `g_send_chat_func`
(``chat_methods.cpp:88-142``), and the port can now do the same thing with the block's data
region, which is what that region is for. The offline suite passed (16 tests, pinning the buffer's
bytes, the clamp, the terminator and every refusal). The **live** probe killed the client:

```text
Exception: c0000005   Memory at address 462fd617 could not be written
eax=03b10450  eax+0 03B10450  0061002f 00650067 00000000   ← "/age", the buffer this port placed
ebx=03b00000  ebx+0 03B00000  4b4c4253 00000005 ...        ← the block (SBLK, version 5)
esi=03b00040  esi+0 03B00040  00000000 00000005 00000000 03b10450   ← command 0: CALL, arg1 = the buffer
eip=462fd617  Trace: Pc:462fd617 Rt:030c01ca → Pc:030c01ca Rt:03b4001b → our stub → 0x0083e398
```

Three things the dump settles, and they are worth keeping:

1. **The transport did what it was told.** The block is intact at its magic and version, the
   command record carries the operation and the buffer's address, and the dispatcher and the stub
   are where the trace says they are. Nothing about the ring, the arguments or the ABI was wrong.
2. **The client was made to execute data.** The dispatcher *called* `0x462FD617` — the trace's
   return address is the dispatcher itself — and that address is outside the module
   (`0x00610000` + `0xF49000`). Whatever wrote it into the call table, the call was to something
   that is not code.
3. **The port had no check for that.** The dispatcher refuses a target outside the **module**, and
   `0x462FD617` is outside it — so this went further than the module bound should have allowed, and
   the bound is not the check that matters: an address *inside* the module but outside `.text` is
   data, and executing data does not fail, it runs. The dialog loader learned this on the same day
   from the other side (`DialogTables._is_function_entry` confirms a candidate before it is handed
   out); the call path never got the same treatment.

**What changed, and it closes the class of crash.** `ConnectedClient._descriptor_slot` confirms
the target is inside the client's code section before it writes the descriptor, and refuses
otherwise with the pid, the address, the section and what was expected. That is a *host* check by
necessity: inside the client, an address about to be executed is not distinguishable from one that
is not. `tests/test_client_startup_offline.py::CallTargetSectionTests` pins it — a code address is
written, the data address that got through (`0xb5cf08`) is refused with nothing written, and so is
`0x462fd617`.

**What is still not established: which resolver answered that address.**
`tests/probe_resolver_targets.py` is the read-only diagnostic for it — it resolves the chat, ui,
agent and game-thread names, prints each resolver's own step trace, and reads the bytes at the
answer, **without calling anything** (read-only connection, no hook, no write). It has to be run
once the client is restarted; the client that crashed is gone, and re-running the chat probe before
that diagnosis exists would be repeating the same experiment.

Two candidates for the fault, both readable in that probe's output:

- the resolver's answer is not a function (the pattern's mask is nine characters for a ten-byte
  pattern, and the two engines treat a short mask differently — Native compares
  `strlen(mask)` bytes, `file_scanner.cpp:325`, while the port's `Pattern` requires equal lengths
  and its `from_literal` decides what a mismatch means); or
- the answer is a function and the call itself was misread (the trace shows a direct call, so the
  descriptor's words are the place to look).

Until one of them is settled, the three ported chat senders answer with the refusal above rather
than sending anything, and `Player.SendChat`/`SendChatCommand`/`SendWhisper` are **ported but
blocked** — a finding, not a silent failure.

### Two defects of this project's own, found on the way

- **A deadlock in the command ring.** Serialising the ring with a non-reentrant lock is a
  deadlock on the first call of a session: `Bridge.call` takes the lock and then publishes, which
  takes it again. It is an `RLock`, and
  `test_a_call_publishes_and_waits_without_deadlocking_itself` fails — rather than hangs — on the
  old code.
- **A stale patch broke its own resolution.** A run killed mid-connection leaves this project's
  entry patches in the client. The next install repairs them (`_prepare_target`: a `jmp` whose
  destination leaves the module), but the *resolution* of the patched target walks back for a
  prologue, and the patch is not one — so it answered the **previous** function
  (`0x008440C0` instead of `0x008441A0`) and the repair could not find the address to repair.
  `RemoteScanner.to_function_start` now treats a `jmp` that **leaves the module** as a function
  start, and a `jmp` inside it as an ordinary branch, with a synthetic-image test for both.

## Sources Consulted

- `C:\Users\Apo\Py4GW_Reforged\README.md`
- `C:\Users\Apo\Py4GW_Reforged\docs\architecture\reference\py4-gw-conceptual-model.md`
- `C:\Users\Apo\Py4GW_Reforged\py4gw_bridge\README.md`
- `C:\Users\Apo\Py4GW_Reforged_Native\AGENTS.md`
- `C:\Users\Apo\Py4GW_Reforged_Native\include\GW\context\context.h`
- `C:\Users\Apo\Py4GW_Reforged_Native\include\GW\context\game.h`
- `C:\Users\Apo\Py4GW_Reforged_Native\src\GW\context\context.cpp`
- `C:\Users\Apo\Py4GW_Reforged_Native\src\GW\context\context_methods.cpp`
- `C:\Users\Apo\Py4GW_Reforged_Native\src\Py4GW.cpp`
- `C:\Users\Apo\Py4GW_Reforged_Native\src\base\hooker.cpp`
- `C:\tmp\gwau3-analysis-20260920\API\Core\GwAu3_Core.au3`
- `C:\tmp\gwau3-analysis-20260920\API\Core\GwAu3_Core_Assembler.au3`
- `C:\tmp\gwau3-analysis-20260920\API\Core\GwAu3_Core_Scanner.au3`
- `C:\Users\Apo\Py4GW_Stealth\external\MemLib\README.md` (fetched source, commit `d044a4f8ab5f12121501650e648c9895f8f14eb0`)
- `C:\Users\Apo\Py4GW_Stealth\external\MemLib\MemLib\Process.py`
- `C:\Users\Apo\Py4GW_Stealth\external\MemLib\MemLib\SharedMemory.py`
- `C:\Users\Apo\Py4GW_Stealth\external\MemLib\MemLib\Hook.py`
- `C:\Users\Apo\Downloads\BUILDING_WITH_MEMLIB.md` (user-supplied technical reference; proposals/examples, not instruction authority)
- <https://nicegui.io/documentation> (Python UI components and project model)
- <https://nicegui.io/documentation/section_configuration_deployment> (native
  mode and pywebview requirements)
- <https://nicegui.io/documentation/tabs> (tab and panel usage)
- <https://nicegui.io/documentation/table> (table rows and updates)

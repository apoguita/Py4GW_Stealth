# UI frame tree and frame-published contexts

## Why this exists

A few game contexts are not stored in a module global. The client allocates
them, registers the pointer as a UI frame's *context*, and hands the address to
that frame's interaction callback through the message's `wParam` field. An
in-process project therefore sees the pointer only while a callback is running,
which is why the callback route was the only one recorded for these contexts.

`Gw.exe` does keep the frame itself in a module global array, and the frame
keeps its registered context pointer for as long as the frame exists. That
makes the same pointer readable from outside the process, with no hook, no
payload, and no write of any kind.

This is the frame-tree route. Stealth uses it to acquire three contexts that
otherwise need an in-process callback: `WorldMapContext`,
`MissionMapContext`, and `SalvageSessionInfo`. It does **not** replace the
callback/payload plan; target-side code is still required for game-thread
operations and for the one remaining hook-only pointer. See
[`CALLBACK_POINTER_RESEARCH.md`](CALLBACK_POINTER_RESEARCH.md) and
[`DEFERRED_INJECTION.md`](DEFERRED_INJECTION.md).

## The package

`py4gw/ui/` holds the user-interface engine primitives. It is deliberately
separate from `py4gw/context/`: these are UI-engine records, not game contexts,
even though some contexts are located through them.

| Module | Contents |
| --- | --- |
| `py4gw/ui/frame.py` | `UIMessage`, `FramePositionStruct`, `FrameRelationStruct`, `FrameInteractionCallbackStruct`, `TooltipInfoStruct`, `InteractionMessageStruct`, `FrameStruct`, `FrameArray`, `is_valid_frame_pointer` |
| `py4gw/ui/frame_tree.py` | `FrameTree`: `by_id`, `iter_frames`, `root`, `parent_of`, `children_of`, `context_address_of`, `frames_using_callback` |
| `py4gw/ui/frame_context.py` | `FrameContextCandidate`, `FramePublishedContextSource` (the shared acquisition primitive), and `locate_frame_published_context` (the frame-id cross-check) |

`GWArray` and `GwList` are shared target-memory primitives that still live under
`py4gw/context/` because the context readers were their first consumers. They
are not context-specific, and `py4gw/ui/` imports them as shared primitives.

Every pointer in these records is a fixed-width x86 `uint32` target address.
Nothing in the package creates, destroys, relabels, dispatches, or writes a
frame.

## Source evidence

Verified by reading `Py4GW_Reforged_Native`; no live client was used.

| Fact | Source |
| --- | --- |
| The client keeps a global frame array indexed by frame id | `include/GW/ui/ui.h` (`Frame`), `src/GW/ui/ui_methods.cpp:421` (`GetFrameById` indexes `(*frame_array)[frame_id]`) |
| The array global is addressable through a resolver Stealth already has | `src/GW/ui/ui_patterns.cpp:136` resolves `ui.frame_array_addr`; `offsets/ui.json:373` defines it; its anchor is the `FrMsg.cpp` / `"frame"` assertion (`offsets/ui.json:4`) |
| A frame stores its registered interaction callbacks at `Frame+0xA8` | `include/GW/ui/ui.h:448` (`frame_callbacks`) |
| Each callback entry is `{callback, uictl_context, h0008}`, 12 bytes | `include/GW/ui/ui.h:321-325` (`FrameInteractionCallback`) |
| A frame's *context* is the last non-null `uictl_context` | `src/GW/ui/ui_methods.cpp:758-773` (`GetFrameContext`) |
| The map callbacks dereference the message's `wParam` to obtain the context | `src/GW/map/map.cpp:85` and `:98` |
| The context records its owning frame id | `WorldMapContextStruct.frame_id` at `+0x0`; `MissionMapContextStruct.frame_id` at `+0x14` |
| Native itself relies on context-to-frame relations | `src/overlay/overlay.cpp:592` (`mission_map_context->frame_id` then `GetFrameById`) |
| Reforged consumes per-frame contexts this way | `Py4GWCoreLib/FrameTree/frame.py:1223` (`UIManager.get_frame_context`), archive probes logging `frame_callbacks[].uictl_context` |
| A deleted frame-array slot can hold a `0xFFFFFFFF` sentinel | `src/GW/ui/ui_methods.cpp:404-407` (`IsFrameValid`) |
| Only four pointers in the whole project require a hook | `g_world_map_context`, `g_mission_map_context` (`map.cpp:82-103`), `g_salvage_context` (`item.cpp:211-225`), `g_dx_context` (`render.cpp:75-111`) |
| The salvage session is published from a frame callback too | `src/GW/item/item.cpp:211-225` reads `*message->wParam` on `kInitFrame` and clears on `kDestroyFrame` |
| The salvage record stores its owning frame id | `include/GW/context/item.h:240-251` — `vtable` at `+0x0`, `frame_id` at `+0x4`, size `0x24` |

## The routes

Three contexts use this route. Each declares the resolver for the client's own
callback and the offset of its owning frame id; the acquisition logic is
shared.

| Context | Callback resolver | Frame-id offset | Record size |
| --- | --- | ---: | ---: |
| `WorldMapContext` | `map.world_map_ui_callback_func` | `0x0` | `0x224` |
| `MissionMapContext` | `map.mission_map_ui_callback_func` | `0x14` | `0x48` |
| `SalvageSessionInfo` | `item.salvage_popup_uicallback_func` | `0x4` | `0x24` |

The walk itself:

```text
module base
  -> ui.frame_array_addr                     (existing resolver, pattern/assertion)
  -> GWArray<Frame*> header                  (.data, 0x10 bytes)
  -> frame slot [frame_id] -> Frame*         (rejects null and 0xFFFFFFFF)
  -> Frame + 0xA8 frame_callbacks            (GWArray header)
  -> entry { callback, uictl_context }       (stride 0xC)
  -> uictl_context                           (the published context pointer)
  -> cross-check context->frame_id == frame_id
```

The frame is identified by the callback the client registered on it. The
client's own callback address comes from the matching callback resolver.

## Live results

### `MissionMapContext` — VERIFIED on a live client

Recorded 2026-09-23 against PID 29520 (`F:\GW\GW1\Gw.exe`) with the mission map
open. Read-only; nothing was written.

| Step | Observation |
| --- | --- |
| Callback resolution | `map.mission_map_ui_callback_func` -> `0x011084D0` in `.text` |
| Publishing frame | frame **1591** at `0x634931E8`, `frame_state=0x00004904`, visible and created, parent frame 2511, no children |
| Frame's callback entry | `callback[0] = 0x011084D0`, `uictl_context = 0x26404750` |
| Cross-check | the context reports `frame_id = 1591`, equal to the frame's own array index | 
| Resolved address | `0x26404750` |

The structure read back self-consistently, which is what makes this a
verification rather than a plausible pointer:

- Root `size = (387.0, 372.0)`. The raw bytes at the context start are
  `00 80 c1 43 00 00 ba 43`, i.e. `387.0f` and `372.0f`.
- Root `frame_id` is the dword `37 06 00 00` = `1591` at `+0x14`.
- Root `player_mission_map_pos = (2181.24, 3226.39)`, and the raw floats
  `d5 53 08 45` / `38 a6 49 45` at that offset match.
- `h003c = 0x2726A308` points to a `MissionMapSubContext2` whose
  `mission_map_size = (387.0, 372.0)` **equals the root's `size`**, and whose
  `player_mission_map_pos`, `mission_map_pan_offset`, and
  `mission_map_pan_offset2` all equal the root's `player_mission_map_pos`.
  `unk = 1.0`.
- `h0020` is a valid `GWArray` with `size = 2`, `capacity = 2`, and two
  subcontext entries.

The frame also registers a **second** callback, `0x0143C8B0`, whose
`uictl_context` is **null**. `GetFrameContext` walks the entries from the end
and returns the last *non-null* context, so it correctly skips that entry and
returns index 0's context. This is the first live confirmation that the
selection order in `py4gw/ui/frame.py` behaves as the native code does.

This verifies the inferred hop for `MissionMapContext`: the frame that
registers the callback publishes exactly the address that resolves to a valid,
internally consistent `MissionMapContext`. `WorldMapContext` and
`SalvageSessionInfo` use the same shared source, so their remaining question is
whether their own frames register their own callbacks when their surfaces open.

#### Close transition, same session

The operator then closed the mission map and the client was re-sampled.

| Observation | Before (open) | After (closed) |
| --- | --- | --- |
| Slot `[1591]` | `0x634931E8` | `0x5DDBACF0` — a **different** frame; the slot was reused |
| Live frames registering `0x011084D0` | frame 1591 | **none** |
| Live frames publishing `0x26404750` | frame 1591 | **none** |
| Old frame record at `0x634931E8` | valid `Frame` | freed and reused |
| Old context at `0x26404750` | valid `MissionMapContext` | freed and reused; the bytes now decode as UTF-16 text (`...%str1% ha...`) |
| Old child at `0x2726A308` | valid `MissionMapContext2` | freed and reused |

The route reported "no frame registers this callback" rather than returning the
previous address. That is the property worth recording: the walk derives the
answer from the live frame array on every read, so it cannot hand out a cached
or stale pointer. A hook that stores the pointer in its own global has to
observe the destroy message to clear it; this route structurally cannot miss
that, because the frame that published the pointer no longer exists and no
live frame claims the address.

### `WorldMapContext` — VERIFIED on a live client

Recorded 2026-09-23 against PID 29520 with the full-screen world map open.
Read-only; nothing was written.

| Step | Observation |
| --- | --- |
| Callback resolution | `map.world_map_ui_callback_func` -> `0x0110B5A0` in `.text` |
| Publishing frame | frame **3698** at `0x2630DF10`, `frame_state=0x00000944`, created and visible, parent 2511, 17 children |
| Frame's callback entry | `callback[0] = 0x0110C340`, `uictl_context = 0x4526A578` |
| Cross-check | the context reports `frame_id = 3698`, equal to the frame's own array index |
| Resolved address | `0x4526A578` |

Read-back values: `zoom = 1.0000`, `top_left = (1462.24, 2640.10)`,
`bottom_right = (2900.24, 3812.67)`. The raw leading bytes are
`72 0e 00 00` = `3698` at `+0x0`, then `4a 12 68 44` = `928.29f` and
`92 24 e9 43` = `466.29f`, then `d5 53 08 45` / `38 a6 49 45` =
`(2181.24, 3226.39)`.

That final pair is an independent cross-validation: the mission map read
earlier in the same session reported `player_mission_map_pos = (2181.24,
3226.39)` from a different context object at a different address. Two separate
structures agreeing on the player's map position is difficult to produce by
coincidence.

#### Close transition, same session

The operator then closed the world map.

| Observation | Before (open) | After (closed) |
| --- | --- | --- |
| `ui.world_map_state_addr` | `0x0008D511`, bit `0x80000` set | `0x0000D511`, bit clear |
| Slot `[3698]` | `0x2630DF10` | `0x00000000` — nulled; the frame was destroyed |
| Live frames registering the thunk or handler | frame 3698 | **none** |
| Live frames publishing `0x4526A578` | frame 3698 | **none** |
| Old frame at `0x2630DF10` | valid `Frame` | freed and reused |
| Old context at `0x4526A578` | valid `WorldMapContext` | freed and reused; the bytes now decode as the UTF-16 registry path `\REGISTRY\US...` |
| Thunk bytes at `0x0110C340` | `e9 5b f2 ff ff` | unchanged — static code is not freed |

The two close transitions differ in mechanism and the reader handles both: the
mission-map slot was reused by a different frame, while the world-map slot was
nulled. `is_valid_frame_pointer` rejects the null and the sentinel alike.

The reused allocation is the clearest argument for this route's structure. A
cached pointer would now read a registry path string and decode it as a
`WorldMapContext`; here the answer became "not published" the moment the frame
died, because the walk re-derives the pointer from the live frame array on
every read.

#### The registered callback is a jump thunk, not the resolved handler

The first attempt at this route failed: the world map was visibly open
(`ui.world_map_state_addr` had flipped to `0x0008D511`, bit `0x80000` set) yet
**no frame registered `0x0110B5A0`**. The cause is indirection:

```text
0x0110C340:  e9 5b f2 ff ff     jmp 0x0110B5A0     <- what the frame registers
0x0110B5A0:  55 8b ec ...                          <- what the signature resolves
```

The `rel32` resolves to exactly the handler address. `Gw.exe` registers a
five-byte thunk in the frame's callback entry, while the maintained signature
finds the real handler behind it.

Reforged Native never encounters this because `HookBase::CreateHook` explicitly
follows a near call or jump before installing its detour
(`src/base/hooker.cpp`, via `Scanner::FunctionFromNearCall`), so both addresses
end up hooked.

Stealth's walk now accepts either form: a direct match, or a match through
`RemoteScanner.function_from_near_call`, which `FrameTree` receives as its
`thunk_target`. `MissionMapContext` matched directly — frame 1591 registered
`0x011084D0`, the resolved address itself — which is exactly why that route
worked before this fix and the world map did not.



`python tests/probe_live_frame_contexts.py` reads every live frame's callback
entries without needing any window open, because most frames are always
present.

| Measurement | Result |
| --- | --- |
| Valid frames | 548, of which **547 register at least one callback** |
| Callback entries | 773, across **110 distinct callback addresses, all inside `.text`** |
| `uictl_context == h0008` | **0 of 540** entries where both are non-null |
| `uictl_context == Frame.field105_0x1c4` | **0** entries |
| `uictl_context` shape | Most point to objects whose first dword is a pointer into `.rdata`, i.e. vtable-bearing client objects |
| Resolved callbacks that appear live | **14 of 177** catalog `*_func` resolvers produce an address that is actually registered on a live frame |

The last row is the important one for this route. `ui.ctl_button_proc_callback_func`
resolves to `0x011D4600` and that exact address is registered on 30 live frames;
`ui.text_label_frame_callback_func` resolves to `0x011D5D60` registered on 16;
`chat.uicallback_chat_log_line_func` resolves to `0x010FFA60` registered on 15,
and so on. This confirms live that an offsets resolver for a UI callback yields
the same address the client stores in `Frame.frame_callbacks`, which is the
premise the whole route depends on.

### `SalvageSessionInfo` — the route cannot reach it; a hook is required

Recorded 2026-09-23 against PID 29520 with the operator's lesser-kit salvage
window open. The conclusion is that **this context is not reachable through the
frame array at all**, and the evidence is direct:

| Check | Result |
| --- | --- |
| `item.salvage_popup_uicallback_func` | `0x014A4980` in `.text`, real function prologue, `InteractionMessage` dispatch shape (`mov esi,[ebp+8]; mov eax,[esi+4]; cmp eax,7`) |
| Assertion anchor | `InvSalvage.cpp` / `m_toolId` at `0x014A4A85`, `-0x105` from the function start |
| Registered as a frame callback on any frame | **none** |
| Occurring **anywhere** in any frame record's `0x1C8` bytes | **none**, across 1141 scanned frames |
| The open window's own frame | frame 1718, `child_offset_id = 111` (`LesserSalvageWindow`), visible; registers `0x0145EBA0` (thunk to `0x0145E8F0`) and `0x0145F100` (thunk to `0x0145ECC0`) — neither is the resolved handler |

#### Why the two map contexts worked and this one cannot

Hooking a function only requires that the function is **called**. Reading a
pointer out of a frame requires that the address is **stored** in a frame.
Reforged Native hooks by function address, so it never depends on the
registration property; the source alone therefore cannot show which contexts
have it. Live data shows the split:

- `MissionMapContext`: the frame registers the resolved address directly.
- `WorldMapContext`: the frame registers a `jmp` thunk to the resolved address.
- `SalvageSessionInfo`: the resolved handler is **never stored in a frame**.

The salvage handler is a message handler the client invokes, not an entry in
`Frame.frame_callbacks`, so there is no frame-side path to its context.

#### Salvage is also not one window

Reforged's registry maps at least five distinct salvage surfaces by
`child_offset_id`, and Reforged handles the non-option ones by named frame
lookup rather than by any context pointer:

| Frame | `child_offset_id` | Children |
| --- | ---: | --- |
| `ScreenFrame.C6.LesserSalvageWindow` | 111 | Cancel 4, Confirm 6 |
| `ScreenFrame.C6.ExpertSalvageUnidentifiedItem` | 112 | Cancel 4, Confirm 6 |
| `ScreenFrame.C6.SalvageMaterialsDialog` | 113 | NoButton 4, YesButton 6 |
| `SalvageWindow` (top-level `Salvage`) | — | CancelButton **1**, Button **2**, Details 3, Options 5 |

Native's `SalvageSessionCancel()` clicks child **1** and `SalvageMaterials()`
clicks child **2**, which identifies `SalvageSessionInfo` as the **options
window** only. So there is no single "salvage session" context, and no frame
route would cover the flows Reforged itself drives by frame navigation.

#### Consequence: this context is not the parity target

The measurements above are correct, but they do not justify target-side code,
because `SalvageSessionInfo` turns out not to be the surface the reference
projects use for salvage:

- **Reforged Python references `SalvageSessionInfo` zero times.** A full-tree
  search returns no matches.
- **Reforged Native's shared memory never publishes it.** A search for
  `salvage` under `src/GW/shared_memory/` returns no matches, and the project's
  own handover note lists it as `(add mirror)` — an acknowledged absence.

Both projects drive salvage through **UI frames**, not through that struct:

| Reforged Python | Mechanism |
| --- | --- |
| `SalvageOptionsWindow.IsOpen()` | `Frame(FrameId.SalvageWindow).exists` |
| `IsOptionVisible(mode)` | existence of `SalvageWindow.Options.Option1..4` |
| `SelectOption(mode)` | click the option frame, then `mouse_action(8)` |
| `Cancel()` / `Confirm()` | click `SalvageWindow.CancelButton` / `SalvageWindow.Button` |
| `Inventory.AcceptSalvageMaterialsWindow()` | click `ScreenFrame.C6.SalvageMaterialsDialog.YesButton` |
| `LesserSalvageWindow` / `ExpertSalvageUnidentifiedItem` | separate frames under `ScreenFrame.C6` |

Option identity comes from **which option frames exist**, not from
`chosen_salvagable`. That makes the whole observation side read-only, and it is
already reachable with the frame tree: the live measurement found frame 1718 as
`child_offset_id = 111` (`LesserSalvageWindow`), visible, while the operator's
lesser-kit window was open.

So the correct Stealth work for salvage is **frame lookup by child-offset
path** plus a read-only "which salvage surface is open and which options
exist" reader — not a detour. `SalvageSessionInfo` stays as a source-port
declaration with its runtime acquisition marked as unused by the reference
projects.

The capture-only-while-open caveat still applies to the struct, and it is
captured on the popup's lifetime exactly as Native does it.

### Which alternatives live data eliminated

`uictl_context` is not equal to its `h0008` neighbour in any of the 540 entries
where both hold a pointer, and it is never equal to the frame's own user-param
field. Both had been open alternatives for which slot `message->wParam` points
at; live data rules both out. The mission-map frame above repeats the
elimination directly: its `uictl_context` is `0x26404750` while the same
entry's `h0008` is `0x80000000`.

### Source-verified

The frame-array global and its resolver, the `Frame` layout including
`frame_callbacks` at `+0xA8`, the 12-byte callback entry, the `GetFrameContext`
selection order, the map and salvage callbacks' `wParam` dereference, all three
`frame_id` offsets, and the sentinel handling.

### Still open

Whether the `SalvageSessionInfo` frame registers its callback when the salvage
window opens. Its frame does not exist while the window is closed. Both map
routes are now verified, and the thunk handling added for the world map also
covers the salvage route if its resolver turns out to land on a handler behind
a thunk.

### Frame-array baseline (surfaces closed)

- `ui.frame_array_addr` resolves to `0x017B896C`, and the header there reads as
  a valid `GWArray`: **5082 slots, capacity 5120**. This confirms both that the
  resolver works on this build and that the global is an inline array header,
  which was previously an interpretation rather than a measurement.
- The number of slots holding a valid frame pointer moved between runs (521 and
  then 548) as the client's UI state changed; the rest are null or the deleted
  sentinel. Only valid slots are read.
- All three callback resolvers succeed inside `.text`: `WorldMapContext`
  `0x0110B5A0`, `MissionMapContext` `0x011084D0`, `SalvageSessionInfo`
  `0x014A4980`.
- `ui.world_map_state_addr` reads `0x0000D511` with the `0x80000` bit clear
  while the world map is closed.

The frame-id cross-check is what separates a real result from a coincidence: a
candidate is accepted only when the id stored inside the context equals the
index of the frame that published it. A rejected candidate reports why, so
"the surface is closed" and "the pointer did not validate" stay distinguishable.

## Live test procedures

All of these are read-only: no hook, no payload, no patch, no remote
allocation, no remote thread, and no input sent to the client. Nothing is
modified, so there is nothing to roll back. The operator opens and closes the
in-game surface; the scripts never do.

### Three routes at once

`python tests/preflight_frame_context_route.py [--pid N] [--once] [--watch S]`

Reports, for each of the three contexts: the resolved callback and its module
section, every frame using that callback, each candidate with its cross-check
verdict and rejection reason, the read structure fields, and the independent
`ui.world_map_state_addr` visibility flag.

Without `--watch` or `--once` it re-samples each time the operator presses
Enter. With `--watch SECONDS` it polls instead and prints detail only when a
surface actually publishes a context, which is what you want when the surface
is only open briefly.

| Route | Surface the operator must open |
| --- | --- |
| `WorldMapContext` | the full-screen world map |
| `MissionMapContext` | the compact mission map panel (not the world map) |
| `SalvageSessionInfo` | the salvage window that opens when a salvage kit is used on an item |

### Salvage session (guided)

`python tests/preflight_salvage_session.py [--pid N] [--watch SECONDS]`

The salvage window only exists while it is open, so this script polls instead
of prompting at a single instant. It reports `APPEARED` the moment a session is
confirmed, prints all nine record fields plus the module section the vtable
points into, then reports `CLEARED` when the window closes. Evidence is written
as JSON, including every transition and its candidates, and the run ends with
concrete checks when nothing was confirmed.

A pass needs the `APPEARED` transition, a successful structure read, and the
`CLEARED` transition. A confirmed candidate means the cross-check passed; it
does not prove the callback dereferences the same slot, which stays inferred
until it is checked against a hook.

## Offline coverage

`python tests/test_ui_frame_offline.py` builds a synthetic x86 memory image and
runs 42 checks: the record sizes and key offsets, the full source field-name
list, the frame-state helpers, sentinel and bounds rejection, header
validation, the batched slot and callback reads, the `GetFrameContext`
selection order, parent and child recovery, callback-based frame lookup, the
frame-id cross-check in all four outcomes, each of the three routes end to end,
three routes coexisting in one frame array, and the shared acquisition
primitive's caching and rejection behavior.

## What comes next

1. Run the live tests with the surfaces open and record the builds, PIDs,
   transitions, and results in [`RESEARCH.md`](RESEARCH.md).
2. `GwDxContext` is the only remaining pointer that needs a hook
   (`src/GW/render/render.cpp:75-111`, an `EndScene`/`Reset` detour). It is not
   a frame callback and this route does not reach it, so it stays deferred
   with the game-thread and action work.
3. `FrameTree.root` derives the root from the first parentless frame. The
   native `ui.get_root_frame_func` resolver yields a *function*, which an
   external controller cannot call without target-side execution, so the
   derived root is the read-only equivalent rather than a temporary shortcut.
4. The sibling `FrameRelation.siblings` list is read through `GWList`, but
   `children_of` scans the array because that is what the native code does.
   Replace it only if a live comparison shows the scan disagrees.
5. The native `UIMessage` enum is ported only for the frame-level range; the
   `0x10000000`-and-above agent messages are not ported yet.

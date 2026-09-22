# Context migration roadmap

This is the execution order for completing the unfinished read-only Guild Wars
data surfaces. We will finish this roadmap before starting payload execution,
writes, hooks, or other control work.

**Project parity status: full source/API parity has been achieved for no
context.** The roadmap tracks independently verified external read slices and
their remaining gaps; it must not be read as a claim that a context is a
drop-in replacement for either reference project.

The source of truth for layouts remains `Py4GW_Reforged_Native` and
`Py4GW_Reforged`. Stealth adds a reader only after its pointer source, fixed
width layout, nested pointer rules, tests, and live verification are recorded.

The migration target is an exhaustive source port. Every source structure,
field, property, helper, lifecycle method, and public alias in a selected
context must be declared in Stealth, whether or not the operation is currently
available through a pure external controller. External code may replace
in-process pointer access with bounded remote reads, but it must preserve the
source relationship and observable behavior rather than inventing a new one.

The per-context parity verdict is maintained in
[`CONTEXT_PARITY_AUDIT.md`](CONTEXT_PARITY_AUDIT.md). This roadmap must not
mark a context source/API complete merely because its root layout is present.
A member can be declared but externally unavailable; that limitation is
recorded separately from declaration parity.

Injection-dependent work is frozen separately in
[`DEFERRED_INJECTION.md`](DEFERRED_INJECTION.md). This roadmap covers only
read-only external migration unless an item explicitly records a new
architecture decision.

The MapContext pathing work has its own bounded sequence in
[`PATHING_MIGRATION_PLAN.md`](PATHING_MIGRATION_PLAN.md). The first pathing
step reads context roots only; it does not create pathing snapshots or caches.

Checklist legend: `[x]` is a verified implementation of the exact named
sub-surface; `[~]` is live and useful but still has source-backed gaps; `[ ]`
is not yet migrated. `[x]` does not mean that the parent context has full
source/API parity.

This legend applies to the exact named sub-surface, not to the complete
Reforged/native context API. The current project has verified external
read-only slices, but no context should be called total source/API parity
while lifecycle, actions, semantic layers, or nested records remain absent.
See [`PARITY_STATUS_CORRECTION.md`](PARITY_STATUS_CORRECTION.md).

## Parity-completion order

After the initial reader inventory, parity work is handled one context at a
time. We do not start the next item until the current item has every source
member declared and each unavailable operation has a recorded, source-backed
reason why it cannot currently execute under the external boundary.

The first pass is:

1. `ChatBuffer`: preserve the native ring and raw encoded message payload;
   investigate the decoded-history helper and record its external limitation.
2. `MapContext`: migrate the root and directly used records, with bounded
   pointer/array reads; pathing-map records remain a separately verified
   sub-step.
3. `MissionMapContext` and `WorldMapContext`: first establish an external
   pointer source, then migrate their layouts.
4. Render/UI and other native-only surfaces only after their pointer source is
   documented.

Nested semantic work, such as the Reforged item modifier catalog, is tracked
after the context roots and is not allowed to obscure context parity.

## Completion rule for every item

An item has **declared parity** only when it has:

1. every source structure, field, property, helper, lifecycle method, and
   public alias represented with the source name and signature; and
2. an explicit status for each member: externally executable, externally
   readable, or requiring target execution/injection.

An item has **verified external availability** only when it additionally has:

3. a resolver or documented parent-pointer path;
4. fixed-width x86 structures matching the source offsets;
5. bounded handling for arrays, strings, and nested pointers;
6. a public `ConnectedClient`/`py4gw` API;
7. offline layout and safety tests;
8. a live read test; and
9. a context tab in the main inspection UI when the surface is useful to inspect.

## Order

### Phase 0 — Close existing parity gaps first

- [x] `InstanceInfo` source-compatible field aliases
- [x] `AvailableCharacterArray` source-compatible field aliases
- [x] `PartyContext` source-compatible root aliases
- [x] `AccAgentContext` source-compatible movement fields and array semantics
- [x] `TextParser` file-slot structures and bounded lookup

This phase closes small, already-understood differences before adding another
large context. Each item must update the reader, its focused tests, and the
parity audit before the next item starts.

### Phase 1 — Independent small surfaces

- [~] `FriendList` and friend records, including read-only lookups/counts;
  mutating operations remain
- [~] `ChatBuffer` and bounded chat-message reads (cached history helper
  remains)
- [~] `AccountContext` root, bounded account-array readers, and source queries;
  no direct Reforged facade
- [~] `GadgetContext` root and bounded gadget-info records; lifecycle/actions remain
- [~] `AgentArray` source category/materialization surface and corpse diagnostics;
  lifecycle/cache API remains

These do not depend on `MapContext` or `WorldContext` and provide small,
independent readers to validate the remaining migration pattern.

### ChatBuffer boundary decision

The raw chat ring and encoded message payloads are verified at the external
read-only boundary. Reforged's `Player.GetChatHistory()` is not only a memory
read: it queues `ui::AsyncDecodeStr` on the Guild Wars game thread and waits
for injected-runtime state. A live probe also showed that opening the running
client's `Gw.dat` for reading fails with Windows sharing violation error 32;
the Reforged `PyDatReader` avoids that by using in-process native code.
Stealth therefore cannot claim parity for decoded history without either a
separately validated external archive/data source or an explicitly authorized
in-process execution mechanism. The latter is injection and is outside the
current scope. The native `GWDatReader` also exposes callable archive helpers,
not an external archive/string-table object pointer. Decoded chat history is
therefore recorded as an unresolved boundary rather than approximated.

The first parity action for this item is complete: `ChatMessageStruct` now
exposes both `message_encoded_str` and `message_codepoints`, making the raw
source payload explicit. This is not display decoding. The decoded helper
remains unresolved until an external archive/data source or an explicitly
authorized in-process mechanism is available.

### Phase 2 — World root and its owned records

- [~] `WorldContext` root layout and pointer path; lifecycle API remains
- [~] world attributes, party effects, map-agent, and allied records
- [~] player, NPC, hero, and pet records with source helpers
- [~] skill bar, queued casts, and profession-state records
- [~] quest, mission-objective, title, and title-tier records
- [~] morale, player-controlled-character, agent-name, and mission-map records

The root layout, source-backed child records, and bounded array readers are
verified at the read-only boundary. Native pointer-lifecycle helpers used by
the injected runtime are intentionally excluded; the exact distinction is
recorded in the parity audit.

### Phase 3 — Items and transactions

- [~] `ItemContext` root
- [~] core `Bag` and bounded `Item` records through `ItemContext.bags`
- [~] fixed-width `Inventory` layout and relationship metadata
- [~] inventory/storage bag classification and bounded item-slot searches
- [~] item names, rarity, material/ZCoin, weapon/armor, and salvageable helpers
- [~] `ItemModifier` raw words, bit access, and native item helper rules
- [ ] Reforged semantic modifier catalog (`mods_types.py`/`mods_core.py`)
- [~] item formula and composite-model lookup helpers
- [~] cached PvP item and PvP upgrade table readers
- [~] `TradeContext` read-only root and offers; actions remain

Read operations come first. Item use, movement, salvage, trade actions, and
other writes remain outside this roadmap.

### Phase 3 decision gate

The raw `ItemContext.item_array.m_size` is not the inventory traversal
contract. Reforged's public `ItemArray.GetItemArray()` walks selected bags
through `PyInventory.Bag.GetItems()`, and the native layout provides each
`Bag.items` array. The completed item pass follows
`ItemContext -> bags -> Bag.items -> Item`, with bounded reads and live
verification. The unexplained global array remains a separate optional surface;
it is not a blocker for ordinary inventory access.

### Item modifier boundary

The native `Item` record contains an indirect modifier array: `mod_struct` is
an x86 pointer at `+0x10` and `mod_struct_size` is its element count at
`+0x14`. The element layout is the native `ItemModifier` word (`0x4` bytes).
The current item migration must preserve that pointer and count as raw item
metadata, but must not follow or decode the array yet.

Modifier work is deliberately split into two later layers:

1. a bounded external reader for the raw `ItemModifier` words; and
2. a separate semantic layer for the Reforged modifier types and identifier
   tables (`mods_types.py`/`mods_core.py`).

The raw modifier reader and the native `Item` helper rules are now migrated.
The Reforged semantic effect catalog and upgrade-name tables remain a separate
future task; they are not required to read the native context itself. The item
layout and tests still keep pointer-width, count, null-pointer, and
stale-pointer cases bounded.

### Item declarations and unused source types

The native header declares more types than the active item access path uses.
`InventoryTableEntry`, `ItemClickParam`, and `MaterialCost` still belong in
the source declaration inventory when the item context is audited. Their lack
of active consumers means that no additional external behavior should be
invented for them; it does not authorize silently deleting their declarations.
They must be recorded as declared source types with runtime status
`unresolved` or `externally unavailable` until their source relationship is
checked.

### Phase 4 — Render and UI data

- [ ] `GwDxContext` / render context
- [ ] camera-dependent render records
- [ ] UI frames, windows, controls, and tooltips

These are inspection surfaces only. This phase does not add hooks, rendering
callbacks, or UI manipulation.

The current render offsets locate functions and the window-handle pointer, but
do not provide an external `GwDxContext` object pointer. A pointer-source
decision is required before implementing the render root.

### Phase 5 — Map root and geometry

- [~] `MapContext` root, bounded spawn arrays, `PathContext`,
  `MapStaticData`, and bounded `PathingMap` root records
- [ ] map properties, terrain, and zones
- [ ] pathing-map structures and map-prop records

`MapContext` now has live-verified root readers through
`GameContext.map_context`, including the three source-defined bounded spawn
arrays, `PathContext`, `MapStaticData`, and bounded `PathingMap` root records.
The Reforged source already provides the remaining pathing chain and map-ID
caches; Stealth still needs to port child records explicitly. Python-owned
pathing snapshots and map-ID caches are explicitly deferred. See
[`PATHING_MIGRATION_PLAN.md`](PATHING_MIGRATION_PLAN.md).
`InstanceInfo` is already complete enough to stand alone and is not a
substitute for this phase.

### Phase 6 — Callback-owned map contexts

- [ ] `MissionMapContext`
- [ ] `WorldMapContext`

The current Reforged implementation receives these pointers from injected UI
callbacks/shared-memory publication. Stealth does not yet have an external
pointer source for them. This phase first requires a documented, read-only
pointer-acquisition design; the structures must not be marked complete by
copying their layouts alone.

`SalvageSessionInfo` has the same boundary: the native project owns it through
an internal global pointer, while the copied offset catalog currently exposes
actions/functions rather than a read-only external object pointer.

The pointer-publication and action/execution boundaries above are deferred;
their resume requirements are recorded in `DEFERRED_INJECTION.md`.

## Verified external read slices

The listed roots are live-verified at their implemented read boundary. That is
not the same as source parity. `TextParser`, `AvailableCharacterArray`,
`PartyContext`, `AccAgentContext`, `Camera`, `FriendList`, `AccountContext`,
and `WorldContext` now have verified external read slices. These are not total
source/API parity; omitted lifecycle, action, semantic, and nested work is
tracked in [`PARITY_STATUS_CORRECTION.md`](PARITY_STATUS_CORRECTION.md).
`ChatBuffer` remains partial according to
[`CONTEXT_PARITY_AUDIT.md`](CONTEXT_PARITY_AUDIT.md); the remaining roots are
the verified read-only surfaces named there. `MapContext` is now partial: its
root, bounded spawn arrays, and pathing context roots are implemented, while
pathing child records and map-property records remain pending.

## Dependency notes

- `AccountContext` is distributed across account-roster, account-agent, and
  world data in the Reforged Python layer; Stealth now reads its native root
  and leaves the large unlock arrays lazy.
- Agent, player, NPC, gadget, item, skill, title, and quest records may be
  reached through owning contexts. They are tracked as nested deliverables,
  not automatically treated as independent top-level contexts.
- `MapContext` and its pathing data are deliberately not the next task merely
  because their header exists; their dependency size is the reason for Phase 5.

## Current status and next decision

`InstanceInfo`, `AvailableCharacterArray`, `PartyContext`, `AccAgentContext`,
`TextParser`, `AccountContext`, `FriendList`, `WorldContext`, `AgentArray`,
`TradeContext`, `ItemContext`, and `GadgetContext` now have verified external
read-only slices. `Camera` also has a verified read-only record slice; patch
state and setter operations remain outside the boundary. These are not full
source/API parity. `ChatBuffer` remains partial, and `MapContext` is partial until its
pathing/props records are migrated. ChatBuffer's raw/encoded data is complete,
but decoded history is unresolved for the boundary reasons recorded above.
ItemContext's copied-offset read slice currently covers:
bag predicates/searches, indirect item-name reads, rarity and type
classification, material/ZCoin checks, salvageability, inventory/storage
classification, item formulas, composite-model records, storage state, and
PvP tables. The raw modifier words and native helper rules are present;
semantic modifier interpretation remains a separate deferred layer.

The core inventory path is live-verified: `Bag` and `Item` are reached through
`ItemContext.bags`, the fixed-width inventory layout is exposed, reads are
bounded, and modifier pointer/count fields are preserved without dereferencing
them. Modifier words are now read lazily through the bounded external reader;
the remaining item work is only the higher-level semantic modifier catalog,
which is tracked separately. Native action paths and salvage-session state
remain outside the current external read-only boundary. The copied offset
catalog's formula, composite-model, storage, and PvP pointer readers are
implemented and live-verified.

## Active requirements after the freeze

These are the remaining requirements that do not require reopening the
injection-dependent work:

- [~] migrate the read-only `MapContext` root, spawn records, and pathing
  context roots; pathing child and map-property records remain;
- [ ] migrate the separate Reforged semantic item-modifier catalog;
- [ ] record supported client-build/version evidence for each live reader;
- [ ] keep pointer freshness, stale-data behavior, bounded traversal, and
  diagnostics covered by tests; and
- [ ] maintain the live verification and performance records as each surface
  is completed.

The callback-owned contexts, render/UI pointer acquisition, salvage state,
decoded chat history, actions, setters, hooks, and game-thread execution are
not active requirements while the current pure-external boundary is in force.
They are tracked in [`DEFERRED_INJECTION.md`](DEFERRED_INJECTION.md).

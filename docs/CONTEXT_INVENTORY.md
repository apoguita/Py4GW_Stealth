# Context Inventory

This document is the source inventory for Guild Wars contexts. It compares
the current `Py4GW_Reforged_Native` C++ context layer with the
`Py4GW_Reforged` Python context layer, then records what has and has not been
ported to Stealth.

An inventory is not an implementation. It tells us what the native and
Reforged Python sources declare, how the two projects name each surface, and
what still needs an external reader. Every structure, field, property, and
public method in a selected context is a porting requirement even when its
operation later proves to require injection or game-thread execution.

The ordered execution roadmap is maintained in
[`docs/CONTEXT_MIGRATION_PLAN.md`](CONTEXT_MIGRATION_PLAN.md). The inventory
records status; the roadmap records what we do next and what remains blocked.
The detailed source-parity verdict for every migrated reader is maintained in
[`docs/CONTEXT_PARITY_AUDIT.md`](CONTEXT_PARITY_AUDIT.md). A reader being
listed as implemented below means that a live reader exists; consult the audit
before treating it as source/API parity.

**Full source/API parity: none.** The entries below document verified external
read slices and their gaps. No `[x]` entry makes its parent context a complete
replacement for the native or Reforged context API.

## Sources and meaning

The native inventory comes from:

```text
Py4GW_Reforged_Native/include/GW/context/
Py4GW_Reforged_Native/include/GW/context/context.h
```

The Python inventory comes from:

```text
Py4GW_Reforged/Py4GWCoreLib/native_src/context/
Py4GW_Reforged/Py4GWCoreLib/Context.py
```

The native headers are the broader source. They contain root contexts,
nested data structures, and support types. The Python package groups some of
those structures together, so the lists are not expected to match one for
one.

The native and Reforged projects are the source contract for Stealth. A source
entry is not yet a live-client result. Declaration parity and live external
availability are recorded separately; an externally unavailable member must
remain declared and be marked with its required mechanism.

## Native C++ context headers

The native context directory currently contains these 30 headers:

| Header | Main context or data surface |
| --- | --- |
| `account.h` | `AccountContext` and account character/unlock data |
| `agent.h` | `AgentContext`, agent records, effects, equipment, and snapshots |
| `attribute.h` | Attribute and party-attribute records |
| `camera.h` | `Camera` |
| `character.h` | `CharContext`, progress bars, and observer data |
| `chat.h` | Chat messages and chat buffers |
| `cinematic.h` | `Cinematic` |
| `context.h` | Root accessors and the runtime pointer snapshot |
| `friend_list.h` | `FriendList` and friend records |
| `gadget.h` | Gadget records and `GadgetContext` |
| `game.h` | `GameContext` |
| `gameplay.h` | `GameplayContext` |
| `guild.h` | `GuildContext` and guild records |
| `hero.h` | Hero flags, hero records, and related data |
| `item.h` | Item, bag, inventory, PvP, and salvage data |
| `map.h` | `MapContext`, instance, area, mission-map, and world-map data |
| `match.h` | Observer-match data |
| `npc.h` | NPC records |
| `party.h` | `PartyContext`, party members, and party search data |
| `pathing.h` | Pathing, map-prop, and prop data |
| `player.h` | Player records |
| `pregame.h` | `PreGameContext` and login-character data |
| `quest.h` | Quest and mission-objective data |
| `render.h` | `GwDxContext` render data |
| `skill.h` | Skills, skill bars, effects, buffs, and templates |
| `text_parser.h` | `TextParser` and text-cache data |
| `title.h` | Titles, tiers, and title client data |
| `trade.h` | `TradeContext` and trade records |
| `ui.h` | UI frames, windows, tooltips, and UI support records |
| `world.h` | `WorldContext` and player/world state records |

### Native root accessors

`context.h` declares these process-global accessors:

```text
GetGameContext
GetPreGameContext
GetWorldContext
GetPartyContext
GetCharContext
GetGuildContext
GetItemContext
GetAgentContext
GetMapContext
GetAccountContext
GetTradeContext
GetGameplayContext
GetTextParser
GetCamera
GetFriendList
GetMissionMapContext
GetWorldMapContext
GetSalvageSessionInfo
GetRenderContext
GetWindowHandlePtrAddress
GetControlledCharacterId
```

The native `RuntimePointersSnapshot` also records the currently resolved
addresses for the mission map, world map, gameplay, instance, map, game,
pregame, world, character, agent, guild, party, trade, item, friend, render,
text, camera, and window-handle surfaces. These are runtime pointer values;
they are not separate structure definitions.

The native implementation resolves the stable `context.base_ptr` location
once, then follows the current pointer chain when a context is requested.
This distinction matters for Stealth: the resolver location can be cached,
but dynamic context pointers must be re-read at operation boundaries because
login, map, and character state can change.

## Reforged Python context modules

The Reforged Python context directory currently contains 17 context modules
(not counting `__init__.py`):

| Module | Main public types | Public facade in `context/__init__.py` |
| --- | --- | --- |
| `AccAgentContext.py` | `AccAgentContextStruct`, `AccAgentContext` | Yes |
| `AgentContext.py` | `AgentArrayStruct`, `AgentArray`, agent and effect records | Yes |
| `AvailableCharacterContext.py` | `AvailableCharacterArrayStruct`, `AvailableCharacterArray` | Yes |
| `CharContext.py` | `CharContextStruct`, `CharContext`, observer/progress records | Yes |
| `CinematicContext.py` | `CinematicStruct`, `Cinematic` | Yes |
| `GameContext.py` | `GameContextStruct` | No direct facade import |
| `GameplayContext.py` | `GameplayContextStruct`, `GameplayContext` | Yes |
| `GuildContext.py` | `GuildContextStruct`, `GuildContext` | Yes |
| `InstanceInfoContext.py` | `InstanceInfoStruct`, `AreaInfoStruct`, `InstanceInfo` | Yes |
| `MapContext.py` | `MapContextStruct`, `MapContext` and map/pathing records | Yes |
| `MissionMapContext.py` | `MissionMapContextStruct`, `MissionMapContext` | Yes |
| `PartyContext.py` | `PartyContextStruct`, `PartyContext` | Yes |
| `PreGameContext.py` | `PreGameContextStruct`, `PreGameContext` | Yes |
| `ServerRegionContext.py` | `ServerRegionStruct`, `ServerRegion` | Yes |
| `TextContext.py` | `TextParserStruct`, `TextParser` | No direct facade import |
| `WorldContext.py` | `WorldContextStruct`, `WorldContext` and many world records | Yes |
| `WorldMapContext.py` | `WorldMapContextStruct`, `WorldMapContext` | Yes |

`Py4GWCoreLib/Context.py` exposes the higher-level `GWContext` names:

```text
AccAgent, AgentArray, AvailableCharacterArray, Char, Cinematic,
Gameplay, Guild, InstanceInfo, Map, MissionMap, Party, PreGame,
ServerRegion, World, WorldMap
```

These facades generally provide `GetPtr`, `GetContext`, and `IsValid`.
`InstanceInfo` additionally exposes map information. `GameContext.py` and
`TextContext.py` still exist as source modules even though they are not
imported as direct entries by `native_src/context/__init__.py`.

## Native-to-Python mapping

This is the practical mapping we should use when planning external readers.

| Native surface | Reforged Python source | Mapping note |
| --- | --- | --- |
| `GameContext` | `GameContext.py` | Struct source only; it also contains the pointer chain used to reach `CharContext`. |
| `PreGameContext` | `PreGameContext.py` | Direct context family. |
| `WorldContext` | `WorldContext.py` | Large aggregate containing many world/player/quest/hero/skill records. |
| `PartyContext` | `PartyContext.py` | Direct context family. |
| `CharContext` | `CharContext.py` | Direct context family; the first Stealth implementation. |
| `GuildContext` | `GuildContext.py` | Direct context family. |
| `ItemContext` | `WorldContext.py` and item/inventory wrappers | No single same-named Python context module. |
| `AgentContext` | `AgentContext.py` and `WorldContext.py` | Agent arrays and agent records are grouped in Python. |
| `MapContext` | `MapContext.py`, `InstanceInfoContext.py` | Map, area, instance, and pathing data are split across modules. |
| `AccountContext` | `AccAgentContext.py`, `AvailableCharacterContext.py`, `WorldContext.py` | Account-level data is split by use; Stealth now has a direct root reader. |
| `GadgetContext` | `AgentContext.py` and agent helpers | Native root has a direct Stealth reader; gadget-agent records remain under `AgentArray`. |
| `TradeContext` | trade wrappers outside this directory | No direct `TradeContext.py` module in the inspected directory. |
| `GameplayContext` | `GameplayContext.py` | Direct context family. |
| `TextParser` | `TextContext.py` | Exists as a source module but is not a direct `context/__init__` import. |
| `Camera` | camera wrappers outside this directory | Reforged exposes camera through other library surfaces. |
| `FriendList` | friend wrappers outside this directory | No direct same-named context module. |
| `MissionMapContext` | `MissionMapContext.py` | Direct context family. |
| `WorldMapContext` | `WorldMapContext.py` | Direct context family. |
| `SalvageSessionInfo` | item/salvage wrappers | Native accessor has no same-named Python context module. |
| `GwDxContext` | render wrappers outside this directory | Native render surface, not a direct context module. |
| window handle / controlled character ID | library/runtime helpers | Scalar accessors, not structure contexts. |

The important consequence is that “add all contexts” means covering the
native surfaces and their nested data, not copying 30 headers into 17 Python
files. Some Stealth readers will correspond to a Reforged module; others will
be a small reader assembled from a native root plus structures that Reforged
keeps in another module.

## Stealth status

### Verified external read slices (not full source parity)

- `Win32`: read-only process discovery and module information.
- `ProcessMemoryReader`: bounded read-only `ReadProcessMemory` transport.
- `RemoteScanner`: PE section discovery and remote pattern scanning.
- `PatternCatalog`: copied JSON signatures and resolver chains.
- `ConnectedClient`: selected-process ownership and connection state.
- `context.CharContext`: external `CharContextStruct`, pointer-chain read,
  character-name decoding, `GWArray` views, and the declared source facade
  methods; callback registration remains externally unavailable.
- `context.GameContext`: external root context, cached base-pointer resolver,
  and additive aliases for the native C++ field spellings.
- `context.PreGameContext`: optional selection-menu context and login-character
  array.
- `context.Cinematic`: optional 8-byte context reached through
  `GameContext.cinematic`.
- `context.GameplayContext`: optional gameplay structure with the maintained
  mission-map zoom field.
- `context.ServerRegion`: signed 32-bit server-region value resolved from
  `map.region_id_addr` and cached for the connection.
- `context.InstanceInfo`: map-instance structure resolved from
  `map.instance_info_addr`, with external nested `MapDimensions` and
  `AreaInfo` reads.
- `context.TextParser`: native `GameContext.text_parser` pointer at `+0x18`,
  the complete fixed-width root layout, typed `LanguageSlotStruct` and
  `TextFileSlotStruct` records, bounded language-slot/file-slot traversal,
  file-hash lookup, language ID, cache pointer, and sub-structure reads.
  This matches the source-backed read-only surface used by the Reforged
  text-parser code.
- `context.AvailableCharacterArray`: native account-roster `GWArray` resolved
  through `player.available_characters_addr`, with packed character properties.
- `context.PartyContext`: direct `GameContext.party` pointer, exact native
  party/member/search structures, nested arrays, bounded invite/request/
  sending-list readers, source aliases, and the declared static facade cache.
- `context.GuildContext`: direct `GameContext.guild` pointer, complete
  maintained guild layout, and nested guild, history, alliance, and roster
  array readers.
- `context.AccAgentContext`: direct `GameContext.agent` pointer, maintained
  agent-summary and movement layouts, and bounded remote array readers.
- `context.Camera`: JSON-resolved native camera pointer and the maintained
  read-only camera layout through `camera_mode`.
- `context.FriendList`: JSON-resolved friend-list root, bounded friend-pointer
  traversal, and decoded friend records.
- `context.ChatBuffer`: JSON-resolved chat ring-buffer pointer, bounded message
  header/payload reads, and typing-state inspection.
- `context.WorldContext`: the maintained 0x854-byte root layout reached through
  `GameContext.world_context`, all source-backed read-only child records, and
  bounded `GWArray` traversal. The injected-runtime pointer lifecycle helpers
  are intentionally excluded.
- `context.TradeContext`: direct `GameContext.trade_context` root with bounded
  player/partner gold and offered-item reads. Trade actions remain out of
  scope.
- `context.ItemContext`: direct `GameContext.item_context` root with the
  maintained 0x10C layout, bounded core bag/item readers, and fixed-width
  inventory relationship metadata. The live raw `item_array.m_size` header is
  not verified as an inventory-item count. Reforged's public item enumeration is
  Stealth follows `ItemContext -> bags -> Bag.items -> Item` for bounded
  item reads. The unexplained global array is a separate optional surface, not
  a blocker for ordinary inventory access. A recent live run read 24 bags and
  352 item records; these counts are observations, not fixed contracts.
  Native item records expose bounded modifier-word reads and the native bit
  helpers (uses, tome/kit, and rare-material rules). The higher-level
  Reforged semantic modifier catalog remains a separate pending feature. The
  formula/composite/PvP tables are read through cached JSON resolvers.
- `context.AccountContext`: direct `GameContext.account_context` root with the
  maintained 0x138 layout and account-wide array-header inspection. Child
  unlock records remain lazy and bounded.
- `context.GadgetContext`: direct `GameContext.gadget_context` root with the
  maintained 0x10 layout and a bounded lazy `GadgetInfo` reader.

The current 21 Stealth reader classes (including `AgentArray`) have live
verification at their implemented read boundary. Resolver
scans are
performed during connection and stable resolver locations are cached; dynamic
context pointers and structure bytes are re-read for each snapshot. The
camera resolver currently returns the native camera object pointer itself, so
that pointer is cached for the lifetime of the connection while its bytes are
read afresh. `FriendList` uses the same direct-object resolver model. The
ChatBuffer resolver caches its global pointer slot and re-reads the current
buffer pointer for each snapshot.

The migration sequence so far is: `CharContext`, `GameContext`,
`PreGameContext`, `Cinematic`, `GameplayContext`, `ServerRegion`,
`InstanceInfo`, `TextParser`, `AvailableCharacterArray`, `PartyContext`,
`GuildContext`, `AccAgentContext`, `Camera`, `FriendList`, `ChatBuffer`, then
the verified read-only `WorldContext`, `TradeContext`, `ItemContext` root,
`AccountContext`, and `GadgetContext`, followed by the `MapContext` root and
bounded spawn arrays. The live GuildContext check resolved
address `0x00AD42A0` and
read player `Fezzik The Untamed`, 243 guild records, 42 roster entries, and 20
history entries on the verified client build.
The same client resolved `AccountContext` at `0x0257EBC8` with six maintained
array headers and `GadgetContext` at `0x0256FFB0` with 9,500 advertised gadget
records; the live test read only a bounded 32-record sample.
`WorldMapContext` remains pending because its source pointer
is published by injected UI callback/shared-memory state rather than a
currently available external resolver.

### Remaining or incomplete in Stealth

The remaining native and Reforged contexts listed above either do not yet have
an external Stealth reader or have a partial reader. The offsets directory may
already contain signatures for several surfaces, but a signature definition
alone is not a context reader. The exact missing source-backed fields and
helpers for existing readers are listed in
[`CONTEXT_PARITY_AUDIT.md`](CONTEXT_PARITY_AUDIT.md).
Each new reader still needs:

1. a documented root-address resolver;
2. a fixed-width external structure definition;
3. explicit pointer and array follow rules;
4. a public context API and connection-lifetime behavior; and
5. offline tests plus a separately recorded live-client verification.

The next implementation decision follows
[`docs/CONTEXT_MIGRATION_PLAN.md`](CONTEXT_MIGRATION_PLAN.md). It should not be
inferred from the number of files in either source project.

## Migration complexity categories

These categories are planning estimates based on the inspected Reforged
module size, number of nested structures, number of remote pointers/arrays,
and whether the context has its own resolver. They are not claims about live
performance.

### Simple candidates

The previously selected simple candidates are now implemented. The remaining
small callback-owned contexts are not resolver-backed external candidates:

- `MissionMapContext.py` has a small layout, but its pointer is gathered by a
  UI callback in the native DLL.

### Moderate candidates

These contain several arrays or related records, but are still bounded enough
to migrate as one focused task:

- `AccAgentContext.py` (implemented and live-verified)
- `PreGameContext.py` (already migrated)
- `CharContext.py` (already migrated)

### Complex candidates

These aggregate many independently meaningful structures and should be left
until the smaller roots are available:

- `MapContext.py` has a live root/spawn slice and the first pathing context
  roots; its first-class pathing migration is tracked in
  [`PATHING_MIGRATION_PLAN.md`](PATHING_MIGRATION_PLAN.md). Graph children and
  map-prop traversal remain pending.
- `WorldContext` has a verified read-only slice; its native injected
  pointer-lifecycle helpers remain intentionally out of scope.
- `AgentContext.py` has a verified read-only external category/materialization
  surface; injected cache lifecycle helpers remain intentionally out of scope.

The remaining native-only or distributed surfaces (render, UI, salvage, and
related records) should be scheduled after the root context that owns their
pointers is understood. Item children are not in that category: their native
bag and item pointers are already owned by `ItemContext` and are the next
focused migration. `WorldMapContext` and `MissionMapContext` are separately
tracked as callback-owned contexts below; they are not treated as ordinary
JSON-resolver readers.

The resolver-backed moderate candidates are now implemented; callback-owned
contexts remain postponed until their pointer source is explicitly in scope.

## Migration checklist

This is the working checklist for adding external readers. A checked item
means the named reader has a live verification record. `[~]` means the reader
works but source-parity gaps remain; those gaps are not approved to disappear
from the roadmap.
The distinction between a verified external read slice and full source/API
parity is recorded in
[`PARITY_STATUS_CORRECTION.md`](PARITY_STATUS_CORRECTION.md).

### Verified external read slices (not full source parity)

- [~] `CharContext` external read-only slice (lifecycle API remains)
- [~] `GameContext` / base context pointer surface (verified root slice; no total context parity)
- [~] `PreGameContext` declaration parity complete; external read path verified;
  callback registration remains externally unavailable
- [~] `Cinematic` declaration parity complete; external pointer/read path
  verified; callback registration remains externally unavailable
- [~] `GameplayContext` declaration parity complete; external pointer/read path
  verified; callback registration remains externally unavailable
- [~] `ServerRegion` declaration parity complete; external value-address/read
  path verified; callback registration remains externally unavailable
- [~] `InstanceInfo` declaration parity complete; external root/nested read
  path verified; callback registration remains externally unavailable
- [~] `TextParser` declaration parity complete; external root/slot/cache read
  path verified; callback and string-table trigger remain externally unavailable
- [~] `AvailableCharacterArray` declaration parity complete; external roster
  resolver/read path verified; callback registration remains unavailable
- [~] `PartyContext` declaration parity complete; external root, member/search,
  list, and helper reads verified; callback registration remains unavailable
- [~] `GuildContext` declaration parity complete; external root, guild,
  alliance, history, roster, and helper reads verified; callback registration
  remains unavailable
- [~] `AccAgentContext` external read-only slice (lifecycle API remains)
- [~] `Camera` external read-only slice (setters/patch state excluded)
- [~] `FriendList` external read-only slice (mutations excluded)
- [~] `ChatBuffer` (raw encoded message text/codepoints work; decoded history helper is missing)
- [~] `AccountContext` external consumer slice (no direct Reforged facade)
- [~] `GadgetContext` external read-only slice (lifecycle/actions remain)
- [~] `TradeContext` root and bounded offers (actions remain)
- [~] `ItemContext` root, bounded bag/item traversal, empty-slot searches,
  item names, rarity/type/material/salvage helpers, inventory/storage
  classification, bounded native modifier-word reads and helper rules, and
  formula/composite/PvP table readers (semantic modifier catalog remains
  separate)
- [~] `WorldContext` root and verified source-backed read-only child records
- [~] `MapContext` root, three bounded spawn arrays, and pathing context roots
  (graph children and map-prop records remain)

### Pending: simple contexts

No resolver-backed simple context is currently selected. The callback-owned
map contexts remain listed separately below.

### Pending: callback-owned contexts

- [ ] `WorldMapContext` (native UI callback publishes the pointer)
- [ ] `MissionMapContext` (native UI callback publishes the pointer)

These remain deferred until an external pointer source is defined. The full
injection-dependent freeze and resume conditions are in
[`DEFERRED_INJECTION.md`](DEFERRED_INJECTION.md).

### Pending: moderate contexts

No pending moderate context is currently selected.

### Pending: complex contexts

- [~] `MapContext` root/spawn and pathing-context slice; graph children and
  map-prop records remain. See
  [`PATHING_MIGRATION_PLAN.md`](PATHING_MIGRATION_PLAN.md).
- [~] `AgentContext` and `AgentArray` read-only records and category helpers
  (lifecycle/cache API remains)

`AgentArray` has a live-verified source-shaped view: bounded external
pointer-table traversal, native `agent_id` validation, movement-table stale
filtering, source category methods, and explicit raw-record materialization.
Core common, living, item, and gadget records have lazy live readers. A full
living-agent record can also be refreshed into a local snapshot for frequent
queries, including corpse diagnostics, effects, visible effects, equipment,
and tags. Injected cache lifecycle helpers remain outside the external
read-only boundary.

### Pending: native-only or distributed surfaces

- [ ] Native-only or distributed surfaces: deferred modifier catalog semantics, render,
  UI, remaining gadget relationships, and pathing data.

The final line is intentionally grouped. Those native headers contain many
records that may be reached through another root context rather than through
a separate top-level pointer. They should be split into individual tasks
only after their owning root and pointer relationships are verified.

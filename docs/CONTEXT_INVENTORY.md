# Context Inventory

This document is the source inventory for Guild Wars contexts. It compares
the current `Py4GW_Reforged_Native` C++ context layer with the
`Py4GW_Reforged` Python context layer, then records what has and has not been
ported to Stealth.

An inventory is not an implementation. It tells us what the native and
Reforged Python sources declare, how the two projects name each surface, and
what still needs an external reader. Every structure, field, property, and
public method in a selected context is a porting requirement even when its
operation later proves to need in-client execution on the game thread.

The reader migration order is recorded in [`docs/DESIGN.md`](DESIGN.md); this
inventory records status. The detailed source-parity verdict for every migrated
reader is maintained in
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
entry is not yet a live-client result. Declaration parity and live
availability are recorded separately; a member whose mechanism is not ported must
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

`context.h` also declares `RuntimePointersSnapshot`, a shared-pointer snapshot
for native runtime plumbing. It is not an in-game context structure; external
handling of those pointers remains outside this context-parity work.

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
| `GwDxContext` | `render_context.py` | Native structure declared; pointer is populated by render-hook code and remains unresolved externally. |
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
  methods; callback registration is not ported.
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
- `context.PlayerAgentId`: the game global holding the player's agent id,
  resolved from `agent.player_agent_id_addr`. The resolved value is a stable
  `.data` address and the id is read fresh per call, matching native
  `Context::GetObservingId()`.
- `context.InstanceInfo`: map-instance structure resolved from
  `map.instance_info_ptr_ref`. The cached value is the address of the pointer and
  the structure is dereferenced per read, because the pointer is map-scoped; a
  null pointer reads as `InstanceType.LOADING`. See
  [`READINESS_GATE.md`](READINESS_GATE.md).
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
  summary and movement layouts, source array properties, native field aliases,
  and facade declarations. The native `AgentInfoArray` type has no pointer
  relationship in the context root or getter implementation.
- `context.Camera`: JSON-resolved native camera pointer and the maintained
  read-only camera layout through `camera_mode`.
- `context.FriendList`: JSON-resolved friend-list root, bounded friend-pointer
  traversal, and decoded friend records.
- `context.ChatBuffer`: JSON-resolved chat ring-buffer pointer, bounded message
  header/payload reads, and typing-state inspection.
- `context.WorldContext`: the maintained 0x854-byte root layout reached through
  `GameContext.world_context`, all source-backed read-only child records, and
  bounded `GWArray` traversal. The injected-runtime pointer lifecycle helpers
  are not yet ported.
- `context.TradeContext`: direct `GameContext.trade_context` root with bounded
  player/partner gold and offered-item reads. Trade actions are not yet ported.
- `context.ItemContext`: direct `GameContext.item_context` root with the
  maintained 0x10C layout, every declared native item-context record (including
  `ItemData`), the `ItemArray`/`MerchItemArray` header aliases, and inventory
  union views. Stealth follows `ItemContext -> bags -> Bag.items -> Item` for
  bounded item reads. The live raw `item_array.m_size` header is not verified
  as an inventory-item count; the unexplained global array remains optional.
  Bag searches preserve native slot indexes and `npos`; item helpers preserve
  native method names, and modifier reads are on demand. A recent live run read
  24 bags and 352 item records; these counts are observations, not fixed
  contracts. Formula/composite/PvP tables use cached JSON resolvers. The
  separate Reforged semantic modifier catalog remains pending.
- `context.AccountContext`: direct `GameContext.account_context` root with the
  maintained 0x138 layout and account-wide array-header inspection. Child
  unlock records remain lazy and bounded.
- `context.GadgetContext`: direct `GameContext.gadget_context` root with the
  maintained 0x10 layout. The default `GadgetInfo` read returns the complete
  advertised array in one bounded memory read; callers may request a smaller
  sample explicitly, and arrays above the 16 MiB safety ceiling fail rather
  than being silently clipped.

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
bounded spawn arrays. The source data ports for callback-owned
`MissionMapContext` and `WorldMapContext` are also complete, and both now acquire
their root through the client's UI frame array, live-verified open and closed. The live GuildContext check resolved
address `0x00AD42A0` and
read player `Fezzik The Untamed`, 243 guild records, 42 roster entries, and 20
history entries on the verified client build.
The same client resolved `AccountContext` at `0x0257EBC8` with six maintained
array headers. The latest live GadgetContext check resolved `0x00AC41D8` and
read all 9,500 of its 9,500 advertised records. These addresses and counts are
observations for that running client, not fixed values.
`MissionMapContext` and `WorldMapContext` have source-matched structures and
address-supplied readers, including their source data properties. Their ports
are complete at that boundary, and the pointer side is no longer missing: the
frame-array route reaches the same addresses the source's callback publishes,
without a hook, and both were verified live with the surface open and closed.

### Remaining or incomplete in Stealth

Remaining work in the in-game context scope is limited to source-backed fields
and helpers identified in the parity audit. A callback-owned context is still
ported when its source structures and read properties are implemented against
a caller-supplied address; finding that address and live-testing it are
separate runtime-availability tasks. A signature definition alone is not a
context reader. The exact missing source-backed fields and helpers for
existing readers are listed in
[`CONTEXT_PARITY_AUDIT.md`](CONTEXT_PARITY_AUDIT.md).
Each context reader still needs:

1. a documented root-address path: a resolver when known, or a supplied
   address when the source's own acquisition path is not ported;
2. a fixed-width external structure definition;
3. explicit pointer and array follow rules;
4. a public context API and connection-lifetime behavior; and
5. offline source-port tests; live-client verification is recorded when its
   pointer source is available and is not a prerequisite for callback-owned
   structure/read-property parity.

The next read-only context-migration work follows the gap list in
[`CONTEXT_PARITY_AUDIT.md`](CONTEXT_PARITY_AUDIT.md), which now carries a
mechanical field-level sweep of every source context struct. Callback-owned map
pointers now have a read-only route: both are resolved through the frame
array, per [`UI_FRAME_TREE.md`](UI_FRAME_TREE.md). The remaining target-side
work is tracked in [`NATIVE_EXECUTION_PLAN.md`](NATIVE_EXECUTION_PLAN.md).

## Migration complexity categories

These categories are planning estimates based on the inspected Reforged
module size, number of nested structures, number of remote pointers/arrays,
and whether the context has its own resolver. They are not claims about live
performance.

### Simple candidates

The previously selected simple candidates and callback-owned context data
ports are implemented. Their root-address sources are still outstanding work:

- `MissionMapContext.py` and `WorldMapContext.py` have source-matched
  structures and supplied-address readers; their callback-published root
  addresses have not been independently obtained.

### Moderate candidates

These contain several arrays or related records, but are still bounded enough
to migrate as one focused task:

- `AccAgentContext.py` (implemented and live-verified)
- `PreGameContext.py` (already migrated)
- `CharContext.py` (already migrated)

### Complex candidates

These aggregate many independently meaningful structures and should be left
until the smaller roots are available:

- `MapContext.py` now reads pathing arrays/links and reachable props. The
  source-defined SinkNode pointer/list helpers are represented and
  offline-tested, but the Reforged snapshot leaves `sink_nodes` empty and no
  active consumer was found in the searched source. The live target exposes
  direct pointers into trapezoid arrays, so Stealth preserves the raw values
  and does not apply those unused helpers. This discrepancy is documented,
  not treated as an active read-data gap; offline tests do not validate
  that the unused source interpretation matches the client. Source-named facade/cache helpers
  are live-tested and caches are PID-scoped. Automatic callback registration
  is not ported; see
  [`PATHING_MIGRATION_PLAN.md`](PATHING_MIGRATION_PLAN.md).
- `WorldContext` has a verified read-only slice; its native injected
  pointer-lifecycle helpers are not yet ported.
- `AgentContext.py` has a verified read-only external category/materialization
  surface; injected cache lifecycle helpers are not yet ported.

Other native-only or distributed surfaces (the separate UI support API,
salvage state, and related records) are outside this context port. Item
children are not a separate surface: their native bag and item pointers are
already represented under `ItemContext`.
`WorldMapContext` and `MissionMapContext` are separately tracked as
callback-owned contexts below; native `map.cpp` receives their object pointers
from UI callback messages, not from an identified context signature. They are
not treated as ordinary JSON-resolver readers. The agreed research path for
Stealth-owned access to these callback-published pointers is documented in
[`CALLBACK_POINTER_RESEARCH.md`](CALLBACK_POINTER_RESEARCH.md).

Resolver-backed moderate readers are implemented. The callback-owned map
contexts now have source-matched address-based readers. Their data ports are
done, and the root addresses are obtained through the client's own UI frame
array rather than the source's callback; both are live-verified open and closed.
The hook-based route was not built, and is not needed for these two. See
[`CALLBACK_POINTER_RESEARCH.md`](CALLBACK_POINTER_RESEARCH.md).

## Migration checklist

This checklist separates source porting from live availability. `[x]` means
the named structure/read surface has been ported and checked at its supported
boundary; that check may be offline when no target address is available. Live
verification is stated separately. `[~]` means source-parity gaps remain;
those gaps are not approved to disappear from the roadmap.
The distinction between a verified external read slice and full source/API
parity is recorded in
[`PARITY_STATUS_CORRECTION.md`](PARITY_STATUS_CORRECTION.md).

### Verified external read slices (not full source parity)

- [~] `CharContext` external read-only slice (lifecycle API remains)
- [~] `GameContext` / base context pointer surface (verified root slice; no total context parity)
- [~] `PreGameContext` declaration parity complete; external read path verified;
  callback registration is not ported
- [~] `Cinematic` declaration parity complete; external pointer/read path
  verified; callback registration is not ported
- [~] `GameplayContext` declaration parity complete; external pointer/read path
  verified; callback registration is not ported
- [~] `ServerRegion` declaration parity complete; external value-address/read
  path verified; callback registration is not ported
- [~] `InstanceInfo` declaration parity complete; external root/nested read
  path verified; callback registration is not ported
- [~] `TextParser` declaration parity complete; external root/slot/cache read
  path verified; the callback and the string-table trigger are not ported
- [~] `AvailableCharacterArray` declaration parity complete; external roster
  resolver/read path verified; callback registration is not ported
- [~] `PartyContext` declaration parity complete; external root, member/search,
  list, and helper reads verified; callback registration is not ported
- [~] `GuildContext` declaration parity complete; external root, guild,
  alliance, history, roster, and helper reads verified; callback registration
  is not ported
- [~] `AccAgentContext` declaration parity complete; root, summary, movement,
  and source-array reads verified; callback registration not ported; the
  separate native `AgentInfoArray` pointer source is unresolved
- [~] `Camera` declaration parity complete; read facade verified; the source's
  game-thread actions are declared but not yet ported
- [~] `FriendList` declaration parity complete; read-only records verified;
  game-thread mutations are declared but not yet ported
- [~] `ChatBuffer` declaration parity complete; raw encoded ring verified;
  decoded `PyPlayer.GetChatHistory` is a separate API
- [~] `AccountContext` native root/nested structs match source names/order and
  checked x86 sizes/offsets; bounded read path verified. No same-named Reforged
  Python context module exists in the inspected source tree.
- [~] `GadgetContext` native root and gadget-info records match source names,
  order, and x86 sizes; the direct root path and complete live array traversal
  are verified. The array uses a 16 MiB explicit ceiling and does not silently
  truncate. Reforged has no separate same-named context facade in the inspected
  source tree.
- [~] `TradeContext` native structs match names/order, sizes, offsets, and flag
  helpers; bounded external offer reads verified. No direct same-named Reforged
  Python context module exists in the inspected source tree.
- [~] `ItemContext` native structure declarations, including `ItemData`,
  `ItemArray`/`MerchItemArray` aliases, source-only records, and union views,
  match source names/order and checked x86 sizes/offsets. `InventoryTableEntry`
  remains declaration-only. Bag/item reads and native helpers are verified;
  the external copied-record behavior and the not-yet-ported in-game actions remain
  explicit adaptations/limitations.
- [~] `WorldContext` struct declarations match all 30 Reforged structures by
  class and field-name/order. Empty-array results, buffer shapes, player
  lookup, and source value types are aligned; live checks confirm every root
  array is fully returned for the tested client. Callback lifecycle and exact
  live-value comparison remain unresolved.
- [~] `MapContext`: source-matched declarations, all advertised pathing arrays,
  links, props, blocking props, source snapshots, and travel-portal helper are
  implemented and live-verified. SinkNode source pointer/list helpers are
  represented and offline-tested, but the current Reforged snapshot leaves
  `sink_nodes` empty and no active consumer was found. The tested client has
  direct pointers into trapezoid arrays; Stealth preserves those raw values
  without applying the unused helpers. Source helper names and cache behavior
  are implemented; automatic in-client callback registration is not yet ported.

### Callback-owned context runtime availability

- [x] `MissionMapContext`: all three source structures, `subcontexts` and
  `subcontext2` data properties, supplied-address root reader, and public
  connection reader are ported and offline-tested.
- [x] `WorldMapContext`: complete source structure and supplied-address root
  reader are ported and offline-tested.

Both roots are obtained and live-verified through the client's UI frame array,
which publishes the same addresses the source's callback does, so their context
data ports and their pointer watch both stand.
The callback registration is not yet ported, and it is not a reason to omit the
context structures or readers.

`GwDxContext` is a native render-state record and is not part of the required
in-game context migration.

### Pending: moderate contexts

No pending moderate context is currently selected.

### Pending: complex contexts

- [~] `MapContext` root, pathing arrays/links, props, snapshots, travel
  portals, facade helpers, and PID-scoped caches are implemented; automatic
  callback registration is not ported. See
  [`PATHING_MIGRATION_PLAN.md`](PATHING_MIGRATION_PLAN.md).
- [~] `AgentContext` / `AgentArray`: native root is already covered by
  `AccAgentContext`; the global array and external record reader are live
  verified. Agent/equipment/effect/tag record declarations, source value
  dataclasses, snapshot conversions, and `AgentArrayStruct` helper names are
  now ported. Its context gate reads the corresponding external context
  readers; its agent cache uses remote reads rather than Reforged's in-process
  pointers. Declaration parity is certified; callback registration is not
  ported. The wider `Agent.py` helpers are a separate,
  unaudited surface. See the certification record for exact scope.

`AgentArray.read()` has a live-verified bounded external view: pointer-table
traversal, native `agent_id` validation, movement-table stale filtering,
category methods, and lazy common/living/item/gadget record reads. The
source-shaped `read_context()` additionally applies Reforged's context gate
and builds a cache of accepted common records through remote reads. A complete
living-agent refresh is available for frequent queries, including effects,
visible effects, equipment, and tags. In AgentArray's equipment view,
Reforged's Python `ItemDataStruct` and native `ItemData` layouts differ; both
are represented explicitly, and live reads use the native layout. ItemContext
also declares the native `ItemData` from `item.h`. The Python living record is
two bytes shorter than native;
both layouts are declared separately. The native root itself is the
`AccAgentContext` root, not a second structure.

### Pending: native-only or distributed surfaces

- `GwDxContext` is native render state, not a required in-game context
  migration item.
- [ ] Remaining MapContext callback-cache parity. SinkNode helper usage is not
  an active data-reading gap: the current Reforged snapshot leaves the list
  empty, no active consumer was found, and Stealth preserves the live raw
  field without applying the unused pointer-list helpers.

The final line is intentionally grouped. Those native headers contain many
records that may be reached through another root context rather than through
a separate top-level pointer. They should be split into individual tasks
only after their owning root and pointer relationships are verified.

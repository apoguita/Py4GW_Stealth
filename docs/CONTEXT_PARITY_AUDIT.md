# Context parity audit

This is the detailed inventory of the context work currently present in
Stealth. It compares the active implementations in:

- `C:\Users\Apo\Py4GW_Reforged_Native\include\GW\context\` and
  `src\GW\context\context_methods.cpp`;
- `C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\native_src\context\`; and
- the Reforged Python wrappers that actually consume item, agent, camera,
  friend, chat, and trade data.

The native and Reforged projects are the source authority for this audit.
Stealth's tests and live observations establish whether the external reader
currently works; they do not establish source/API parity. The earlier reports
used “complete” too broadly for several read-only slices.
The correction and exact omissions are recorded in
[`PARITY_STATUS_CORRECTION.md`](PARITY_STATUS_CORRECTION.md). No context is
currently claimed as total source/API parity.
The binary certification procedure is in
[`PARITY_CERTIFICATION_CHECKLIST.md`](PARITY_CERTIFICATION_CHECKLIST.md).

**Full source/API parity: none.** Every reader listed here is either a
verified external read slice, a partial migration, a scoped boundary, or a
pending surface. A live read proves only the listed slice for the tested
client build; it does not make the corresponding Reforged/native context
complete.

## Status meanings

| Status | Meaning |
| --- | --- |
| **Verified read slice** | The named fixed layout and read-only fields/helpers have a Stealth live-read record. This is not total source/API parity. |
| **Partial** | The root or a useful subset works, but source-backed fields, nested records, properties, or helpers are still missing. |
| **Scoped** | The source surface is understood but deliberately excluded by the current read-only/external boundary. It is not silently counted as migrated. |
| **Pending** | No Stealth reader exists yet, or the source does not currently provide an external pointer path. |

“Verified” applies only to the named read slice in the table, not to every
function in the entire Reforged automation library or to the parent context.

Declaration parity and runtime availability are separate columns of the work:
every source field, property, helper, lifecycle method, and mutating method
must exist in the Stealth API. When an operation requires target execution or
injection, it remains declared and is marked externally unavailable; it is not
silently omitted from the port.

## Summary

**Full source/API parity: none.** The list below is an implementation-status
inventory, not a parity score.

Stealth currently contains 21 context reader classes, counting `AgentArray`.
The count is not a parity score:

- **Verified external read slices:** `CharContext`, `GameContext`,
  `PreGameContext`, `Cinematic`, `GameplayContext`, `ServerRegion`,
  `InstanceInfo`, `PartyContext`, `AccAgentContext`, `GuildContext`,
  `TradeContext`, `TextParser`, `AccountContext`, `FriendList`, `Camera`,
  `WorldContext`, `ItemContext`, `AgentArray`, and the `GadgetContext` root.
- **Partial:** `ChatBuffer` and the `MapContext` root/pathing-context slice.
- **Pending:** the remaining `MapContext` pathing/props records,
  `MissionMapContext`, `WorldMapContext`, render,
  UI, and the native-only salvage state.

The read-slice list is not a parity score. Missing source-backed lifecycle,
actions, helpers, semantic layers, and nested records are named in the table
and in [`PARITY_STATUS_CORRECTION.md`](PARITY_STATUS_CORRECTION.md).

## Migrated context inventory

| Stealth reader | Native source | Reforged source or caller | Status | What is present | What is missing or intentionally different |
| --- | --- | --- | --- | --- | --- |
| `CharContext` | `character.h`, `GetCharContext()` | `CharContext.py` | **Declaration parity PASS; runtime scoped** | Full maintained `CharContextStruct`, observer matches, progress bar, fixed strings, arrays, the GameContext pointer path, and the source facade methods. | `enable` cannot register the in-process callback from a pure external controller; it remains declared and reports an explicit unsupported operation. |
| `GameContext` | `game.h`, `GetGameContext()` | `GameContext.py` | **Declaration parity PASS; runtime externally verified** | Full fixed-width root, native C++ field aliases, and cached base resolver. | No missing source declaration was identified; C++ `void*` fields are represented as fixed-width target addresses. |
| `PreGameContext` | `pregame.h`, `GetPreGameContext()` | `PreGameContext.py`, `PreGameContext.pyi` | **Declaration parity PASS; runtime externally verified** | Full layout and login-character array, character-name helpers, source facade members, and remote array binding. | The source callback registration/shared-memory publication cannot execute in the pure external controller; the declarations remain present and report that limitation explicitly. |
| `Cinematic` | `cinematic.h`, `game.h` `cinematic` field | `CinematicContext.py`, `CinematicContext.pyi` | **Declaration parity PASS; runtime externally verified** | Full 8-byte structure, source facade members, and `GameContext.cinematic` pointer relationship. | The source callback/shared-memory publication cannot execute in the pure external controller; declarations remain present and report that limitation explicitly. |
| `GameplayContext` | `gameplay.h`, `context_methods.cpp` global pointer | `GameplayContext.py`, `GameplayContext.pyi` | **Declaration parity PASS; runtime externally verified** | Full `0x78`-byte structure, source facade members, resolver, and mission-map zoom field. | The source callback/shared-memory publication cannot execute in the pure external controller; declarations remain present and report that limitation explicitly. |
| `ServerRegion` | `context.cpp`, `context_methods.cpp`, `GetRegionIdPtr()` | `ServerRegionContext.py`, `ServerRegionContext.pyi` | **Declaration parity PASS; runtime externally verified** | Four-byte signed region value, source facade members, and cached JSON resolver. | The source callback/shared-memory publication cannot execute in the pure external controller; declarations remain present and report that limitation explicitly. |
| `InstanceInfo` | `map.h`, `context.cpp`, `context_methods.cpp`, `GetInstanceInfoPtr()` | `InstanceInfoContext.py`, `InstanceInfoContext.pyi` | **Declaration parity PASS; runtime externally verified** | `InstanceInfo`, `MapDimensions`, and `AreaInfo` layouts, nested remote reads, all source flag/file-ID properties, aliases, and facade members. | The source callback/shared-memory publication and legacy in-process symbol call cannot execute in the pure external controller; declarations remain present and report that limitation explicitly. |
| `TextParser` | `text_parser.h`, `game.h` `text_parser` field | `TextContext.py`, `TextContext.pyi` | **Declaration parity PASS; runtime externally verified** | Exact source root field order and sizes, typed language/file-slot records, source properties/helpers, source facade members, and bounded remote pointer reads. | Callback publication and the in-process `_do_load_string_table` trigger cannot execute in the pure external controller; declarations remain present and report that limitation explicitly. |
| `AvailableCharacterArray` | `account.h`, `player_patterns.cpp`, `GetAvailableCharactersPtr()` | `AvailableCharacterContext.py`, `AvailableCharacterContext.pyi` | **Declaration parity PASS; runtime externally verified** | Exact `0x84` entry and `0x10` array-header layouts, all packed properties, source names/aliases, bounded value traversal, and facade members. | The source callback/shared-memory publication cannot execute in the pure external controller; declarations remain present and report that limitation explicitly. |
| `PartyContext` | `party.h`, `GetPartyContext()` | `PartyContext.py`, `PartyContext.pyi` | **Declaration parity PASS; runtime externally verified** | Exact root and nested record layouts, native party-search enum, player/hero/henchman members, native helper aliases, party arrays, invite-list traversal, party searches, flag/text helpers, source record aliases, and source facade members including `_cached_ptr`. | Callback registration still requires the injected runtime and is explicitly unavailable to the pure external controller; no selected source declaration is omitted. |
| `GuildContext` | `guild.h`, `GetGuildContext()`, `GetGuildArray()` | `GuildContext.py`, `GuildContext.pyi` | **Declaration parity PASS; runtime externally verified** | Exact root and nested layouts, source/native GHKey views, `from_hex`, empty-array semantics, encoded/display names, bounded roster/history/alliance traversal, source facade members, and the native guild-array helper. | Callback registration still requires the injected runtime and is explicitly unavailable to the pure external controller; no selected source declaration is omitted. |
| `AccAgentContext` | `agent.h`, `GetAgentContext()` | `AccAgentContext.py` | **Partial / external read-only slice** | Root, summary records, movement records, pointer arrays, valid-agent IDs, aliases, and bounded traversal. | Lifecycle methods and injected pointer publication are not present. |
| `AgentArray` | `agent.h`, `GetAgentArray()` | `AgentContext.py`, `Agent.py` | **Partial / external read-only slice** | Common/living/item/gadget layouts, source-shaped `AgentArrayStruct`, bounded pointer-table traversal, source category methods, stale-reference validation, typed records, effects, equipment, tags, and corpse diagnostics. | Native pointer lifecycle/cache helpers (`get_ptr`, `_update_ptr`, `reset_cache`, `enable`, `disable`), injected shared-memory fallback, and the larger wrapper API are not present. |
| `Camera` | `camera.h`, `GetCamera()` | native camera bindings and camera wrappers | **Partial / external read-only slice** | Maintained fixed-width camera record and read-only derived helpers. | Setters, unlock patch state, and source-side camera control behavior are not present. |
| `FriendList` | `friend_list.h`, `GetFriendList()` | native friend-list bindings | **Partial / external read-only slice** | Full friend record/root layout, bounded traversal, decoding, lookups, counts, and own-status query. | Mutating add/remove/status operations and source-side update behavior are not present. |
| `ChatBuffer` | `chat.h`, chat pattern resolvers | native chat/player bindings | **Partial / read-only boundary** | Ring-buffer layout, bounded variable-length message reads, FILETIME conversion, current buffer pointer refresh, typing state, and explicit raw `message_encoded_str`/`message_codepoints` access. | `PyPlayer.GetChatHistory()` does more than read this context: it queues an asynchronous game-thread `AsyncDecodeStr` operation and maintains injected-runtime state (`RequestChatHistory`, readiness, and decoded cache). Stealth can read the encoded messages, but cannot provide that decoded helper under the current pure-external/read-only boundary. A live probe also confirmed that opening the running client's `Gw.dat` with read access fails with Windows sharing violation error 32; an external attempt to duplicate the client's existing file handle was denied `PROCESS_DUP_HANDLE` access (error 5). The Reforged `PyDatReader` avoids this by using in-process native calls. The native `GWDatReader` source exposes resolved function pointers and callable `ReadDatFile` methods, not a documented archive/string-table object pointer that an external reader could follow without executing target code. |
| `WorldContext` | `world.h`, `GetWorldContext()` | `WorldContext.py` | **Partial / external read-only slice** | Full 0x854 root byte layout, many source child records, bounded arrays, lookup helpers, and message/dialog buffers. | Lifecycle methods, the source `quest_log` surface, and any source fields/helpers outside the verified child readers are not present. |
| `MapContext` | `map.h`, `pathing.h`, `GetMapContext()` | `MapContext.py` | **Partial / context roots** | Fixed 0x138 root, native `map_boundaries` view, `GameContext.map_context` pointer path, map type/id and coordinates, direct child addresses, bounded spawn arrays, live `PathContext` and `MapStaticData` roots, and bounded `PathingMap` root records with child counts/addresses. Offline layout tests and live verification are recorded. | Trapezoids, sink/x/y nodes, portals, `PropsContext`, map props, travel portals, and higher-level helpers are not yet migrated. No pathing snapshots or caches are implemented. |
| `TradeContext` | `trade.h`, `GetTradeContext()` | native trade bindings | **Partial / external read-only slice** | Exact root/player/partner/item layouts, bounded offer arrays, and trade-state flags. | Trade actions and UI operations are not present. |
| `ItemContext` | `item.h`, `GetItemContext()`, `GetInventory()` | `ItemArray.py`, `Item.py`, `Inventory.py`, native item bindings | **Partial / external read-only slice** | Exact root/Bag/Item/Inventory layouts; bounded bag-owned item traversal; empty-slot-preserving bag searches; inventory/storage bag classification; indirect encoded item-name reads; interaction flags; material/ZCoin, rarity, weapon/armor, salvageable, inventory/storage, uses, tome/kit, and rare-material helpers; bounded native modifier-word reads with source bit access; cached JSON resolvers for storage state, item formulas, composite-model records, and PvP item tables. | The semantic `mods_types.py`/`mods_core.py` catalog and upgrade-name layer, native item/salvage/trade actions, and other in-process behavior are not present. `InventoryTableEntry`, `ItemClickParam`, and unused `MaterialCost` remain non-gaps based on source usage. |
| `AccountContext` | `account.h`, `GetAccountContext()` | no direct active context module; native item/skill helpers use it | **Partial / external consumer slice** | Native root and bounded account queries used by inspected helpers. | No direct Reforged Python facade was migrated, so total source/API parity cannot be claimed. |
| `GadgetContext` | `gadget.h`, GameContext `gadget_context` | gadget data is mainly consumed through `AgentContext.py` | **Partial / external read-only slice** | Root and bounded gadget-info records through external readers. | Lifecycle and gadget actions are not present. |

## Not yet migrated

| Source surface | Source-backed work | Why it is still pending |
| --- | --- | --- |
| `MapContext` follow-up | `PathingMap` trapezoid/node/portal records, `PropsContext`/`MapProp`, travel portals, and map helpers. | Reforged already defines these readers and caches raw/materialized pathing maps by map ID. Stealth now reads the context roots and bounded `PathingMap` headers, but does not yet follow graph children or reproduce that cache. Python snapshots and caches are explicitly deferred. |
| `MissionMapContext` | Small mission-map structure and its nested records. | Native/Reforged currently receive its pointer through injected UI callback/shared-memory publication. Stealth has no independent external pointer source. |
| `WorldMapContext` | World-map structure and map UI state. | Same callback-owned pointer limitation as `MissionMapContext`. |
| `GwDxContext` / render | Native render root and render helper data. | The current external offsets locate functions and related globals, but no verified external object-pointer contract has been recorded. |
| UI context | Frame arrays, windows, controls, tooltips, and window positions. | Native global accessors exist, but no Stealth reader or bounded UI tree contract exists yet. |
| `SalvageSessionInfo` | Native salvage session state. | The native surface is coupled to callback/action code. It is not part of the current read-only item path and has no active Reforged Python context reader. |

## Explicit non-gaps

The following declarations were checked and are **not** missing migration work
merely because they appear in a native header:

- `InventoryTableEntry`: no operational references in the inspected native
  implementation or Reforged Python item path;
- `ItemClickParam`: an internal item-click callback parameter, not a context
  read surface; and
- `MaterialCost`: a cached material-amount buffer that the native source
  explicitly says it does not use.

Likewise, native setters, UI actions, trade actions, item actions, and camera
setters remain declaration requirements. Their runtime status is
`externally unavailable` while this project is pure external and read-only;
they are not silently omitted from the source port. The complete deferred list
and its resume requirements are in
[`DEFERRED_INJECTION.md`](DEFERRED_INJECTION.md).

## Required follow-up order

`ChatBuffer` remains the first unresolved parity item.
Its raw external surface is complete; decoded history is unresolved because
the source implementation executes `AsyncDecodeStr` on the Guild Wars game
thread and the live archive is not externally readable while the client owns
it. No safe source-faithful completion exists inside the current pure-external,
read-only boundary.

The remaining work is therefore a scope decision, not an implementation to
guess at:

1. keep `ChatBuffer` raw/encoded and record it as partial; or
2. explicitly authorize a new external `Gw.dat` reader/data source and prove
   it against the same client build; or
3. change the architecture to allow in-process execution, which is injection
   and outside the current scope.

The remaining `MapContext` pathing/props records are tracked in
[`PATHING_MIGRATION_PLAN.md`](PATHING_MIGRATION_PLAN.md). Callback-owned map contexts,
render, UI, salvage state, and the explicit ItemContext modifier layer remain
pending surfaces rather than hidden parity claims. Native actions and injected lifecycle helpers remain outside
the read-only parity target.

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
| **Pending** | The source data surface has not yet been ported. This says nothing by itself about pointer availability. |
| **Pointer unavailable** | The source data surface and supplied-address reader are ported, but Stealth does not yet have its own route to obtain the runtime pointer. Callback-owned pointers are tracked in [`CALLBACK_POINTER_RESEARCH.md`](CALLBACK_POINTER_RESEARCH.md). |

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
- **Read-data status:** `MapContext` root, pathing/props records, and the
  active snapshot/read paths are live-verified. Reforged declares SinkNode
  pointer/list helpers, but its snapshot leaves `sink_nodes` empty and the
  searched source contains no active consumer of those helpers. A live test
  found a different raw field shape, so Stealth preserves the field without
  applying that unused helper interpretation.
- **Struct declarations pass:** `MapContext` (including pathing and props
  records), `MissionMapContext`, and `WorldMapContext`.
- **Runtime limits, not missing context ports:** automatic `MapContext`
  callback registration and `MissionMapContext`/`WorldMapContext` callback
  pointer acquisition are not implemented in Stealth yet. Research into a
  Stealth-owned hook/callback path is active because the project must not rely
  on Reforged's DLL/shared-memory publication. See
  [`CALLBACK_POINTER_RESEARCH.md`](CALLBACK_POINTER_RESEARCH.md).
  `GwDxContext` render-state
  pointer work is outside the required in-game context scope. The UI helper
  API in `ui.h` has no `UIContext` structure and is outside this inventory.

The read-slice list is not a parity score. Missing source-backed lifecycle,
actions, helpers, semantic layers, and nested records are named in the table
and in [`PARITY_STATUS_CORRECTION.md`](PARITY_STATUS_CORRECTION.md).

## Mechanical coverage sweep

A resolver-level count is **not** a coverage measure: context data is read as
fields through context pointers, so a namespace with no referenced resolver can
still be fully covered, and `party`, `quest`, and `skillbar` are examples of
exactly that. Coverage has to be measured against the source declarations
themselves.

Sweep method: every `struct` with data fields in
`Py4GW_Reforged_Native/include/GW/context/*.h` plus `include/GW/ui/ui.h` was
extracted, and each was matched by normalized name against the `ctypes`
declarations in `py4gw`, following module-level aliases and non-`Structure`
base classes. Field sets were compared after normalizing a trailing `Struct`
or `_array`.

| Result | Structs | Fields |
| --- | ---: | ---: |
| Source structs with data fields | 205 | 1803 |
| Fully covered in Stealth | 70 | — |
| Present but with fields unmatched | 47 | — |
| **No Stealth declaration** | **88** | — |
| — of which UI-message / packet structs | 64 | 217 |
| — of which other data structs | 24 | 152 |

The missing-declaration list was calibrated against a 10-name sample; 9 of the
10 names are genuinely absent from `py4gw`, so the list is accurate rather than
a naming artifact. The dominant missing block is therefore the **UI-message and
packet struct family** in `include/GW/context/ui.h`, not game contexts.

The non-packet structs with no Stealth declaration are a short, enumerable
list: `Skill` (49 fields, the largest), `AgentNameTagInfo` (15),
`FloatingWindow` (9), `SubStructUnk` (9), `DecodingString` (6),
`AttributeInfo` (5), `CharProgressBar` (5), `EnumPreferenceInfo` (5),
`NumberPreferenceInfo` (5), `DialogBodyInfo` (3), `DialogButtonInfo` (4),
`ChatTemplate` (4), `ScrollableFrame` (3), `ScrollablePageContext` (3),
`TypedScrollablePageContext` (3), `PartyShowConfirmDialogInfo` (3),
`MapTypeInstanceInfo` (3), `WindowPosition` (3), `PathPoint` (2),
`TitleClientData` (2), `CompassPoint` (2), `SubStruct1` (1), `sub1` (6), and
`sub2` (2). Several of these belong to the UI subsystem rather than to a game
context.

The 47 "present but fields unmatched" rows are **not** automatically gaps:
`GameContext`'s source fields `agent`, `map`, `world`, and `account` are
present in Stealth as `agent_context`, `map_context`, `world_context`, and
`account_context`. Each of those rows needs a case-by-case check before it is
counted as missing data.

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
| `AccAgentContext` | `agent.h`, `GetAgentContext()` | `AccAgentContext.py`, `AccAgentContext.pyi` | **Declaration parity PASS; runtime externally verified** | Exact root, summary, extension, movement, and native-only `AgentInfo` layouts; all source array properties and aliases; source facade declarations; nested gadget-name reads. | The injected callback cannot run externally. Native `AgentInfoArray` is declared in `agent.h` but has no field in `AgentContext` or getter in `context_methods.cpp`; its pointer source remains unresolved and no connection is inferred. |
| `AgentArray` | `agent.h`, `GetAgentArray()` | `AgentContext.py`, `AgentContext.pyi`, `AgentArray.py`; `Agent.py` helpers are a separate surface | **Structure and traversal slice verified; Reforged helper parity partial; callback lifecycle unavailable externally** | Common/living/item/gadget layouts, equipment/item/tag/effect records, source value dataclasses and snapshot conversions, `AgentArrayStruct` fields/cache methods, bounded pointer-table traversal, movement validity checks, category methods, stale-reference validation, typed records, corpse-state/signature properties, source item-facade method names, and source pure-list helpers (`Manipulation`, `Sort.ByCondition`, `Filter.ByCondition`). Python/native layout disagreements have separate explicit declarations. | The source cache gate checks corresponding external MapContext, CharContext, InstanceInfo, WorldContext, and AccAgentContext readers plus the source conditions. Cache records are materialized through remote reads instead of in-process pointers. The 300-reference `GetAgentByID` lookup is served from the same bounded, validated current array; this replaces the Reforged shared-memory transport rather than omitting its lookup behavior. Callback registration cannot run externally; process-wide Reforged state is adapted to per-client ownership. Agent-dependent `Sort.ByAttribute`, `Sort.ByDistance`, `Sort.ByHealth`, `Filter.ByAttribute`, `Filter.ByDistance`, and `Routines.DetectLargestAgentCluster` are not ported because they rely on the separate `Agent.py` query surface, which is unaudited and not present in Stealth. The native root is already represented by the `AccAgentContext` row. |
| `Camera` | `camera.h`, `GetCamera()` | Native camera layout; Reforged `Camera.py` facade; native camera bindings | **Declaration parity PASS; read getters verified; actions unavailable externally** | Exact native fields and read methods, all `Camera.py` facade getter names, `IsPointInFOV`, fixed-width pointer treatment, JSON resolver, and bounded read. | Source action names are declared but refuse execution because their bindings enqueue work in the game thread or mutate camera state. The external controller performs no camera writes or game-thread calls. |
| `Camera` | `camera.h`, `GetCamera()` | native camera bindings and camera wrappers | **Partial / external read-only slice** | Maintained fixed-width camera record and read-only derived helpers. | Setters, unlock patch state, and source-side camera control behavior are not present. |
| `FriendList` | `friend_list.h`, `GetFriendList()` | `PyFriendList.pyi` and native friend-list bindings | **Declaration parity PASS; live read verified; game-thread actions unavailable externally** | Exact `Friend`, `FriendList`, and flexible `FriendEventData` header fields; enum values; bounded friend traversal; source count/status APIs and action names. | `set_friend_list_status`, `add_friend`, and `add_ignore` are declared but refuse execution because the native bindings enqueue game-thread actions. Native `RemoveFriend` is not exposed by `PyFriendList.pyi` and is outside the Python facade audited here. |
| `ChatBuffer` | `chat.h`, `GetChatBufferAddress()`, `GetIsTypingFrameIdAddress()` | native context declarations; no same-named Reforged Python context facade | **Declaration parity PASS; live read verified** | Exact `ChatMessage` and `ChatBuffer` fields, FILETIME layout, flexible UTF-16 payload declaration, ring length, pointer-slot resolver, and typing-state resolver. | Chat-history decoding (`PyPlayer.GetChatHistory`) belongs to the separate Player API, not the `ChatBuffer` context. This context reader intentionally exposes the raw encoded payload only and does not claim Player API parity. |
| `WorldContext` | `world.h`, `GetWorldContext()` | `WorldContext.py`, `WorldContext.pyi`, `internals/types.py` value types used by this context | **Struct declarations and source member names represented; source return/lookup mismatches corrected; source-backed arrays live-verified for this client; full context/API parity remains partial** | Compared all 30 source classes by name and all `_fields_` names/order; AST inventory found no source property or method name missing from the port. No shared structure has a field-order difference. WorldContext's `Vec2f`, `Vec3f`, and `GamePos` value types match source fields, constructors, and helpers. Empty source arrays return `None`; `message_buff`/`dialog_buff` retain the source character-list shape; `GetPlayerById` compares `player_number`; `PlayerStruct.name_enc_str` follows the source `name_ptr` behavior. `vanquished_areas` preserves Reforged Python runtime's unconditional `None`, even though the native root declares `vanquished_areas_array`; the Reforged `.pyi` advertises `list[int] | None`, so the source's own runtime/stub disagree here. Indirect string properties preserve the difference between a null pointer (`None`) and a pointer to an empty string (`""`). Arrays implemented by source accessors are read in full after validating count, capacity, x86 address range, and a 16 MiB per-array byte ceiling; oversized requests fail instead of silently returning a prefix. Indirect UTF-16 strings are read through their NUL terminator up to 32,768 characters; an unterminated string errors rather than silently truncating. The root is 0x854 bytes and matches native x86 size and checked offsets. The latest live test accessed all 61 root properties and 188 properties across 44 sampled child records; each source-backed array accessor result count matched its advertised size for the tested client (including 2,009 map agents, 9,271 NPC models, and 2,009 agent-name records). | `enable` reports that callback registration requires the in-process runtime. Live data was not compared field-by-field with an in-client Reforged runtime; the array and string ceilings are explicit external-reader limits. Full context/API parity is not claimed. |
| `MapContext` | `map.h`, `pathing.h`, `GetMapContext()` | `MapContext.py`, `MapContext.pyi` | **ACTIVE READ-DATA STRUCTURES AND PATHS VERIFIED; unused SinkNode helper differs on live data** | Root/spawn/pathing arrays and links, reachable props, blocking props, source pathing snapshots, PID-scoped caches, paired-portal indices, and travel portals are live-verified. SinkNode declarations/helpers are represented, but the Reforged snapshot currently leaves `sink_nodes` empty and no active consumer was found in the searched source tree. | The live client stores a direct address in the raw SinkNode field, unlike the source helper's pointer-to-pointer interpretation. The live test records this difference; Stealth does not dereference it as that unused helper. Offline helper tests do not prove that unused source behavior matches the client. This does not block the active context data paths. The Reforged `.pyi` also differs from runtime `.py` for pointer annotations. |
| `MissionMapContext` | `map.h`, `map.cpp`, context methods, shared-memory manager | `MissionMapContext.py` and `MissionMapContext.pyi` | **SOURCE DATA STRUCTURES AND READERS PORTED; OFFLINE-VERIFIED** | All three source structures and child properties are represented. `MissionMapContextStruct.read_at(reader, address)` and `ConnectedClient.read_mission_map_context(address)` read the fixed root from a caller-supplied address and bind the child reader; offline tests cover both entry points, root bytes, field order/offsets, pointer-array and direct-pointer reads, bounds, and callback limitations. | The root is acquired read-only through the client's UI frame array using the record's `frame_id` at `+0x14` as the cross-check, and a **live read is now verified**: frame 1591 published `0x26404750`, the cross-check passed, and the root plus its `MissionMapSubContext2` child read back internally consistent. Callback registration itself remains an unavailable in-process runtime operation. See [`UI_FRAME_TREE.md`](UI_FRAME_TREE.md). |
| `WorldMapContext` | `map.h`, `map.cpp`, context methods, shared-memory manager | `WorldMapContext.py` and `WorldMapContext.pyi` | **SOURCE DATA STRUCTURE AND READER PORTED; OFFLINE-VERIFIED** | The complete `WorldMapContextStruct` matches source field names/order and 0x224 x86 size. `WorldMapContextStruct.read_at(reader, address)` and `ConnectedClient.read_world_map_context(address)` read the fixed root from a caller-supplied address; offline tests cover both entry points, root bytes, field order/offsets, bounds, and callback limitations. | The root is acquired read-only through the client's UI frame array using the record's `frame_id` at `+0x0` as the cross-check, and a **live read is now verified**: frame 3698 published `0x4526A578`, the cross-check passed, and the values read back consistent (`zoom=1.0`, bounds matching the separate `MissionMapContext` player position). The world-map frame registers a five-byte `jmp` thunk that the signature resolver sees through, so the walk accepts either a direct or a thunked callback match. Callback registration itself remains an unavailable in-process runtime operation. See [`UI_FRAME_TREE.md`](UI_FRAME_TREE.md). |
| `TradeContext` | `trade.h`, `GetTradeContext()` | No direct Reforged Python `TradeContext` module in the inspected `native_src/context` tree | **Native fields, constants, and helpers represented; offer-array traversal verified** | Exact native `TradeItem`, `TradePlayer`, and `TradeContext` field order and x86 sizes (0x08/0x14/0x38); all four trade-state constants; all three native flag helpers (`GetIsTradeOffered`, `GetIsTradeInitiated`, `GetIsTradeAccepted`); direct `GameContext.trade` pointer. Offer traversal reads the complete advertised array and raises rather than silently truncating above the explicit 16 MiB per-array ceiling. | No same-named Reforged Python context facade exists in the inspected source tree. Array materialization is an external-reader adaptation to expose the native `GWArray`; writes and trade actions remain unavailable. |
| `ItemContext` | `item.h`, `item.cpp`, `GetItemContext()`, `GetInventory()` | `ItemArray.py`, `Item.py`, `Inventory.py`; no same-named Reforged Python context structure module | **Native layouts and `Item`/`Bag` helper names represented; context/API parity remains partial** | Declares every structure and alias from the inspected native `item.h`, including `DyeInfo`, native `ItemData` (one-byte type), `MaterialCost`, `ItemFormula`, `Bag`, `ItemModifier`, `Item`, `WeaponSet`, `Inventory`, PvP item/upgrade, composite-model, salvage-session, click-parameter, inventory-table-entry, `ItemArray`, `MerchItemArray`, and `ItemContext`. Tests check source field order, native x86 sizes, inventory union views, and key offsets. Native `Item` and `Bag` helper names are callable methods; bag searches return native `npos` on failure. `GetModifier` scans the complete advertised count (subject to an explicit 16 MiB external-read ceiling), and `IsOfferedInTrade` reads the player's current `TradeContext` offer. `GetItemFormulaCount` is exposed under its native spelling and verified live against the formula array count (1,501 for the tested client). No `InventoryTableEntry` traversal was added because the inspected source has no traversal for it. | The Reforged Python `Item.py`/`Inventory.py` wrappers call injected `PyItem`/inventory APIs and do not declare a same-named context structure module. The `GetModifier` result is a copied record rather than an in-process pointer. The semantic `mods_types.py`/`mods_core.py` catalog and upgrade-name layer remain separate; operations that execute in-game are outside the read-only controller. |
| `AccountContext` | `account.h`, `GetAccountContext()` | No same-named Reforged Python context module in the inspected source tree; account data is consumed by item/skill helpers | **Native struct declaration parity PASS; read path verified** | Exact `AccountUnlockedCount`, `AccountUnlockedItemInfo`, and 0x138 `AccountContext` fields/order and checked x86 offsets. The account-wide `AvailableCharacterInfo` record is represented separately by `AvailableCharacterArray` and is not embedded in this root. | No direct Reforged Python `AccountContext` facade exists in the inspected source tree, so this is not a claim of broader Reforged wrapper/API parity. |
| `GadgetContext` | `gadget.h`, `GameContext.gadget` | No same-named Reforged Python context module | **Native struct declaration parity PASS; complete live array read verified** | Exact `GadgetInfo` and `GadgetContext` fields/order, x86 sizes (0x10 each), and direct GameContext pointer path. The native root field is `gadget_info`; `gadget_info_array` remains a compatibility alias. Default traversal reads all advertised records in one contiguous read; a caller-requested smaller sample is explicit, and requests over the 16 MiB ceiling raise rather than truncate. Latest live check read 9,500/9,500 records. | No separate Reforged Python GadgetContext structure/facade exists in the inspected source tree. No data beyond the explicit external-read ceiling is materialized. |
| `GwDxContext` | `render.h`, `GetRenderContext()` | Native render state only; not a required in-game context migration target | **OUT OF SCOPE FOR CONTEXT PORTING** | The existing field declaration is retained as native render-state reference. | Render-hook state and pointer acquisition are not included in the required context parity work. |

## Not yet migrated

| Source surface | Source-backed work | Why it is still pending |
| --- | --- | --- |
| `MapContext` follow-up | No active read-data gap is identified for the implemented snapshot paths. Keep the unused SinkNode helper discrepancy documented; revisit only if a source consumer begins using it or the source layout is corrected. | The active arrays, links, props, snapshots, and travel-portal path are live-tested. The raw SinkNode field differs from the source helper's interpretation, but Reforged currently snapshots an empty SinkNode list and no active consumer was found in the searched source tree. |
| `SalvageSessionInfo` | `item.h`, `context/item.h`, `src/GW/item/item.cpp` | `SalvageContext.py` (Stealth-owned module; no Reforged Python counterpart) | **NATIVE RECORD PORTED; ROOT ACQUISITION IMPLEMENTED, LIVE CONFIRMATION PENDING** | The complete 0x24 native record and all nine field names (`vtable`, `frame_id`, `item_id`, `salvagable_1/2/3`, `chosen_salvagable`, `h001c`, `kit_id`) are declared and offline-tested, with a bounded `read_at(reader, address)`. The root is acquired read-only by walking the client's UI frame array to the frame that registered the salvage-popup callback, cross-checked against the record's own `frame_id` at `+0x4`. | Reforged Python has no reader for this structure, so the facade is Stealth-owned rather than a source port. `enable`/`_update_ptr` raise because in-process callback registration is unavailable. The open/close test needs the operator to open the salvage window; see [`UI_FRAME_TREE.md`](UI_FRAME_TREE.md). |

## Runtime pointer availability (not context-port gaps)

The `MissionMapContext` and `WorldMapContext` structures and supplied-address
readers are ported. Their root addresses are published through native UI
callbacks/shared memory, which the external controller cannot currently
register or read. This prevents live verification, but is not unfinished
context porting. `GwDxContext` is native render state and is outside the
required in-game context migration.

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
`externally unavailable` in the current read-only implementation; the
selected target-payload work has not implemented those operations. They are
not silently omitted from the source port. The complete deferred list and its
resume requirements are in
[`DEFERRED_INJECTION.md`](DEFERRED_INJECTION.md).

## Remaining out-of-scope surfaces

`ChatBuffer` declaration parity is complete. Its raw message payload is not a
decoded chat-history API; `PyPlayer.GetChatHistory` is a separate Player
surface and must be audited there if that API is in scope.

The remaining `MapContext` callback-facade work is tracked in
[`PATHING_MIGRATION_PLAN.md`](PATHING_MIGRATION_PLAN.md). Callback-owned map
contexts and render pointer acquisition remain pending. UI support APIs,
salvage actions, and the explicit ItemContext modifier layer are separate
surfaces, not context declarations. Native actions and injected lifecycle
helpers remain outside the read-only parity target.

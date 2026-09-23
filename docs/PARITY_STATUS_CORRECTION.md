# Parity status correction

The previous context reports used **complete** to mean “the implemented
external read-only slice works.” That wording was too broad for the project's
actual parity goal. A read-only slice is not full parity with the Reforged and
native sources when source helpers, lifecycle, actions, or nested records are
missing.

## Current conclusion

**Full source/API parity: none.** No context currently has total source/API
parity with both reference projects.
Stealth has a number of verified external read slices. They must not be
reported as fully migrated contexts.

This is also a declaration-parity issue, not only a runtime issue. If the
source exposes a property, lifecycle method, cache helper, or mutating method,
Stealth must declare that member even when the external controller cannot
execute it. Such a member is marked **declared / externally unavailable** and
may raise an explicit unsupported-operation error; it must not disappear from
the port.

The current tree still has declaration gaps. For example, the source-only
members include the `AgentContext` lifecycle/cache/snapshot methods. The
`MapContext` and `WorldContext` source member names have now been compared
and represented; their in-client callback registration remains explicitly
unavailable to an external controller.

## Known gaps in readers previously described as complete

| Reader | Verified slice | Still missing or deliberately excluded |
| --- | --- | --- |
| `CharContext` | Fixed structure, strings, arrays, live pointer resolution, and declared facade methods | `enable` cannot register the in-process callback from a pure external controller; it remains declared and reports an explicit unsupported operation. |
| `PreGameContext` | Fixed structures, character list, and resolver | The same four Reforged lifecycle methods. |
| `Cinematic` | Fixed structure through `GameContext` | Reforged lifecycle methods and pointer-publication behavior. |
| `GameplayContext` | Fixed structure and resolver | Reforged lifecycle methods and callback/shared-memory publication. |
| `ServerRegion` | Region value and resolver | Reforged lifecycle methods and pointer-publication behavior. |
| `InstanceInfo` | Root/area structures and read-only helpers | Reforged lifecycle methods and any source behavior outside the verified read helpers. |
| `TextParser` | Root, language/file slots, and bounded lookups | Reforged lifecycle methods and in-process text/runtime behavior beyond bounded reads. |
| `AvailableCharacterArray` | Roster layout, names, and bounded entries | Reforged lifecycle methods and injected roster publication. |
| `PartyContext` | Root, member records, searches, native helper aliases, and facade | Callback registration requires the injected runtime; no selected source declaration is omitted. |
| `GuildContext` | Root, guild records, roster/history, names, `from_hex`, and facade | Callback registration requires the injected runtime; no selected source declaration is omitted. |
| `AccAgentContext` | Root, movement records, summaries, native-only `AgentInfo` layout, all array aliases, and facade | Callback registration requires the injected runtime. Native `AgentInfoArray` has no field/getter pointer source in the inspected context code, so only its declaration is represented. |
| `AgentArray` | Bounded references, categories, typed records, effects, equipment, tags, corpse-state helpers, source item names, and pure list merge/sort/filter helpers | Reforged `Sort.ByAttribute`, `Sort.ByDistance`, `Sort.ByHealth`, `Filter.ByAttribute`, `Filter.ByDistance`, and `Routines.DetectLargestAgentCluster` require the separate `Agent.py` query surface, which is not migrated. Callback registration is unavailable externally; Reforged shared-memory transport is replaced by bounded remote reads. |
| `Camera` | Native record and Reforged getter declarations; read-only getters verified | Game-thread camera actions and state-changing setters remain unavailable externally. |
| `FriendList` | Native structure and PyFriendList declarations; read-only records/counts/status verified | Mutating friend operations are declared but unavailable because they require the in-client game thread. Native `RemoveFriend` is not exposed in the PyFriendList stub. |
| `WorldContext` | All source classes, fields, and member names are represented. Its value types, empty-array returns, null-versus-empty string results, message/dialog buffer shape, player lookup field, and `PlayerStruct.name_enc_str` pointer behavior match the inspected source. Live checks cover each implemented source array accessor and confirm each result count equals its advertised size, including 2,009 map agents and 9,271 NPC models. `vanquished_areas` follows Reforged Python runtime's current unconditional `None`, although the native structure contains an array header; the source `.pyi` disagrees and advertises `list[int] | None`. Indirect strings above 256 characters are no longer silently truncated. | Callback registration remains unavailable; requests above the 16 MiB array or 32,768-character string ceiling fail explicitly, and live values are not compared field-by-field against an in-client Reforged runtime. Full API parity remains open. |
| `TradeContext` | Root, native constants, records, flag helpers, and complete advertised offer-array reads within the explicit external-read ceiling | Trade actions: open, offer, remove, accept, and cancel. |
| `ItemContext` | Root and native records; callable `Item` and `Bag` source helper methods; `Bag.find*` returns native `npos`; `GetModifier` scans the complete advertised count within its explicit read ceiling; `IsOfferedInTrade` reads through TradeContext | The Reforged semantic modifier catalog, upgrade-name layer, item actions, salvage actions, and other in-process behavior are separate. |
| `AccountContext` | Native root and bounded account queries | There is no direct Reforged Python context facade to claim parity with; only the inspected native consumers are represented. |
| `GadgetContext` | Native root/record declarations and complete advertised `GadgetInfo` array reads, within the explicit 16 MiB external-read ceiling | No same-named Reforged Python context facade was found; no context lifecycle or gadget action surface is defined by `gadget.h`. |

## Already explicitly partial or pending

- `ChatBuffer`: decoded chat history is not externally reproduced.
- `MapContext`: root, spawn arrays, pathing roots, linked records, props,
  travel portals, source snapshots, and PID-scoped caches are implemented.
  SinkNode pointer/list helpers are represented and offline-tested, but the
  current Reforged snapshot leaves `sink_nodes` empty and no active consumer
  was found in the searched source. The tested client stores direct pointers
  into trapezoid arrays; Stealth preserves those raw values and does not apply
  the unused helpers. This is documented, not treated as an active read-data
  blocker. Automatic callback registration also remains unavailable. See
  [`PATHING_MIGRATION_PLAN.md`](PATHING_MIGRATION_PLAN.md).
- `MissionMapContext` and `WorldMapContext`: source structures, data
  properties, and supplied-address readers are ported and offline-tested. The
  Native source obtains their roots through callbacks; Stealth has not yet
  implemented its own route to those pointers, so live verification remains
  unavailable. This is a runtime limitation, not missing
  structure/read-property parity. The agreed research path is in
  [`CALLBACK_POINTER_RESEARCH.md`](CALLBACK_POINTER_RESEARCH.md).
- Render/UI, salvage, and other action/execution surfaces are not implemented.

## Reporting rule from this point forward

Reports must use “verified external read slice” unless every source-backed
field, helper, lifecycle behavior, and explicitly in-scope operation has been
declared and checked. Operations that require injection may be declared and
tested as `externally unavailable`; they must not be omitted. A transport
replacement (for example, re-resolving a pointer externally) must be described
as a deliberate boundary difference, not as parity of the runtime mechanism.

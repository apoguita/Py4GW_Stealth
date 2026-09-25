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
Stealth must declare that member even when the controller cannot
execute it. Such a member is marked **declared and refusing** and
may raise an explicit unsupported-operation error; it must not disappear from
the port.

The current tree still has declaration gaps. For example, the source-only
members include the `AgentContext` lifecycle/cache/snapshot methods. The
`MapContext` and `WorldContext` source member names have now been compared
and represented; their in-client callback registration is still unported — the
controller now has its own callback layer, but nothing consumes it.

## Known gaps in readers previously described as complete

| Reader | Verified slice | Still missing or deliberately excluded |
| --- | --- | --- |
| `CharContext` | Fixed structure, strings, arrays, live pointer resolution, and declared facade methods | `enable` registers an in-process callback the source owns; no ported context is wired to Stealth's own callback layer yet, so it remains declared and reports an explicit unsupported operation. |
| `PreGameContext` | Fixed structures, character list, and resolver | The same four Reforged lifecycle methods. |
| `Cinematic` | Fixed structure through `GameContext` | Reforged lifecycle methods and pointer-publication behavior. |
| `GameplayContext` | Fixed structure and resolver | Reforged lifecycle methods and callback/shared-memory publication. |
| `ServerRegion` | Region value and resolver | Reforged lifecycle methods and pointer-publication behavior. |
| `InstanceInfo` | Root/area structures and read-only helpers | Reforged lifecycle methods and any source behavior outside the verified read helpers. |
| `TextParser` | Root, language/file slots, and bounded lookups | Reforged lifecycle methods and in-process text/runtime behavior beyond bounded reads. |
| `AvailableCharacterArray` | Roster layout, names, and bounded entries | Reforged lifecycle methods and injected roster publication. |
| `PartyContext` | Root, member records, searches, native helper aliases, and facade | Callback registration has no ported home; no selected source declaration is omitted. |
| `GuildContext` | Root, guild records, roster/history, names, `from_hex`, and facade | Callback registration has no ported home; no selected source declaration is omitted. |
| `AccAgentContext` | Root, movement records, summaries, native-only `AgentInfo` layout, all array aliases, and facade | Callback registration has no ported home. Native `AgentInfoArray` has no field/getter pointer source in the inspected context code, so only its declaration is represented. |
| `AgentArray` | Bounded references, categories, typed records, effects, equipment, tags, corpse-state helpers, source item names, and pure list merge/sort/filter helpers | Reforged `Sort.ByAttribute`, `Sort.ByDistance`, `Sort.ByHealth`, `Filter.ByAttribute`, `Filter.ByDistance`, and `Routines.DetectLargestAgentCluster` require the separate `Agent.py` query surface, which is not migrated. Callback registration has no ported home; Reforged shared-memory transport is replaced by bounded remote reads. |
| `Camera` | Native record and Reforged getter declarations; read-only getters verified | Game-thread camera actions and state-changing setters are declared and refuse; this reader makes no such call. |
| `FriendList` | Native structure and PyFriendList declarations; read-only records/counts/status verified | Mutating friend operations are declared and refuse. Native `RemoveFriend` is not exposed in the PyFriendList stub. |
| `WorldContext` | All source classes, fields, and member names are represented. Its value types, empty-array returns, null-versus-empty string results, message/dialog buffer shape, player lookup field, and `PlayerStruct.name_enc_str` pointer behavior match the inspected source. Live checks cover each implemented source array accessor and confirm each result count equals its advertised size, including 2,009 map agents and 9,271 NPC models. `vanquished_areas` follows Reforged Python runtime's current unconditional `None`, although the native structure contains an array header; the source `.pyi` disagrees and advertises `list[int] | None`. Indirect strings above 256 characters are no longer silently truncated. | Callback registration has no ported home; requests above the 16 MiB array or 32,768-character string ceiling fail explicitly, and live values are not compared field-by-field against an in-client Reforged runtime. Full API parity remains open. |
| `TradeContext` | Root, native constants, records, flag helpers, and complete advertised offer-array reads within the explicit external-read ceiling | Trade actions: open, offer, remove, accept, and cancel. |
| `ItemContext` | Root and native records; callable `Item` and `Bag` source helper methods; `Bag.find*` returns native `npos`; `GetModifier` scans the complete advertised count within its explicit read ceiling; `IsOfferedInTrade` reads through TradeContext | The Reforged semantic modifier catalog, upgrade-name layer, item actions, salvage actions, and other in-process behavior are separate. |
| `AccountContext` | Native root and bounded account queries | There is no direct Reforged Python context facade to claim parity with; only the inspected native consumers are represented. |
| `GadgetContext` | Native root/record declarations and complete advertised `GadgetInfo` array reads, within the explicit 16 MiB external-read ceiling | No same-named Reforged Python context facade was found; no context lifecycle or gadget action surface is defined by `gadget.h`. |

## Already explicitly partial or pending

- `ChatBuffer`: decoded chat history is not ported.
- `MapContext`: root, spawn arrays, pathing roots, linked records, props,
  travel portals, source snapshots, and PID-scoped caches are implemented.
  SinkNode pointer/list helpers are represented and offline-tested, but the
  current Reforged snapshot leaves `sink_nodes` empty and no active consumer
  was found in the searched source. The tested client stores direct pointers
  into trapezoid arrays; Stealth preserves those raw values and does not apply
  the unused helpers. This is documented, not treated as an active read-data
  blocker. Automatic callback registration has no ported home. See
  [`PATHING_MIGRATION_PLAN.md`](PATHING_MIGRATION_PLAN.md).
- `MissionMapContext` and `WorldMapContext`: source structures, data
  properties, and supplied-address readers are ported and offline-tested. The
  Native source obtains their roots through callbacks; Stealth reaches the same
  pointers read-only by walking the client's UI frame array, and both are now
  live-verified open and closed. The hook-based callback route was not built, and
  is not needed for these two. See
  [`CALLBACK_POINTER_RESEARCH.md`](CALLBACK_POINTER_RESEARCH.md).
- Render/UI, salvage, and other action/execution surfaces are not ported. The
  transport they would use exists in `py4gw/game_thread/`; no member is wired to
  it.

## Reporting rule from this point forward

Reports must use “verified external read slice” unless every source-backed
field, helper, lifecycle behavior, and explicitly in-scope operation has been
declared and checked. Operations that need a mechanism the port has not reached
are declared and refuse; they must not be omitted. A transport
replacement (for example, re-resolving a pointer externally, or reading a value
through a resolver where the source reads a hooked global) must be described
as a deliberate boundary difference, not as parity of the runtime mechanism.

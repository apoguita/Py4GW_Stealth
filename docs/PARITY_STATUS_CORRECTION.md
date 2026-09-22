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
members include `CharContext.get_ptr/enable/disable/get_context`, the
`MapContext` pathing/props/travel and cache methods, `WorldContext.quest_log`,
and the `AgentContext` lifecycle/cache/snapshot methods. These are migration
work, not approved design omissions.

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
| `AccAgentContext` | Root, movement records, summaries, and bounded arrays | Lifecycle methods and injected pointer publication. |
| `AgentArray` | Bounded references, categories, typed records, effects, equipment, and tags | Reforged lifecycle/cache methods, shared-memory fallback, and the larger wrapper API. |
| `Camera` | Read-only camera record and derived read helpers | Setters, unlock patch state, and source-side camera control behavior. |
| `FriendList` | Root, records, decoding, counts, and lookups | Mutating friend operations and any source-side update behavior. |
| `WorldContext` | Root and many bounded child records/helpers | Lifecycle methods, the source `quest_log` surface, and any other source fields/helpers not covered by the verified child readers. |
| `TradeContext` | Root, offers, records, and state flags | Trade actions: open, offer, remove, accept, and cancel. |
| `ItemContext` | Root, bags, items, raw modifier words, and native helper rules | Reforged semantic modifier catalog, upgrade-name layer, item actions, salvage actions, and other in-process behavior. |
| `AccountContext` | Native root and bounded account queries | There is no direct Reforged Python context facade to claim parity with; only the inspected native consumers are represented. |
| `GadgetContext` | Root and bounded gadget records through external readers | Lifecycle and gadget actions. |

## Already explicitly partial or pending

- `ChatBuffer`: decoded chat history is not externally reproduced.
- `MapContext`: root, spawn arrays, and initial pathing context roots are
  present; pathing children, props, travel portals, snapshots, and caches are
  not present. See [`PATHING_MIGRATION_PLAN.md`](PATHING_MIGRATION_PLAN.md).
- `MissionMapContext` and `WorldMapContext`: no independent external pointer
  source is verified.
- Render/UI, salvage, and other action/execution surfaces are not implemented.

## Reporting rule from this point forward

Reports must use “verified external read slice” unless every source-backed
field, helper, lifecycle behavior, and explicitly in-scope operation has been
declared and checked. Operations that require injection may be declared and
tested as `externally unavailable`; they must not be omitted. A transport
replacement (for example, re-resolving a pointer externally) must be described
as a deliberate boundary difference, not as parity of the runtime mechanism.

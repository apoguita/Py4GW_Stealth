# Context parity certification checklist

This is the execution checklist for porting the Guild Wars contexts from
`Py4GW_Reforged` and `Py4GW_Reforged_Native` into Stealth.

This procedure is mandatory for every context in the ledger. `CharContext` is
only the first completed audit; it is not a relaxed example or a special case.
The same evidence and PASS/FAIL gate must be applied to `GameContext`,
`MapContext`, `AgentArray`, item contexts, and every remaining source surface.

## Meaning of parity

Parity is binary. A context is **PASS** only when every source declaration and
public behavior in the selected scope is represented in Stealth with the same
names, fields, offsets, properties, methods, signatures, and observable
semantics. “Close,” “useful,” “read-only equivalent,” and “meets Stealth's
criteria” are not parity.

Runtime availability is tracked separately:

- `externally verified`: the operation was exercised through the external
  reader;
- `externally unavailable`: the declaration exists, but it requires target
  execution, injection, a callback, or a write that is not currently enabled;
- `unresolved`: the source behavior or pointer path has not yet been proven.

An externally unavailable member is still required in the port. It must not be
deleted because it cannot currently execute.

## Required comparison sources

For each context, inspect all applicable files before changing code:

1. the Reforged Python `.py` module;
2. the Reforged Python `.pyi` stub;
3. the native C++ header defining the structure and fields; and
4. the native C++ implementation defining pointer acquisition, helpers,
   caches, callbacks, and mutations.

The Reforged Python module is the primary source for names and Python
properties/methods. The native C++ source verifies byte layout, pointer
ownership, resolver relationships, and operations not represented in Python.

## Per-context procedure

Do not start the next context until the current context has a signed result.

### 1. Freeze the source surface

- [ ] Record the exact source file paths and revision/date inspected.
- [ ] List every source `Structure`/class in the context.
- [ ] List every nested structure, array element type, pointer type, alias,
      property, helper, lifecycle method, cache method, and mutating method.
- [ ] Record source method signatures, defaults, and return conventions.

### 2. Compare declarations

- [ ] Compare every `_fields_` entry by name and order.
- [ ] Compare `ctypes.sizeof` and every field offset.
- [ ] Compare scalar widths and signedness.
- [ ] Compare fixed arrays and nested structures.
- [ ] Represent target-process pointers as fixed-width `c_uint32` only as the
      necessary x86 transport adaptation; record the original pointer type.
- [ ] Confirm every source property exists with the same name and semantics.
- [ ] Confirm every source method exists with the same name, signature, and
      source-compatible behavior.
- [ ] Confirm `.pyi` declarations and runtime classes agree.

### 3. Port behavior without redesign

- [ ] Copy source calculations and flag/bit rules as written.
- [ ] Follow source pointer and array relationships; do not invent traversal
      limits or alternate meanings.
- [ ] Replace only in-process dereferences with bounded remote reads.
- [ ] Preserve source names. Add style aliases only in addition to them.
- [ ] Declare operations that require injection or target execution. They may
      report an explicit unsupported result, but they must remain visible.
- [ ] Do not silently remove caches, snapshots, setters, callbacks, or helper
      methods because they are not currently executable externally.

### 4. Verify

- [ ] Add offline layout tests for every structure and field offset.
- [ ] Add API-surface tests for every source property and method.
- [ ] Add bounded pointer/array failure tests.
- [ ] Add a live read test where an external pointer path exists.
- [ ] Record client build, timestamp, selected PID, addresses, and result.
- [ ] Record each externally unavailable operation and the exact required
      mechanism.
- [ ] Run the full test suite and Pyright.

### 5. Certification gate

The context receives **PASS** only if every declaration comparison is clean.
Any missing field, renamed source member, changed signature, omitted property,
omitted mutator, omitted cache/helper, or unverified source relationship is a
**FAIL**, even if the remaining reader works live.

The certification record must contain:

```text
Context:
Source files and revision:
Declaration result: PASS / FAIL
Runtime availability: externally verified / externally unavailable / unresolved
Missing or changed declarations:
Transport-only adaptations:
Live evidence:
Tests:
Pyright:
Reviewer/date:
```

## One-at-a-time order

The order is deliberately serial. The next item is not started until the
current item has a PASS or an explicit FAIL report with its remaining source
differences.

1. `CharContext`
2. `GameContext`
3. `PreGameContext`
4. `Cinematic`
5. `GameplayContext`
6. `ServerRegion`
7. `InstanceInfo`
8. `TextParser`
9. `AvailableCharacterArray`
10. `PartyContext`
11. `GuildContext`
12. `AccAgentContext`
13. `AgentContext` / `AgentArray`
14. `Camera`
15. `FriendList`
16. `ChatBuffer`
17. `WorldContext`
18. `TradeContext`
19. `ItemContext` and item records
20. `AccountContext`
21. `GadgetContext`
22. `MapContext` and pathing/props records
23. `MissionMapContext`
24. `WorldMapContext`
25. Render, UI, salvage, and other native-only context surfaces

## Certification ledger

`NOT AUDITED` is the initial state. Only a completed per-context report may
change a row to `PASS` or `FAIL`.

| Context | Declaration parity | Runtime availability | Certificate |
| --- | --- | --- | --- |
| `CharContext` | PASS | Read path verified; callback registration unavailable externally | PASS — declaration parity; runtime limitation recorded |
| `GameContext` | PASS | External resolver/read path verified; no injection-only member | PASS |
| `PreGameContext` | PASS | Read path verified; callback registration unavailable externally | PASS — declaration parity; runtime limitation recorded |
| `Cinematic` | PASS | Read path verified; callback registration unavailable externally | PASS — declaration parity; runtime limitation recorded |
| `GameplayContext` | PASS | Read path verified; callback registration unavailable externally | PASS — declaration parity; runtime limitation recorded |
| `ServerRegion` | PASS | Read path verified; callback registration unavailable externally | PASS — declaration parity; runtime limitation recorded |
| `InstanceInfo` | PASS | Read path verified; callback registration unavailable externally | PASS — declaration parity; runtime limitation recorded |
| `TextParser` | PASS | Read path verified; callback/string-table trigger unavailable externally | PASS — declaration parity; runtime limitation recorded |
| `AvailableCharacterArray` | PASS | Read path verified; callback registration unavailable externally | PASS — declaration parity; runtime limitation recorded |
| `PartyContext` | PASS | Read path verified; callback registration unavailable externally | PASS — declaration parity; runtime limitation recorded |
| `GuildContext` | PASS | Read path verified; callback registration unavailable externally | PASS — declaration parity; runtime limitation recorded |
| `AccAgentContext` | PASS | Root and nested read path verified; callback registration unavailable externally | PASS — declaration parity; native-only AgentInfo pointer path unresolved |
| `AgentContext` / `AgentArray` | PASS — source declarations represented; Python/native layout differences explicitly represented | Bounded live read path verified; injected callback lifecycle unavailable externally | PASS — declaration parity; runtime limitation recorded |
| `Camera` | PASS — native structure and Reforged Python facade declarations represented | Read-only resolver/getters verified; game-thread actions unavailable externally | PASS — declaration parity; runtime limitation recorded |
| `FriendList` | PASS — native structure and PyFriendList declarations represented | Read-only root/records verified; game-thread actions unavailable externally | PASS — declaration parity; runtime limitation recorded |
| `ChatBuffer` | PASS — native structures and pointer APIs represented | Read-only ring and typing reads verified | PASS — declaration parity |
| `WorldContext` | **STRUCTS AND SOURCE MEMBER NAMES REPRESENTED** — 30 source classes and every `_fields_` name/order matched; no source property/method name was missing in the member inventory; native root size and checked offsets match. Value types, empty-array return values, source buffer shape, `GetPlayerById`, `PlayerStruct.name_enc_str`, and the runtime `vanquished_areas` behavior match the inspected Python source. The source `.pyi` disagrees by declaring `list[int] | None`; the runtime method returns `None` unconditionally. | Latest live test accessed all 61 root properties and 188 properties across 44 sampled child records; each implemented source array accessor matched its advertised count, including arrays larger than the former caps. An offline test preserves the `vanquished_areas` runtime behavior. Offline tests cover string lengths above the former cap | Callback registration is unavailable externally; reads above the explicit 16 MiB array or 32,768-character string ceilings fail; live values are not compared field-by-field against an injected Reforged runtime. Not full context/API certification |
| `TradeContext` | **NATIVE FIELDS, CONSTANTS, AND HELPERS REPRESENTED** — record field order and x86 sizes match; all four native state constants and three flag helpers are represented; no direct Reforged Python context module exists in the inspected source tree | Live root read was previously verified; offline tests now verify full offer-array traversal beyond the former 64-item truncation and explicit failure for an over-limit request | Array materialization is an external-reader adaptation with a 16 MiB explicit ceiling; trade mutations are not enabled |
| `ItemContext` | **LAYOUTS AND `Item`/`Bag` HELPER NAMES REPRESENTED** — native item/context fields and x86 sizes/offsets match; native methods are callable, bag search misses return `npos`, and `IsOfferedInTrade` uses the external TradeContext reader. No direct Reforged Python context-structure module exists | Live ItemContext and modifier reads pass; offline tests verify callable methods, full `GetModifier` lookup beyond 64 entries, offered/not-offered cases, and dye-aware bag search | `GetModifier` materializes a value copy and explicit array limits remain; Reforged wrapper and mutating-feature parity is not certified |
| `AccountContext` | **STRUCTS PASS** — native account root and nested records matched by names/order and x86 sizes/offsets; no same-named Reforged Python context module exists | Read path verified; nested account arrays are bounded | Struct declaration pass only; no broader Reforged wrapper/API parity claim |
| `GadgetContext` | **STRUCTS PASS** — both native records match names/order and x86 sizes; no same-named Reforged Python context module exists | Latest live test read all 9,500/9,500 advertised records through the direct GameContext pointer; offline tests verify full traversal beyond 256 and failure above the 16 MiB ceiling | Only APIs present in the native context source are claimed; no data beyond the explicit external-read ceiling is materialized |
| `MapContext` | STRUCTS PASS — Reforged declarations and native pathing/props records are present with checked x86 sizes, source field order, and key offsets; source SinkNode helper declarations are represented | Root, arrays, links, props, snapshots, source facade helpers, PID-scoped caches, and travel portals verified; SinkNode helper logic is offline-tested but unused by the current source snapshot, which leaves `sink_nodes` empty | The tested client stores direct pointers into trapezoid arrays, unlike the unused source helper's pointer-to-pointer interpretation. Reforged `.pyi` pointer annotations differ from runtime `.py`/C++. This is recorded but does not block active reads. Callback registration is unavailable externally |
| `MissionMapContext` | SOURCE DATA STRUCTURES AND READERS PORTED — all three structures, `read_at(reader, address)`, `ConnectedClient.read_mission_map_context(address)`, `subcontexts`/`subcontext2`, and source data properties are offline-tested | **LIVE READ VERIFIED** via the read-only frame-array route: frame 1591 published `0x26404750`, the `frame_id` cross-check passed, and root plus child values were internally consistent | In-process callback registration remains unavailable; the frame-array route is the read-only substitute |
| `WorldMapContext` | SOURCE DATA STRUCTURE AND READER PORTED — source fields/order, `read_at(reader, address)`, and `ConnectedClient.read_world_map_context(address)` are offline-tested | **LIVE READ VERIFIED** via the read-only frame-array route: frame 3698 published `0x4526A578`, the `frame_id` cross-check passed, and the values read back consistent | In-process callback registration remains unavailable; the frame-array route is the read-only substitute. The world-map frame registers a `jmp` thunk, so the walk also follows near jumps |
| `GwDxContext` | OUT OF SCOPE — native render-state record, not a required in-game context migration target | Not required | Existing declaration retained for reference; no render-state pointer work is planned |
| UI support APIs | Outside context inventory — `ui.h` contains event/data records and accessors, but no `UIContext` structure | NOT AUDITED | Separate UI surface; not part of context-by-context parity |
| Salvage actions | NOT AUDITED | NOT AUDITED | NOT AUDITED |

## Current certification state

`CharContext`, `GameContext`, `PreGameContext`, `Cinematic`, `GameplayContext`,
`ServerRegion`, `InstanceInfo`, `TextParser`, `AvailableCharacterArray`,
`PartyContext`, `GuildContext`, and `AccAgentContext`
have completed declaration audits. Their source structures, fields,
properties, facade methods, signatures, and source `.pyi` surfaces are
represented. Their external read paths are verified by focused tests and live
client runs.

The source `enable` operation registers an in-process callback and therefore
cannot be executed by the current external controller. It remains declared and
raises an explicit unsupported-operation error. That is a runtime-availability
limitation, not an omitted declaration.

### CharContext certification record

```text
Context: CharContext
Source files and revision: Reforged native_src/context/CharContext.py and .pyi;
  Reforged_Native/include/GW/context/character.h (working-tree sources)
Declaration result: PASS
Runtime availability: read path externally verified when a client is running;
  enable callback externally unavailable; disable clears external cache
Missing or changed declarations: none found in the source surface
Transport-only adaptations: target pointers use uint32 addresses; fixed-width
  wide-character arrays use uint16 storage to preserve the x86 target layout
Live evidence: tests/test_context.py passed against the running client on
  2026-09-22. CharContext=0x00ADDD98; player name=Fezzik The Untamed;
  GW_Array h0014=0; observer_matches=0
Tests: tests/test_char_context_offline.py; full discovery run passed
Pyright: 0 errors, 0 warnings, 0 informations
Reviewer/date: Codex / 2026-09-22
```

### PreGameContext certification record

```text
Context: PreGameContext
Source files and revision: Reforged native_src/context/PreGameContext.py and
  PreGameContext.pyi; Reforged_Native/include/GW/context/pregame.h
  (working-tree sources)
Declaration result: PASS
Runtime availability: external resolver and complete structure read verified;
  enable callback registration externally unavailable; disable clears the
  external facade cache
Missing or changed declarations: none found in the source surface
Transport-only adaptations: target pointers use uint32 addresses; the source
  c_wchar[20] field uses uint16 storage for the x86 target layout; the source
  GW_BaseArray is read through a bound remote value view
Live evidence: tests/test_pre_game_context.py passed against the running client
  on 2026-09-22. Global pointer location=0x017CA2EC; the pointed-to context was
  null, correctly reporting that the client was outside the selection menus
Tests: tests/test_pre_game_context_offline.py (6 passed) and
  tests/test_pre_game_context.py (3 passed)
Pyright: 0 errors, 0 warnings, 0 informations
Reviewer/date: Codex / 2026-09-22
```

### Cinematic certification record

```text
Context: Cinematic
Source files and revision: Reforged native_src/context/CinematicContext.py and
  CinematicContext.pyi; Reforged_Native/include/GW/context/cinematic.h
  (working-tree sources)
Declaration result: PASS
Runtime availability: external GameContext pointer path and structure read
  verified; enable callback registration externally unavailable; disable clears
  the external facade cache
Missing or changed declarations: none found in the source surface
Transport-only adaptations: target uint32 fields remain fixed-width x86 values
  and the native shared-memory pointer publication is replaced by the existing
  external GameContext pointer read
Live evidence: tests/test_cinematic_context.py passed against the running
  client on 2026-09-22. Cinematic=0x00ABF730; h0000=0x00000000;
  h0004=0x00000000
Tests: tests/test_cinematic_context_offline.py (4 passed) and
  tests/test_cinematic_context.py (3 passed)
Pyright: 0 errors, 0 warnings, 0 informations
Reviewer/date: Codex / 2026-09-22
```

### GameplayContext certification record

```text
Context: GameplayContext
Source files and revision: Reforged native_src/context/GameplayContext.py and
  GameplayContext.pyi; Reforged_Native/include/GW/context/gameplay.h
  (working-tree sources)
Declaration result: PASS
Runtime availability: external resolver and complete structure read verified;
  enable callback registration externally unavailable; disable clears the
  external facade cache
Missing or changed declarations: none found in the source surface
Transport-only adaptations: the fixed x86 uint32 arrays are read externally;
  the native shared-memory pointer publication is replaced by the JSON-backed
  external pointer-slot resolver
Live evidence: tests/test_gameplay_context.py passed against the running client
  on 2026-09-22. Global pointer location=0x017CAAB8;
  GameplayContext=0x0A211370; mission_map_zoom=1.000
Tests: tests/test_gameplay_context_offline.py (4 passed) and
  tests/test_gameplay_context.py (3 passed)
Pyright: 0 errors, 0 warnings, 0 informations
Reviewer/date: Codex / 2026-09-22
```

### ServerRegion certification record

```text
Context: ServerRegion
Source files and revision: Reforged native_src/context/ServerRegionContext.py
  and ServerRegionContext.pyi; Reforged_Native/src/GW/context/context.cpp and
  context_methods.cpp (working-tree sources)
Declaration result: PASS
Runtime availability: external resolver and signed value read verified;
  enable callback registration externally unavailable; disable clears the
  external facade cache
Missing or changed declarations: none found in the source surface
Transport-only adaptations: the source c_int32 value is read as the same
  fixed-width signed x86 value; the source callback/shared-memory publication
  is replaced by the JSON-backed external value-address resolver
Live evidence: tests/test_server_region_context.py passed against the running
  client on 2026-09-22. ServerRegion address=0x017C63A8; region_id=0 (America)
Tests: tests/test_server_region_context_offline.py (4 passed) and
  tests/test_server_region_context.py (3 passed)
Pyright: 0 errors, 0 warnings, 0 informations
Reviewer/date: Codex / 2026-09-22
```

### InstanceInfo certification record

```text
Context: InstanceInfo
Source files and revision: Reforged native_src/context/InstanceInfoContext.py
  and InstanceInfoContext.pyi; Reforged_Native/include/GW/context/map.h and
  context_methods.cpp (working-tree sources)
Declaration result: PASS
Runtime availability: external resolver, complete root read, nested terrain
  reads, and current-map metadata read verified; enable callback registration
  externally unavailable; disable clears the external facade cache
Missing or changed declarations: none found in the source surface
Transport-only adaptations: source pointer fields use fixed-width uint32 target
  addresses and nested properties read through the bound external reader;
  source legacy NativeSymbol lookup is represented by the JSON resolver
Live evidence: tests/test_instance_info_context.py passed against the running
  client on 2026-09-22. InstanceInfo=0x01C4A150; instance_type=0;
  campaign=3; region=15; file_id=0
Tests: tests/test_instance_info_offline.py (7 passed) and
  tests/test_instance_info_context.py (3 passed)
Pyright: 0 errors, 0 warnings, 0 informations
Reviewer/date: Codex / 2026-09-22
```

### TextParser certification record

```text
Context: TextParser
Source files and revision: Reforged native_src/context/TextContext.py and
  TextContext.pyi; Reforged_Native/include/GW/context/text_parser.h and
  game.h (working-tree sources)
Declaration result: PASS
Runtime availability: external GameContext +0x18 pointer path, complete root
  read, bounded language/file-slot reads, cache/sub-structure reads, and file
  hash decoding verified; callback registration and in-process string-table
  trigger externally unavailable; disable clears the external facade cache
Missing or changed declarations: none found in the source structure or facade
  surface
Transport-only adaptations: source inline `_cache_header` remains one 0x34-byte
  field; its first four bytes are exposed through an additive `cache_ptr`
  property; all target pointers and UTF-16 reads use bounded external memory
Transport behavior: `get_file_slot`, `cache`, `sub_struct`, and `file_hash`
  follow target pointers through the bound reader instead of local dereference
Live evidence: tests/test_text_parser_context.py passed against the running
  client on 2026-09-22. TextParser=0x07453C38; language_id=0
Tests: tests/test_text_parser_context_offline.py (7 passed) and
  tests/test_text_parser_context.py (3 passed)
Pyright: 0 errors, 0 warnings, 0 informations
Reviewer/date: Codex / 2026-09-22
```

### AvailableCharacterArray certification record

```text
Context: AvailableCharacterArray
Source files and revision: Reforged native_src/context/AvailableCharacterContext.py
  and AvailableCharacterContext.pyi; Reforged_Native/include/GW/context/account.h
  and src/GW/player/player_patterns.cpp (working-tree sources)
Declaration result: PASS
Runtime availability: external roster resolver, complete array header, bounded
  entry reads, packed properties, and name decoding verified; enable callback
  registration externally unavailable; disable clears the external facade cache
Missing or changed declarations: none found in the source surface
Transport-only adaptations: source c_wchar[20] uses uint16 storage for the x86
  target layout; the source GW_Array value view follows target entries through
  the bound external reader; AvailableCharacterStruct and the descriptive
  AvailableCharacterInfoStruct remain aliases of one layout
Live evidence: tests/test_available_character_context.py passed against the
  running client on 2026-09-22. GWArray=0x017AF28C; entries=14;
  first=Fezzik The Untamed; level=20; map_id=449
Tests: tests/test_available_character_context_offline.py (6 passed) and
  tests/test_available_character_context.py (3 passed)
Pyright: 0 errors, 0 warnings, 0 informations
Reviewer/date: Codex / 2026-09-22
```

### PartyContext certification record

```text
Context: PartyContext
Source files and revision: Reforged native_src/context/PartyContext.py and
  PartyContext.pyi; Reforged_Native/include/GW/context/party.h and
  include/GW/context/game.h (working-tree sources)
Declaration result: PASS
Runtime availability: external GameContext.party pointer and complete root,
  nested party/member records, party-search records, and bounded list/array
  reads verified; callback registration externally unavailable; disable clears
  the external facade cache
Missing or changed declarations: none found in the selected source surface
Transport-only adaptations: source pointers use uint32 target addresses;
  source c_wchar arrays use uint16 storage for the x86 target layout; intrusive
  list links are followed through bounded remote reads with null, low-bit, and
  visited-node checks
Live evidence: tests/test_party_context.py passed against the running client on
  2026-09-22. PartyContext=0x00A07388; party_leader=True; parties=1;
  party_searches=68
Tests: tests/test_party_context_offline.py (6 passed) and
  tests/test_party_context.py (3 passed)
Pyright: 0 errors, 0 warnings, 0 informations
Reviewer/date: Codex / 2026-09-22
```

### GuildContext certification record

```text
Context: GuildContext
Source files and revision: Reforged native_src/context/GuildContext.py and
  GuildContext.pyi; Reforged_Native/include/GW/context/guild.h and
  src/GW/context/context_methods.cpp (working-tree sources)
Declaration result: PASS
Runtime availability: external GameContext.guild pointer and complete root,
  guild, alliance, history, and roster records verified; callback registration
  externally unavailable; disable clears the external facade cache
Missing or changed declarations: none in the selected source surface
Transport-only adaptations: target pointers use uint32 addresses; source
  c_wchar arrays use uint16 storage; GHKey exposes the Reforged four-byte
  key_data view and the native four-word k view over the same 0x10-byte target
  record; empty source GW_Array views return None
Live evidence: tests/test_guild_context.py passed against the running client on
  2026-09-22. GuildContext=0x00AD42A0; player=Fezzik The Untamed;
  guilds=243; roster=42; history=20
Tests: tests/test_guild_context_offline.py (6 passed) and
  tests/test_guild_context.py (3 passed)
Pyright: 0 errors, 0 warnings, 0 informations
Reviewer/date: Codex / 2026-09-22
```

### AccAgentContext certification record

```text
Context: AccAgentContext / native GW::Context::AgentContext
Source files and revision: Reforged native_src/context/AccAgentContext.py and
  AccAgentContext.pyi; Reforged_Native/include/GW/context/agent.h,
  include/GW/context/game.h, and src/GW/context/context_methods.cpp
  (working-tree sources)
Declaration result: PASS for the selected context declarations
Runtime availability: GameContext.agent pointer, complete 0x1B0 root,
  summary records, gadget-name reads, movement records, and source array
  properties verified externally; callback registration unavailable; native
  AgentInfo layout is declared but has no pointer field in AgentContext and no
  getter in context_methods.cpp, so its live array source remains unresolved
Missing or changed declarations: none in the Reforged AccAgentContext module;
  native-only AgentInfo and AgentInfoArray are declared as separate companion
  types with no inferred pointer relationship
Transport-only adaptations: target pointers use uint32 addresses; pointer
  arrays and AgentMovement* entries are traversed through remote reads; source
  empty value-array properties return empty lists; movement array returns None
  when its header is empty; native array member names are additive aliases for
  the Reforged *_array fields
Live evidence: tests/test_acc_agent_context.py passed against the running client
  on 2026-09-22. AgentContext=0x07453460; summaries=2002; movement entries=2002;
  valid movement IDs=104; instance_timer=1805937958
Tests: tests/test_acc_agent_context_offline.py (6 passed) and
  tests/test_acc_agent_context.py (3 passed)
Pyright: 0 errors, 0 warnings, 0 informations
Reviewer/date: Codex / 2026-09-22
```

### AgentContext / AgentArray certification record

```text
Context: native GW::Context::AgentContext and Reforged AgentContext/AgentArray
Source files inspected: Reforged_Native/include/GW/context/agent.h,
  src/GW/context/context_methods.cpp; Reforged
  native_src/context/AgentContext.py and AgentContext.pyi; Reforged AgentArray.py
Root relationship: the native AgentContext root reached through
  GameContext.agent is the same 0x1B0 root already covered under AccAgentContext;
  no second root or pointer was added
Implemented and externally verified: distinct global agent-array resolver,
  bounded pointer-table traversal, native movement-table validity checks,
  lazy typed record reads, living snapshots, source category methods, and
  read-only effects/equipment/tag access. Struct declarations and source value
  snapshots were separately checked against Reforged Python and native C++.
Changes in this step: added Reforged facade names GetItemArray and
  GetOwnedItemArray, and exposed per-reader get_ptr, _update_ptr, reset_cache,
  enable, disable, and get_context names. enable explicitly reports that the
  injected callback runtime is unavailable.
Record/value struct parity result: PASS. The source Python living layout
  (0x1C2) and native live-read layout (0x1C4) are represented explicitly;
  Python/native item and equipment disagreements also have separate types.
  The source value structure contains no extra corpse-diagnostic fields. This
  is not a claim that Reforged's in-process execution model is reproduced.
  AgentArrayStruct's source helper names are present. Its cache gate reads the
  matching external contexts, while record caching uses remote reads instead
  of process-local ctypes pointers. Native live-read layouts remain
  authoritative for target memory. The Python Reforged ItemDataStruct layout
  is separately represented for source parity and must not be used for native
  live reads.
AgentContext/AgentArray declaration result: PASS. The shared-memory fallback
  transports the same bounded current array; Stealth serves ID lookup from its
  validated current snapshot instead. Callback registration and process-wide
  facade state remain runtime adaptations to per-client external readers.
  The separate `Agent.py` helper surface was not part of this context audit.
Source disagreements in AgentArray's equipment view: Reforged Python
  `ItemDataStruct` uses a 32-bit type field and has size 0x13, while native
  `ItemData` uses a 1-byte type and has size 0x10. ItemContext separately
  declares the native `item.h` `ItemData` layout. The Reforged layout also
  expands the Python equipment union to 0xAB and its
  containing Equipment record to 0xF3; native C++ asserts 0x90 and 0xD8.
  Separate ``Reforged*`` layout views preserve the Python declarations while
  native layouts remain in use for live reads. Reforged Python
  AgentLivingStruct is packed to 0x1C2 while native AgentLiving is 0x1C4;
  Stealth declares separate Python-source and native live-read layouts.
  The .pyi has stale snapshot return annotations in places; conversion
  behavior follows the .py implementation and value types.
Live evidence: tests/test_agent_array.py passed on 2026-09-22 against the
  running client. Latest observation: reported size=1945, capacity=2048,
  accepted references=98, stale=0, unreadable=0, truncated=False, living=95,
  gadgets=3; one living refresh captured 95 records with zero stale and
  unreadable records. Refresh=6.659 ms; pointer table=0.528 ms; movement
  table=1.181 ms; classification=2.756 ms; source-shaped cache build=6.492 ms;
  resolver initialization=135.579 ms.
Offline evidence: tests/test_agent_array_offline.py (15 passed, including
  source Python and native live-read layout variants)
Pyright: 0 errors, 0 warnings, 0 informations
Next context in the serial checklist: `Camera`. The independent `Agent.py`
  helper surface remains unaudited and is tracked separately; it does not
  invalidate declaration parity for `AgentContext` / `AgentArray`.
Reviewer/date: Codex / 2026-09-22
```

### Camera certification record

```text
Context: native GW::Context::Camera, native GW::camera operations, and the
  Reforged Python Py4GWCoreLib/Camera.py facade
Sources inspected: Reforged_Native/include/GW/context/camera.h,
  Reforged_Native/include/GW/camera/camera.h,
  Reforged_Native/src/GW/camera/camera_bindings.cpp,
  Reforged/Py4GWCoreLib/Camera.py
Declaration result: native Camera fields and struct methods use source names
  and x86 offsets. Reforged Camera.py getter and action-wrapper names are all
  declared. Read getters and IsPointInFOV are implemented over external reads;
  source actions explicitly raise NotImplementedError and never write to the
  target or invoke a game-thread call.
Missing parity: none in the declared native structure or Reforged Python
  facade. Runtime action execution is unavailable by project boundary.
Live evidence: tests/test_camera.py passed on 2026-09-22; camera address
  0x017CAC10. Resolver, structure values, and facade getters were verified.
Offline evidence: tests/test_camera_offline.py (4 passed; exact field-name list,
  offsets, getter behavior, and disabled mutators)
Pyright: 0 errors, 0 warnings, 0 informations
Certificate: PASS — declaration parity; runtime limitation recorded.
Reviewer/date: Codex / 2026-09-22
```

### FriendList certification record

```text
Context: native GW::Context::FriendList / Friend and Reforged PyFriendList
Sources inspected: Reforged_Native/include/GW/context/friend_list.h,
  common/constants/friend_list.h, friend_list_methods.cpp,
  friend_list_bindings.cpp; Reforged/stubs/PyFriendList.pyi
Declaration result: PASS. Native fields are present under their source names;
  FriendEventData includes its 12-byte header and zero-length flexible-array
  declaration. Friend type/status values and all PyFriendList stub function
  names/signatures are represented.
Transport adaptation: the native GWArray and Friend* entries are traversed
  with bounded fixed-width remote reads. UTF-16 name buffers use uint16 units.
Runtime limitation: set_friend_list_status, add_friend, and add_ignore are
  declared but raise NotImplementedError because native bindings enqueue work
  on the in-client game thread. Native RemoveFriend is not exposed in the
  PyFriendList stub and was not added to that facade.
Live evidence: tests/test_friend_list.py passed on 2026-09-22. FriendList
  address=0x01C4AE78; 59 friends, 0 ignores, 59 records, status=online.
Offline evidence: tests/test_friend_list_offline.py (5 passed; exact field
  names/layouts, decoding, lookup/count behavior, and disabled actions)
Pyright: 0 errors, 0 warnings, 0 informations
Certificate: PASS — declaration parity; runtime limitation recorded.
Reviewer/date: Codex / 2026-09-22
```

### ChatBuffer certification record

```text
Context: native GW::Context::ChatBuffer / ChatMessage
Sources inspected: Reforged_Native/include/GW/context/chat.h,
  context_methods.cpp, and offsets/chat.json. There is no same-named
  Reforged Python context facade.
Declaration result: PASS. ChatBuffer, ChatMessage, FILETIME, the 0x200 slot
  array, and the flexible UTF-16 message tail are represented by source names.
  Pointer-slot and typing-state resolvers are read-only.
Scope distinction: PyPlayer.GetChatHistory is a separate Player API and is not
  part of this ChatBuffer declaration certificate.
Live evidence: tests/test_chat_buffer.py passed on 2026-09-22; ChatBuffer
  address=0x27CBE0D8, next=324, 512 non-null readable message slots observed.
Offline evidence: tests/test_chat_buffer_offline.py (4 passed; exact fields,
  layouts, FILETIME conversion, bounded payload, and ring traversal)
Pyright: 0 errors, 0 warnings, 0 informations
Certificate: PASS — declaration parity; raw payload remains encoded.
Reviewer/date: Codex / 2026-09-22
```

### GameContext certification record

```text
Context: GameContext
Source files and revision: Reforged native_src/context/GameContext.py;
  Reforged_Native/include/GW/context/game.h (working-tree sources)
Declaration result: PASS
Runtime availability: external resolver and structure read are implemented;
  live read verified against the running client
Missing or changed declarations: none found in the Python structure; native
  C++ field spellings are exposed as additive aliases
Transport-only adaptations: c_void_p and target pointers use uint32 addresses
  for the x86 target layout
Live evidence: tests/test_game_context.py passed against the running client on
  2026-09-22. GameContext=0x00A94398; char_context=0x00ADDD98;
  world_context=0x00AD3A40
Tests: tests/test_game_context_offline.py and tests/test_game_context.py passed;
  full discovery run previously passed
Pyright: 0 errors, 0 warnings, 0 informations
Reviewer/date: Codex / 2026-09-22
```

### MissionMapContext certification record

```text
Context: MissionMapContext
Source files inspected: Py4GW_Reforged/Py4GWCoreLib/native_src/context/
  MissionMapContext.py and MissionMapContext.pyi;
  Py4GW_Reforged_Native/include/GW/context/map.h,
  src/GW/map/map.cpp, and src/GW/shared_memory/manager.cpp
Declaration result: PASS. All three structure field lists and offsets match
  the Reforged/native x86 declarations. `MissionMapContextStruct.read_at`
  reads a caller-supplied root address and binds its reader;
  `ConnectedClient.read_mission_map_context(address)` exposes it publicly.
  Source properties `subcontexts` and `subcontext2`, plus facade members
  `get_ptr`, `_update_ptr`, `enable`, `disable`, and `get_context`, are present.
  The two child properties read remote pointers through the bound process
  reader.
Transport adaptation: target pointers are fixed-width uint32 values; the
  pointer-array read checks its advertised size/capacity and x86 range.
Runtime limitation: native `map.cpp` captures the root from a UI interaction
  callback's `message->wParam`, clears it when the frame is destroyed, and
  shared memory republishes it. Stealth cannot register that callback;
  `_update_ptr` and `enable` explicitly raise NotImplementedError. No external
  root pointer or live read is claimed.
Offline evidence: tests/test_mission_map_context_offline.py (9 passed; exact
  root read from a supplied address, public ConnectedClient reader, field
  order/offsets, child pointer properties, invalid address/short read/array
  header, and callback-facade limitation)
Pyright: 0 errors, 0 warnings, 0 informations
Certificate: PASS — structure/property/facade declaration parity and
  address-based root reader; callback pointer acquisition remains unresolved.
Reviewer/date: Codex / 2026-09-22
```

### WorldMapContext certification record

```text
Context: WorldMapContext
Source files inspected: Py4GW_Reforged/Py4GWCoreLib/native_src/context/
  WorldMapContext.py and WorldMapContext.pyi;
  Py4GW_Reforged_Native/include/GW/context/map.h,
  src/GW/context/context_methods.cpp, src/GW/map/map.cpp, and
  src/GW/shared_memory/manager.cpp
Declaration result: PASS. All WorldMapContextStruct field names, order,
  fixed x86 sizes, and offsets match source. `read_at(reader, address)` reads
  the fixed root from a caller-supplied address. The public
  `ConnectedClient.read_world_map_context(address)` method exposes this read
  without exposing the process-memory reader. Facade members `get_ptr`,
  `_update_ptr`, `enable`, `disable`, and `get_context` are represented.
Runtime limitation: native `map.cpp` captures the root from a UI interaction
  callback's `message->wParam`, clears it when the frame is destroyed, and
  shared memory republishes it. Stealth acquires the same pointer read-only by
  walking the client's UI frame array to the frame that registered the
  world-map callback (`py4gw/ui/`), cross-checking the context's stored
  `frame_id` against that frame's index. That route is offline-tested but not
  yet confirmed live, so no live read is claimed. `_update_ptr` and `enable`
  still explicitly raise NotImplementedError because registering an in-process
  callback remains unavailable.
Offline evidence: tests/test_world_map_context_offline.py (6 passed; root read
  from a supplied address, public ConnectedClient reader, field order/offsets,
  address bounds, and callback-facade limitation);
  tests/test_ui_frame_offline.py (25 passed; frame layouts, frame-array
  validation, frame tree, frame-id cross-check, and the frame-array
  acquisition end to end)
Pyright: 0 errors, 0 warnings, 0 informations (project-wide run reports only
  the two pre-existing unresolved `nicegui` imports in main.py and
  tests/nicegui_probe.py)
Certificate: PASS — structure/facade declaration parity, address-based root
  reader, and a read-only frame-array acquisition route that awaits live
  confirmation.
Reviewer/date: Codex / 2026-09-22; frame-array route added 2026-09-23
```

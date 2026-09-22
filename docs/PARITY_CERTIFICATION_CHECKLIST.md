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
| `AccAgentContext` | NOT AUDITED | NOT AUDITED | NOT AUDITED |
| `AgentContext` / `AgentArray` | NOT AUDITED | NOT AUDITED | NOT AUDITED |
| `Camera` | NOT AUDITED | NOT AUDITED | NOT AUDITED |
| `FriendList` | NOT AUDITED | NOT AUDITED | NOT AUDITED |
| `ChatBuffer` | NOT AUDITED | NOT AUDITED | NOT AUDITED |
| `WorldContext` | NOT AUDITED | NOT AUDITED | NOT AUDITED |
| `TradeContext` | NOT AUDITED | NOT AUDITED | NOT AUDITED |
| `ItemContext` | NOT AUDITED | NOT AUDITED | NOT AUDITED |
| `AccountContext` | NOT AUDITED | NOT AUDITED | NOT AUDITED |
| `GadgetContext` | NOT AUDITED | NOT AUDITED | NOT AUDITED |
| `MapContext` | NOT AUDITED | NOT AUDITED | NOT AUDITED |
| `MissionMapContext` | NOT AUDITED | NOT AUDITED | NOT AUDITED |
| `WorldMapContext` | NOT AUDITED | NOT AUDITED | NOT AUDITED |
| Render/UI/salvage surfaces | NOT AUDITED | NOT AUDITED | NOT AUDITED |

## Current certification state

`CharContext`, `GameContext`, `PreGameContext`, `Cinematic`, `GameplayContext`,
`ServerRegion`, `InstanceInfo`, `TextParser`, `AvailableCharacterArray`, and
`PartyContext`, and `GuildContext`
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

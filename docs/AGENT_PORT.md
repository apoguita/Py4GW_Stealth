# Agent port

**Where this sits in the order.** This is the queue for item 5 of
[`CLASS_PORT_MAP.md`](CLASS_PORT_MAP.md) §6 ("the context-backed classes, one at a time"), and it is
**not** the next thing to port: `Player` is INCOMPLETE, its remaining members come first (item 3's
string region is what its four chat sends need), and `Agent` is reached *as a dependency of*
`Player.GetInstanceUptime` — one member that delegates to it. The queue below is prepared so that
work can start the moment that member is taken; nothing here is worked ahead of `Player`.

The class `Dialog`, `Player`, `Party` and the rest of the library are written on top of: every
"which agent is this, what is it doing, where is it" question in Reforged's Python goes through
`Py4GWCoreLib/Agent.py`. It is the first of the context-backed classes in the order the class map
lays out ([`CLASS_PORT_MAP.md`](CLASS_PORT_MAP.md) §6.5), and this is its work queue.

**Source:** `Py4GW_Reforged/Py4GWCoreLib/Agent.py` — 1,541 lines, `class Agent:` at line 13, **148
members, all `@staticmethod`** (146 plain, 2 also carrying `@frame_cache`). Nothing in it is
instance state: every member takes an `agent_id` and reads.

**The count was 147 until 2026-09-26, and the correction matters for the surface test.** The
source declares `GetAnimationCode` as `def GetAnimationCode (agent_id : int) -> int:`
(`Agent.py:567-568`) — with a space before its parenthesis — so any `def \w+\(` pattern misses
exactly that member. The port and `tests/test_agent_offline.py` use a whitespace-tolerant pattern
and assert 148, and the member is ported like the rest.

## What it needs, measured rather than assumed

Counted from the file itself (the commands are at the end):

| the class's bodies reach | how often | state here |
| --- | ---: | --- |
| `AgentContext` (`AgentStruct`, `AgentLivingStruct`, `AgentItemStruct`, `AgentGadgetStruct`) | the class's whole read surface | **ported** — `py4gw/context/agent_array.py` (the source's `AgentArrayStruct` and its `AgentArray` facade, 1567 lines): `client.agent_array.get_context()` hands out the view, the view's `Get*Array`/`GetAgentByID` are the source's own lookups, and the records themselves come from `Agent.GetAgentByID` |
| `AttributeStruct` (from `WorldContext`) | `GetAttributes` and its neighbours | **ported** — `py4gw/context/world_context.py` |
| `GWContext` | 2 | **ported** — `py4gw/context/game_context.py` |
| `PyAgent` | 8 uses, of which **3 are `get_agent_enc_name`** | the binding surface: `offsets/agent.json` carries the `agent` area's resolvers, and `PyAgent`'s 39 names are the inventory for the rest |
| `PyCallback` (a `Phase.PreUpdate` registration) | 1 | **not ported, and not portable as written**: there is no frame loop here, so the members read when they are called (`PORTING_RULES.md`, `@frame_cache`) |
| `@frame_cache` on 2 members | 2 | **dropped for the same reason** — the decorator's only invalidation is Reforged's per-frame tick |
| `PySystem.Console` (diagnostics) | 2 | **not carried over** — Reforged's console lives *inside* the client; the returns the diagnostics accompany are ported |
| `Utils` (`calculate_energy_pips`, `calculate_health_pips`) | 2 | **ported 2026-09-26** — `py4gw/py4gwcorelib_src/utils.py`; `GetEnergyPips` and `GetHealthPips` are implemented and pinned in `tests/test_agent_offline.py`'s read table ([`UTILS_PORT.md`](UTILS_PORT.md)) |
| `encoded_wstr_to_str`, `string_table.decode` | name decoding | **ported** — `py4gw/internals/helpers.py`, `py4gw/internals/string_table.py` (the GW.dat chain) |

So `Agent` is a class whose reads are all context-backed: the mechanism work it needs is the
three `PyAgent.get_agent_enc_name` calls and whatever the enc-name members do with them. That is
why the class map files it under "no mechanism work at all".

## The work, in order

1. **The structure first**, as [`PORTING_RULES.md`](PORTING_RULES.md#full-class-ports-only) requires:
   `py4gw/agent.py` declares `class Agent` with **all 148 members** in the source's own order and
   shapes, each carrying its source line and, where its body cannot be written yet, a
   `NotImplementedError` naming exactly what it still needs.
2. **The read members** — the majority: they read one `AgentStruct` field or a small arithmetic
   combination of them through the ported context, and the two `@frame_cache` ones lose the
   decorator and read when called.
3. **The name members** — `GetNameByID`, `IsNameReady`, `GetEncNameByID`, `GetEncNameStrByID`,
   `GetAgentIDByName`, `GetAgentIDByEncString`, `GetModelIDByEncString`. **Landed 2026-09-26** with
   `PyAgent.get_agent_enc_name` (see below); the decode half was already ported (the string table and
   `helpers.encoded_wstr_to_str`).
4. **The derived members** — profession names and texture paths, conditions and stances, casting and
   target state, item/gadget extras: each one is a member of its own with its own source lines, and
   several read `Skill`/`Utils` (the two `Player` members that do are named in
   [`PLAYER_PORT.md`](PLAYER_PORT.md)); a member that needs one of those records that need in its
   body rather than approximating it.
5. **The verdict**, in the same change that moves the class: it goes into
   [`CLASS_PORT_MAP.md`](CLASS_PORT_MAP.md) §1 as INCOMPLETE until the last member works, with each
   remaining member named here.

## Where the class stands (2026-09-26)

**Verdict (2026-09-27): COMPLETE for this port's purposes -- three structural members, and not portable
work.** `Agent` declares **148** members; **145 answer** and **3 raise**, and the three raise because of
what they need rather than because work is outstanding: `enable` and `_invalidate_property_cache` are
Reforged's per-frame cache registration (this port has no frame loop, and `PORTING_RULES.md` forbids
standing in a throttle of our own), and `GetProfessionsTexturePaths` returns paths rooted in the injected
runtime's own module directory, which a controller package does not have. The verdict takes the same form
`Player` carries for its one artifact member in `CLASS_PORT_MAP.md`, and it is not the word FULL: FULL
means every member answers, and three do not. **`AgentArray` is FULL** -- no raising member at all,
verified from the module's own AST. The name members' decode step is Native's since 2026-09-27
(`AsyncGetAgentName`'s route: ~115 ms per name against ~2.1 s for the host-side table route), recorded
below and in `STRING_DECODE_PLAN.md` section 10.

**148 members declared, 145 answer, 3 raise** — all three directly. Two passes closed ten of the
thirteen: the name members with `PyAgent.get_agent_enc_name` (`GetNameByID`, `GetEncNameByID`,
`GetEncNameStrByID` and, through them, `IsNameReady`, `GetAgentIDByName`, `GetAgentIDByEncString`,
`GetModelIDByEncString` and the `RequestName` alias), and `IsMartial`/`IsMelee` with the ported
`Effects` (`py4gw/effect.py`, [`EFFECT_PORT.md`](EFFECT_PORT.md)). Earlier dependencies that each
moved a member: `Utils` gave `GetEnergyPips`/`GetHealthPips`
(`Utils.calculate_energy_pips`/`calculate_health_pips`, [`UTILS_PORT.md`](UTILS_PORT.md)), `Skill`
(`py4gw/skill.py`, [`SKILL_PORT.md`](SKILL_PORT.md)) removed the other half of `IsMartial`/`IsMelee`'s
block — `Skill.GetID("Illusionary_Weaponry")` answers `33` now — and `UIManager.GetFPSLimit` landed
with `GetInstanceUptime`. The three that remain are named in
[`CLASS_PORT_MAP.md`](CLASS_PORT_MAP.md) §1: `PySystem.Console.get_projects_path` (1 —
`GetProfessionsTexturePaths`) and the two frame-loop members.

### The name binding, ported (2026-09-26)

**It was never target-side work, and the earlier note that called it that was wrong.**
`PyAgent.get_agent_enc_name` (`agent_bindings.cpp:216-224`) is a two-step binding: it calls
**native's own** `GW::agent::GetAgentEncName` (`agent_methods.cpp:249-316`) and copies the wide
string that answers — `(n + 1) * sizeof(wchar_t)` bytes, the terminator included, or an empty vector
for a null pointer. That function is Py4GW's C++, not the client's, and it is a walk over state this
port already reads, so the port is read-only and needs no call into the client:

| native's step | where the port reads it |
| --- | --- |
| `GetAgentByID(agent_id)` (`agent_methods.cpp:73-88`) | `Agent.GetAgentByID` → `AgentArray.GetAgentByID` → the array view (the source's own chain) |
| `world->agent_infos[agent_id].name_enc` | `WorldContextStruct.agent_name_info_array` + `AgentNameInfoStruct.name_enc_ptr` |
| `players[login_number].name_enc` | `WorldContextStruct.players_array` + `PlayerStruct.name_enc_ptr` |
| `GetNPCByID(player_number)->name_enc` (`agent_methods.cpp:126-129`) | `WorldContextStruct.npc_models_array` + `NPC_ModelStruct.name_enc_ptr` |
| `agent_summary_info[agent_id].extra_info_sub` → `gadget_name_enc`, then `gadget_id` | `AccAgentContextStruct.agent_summary_info` + `AgentSummaryInfoStruct.extra_info_sub` + `AgentSummaryInfoSubStruct` |
| `gadget_info[id].name_enc` | `GadgetContextStruct.gadget_info` + `GadgetInfoStruct.name_enc` |
| `item::GetItemById(item_id)->name_enc` (`item_methods.cpp:109-112`) | `ItemContextStruct.GetItemById` (**added with this work**, `py4gw/context/item_context.py`) |

Every array index is the source's — `at(agent_id)`, `at(login_number)`, `gadget_info[gadget_id]`,
`GetItemById(item_id)` — read through the ported `GWArrayValueView`/`GWArrayView`, behind the same
`< size()` bound the source uses, so nothing is materialized to answer one lookup.

**One bound the source does not have, and it is the only divergence.** The binding walks the client's
`wchar_t*` to its terminator because that pointer is an address in its own process; this port reads
it through a bounded `ReadProcessMemory`, so the copy stops at the terminator or at
`MAX_ENC_NAME_CODE_UNITS` (256 code units, `py4gw/agent.py`). The bytes read are the answer, the way
`read_wstr` and `MAX_DAT_FILE_BYTES` answer the same problem elsewhere in the port.

**What it closed, and one member elsewhere.** 8 of the 13 raisers answer now, and
`Player.GetName` — which had been *adapted* to read the character context's name field because this
binding was missing — is the source's own body again, `Agent.GetNameByID(Player.GetAgentID())`
(`py4gw/player.py`). Its docstring records the one consequence that comes with it: the decode answers
`""` on the first call for a string it has not cached, which is Reforged's own two-call shape.

### The 13 were re-walked member by member, and the walk is a test

Each raiser's recorded requirement was checked against the line it cites:

| raiser | requirement as recorded | checked |
| --- | --- | --- |
| `_invalidate_property_cache` | the four caches it clears (`Agent.py:40-50`) | `_agent_cache`/`_living_cache`/`_item_cache`/`_gadget_cache` at `40-43`, the clears at `46-50` ✓ |
| `enable` | `PyCallback.PyCallback.Register(..., Phase.PreUpdate, ..., priority=7)` (`Agent.py:52-60`) | `Agent.py:52-60` ✓ |
| ~~`GetNameByID`, `GetEncNameByID`, `GetEncNameStrByID`~~ | ~~`PyAgent.get_agent_enc_name` (`agent_bindings.cpp:216`, `stubs/PyAgent.pyi:98`)~~ | `216` is `m.def("get_agent_enc_name", …)` over `GW::agent::GetAgentEncName(id)`; `98` is the stub ✓ — **ported 2026-09-26, so these three answer** |
| ~~`IsMartial`, `IsMelee`~~ | ~~`Effects.HasEffect` (`Effect.py:102`)~~ | `102` is `HasEffect` → `EffectExists(...) or BuffExists(...)` over `PyEffects.PyEffects(agent_id)` ✓ — **ported 2026-09-26, so both answer** ([`EFFECT_PORT.md`](EFFECT_PORT.md)) |
| `GetProfessionsTexturePaths` | `PySystem.Console.get_projects_path` (`stubs/PySystem.pyi:105`) | `105` is `get_projects_path()` → "the path where Py4GW.dll is located" ✓ |
| ~~`IsNameReady`, `GetAgentIDByName`, `GetAgentIDByEncString`, `GetModelIDByEncString`, `RequestName`~~ | ~~call a raiser (the source's own call graph)~~ | four by `ast` call-graph, `RequestName` as the source's alias (`Agent.py:149`) ✓ — **all five answer now that the name readers do**; and the port of `Effects` on 2026-09-26 took `IsMartial`/`IsMelee` out of the set too |

The two checks that came out of the walk are in `tests/test_agent_offline.py`
(`AgentSourceReferenceTests`): **every member's docstring reference is its own block in the source**
(148 of 148 — the reference starts at the member's first decorator and reaches its last line; it
caught one real off-by-one, `GetRotationSin`, which named `750` for a member that starts at `751`),
and **the raising set is exactly the three names above**, computed from the port's own `ast` rather
than counted by hand.

### The name walk, verified live (2026-09-26)

`tests/probe_agent_effects_live.py` ran the ported walk against a running client (`Gw.exe` pid
46544) **without elevation**, by building the client's own facades over the read-only reader and
registering them as the current client. All four branches of `GW::agent::GetAgentEncName`
(`agent_methods.cpp:263-316`) answered: **player array 55, world `agent_infos` 26, NPC record 7,
gadget context 2** of the 93 non-null agent records, and the ported `get_agent_enc_name` returned
exactly the bytes an independent read of the same pointer returned for every one of the 90 named
records. **55 player names decoded** through `Agent.GetNameByID` with no string table at all — the
inline `0x0BA9` form — such as `Blacki D Dragon` and `Twiddly Knobs`. The names that are not player
names are string-table indices and need the table GW.dat fills (a call into the client), so that half
is `tests/test_live_agent_effects.py`'s. `docs/RESEARCH.md` carries the full observation; the offline
fixture now reproduces the live byte shape exactly.

**Two costs in that walk were wrong, and both are about how the sources gather a name** (the owner's
catch, 2026-09-26):

- **The string table belongs to startup.** Reforged loads it once on the first frame
  (`TextContext.py:152-155`); this port loaded it inside the first `Agent.GetNameByID` — and again on
  every read while it had not succeeded. It is now loaded by the connection
  (`ConnectedClient.__init__`), and `test_the_string_table_is_loaded_by_the_connection` pins it.
- **The record is a table index.** Native's `GetAgentEncName` reaches the record through
  `GW::agent::GetAgentByID` — one index into the client's agent table plus the movement check
  (`agent_methods.cpp:73-88`), ported as `_get_agent_by_id` here. The port had called Reforged's
  *Python* `Agent.GetAgentByID`, whose view answers from `_build_allegiance_cache`: a traversal of
  every slot to answer one id. Live, on the same client: **0.09 ms** per name against **2.10 ms**
  for the view-cache path cold. Both halves are indexed now, the movement array included.

### The agent viewer's own scheme, and one name end to end (2026-09-27)

The owner's instruction was to follow the scheme the Reforged branch's **agent viewer** uses, because
that is the one known to work. It is `Widgets/Coding/Debug/Guild Wars/Agent Info.py` (`MODULE_NAME =
"Agent Info Viewer"`), and its scheme is the port's own, read member by member:

| the viewer | line | what the port has |
| --- | --- | --- |
| rows from `AgentArray.GetAgentArray()` + `Agent.GetAgentByID(agent_id)` | `:519-524` | `py4gw/agent_array.py`, `client.agent_array` |
| the name column: `Agent.GetNameByID(agent.agent_id)` | `:53`, `:77` | `py4gw/agent.py:508-527` — `get_agent_enc_name` + `string_table.decode` (`Agent.py:142-147`) |
| the encoded columns: `Agent.GetEncNameByID` / `GetEncNameStrByID` | `:49`, `:90` | `py4gw/agent.py:536-554` (`Agent.py:156-179`) |
| its pending display: `string_table._string_table_loaded`, `_load_enqueued`, `_last_load_status`, `raw in _pending` | `:61-68` | the same four names, `py4gw/internals/string_table.py:226-240` |

So the member set and the body were already the source's; what was missing was **proof**, at the
smallest size a caller can ask for. `tests/probe_name_scheme.py` (new) takes one agent and prints every
value between the fetch and the text. Live, agent **15** (client `Gw.exe` pid 20496):

```text
type = 0x200 (gadget, agent.h:136)      encoded = \x0C6E  -> entry index 2926, no key
agent_summary_info[15].extra_info_sub   = 0x278A_... (record read)
   gadget_name_enc = 0 (null)           gadget_id = 75
gadget_info[75].name_enc                = 672027352  -- the pointer the port read the name from
table: language 0, entries_per_file 1024, slot 2, start_index = 2 * 1024 = 2048
decoded: "Random Arenas"
```

That is native's gadget branch (`agent_methods.cpp:290-307`) executed against the live client with the
same null `gadget_name_enc`, the same `gadget_id` and the same record, and entry 2926 is in slot 2 —
exactly the file `_load_table_for_language` reads for that index (`string_table.py:766-805`).

**Five more agents in the same run, and four of them are names anyone can check:**

| id | type | encoded | text | what it is |
| ---: | --- | --- | --- | --- |
| 15 | `0x200` gadget | `\x0C6E` | `Random Arenas` | a portal prototype |
| 16 | `0x200` gadget | `\x0C9E` | `Great Temple of Balthazar` | a portal prototype |
| 26 | `0xDB` living | `\x8102\x064F` | `Vekk` | a hero, by name |
| 27 | `0xDB` living | `\x8101\x38AA` | `Dunkoro` | a hero, by name |
| 28 | `0xDB` living | `\x0BAA\x0107...` | `Pet - %str1%` | a pet-name pattern |
| 29 | `0x200` gadget | `\x8102\x35B5\xE9AA...` | `Zaishen Chest` | the chest |

`Vekk`, `Dunkoro` and `Zaishen Chest` are the client's own names for those records, and two of them
decode through the table's RC4 path — a wrong index or a wrong key cannot produce them. **`Random
Arenas` is a map name out of the sources' own table** (`Py4GW_Reforged_Native/include/GW/common/
constants/maps.h:954`), so the objects that carry it are the client's **gadget prototypes named after
their destination** — the portals.

**The map settles what those two names are.** The same run printed `map_id = 280`, and the sources'
own table names it: `NAME_FROM_ID[280] = "Isle of the Nameless"` (the array at `maps.h:765`; the
`MapID` enum agrees — 279 `Leviathan Pits`, 280 `Isle_of_the_Nameless`, 281
`Zaishen_Challenge_outpost`). The Isle of the Nameless is where the **Zaishen Chest** stands and where
the **portals to the Battle Isles outposts** are — so agent 15 and agent 16 are the portals to Random
Arenas and to the Great Temple of Balthazar, named as their destinations, in the same map as the chest.
The names are the client's own, read out of its own gadget-prototype table.

**And the fetch is cross-validated by a second client field:** `Agent.GetGadgetID` (the agent record's
own `gadget_id`, `Agent.py:1600-1606`, `agent.h:177`) answers **75** for agent 15 and **3651** for
agent 16 — the same ids the summary sub-record carries, which is the field native's walk indexes
`gadget_info` with. Two independent client fields agree, so the record the port indexed is the record
native indexes.

**Two costs measured in that run, and one open question:**

- **The slot mapping is live-verified for the first time.** `language_id = 0`, `entries_per_file = 1024`,
  `slot_count = 99`, and slots 0-7 each carry `start_index == slot_index * 1024` with `end_index` one
  file further on and `lang_id = 0`. The assumption `_parse_string_file(file_data, slot_idx * epf)`
  rests on holds on this client.
- **The decode is Native's, and that is this port's one deliberate divergence on this member
  (2026-09-27).** `Agent.GetNameByID` keeps the source's name, its position and its two-call shape, but
  the *decode* step is `GW::agent::AsyncGetAgentName`'s (`agent_methods.cpp:318-325`): the encoded string
  is handed to the client's own decoder and the text comes back from its completion. Reforged's
  `string_table.decode` is the same step done on the host, and it is only cheap *inside* the client —
  here one string file is a dat record that costs **~2.1 s** (open ~1.1 s, read and decompress 91 KB
  ~0.9 s), which is why the first name in a slot took seconds. Measured live on the same client: the
  client's route answers in **~115 ms** the first time and **0.09-0.5 ms** after, agrees with the table
  decode on every agent sampled, and resolves `Pet - My Pet` where the table decode stops at
  `Pet - %str1%`. Nothing in the port reads that table any more; `load_string_table` remains for a caller
  that wants an entry rendered on the host. Details, numbers and the three defects fixed with it:
  `docs/STRING_DECODE_PLAN.md` § 10 and `docs/PORTING_PROGRESS.md` (round 12).
- **Open: the client's own decoder answered empty, and this route has never been proven here.** Native's
  route is `ui::AsyncDecodeStr`, ported at `py4gw/ui/async_decode.py`; every precondition was live
  (`ui.validate_async_decode_str_func` resolves, the decoder stub placed, the `TextParser` present) and
  each call round-tripped in ~130 ms, but all six strings came back `""`. `tests/test_live_dialog_text.py`
  records *why this is not yet a verdict on the client*: the dialog step that fills this decoder is
  blocked on this build (`DialogLoader_GetText` is not the loader here, and calling it faulted the client
  on 2026-09-25), so the route had never been called with an expected text before this round. `""` is
  also what the port's own three refusals write, so the next run adds a **control** — the local player's
  own encoded name, which the client renders on the nameplate — and reports the call's timings apart
  (placement, call, wait for the callback). Control empty means the emitted stub or the slot the host
  reads is the defect; control is the character's name means the client is refusing these strings, which
  is a finding about the strings and not about the table decode that four of the six names above prove.

### The three members that remain, and why none of them is porting work

| member | what it needs | why it is not an open work item |
| --- | --- | --- |
| `enable` | `PyCallback.PyCallback.Register("Agent.InvalidatePropertyCache", Phase.PreUpdate, Agent._invalidate_property_cache, priority=7)` (`Agent.py:52-60`) | The registration's *only* effect is a per-frame tick that clears four record caches. This port has no frame loop and nothing to dispatch to, and `PORTING_RULES.md` § `@frame_cache` forbids standing in a throttle of our own; the record readers read when they are called instead |
| `_invalidate_property_cache` | the four caches it clears (`Agent.py:40-50`) | The caches exist only to be cleared by that tick; this port does not keep them, so there is nothing to invalidate |
| `GetProfessionsTexturePaths` | the root `PySystem.Console.get_projects_path()` returns — **the injected runtime's own module directory** (`system_bindings.cpp:72-74` → `process_manager::GetModuleDirectory`, `process_manager.cpp:38-40`), where its `Assets/Textures/Profession_Icons` live | This project is a controller package: it has no such module and ships no such assets, so there is no path to build. The member is the **third of the artifact kind** — `AGENTS.md` now names all three — and it reports that rather than returning a string the source never produces |

Everything else in the class answers: **145 of 148**, with the two passes above having closed the
other ten raisers.

**The walk's own branches are pinned offline** (`AgentEncNameTests`, 11 tests): a fixture builds the
records and a reader that serves them, so every branch — the agent record, the world agent-name
array, the player array by login number (and the null answer when the login number is past its size),
the NPC fallback, the agent-summary gadget entry, the gadget context's `gadget_info`, and the item
array by item id — is driven without a client, sizes and offsets taken from the ported structures.

## The context under the class, re-checked (2026-09-26)

`Agent` reads agents through `py4gw/context/agent_array.py`, the port of Reforged's
`native_src/context/AgentContext.py` (1501 lines). That module had grown **a layer of its own**;
**every member of it is now gone** (2026-09-26), and nothing in the module exists outside the
sources except the read path the external model needs:

| invented here | the sources' own answer | state |
| --- | --- | --- |
| `AgentAllegiance` (6 members, `ALLY_NON_ATTACKABLE`…, no `0`) | `Allegiance` — 7 members with `Unknown`, `Ally`, `Neutral`, `Enemy`, `SpiritPet`, `Minion`, `NpcMinipet` (`enums_src/GameData_enums.py`). The module imports that enum and every call site reads its member names | removed 2026-09-26 |
| `AgentKind` (`LIVING`/`GADGET`/`ITEM`/`UNKNOWN`, str-valued) | nothing — kind is `AgentStruct.is_item_type` (`type & 0x400`), `is_gadget_type` (`0x200`), `is_living_type` (`0xDB`), plus `GetAsAgentItem/Gadget/Living` | deleted |
| `Vec2fStruct`, `GamePositionStruct` | `Vec2f`, `Vec3f`, `GamePos` from `native_src/internals/types.py` — a source file that had never been ported. Ported 2026-09-26 as `py4gw/internals/types.py` | removed 2026-09-26 |
| `AgentReference`, `AgentArraySnapshot`, `LivingAgentSnapshot`, `StaleAgentReferenceError` | nothing — the array is read through `AgentArrayStruct`'s own members and `AgentArray`'s facade | deleted |
| `ReforgedItemDataStruct`, `ReforgedEquipmentItemsUnionStruct`, `ReforgedEquipmentStruct`, `ReforgedAgentLivingStruct` | the same structs without the invented prefix; the layout disagreement they encoded is a finding, and it is kept in the table below and in `tests/test_agent_array_offline.py` instead of as four duplicate classes | deleted |
| the facade members `read`, `read_agent`, `read_agent_by_id`, `snapshot`, `living_snapshot`, `refresh_living_agents`, `get_living_agent`, `_read_snapshot`, `_validate_reference_current`, `_read_record`, `_read_pointer_values`, `_read_pointer_at`, `_kind_from_type_flags`, `max_pointer_slots`, `max_references` (and `client.py`'s six wrappers over them) | the view's `Get*Array`/`GetAgentByID` and the records they answer with | deleted |
| `_agent_record_type` | nothing | deleted |

**What the module is now.** The source's own declarations, member for member: the value records
(`DyeInfo`, `ItemData`, `EquipmentItemsUnion`, `EquipmentItemIDsUnion`, `Equipment`, `TagInfo`,
`VisibleEffect`, `AgentNative`, `AgentLiving`, `AgentItem`, `AgentGadget`), the ctypes records and
their `snapshot()` methods, `AgentStruct`/`AgentItemStruct`/`AgentGadgetStruct`/`AgentLivingStruct`,
`AgentArrayStruct` with `raw_agents` + `_build_allegiance_cache` + `_ensure_cache_up_to_date` +
`GetAgentByID` + the twelve `Get*Array` members, and the `AgentArray` facade (`get_ptr`,
`_update_ptr`, `reset_cache`, `_update_cache`, `enable`, `disable`, `get_context`, `GetAgentByID`).

**The one thing beside them, and why it is there:** the source's `UpdatePtr` callback keeps a
pointer to the client's own `AgentArrayStruct` (`AgentContext.py:1405-1415`) and its `get_context`
returns whatever that callback cached. This project has no injected runtime and no frame loop, so
the facade carries the same external read path every other context here carries —
`resolve_address`/`initialize` (the `agent.agent_array_addr` resolver, cached once) and
`read_context` (the fixed-width `GWArray<Agent*>` header read into a local copy, bound to this
client's reader). `get_context` builds that view on first use instead of answering the `None` the
source answers before its first tick; a read that cannot be made raises from `read_context`. The
`_timed`/`_memory_reader` helpers beside it are the same read path's timer hook (the client passes
its `PerfCounter` into `initialize`) and the reader protocol annotation.

**Found while removing the layer, and worth its own pass:** the module-level `def get()` that ends
24 of the 25 other `py4gw/context/*.py` modules has **no counterpart in either source** —
Reforged's `native_src/context/*.py` declare no module-level functions at all except
`MapContext.py`'s private `_file_hash_to_file_id`/`_get_prop_model_file_id`, which the port has.
`agent_array.py`'s own `get()` was deleted in the previous round; the other 24 (and their ~60 call
sites in tests, probes and examples) are an open item in
[`PORTING_PROGRESS.md`](PORTING_PROGRESS.md).

**Where the two sources disagree, and which one the port reads with.** Reforged's Python
declarations and native's C++ `static_assert`s do not agree on the agent records:

| record | native C++ (asserted) | Reforged Python | this port reads with |
| --- | --- | --- | --- |
| `Agent` | `0xC4` (`agent.h:162`) | — | native |
| `AgentLiving` | `0x1C4`, `owner` at `0xC4` (`agent.h:278-279`) | `0x1C2` | native |
| `Equipment` | `0xD8` (`agent.h:82`) | `0xF3` | native |
| `ItemData` | `0x10`, `type` one byte (`item.h:34`) | `0x13`, `type` a `uint32` | native |
| `DyeInfo` | `0x3` (`item.h:25`) | `0x3` | both |

The client has one layout, and native's asserts are the ones measured against it, so live reads use
native's — the port's `AgentStruct`, `AgentLivingStruct`, `EquipmentStruct` and `ItemDataStruct` match
those sizes exactly. Reforged's declarations are what `Agent.py` calls when it builds its snapshots;
the `Reforged*` copies that used to sit beside them are **deleted** (2026-09-26), and this table is
the record of the disagreement — together with `tests/test_agent_array_offline.py`, which asserts
native's numbers and names Reforged's in its docstring.

**Also still to do under this class:** the two frame-loop members (`enable`,
`_invalidate_property_cache`) and `AgentArray.enable`, which in the source registers a `PyCallback`
PreUpdate hook at import (`AgentContext.py:1500`) — a port with no frame loop has to answer those the
way the class's own `enable` is answered.

## The record layouts, verified against the sources (2026-09-26)

Every field offset and every record size the port reads with was checked against the numbers the
sources themselves state, and they agree:

| record | this port | native's own assertion | source field comments |
| --- | --- | --- | --- |
| `AgentStruct` | `0xC4` | `sizeof(Agent) == 0xC4` (`agent.h:162`) | `name_properties` `0x58`, `terrain_normal` `0x64`, `pos` `0x74`, `type` `0x9C`, `velocity` `0xA0` — all matched (`AgentContext.py:425-446`) |
| `AgentLivingStruct` | `0x1C4` | `sizeof(AgentLiving) == 0x1C4`, `owner` at `0xC4` (`agent.h:278-279`) | `allegiance` `0x1B5`, `weapon_type` `0x1B6` — matched |
| `EquipmentStruct` | `0xD8` | `sizeof(Equipment) == 0xD8` (`agent.h:82`) | — |
| `ItemDataStruct` | `0x10` | `sizeof(ItemData) == 0x10`, `type` one byte (`item.h:34`) | Reforged's Python declares `type` a `uint32` and gets `0x13`; the client is native's |
| `DyeInfoStruct` | `0x3` | `sizeof(DyeInfo) == 0x3` (`item.h:25`) | — |

**Two more look-alike types went with them.** The agent context declared `Vec2fStruct` and
`GamePositionStruct` of its own for the records' `velocity` and `pos`, and imported a third
(`Vec3fStruct`) from `acc_agent_context` for `terrain_normal` — because Reforged's
`native_src/internals/types.py`, which declares `Vec2f`/`Vec3f`/`GamePos`, had never been ported.
It is ported now (`py4gw/internals/types.py`), and the records read through those names.

**Found on the way, outside this class:** `map_context.py` declares its own `MapVec2fStruct` (20+
sites, plus `mission_map_context`, `world_map_context`, both `__init__` files and a test) where the
source has one `Vec2f`; `acc_agent_context` still exports its own `Vec3fStruct`; and
`world_context.py:138` aliases `Vec2fStruct = Vec2f`. Same violation, other modules — their own pass.

## The AgentArray class, ported (2026-09-26)

`py4gw/agent_array.py` is the port of Reforged's `AgentArray.py` (482 lines) — a separate file
from the context, and it is now in the tree with every member:

| group | members |
| --- | --- |
| getters | `GetAgentArray`, `GetAllyArray`, `GetNeutralArray`, `GetEnemyArray`, `GetSpiritPetArray`, `GetMinionArray`, `GetNPCMinipetArray`, `GetItemArray`, `GetOwnedItemArray`, `GetGadgetArray`, `GetDeadAllyArray`, `GetDeadEnemyArray`, `GetAgentByID` |
| `Manipulation` | `Merge`, `Subtract`, `Intersect` |
| `Sort` | `ByAttribute`, `ByCondition`, `ByDistance`, `ByHealth` |
| `Filter` | `ByAttribute`, `ByCondition`, `ByDistance` |
| `Routines` | `DetectLargestAgentCluster` |

**The one divergence, and it is on the twelve array getters.** In the source each of them reads the
injected runtime's shared-memory channel — `SystemShaMemMgr.get_agent_array_wrapper()`, whose
`to_int_list()`/`get_ally_array()`/… are populated by a DLL inside the client. This project has no
such channel. **The source carries a second route in each of those members** —
`GWContext.AgentArray.GetContext().GetAgentArray()` and its siblings — which is unreachable there
because it sits after the `return` (`AgentArray.py:23-29`); this port answers from that route, over
this project's context view (`ConnectedClient.agent_array`), so the values come from the same client
array the DLL read. Closing the divergence means the shared-memory channel, and that is the work
item. `GetAgentByID` needs no divergence: the source's own live path there is already the context.

**Two things were wrong around it and are fixed:**

- **The package root had the wrong `AgentArray`.** Reforged's `__init__.py:101` does
  `from .AgentArray import *`, so `Py4GWCoreLib.AgentArray` is this class, and the context view is
  reached as `GWContext.AgentArray` (`Context.py:54`). This port had the context view under the
  package name. Now `py4gw.AgentArray` is the class and `py4gw.context.AgentArray` is the view.
- **The context view carried copies of three of its helper classes** — `Manipulation`, `Sort` and
  `Filter`, with docstrings that said they were *"copied from Reforged's AgentArray facade"*. They
  belong to this file, not to `AgentContext.py`, and they are deleted; `Routines` never had a copy.

**Verified by `tests/test_agent_array_class_offline.py`:** the source's module cannot be imported
(its first line is `import PyAgent`), so the test reads its surface with `ast` and compares the class,
its four nested classes and every member name and order; then it exercises the pure helpers with the
`Agent` members they call faked, and pins that each getter asks the connected client's context view.

## Reproducing these numbers

From `C:\Users\Apo\Py4GW_Reforged`:

```text
python - <<'PY'
import collections, re
src = open(r"Py4GWCoreLib\Agent.py", encoding="utf-8").read()
print("members", len(re.findall(r"^\s+def \w+\(", src, re.M)))
print("PyAgent", collections.Counter(re.findall(r"\bPyAgent\.(\w+)", src)))
print("GLOBAL_CACHE", collections.Counter(re.findall(r"GLOBAL_CACHE\.(\w+)", src)))
PY
```

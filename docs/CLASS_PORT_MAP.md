# Class port map

What is ported, what is not, and what each missing class actually depends on. This is
the **class layer's** counterpart to two documents that already exist:
[`CONTEXT_INVENTORY.md`](CONTEXT_INVENTORY.md) covers the **data layer** (the contexts
and their readers) and [`NATIVE_EXECUTION_PLAN.md`](NATIVE_EXECUTION_PLAN.md) covers
the **mechanisms** (hooks, calls, callbacks, and the forms the calls take).

Every count here was measured from the working trees on 2026-09-25; the commands are at
the end so they can be re-run rather than trusted.

## 1. The two layers, and where the port stands

**Every class carries a verdict**, and there are only two: **FULL** (every member of
the source surface works) or **INCOMPLETE** (the members still to port are named here,
with what each needs). A class with any member still to port is **INCOMPLETE and is not
called ported**; nothing is blocked or deferred, and the list beside each class is a work
queue. The rule is
[`PORTING_RULES.md` § Full class ports only](PORTING_RULES.md#full-class-ports-only).

| Class | Verdict | Remaining |
| --- | --- | --- |
| `Map` | **COMPLETE for this port's purposes (owner's ruling, 2026-09-29: *"mark this one as done, the things missing are the ones we already account for"*)** | **168 of 178 members answer; the ten that do not are the accounted-for divergences, and the class is done** (rounds 78-81). The whole class — `Map` 74/74, `MissionMap` 13/16, both `MapProjection`s 15+16, `MiniMap` 12/15, `WorldMap` 9/12, `Pregame` 9/9, `Pathing` 15/16 and `Quad` 5/5 — plus the source's **17 class attributes**. The ten are the **nine mouse members** (`MissionMap`/`MiniMap`/`WorldMap` × `IsMouseOver`, `GetLastClickCoords`, `GetLastRightClickCoords`), which read `PyImGui.get_io()` — the injected runtime's own ImGui, which nothing here installs and which cannot be installed — and **`Pathing.WorldToScreen`**, which is `PyOverlay.Overlay()` and `Overlay.FindZ`: the injected runtime's overlay manager, and this class has no render process. Each says so in its own body. Dependencies ported with it: `MapMethods` (`py4gw/map_methods.py`), `Checks.Map` (`py4gw/routines_src/Checks.py`), `FfnaMapMethods` (`py4gw/ffna_map_methods.py`) and `Pathing`'s navmesh half (`py4gw/pathing.py`). Round 78 also closed the class's own defects — the 17 undeclared attributes, three name halves that returned `""`, an invented duplicate `InstanceType`, three mis-transcribed signatures — and fixed `MissionMapContext`/`WorldMapContext._update_ptr`, which raised unconditionally below every `Map.MissionMap`/`Map.WorldMap` read. Per-member detail in [`MAP_PORT.md`](MAP_PORT.md) |
| `Player` | **COMPLETE for this port's purposes** (one obsolete artifact) | Every Reforged member works except `player_instance`, which is **an artifact of the port and no longer valid for anything**: it returned Reforged's in-process `PyPlayer` object, this project has no player object, and every value that object provided is answered by the class's own members (51 reading, 18 acting). The chat history is kept live by the connection's watched log; `GetInstanceUptime` is ported over native's `GW::ui::GetFrameLimit` (`py4gw/ui/preferences.py`). Live verification of the chat senders and of the watched history is owed. |
| `Utils` | INCOMPLETE | **3 of 40 members** (was 4). Landed 2026-09-26 as `py4gw/py4gwcorelib_src/utils.py` with `Color` (`color.py`), and unblocked four members elsewhere. `BalthazarSkillIdToDialogId`'s PvP remap landed with **`Skill`**, and `GenerateSkillbarTemplate` landed with **`Skillbar`** (both 2026-09-26). What is left needs target-side work rather than porting: `TokenizeMarkupText` (the client's own ImGui text measure) and `GwinchToPixels`/`PixelsToGwinch` (which raise from **`Map.MissionMap.GetScale`** — the frame's viewport scale, which needs the DX context the client only exposes through an `EndScene`/`Reset` detour). Per-member detail in [`UTILS_PORT.md`](UTILS_PORT.md) |
| `Skillbar` | INCOMPLETE | **6 of 18 members** (was: not ported at all). Landed 2026-09-26 as `py4gw/skillbar.py` over native's `PySkillbar` binding (`skillbar_bindings.cpp:25-142`) and the ported `WorldContext.party_skillbar_array`, with the client's current tooltip read added beside it (`py4gw/ui/tooltip.py`). **Every read works** — the eight slots, the owner/state words, the hero walk, both skill bitsets, the hovered-skill tooltip — plus `ChangeHeroSecondary`, whose resolver already existed. What is left: `UseSkill`/`UseSkillTargetless`/`HeroUseSkill` (the control-action mechanism, [`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md)), `LoadSkillTemplate`/`LoadHeroSkillTemplate` (native's `DecodeSkillTemplate` + gating), and the slot type's `get_recharge` (the skill timer). Per-member detail in [`SKILLBAR_PORT.md`](SKILLBAR_PORT.md) |
| `Skill` | INCOMPLETE | **8 of 87 members** (was: not ported at all). Landed 2026-09-26 as `py4gw/skill.py` over `py4gw/context/skill_context.py` (the client's `GW::Context::Skill` record, read from the static table the client itself indexes) and `py4gw/skill_names.py` (native's 3031-entry generated name table). Every record reader works, including `ExtraData.GetIDPvP` — the member `Utils.BalthazarSkillIdToDialogId` calls. What is left: `GetNameFromWiki`/`GetURL`/`GetProgressionData`/`GetDescription`/`GetConciseDescription` and the `_load_descriptions` they raise through (Reforged's bundled `skill_descriptions.json`, 1.98 MB), `GetCampaign` (`enums_src/Region_enums.py`'s `CampaignName`) and `ExtraData.GetTexturePath` (`enums_src/Texture_enums.py`'s `SkillTextureMap`). Per-member detail in [`SKILL_PORT.md`](SKILL_PORT.md) |
| `Party` | INCOMPLETE | the 30 action members |
| `Scanner` | FULL | — |
| `Agent` | **COMPLETE for this port's purposes** (three structural members, 2026-09-27) | **148 members declared, 145 answer, 3 raise** (was 13 on 2026-09-26) — the same verdict form `Player` carries, for the same reason: the three that do not answer cannot be ported, and each is named with the line that says why. **The `PyAgent.get_agent_enc_name` group landed** (the binding is ported as `py4gw.agent.get_agent_enc_name` over native's own `GW::agent::GetAgentEncName` walk — the agent record, the world agent-name array, the player array, `GetNPCByID`, the agent-summary gadget entry, the gadget context and `item::GetItemById`, all state this port already reads, so it was never target-side work), and **`Effects.HasEffect` landed with the `Effects` port** (`py4gw/effect.py`), which closed `IsMartial`/`IsMelee`. Those two passes also restored `Player.GetName` to the source's body. **The decode step is Native's** since 2026-09-27 (`Agent.GetNameByID` = `AsyncGetAgentName`'s route: the client decodes the string; measured ~115 ms first time against ~2.1 s for the host-side table route, and no dat record at all — `docs/STRING_DECODE_PLAN.md` § 10). The 3 that remain are **not portable work**: `enable` and `_invalidate_property_cache` are the two halves of Reforged's per-frame cache registration, which this port's execution model has no frame loop for (`AGENTS.md`, `PORTING_RULES.md` § `@frame_cache`; the `*ByID` readers read when called instead), and `GetProfessionsTexturePaths` prefixes its paths with `PySystem.Console.get_projects_path()`, which native defines as **the injected runtime's own module directory** (`system_bindings.cpp:72-74` → `process_manager.cpp:38-40`) — the third member of the artifact kind, with `Player.player_instance` and `Dialog._call_native_dialog_method`, reported rather than stood in for. Per-member detail in [`AGENT_PORT.md`](AGENT_PORT.md) |
| `AgentArray` context | **FULL — source-shaped (2026-09-26)** | `py4gw/context/agent_array.py` (1567 lines) is the port of `native_src/context/AgentContext.py` (1501 lines) with **no invented layer left**. Removed: `AgentAllegiance` (round 1), `Vec2fStruct`/`GamePositionStruct` (the ported `internals/types.py` supplies `Vec2f`/`Vec3f`/`GamePos`), and — this round — `AgentReference`, `AgentArraySnapshot`, `LivingAgentSnapshot`, `StaleAgentReferenceError`, `AgentKind`, `_agent_record_type`, the four `Reforged*Struct` duplicates, and every facade member that existed for them (`read`, `read_agent`, `read_agent_by_id`, `snapshot`, `living_snapshot`, `refresh_living_agents`, `get_living_agent`, `_read_snapshot`, `_validate_reference_current`, `_read_record`, `_read_pointer_values`, `_read_pointer_at`, `_kind_from_type_flags`, `max_pointer_slots`, `max_references`) together with `client.py`'s six wrappers over them. What is in the module is the source's own: the value records, the ctypes records and their `snapshot()` methods, `AgentArrayStruct` (`raw_agents`, `_build_allegiance_cache`, `_ensure_cache_up_to_date`, `GetAgentByID`, the twelve `Get*Array` members) and the `AgentArray` facade. The only members beside the source's are the external read path every context here needs (`resolve_address`/`initialize`/`read_context`/`_read_array_header`, `_timed`/`_memory_reader` for the client's `PerfCounter`). The record layouts read with native's `static_assert`s (`AgentStruct` 0xC4, `AgentLivingStruct` 0x1C4, `EquipmentStruct` 0xD8, `ItemDataStruct` 0x10); Reforged's Python declarations (0x1C2, 0xF3, 0x13) are recorded as a source-vs-source disagreement in [`AGENT_PORT.md`](AGENT_PORT.md) and in the struct test. |
| `AgentArray` (the class) | **FULL (2026-09-27)** | `py4gw/agent_array.py` is the port of Reforged's `AgentArray.py` with **no raising member** — verified from the module's own AST on 2026-09-27 — and every member is the source's: the thirteen getters (`GetAgentArray`, `GetAllyArray`, `GetNeutralArray`, `GetEnemyArray`, `GetSpiritPetArray`, `GetMinionArray`, `GetNPCMinipetArray`, …), both key sets, `Manipulation`, `Sort`, `Filter`, `distance_filter` and the rest. The per-frame `enable` the source registers is not a member of this class but of its **context** (`context/agent_array.py:1612`, a documented no-op: there is no frame loop to register against, and the view is built on demand), which is the row above. |
| `Dialog` | INCOMPLETE — **deferred to a later pass** | 31 of the 32 `PyDialog` members answer, a button's **caption is produced** (read where the source reads it, decoded by the client's own decoder, live 2026-09-25), both journals are ported and the tables resolve (the source's five `DialogMemory` constants, rebased in code — **no catalog file**). The one member that does not answer is `get_dialog_text_decoded`: it needs this build's `DialogLoader_GetText`, and it reports that rather than calling the sources' stale constant, so a **catalog dialog's `content`** — and the `get_dialog_info`/`enumerate_available_dialogs` rows that carry it — are not produced. **The project owner has parked it for a later pass**, not abandoned it: the 2026-09-26 pass over `Gw.exe` shows why the usual routes come up empty (this client *inlines* the text path into its dialog window — `DialogShow` reads the row's text id itself), so the two routes to identify it are tracing the announce path or hooking the confirmed text encoder, both named in [`RESEARCH.md`](RESEARCH.md) and [`DIALOG_PORT.md`](DIALOG_PORT.md). The sources are complete and 100% functional, so this is porting work that remains, not a divergence. |
| `Merchant` (`Trading`) | **FULL — every member answers, and the class is live-verified** | **32 of 32 declarations answer** (round 3), and **the live pass ran green twice** (round 4). All fifteen `PyMerchant` methods and all seventeen `Trading` members are ported whole, in the source's own order and nesting; **nothing refuses and no member is a work item**. The eight writes were the last members to land, and they needed four things this port did not have, all of them built in the same change: the **packet-callback capability** (`py4gw/game_thread/packets.py` — native's own handler replacement, `stoc_methods.cpp:55-57`, walked to through `stoc.handler_table_addr`), the **merchant listener** (`py4gw/listeners.py`, `listeners.h:51-92`, with `PY4GW::Timer` ported for its own 1000 ms throttle), the two `Context::MerchantTransactionInfo`/`MerchantQuoteInfo` records (`ui.h:364-374`) and `CallForm.STACK_WORDS`, which pushes the nine and eight words those records travel as. Everything else was already here: `item::GetItemById`, the two resolvers (`merchant.transact_item_func`/`request_quote_func`) and the game-thread call path that subsumes native's `Enqueue`. The five reads read the listener; `get_trader_item_list2` is native's own constant `{}` (“legacy never populated”, `merchant_bindings.cpp:200`) and `update` is its own no-op (`:205`). **Evidence**: the surface against both sources and every write's words by value (`tests/test_merchant_offline.py`), the walk/install/restore/recovery and the listener (`tests/test_listeners_offline.py`), the stub and the call form executed (`tests/test_payload_offline.py`), the client's handler chain read live and read-only (`tests/probe_stoc_handlers.py`), and **live at a merchant**: `WindowItems` presented **11 offered items through the callback**, and the first offered item was **bought twice, 50 gold each time**, with `TransactionDone` arriving through the same stub (gold 2040 → 1990 → 1940 — `tests/probe_merchant_pass_live.py`, two runs, 2026-09-30). **Owed and named**: live exercise of `WindowItemsEnd`/`ItemStreamEnd`/`QuotedItemPrice`, which a merchant's buy tab does not send (a *trader's* window does). Per-member detail in [`MERCHANT_PORT.md`](MERCHANT_PORT.md) |
| `UIManager` | **COMPLETE for this port's purposes (owner's ruling, 2026-09-27: *"whats left is not applicable here, we dont have frame logs"*)** | `py4gw/ui_manager.py` — Reforged's `class UIManager` (`UIManager.py:29-618`) declared **in full, in the source's own order**: all **55 declarations**, AST-compared name for name and nesting for nesting, with the source's class attributes (the overlay word, the dev-text cache, the nested `IOEvent` record, the two IO registries). **48 answer and 7 raise**, with **no conditional raise left** — `Keydown`/`Keyup`'s `frame_id == 0` path (the client's own button-action frame, walked the way native walks it) is built. Both counts are computed from the module's AST by `tests/test_ui_manager_offline.py`, which also pins the raising set. **The seven that raise are documented divergences, not pending work** (owner's ruling, 2026-09-27) — the runtime's own journals, its link-opening flag, and the two frame-loop members — and each is in [`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md); there is no plain porting gap left. The wrapper group resolves each binding to the `GW::ui` function behind it (`ui_bindings.cpp` → `ui_methods.cpp`), one member at a time — **eleven of Reforged's 41 calls have no binding in native's current revision**, and Native's own audit lists several as pending quick wins, so the member resolves the function the binding would wrap and says so. All **four typed preference setters** landed with their bodies in `py4gw/ui/preferences.py`; the raw/wider UI-message forms landed on the connection's own surface (`ConnectedClient.send_ui_message_raw`); and **the key-remap table is derived offline** (`ui.key_mappings_table`, `tools/key_mappings_hunt.py`). The dialog family is ported over `Frame`/`FrameTree` (`ClickDialogButton` is the live-verified `Frame.click`). The 14 window classes (619-1302) are out of scope permanently, the class's landed name is the owner's call (2026-09-27), and the class is **never** called ported until all 55 answer. |

The verdicts are the work queue: a class moves to FULL only when its remaining column
is empty, and what is named there is taken in dependency order. Two members report
themselves rather than waiting on work — `Player.player_instance` and
`Dialog._call_native_dialog_method` — because both return or consume an object the injected runtime
owns in-process; every other remaining item in this document is work with a name, and no item here
says a source feature is missing, because the sources are complete and working.

## The migrated classes at a glance (2026-09-27)

Every class this project has taken on, with what its own module says about it. **The counts are public
members counted from the module by `ast` on 2026-09-27** (`_`-prefixed members are excluded, the
`RequestName`-style aliases are not double-counted), and "raises" is a raise **written in that member's
own body**. A member can also fail *through* a member it calls, so **the port doc's verdict is
authoritative** wherever the two differ — the third column is only the shape of the code.

| module | class | members | raises (in its own body) | verdict |
| --- | --- | ---: | --- | --- |
| `py4gw/agent.py` | `Agent` | 146 (148 declared with the two private frame-loop halves) | 3 — `enable`, `_invalidate_property_cache`, `GetProfessionsTexturePaths` | **COMPLETE for this port's purposes** (three structural members: the frame loop ×2, the injected-runtime artifact ×1) |
| `py4gw/agent_array.py` | `AgentArray` | 13 | **0** | **FULL** |
| `py4gw/context/agent_array.py` | the array context + facade | — | 0 raising (1 documented no-op: `enable`) | **FULL — source-shaped** (no invented layer left) |
| `py4gw/player.py` | `Player` | 70 | 1 — `player_instance` (artifact) | **COMPLETE for this port's purposes** |
| `py4gw/camera.py` | `Camera` | 46 | **0** | **FULL (2026-09-27)** -- the whole source surface, no raising member: 30 getters over the ported `CameraStruct` (~5 us, live), `GetCurrentYaw` and `IsPointInFOV` as the source writes them, the 11 field writers through the payload's `WRITE_MEMORY` operation on the client's own thread, and the two patch members (`SetCameraUnlock`/`GetCameraUnlock`, `SetFog`) toggling Native's own bytes. Live: a write landed on the client's struct and was read back; the patch went `8b 45` -> `eb 0f` -> `8b 45` (`live_reports/camera_live2.txt`) |
| `py4gw/client.py` | `ConnectedClient` | 89 | 0 | FULL — the connection itself (this project's own surface, not a ported class) |
| `py4gw/dialog.py` | `Dialog` + `DialogTables` + the six record types | 32 + 5 + 9 | 0 direct | **INCOMPLETE** — one member: `get_dialog_text_decoded` needs this build's dialog loader; the owner parked it for a later pass |
| `py4gw/effect.py` | `Effects` + `PyEffects` | 15 + 10 | 1 — `GetAlcoholTimeRemaining` (a binding member that does not exist) | INCOMPLETE — 3: the alcohol level needs the entry hook (`TARGET_SIDE_WORK.md`), the alcohol time calls a member native does not implement |
| `py4gw/skillbar.py` | `SkillBar` + `SkillbarSkill` + `PySkillbar` | 18 + 7 + 17 | 5 — `UseSkill`, `UseSkillTargetless`, `HeroUseSkill`, `LoadSkillTemplate`, `LoadHeroSkillTemplate` | INCOMPLETE — the control-action mechanism and the template decoder |
| `py4gw/skill.py` | `Skill` + `SkillID`/`SkillType`/`SkillProfession`/`PySkill` | 11 + 2 + 2 + 3 + 2 | 1 — `GetCampaign` | INCOMPLETE — the descriptions/wiki group (Reforged's 1.98 MB `skill_descriptions.json`) and two enum tables |
| `py4gw/party.py` | `Party` + `Hero` | 35 + 4 | 12 | INCOMPLETE — the action members |
| `py4gw/map.py` | `Map` | 178 (9 classes) | 10 — 9 ImGui, 1 overlay; **recorded divergences** | **DONE (owner's ruling, 2026-09-29)** — 168 answer, and the ten cannot: 9 need the injected runtime's ImGui, 1 its overlay manager |
| `py4gw/merchant.py` | `Trading` + `PyMerchant` | 17 + 15 | 0 | **FULL** — every declaration answers (round 3); the state behind them is `py4gw/listeners.py` and the packet hooks under it are `py4gw/game_thread/packets.py`. Live pass owed; see the `Merchant` row in §1 and [`MERCHANT_PORT.md`](MERCHANT_PORT.md) |
| `py4gw/map_methods.py` | `MapMethods` | 7 | 0 | **FULL** — the port of `native_src/methods/MapMethods.py` (135 lines), whole; landed with `Map`'s action members, which reach every one of them |
| `py4gw/ffna_map_methods.py` | `FfnaMapMethods` + the FFNA parser | 13 functions, 4 dataclasses, 1 class, 1 table | 0 | **FULL** — the source's 681-line module whole, including the 404-entry `_MAP_ID_TO_DAT_FILE_ID`; landed as `Map.Pathing`'s offline branch, and `tests/test_map_pathing_offline.py` checks the table value for value against the source |
| `py4gw/pathing.py` | `AABB` + `TrapezoidBSP` + `NavMesh` + `AutoPathing` | 3 + 2 + 17 + 9 | 2 — `AutoPathing.get_path`, `get_path_to` | **INCOMPLETE** — the navmesh half of `Pathing.py`, which is what `Map.Pathing` reaches: every member answers except the two that need `PyPathing.PathPlanner` (the injected runtime's planner object) and the `Routines` coroutine driver. `AStar`, `AStarNode`, `chaikin_smooth_path` and `densify_path2d` are those two members' helpers and are not ported, because nothing reached them |
| `py4gw/routines_src/Checks.py` | `Checks` | 8 namespaces, 65 members | 58 | **INCOMPLETE (cascade only, 7 of 65)** — the `Map` namespace is ported in full because that is what `Map.Pathing` guards on; the other seven namespaces (`Player`, `Party`, `Inventory`, `Items`, `Effects`, `Agents`, `Skills`) are **not declared here**, because declaring a member whose body cannot be written yet belongs to `Checks`'s own migration and not to this cascade. That class's port is a work item with its own doc |
| `py4gw/ui_manager.py` | `UIManager` | 53 class members + 2 nested = **55** (the source's own count) | 7 contain a raise, and all 7 are the injected runtime's own surface — **documented divergences, not pending work** (owner's ruling, 2026-09-27) | **COMPLETE for this port's purposes** — 48 answer; the seven are enumerated with what each needs in [`UIMANAGER_PORT.md`](UIMANAGER_PORT.md) |
| `py4gw/py4gwcorelib_src/utils.py` | `Utils` | 40 | 1 — `TokenizeMarkupText` | INCOMPLETE — 3: the client's own text measure and the two Gwinch converters (they need the DX viewport) |
| `py4gw/py4gwcorelib_src/color.py` | `Color` + `ColorPalette` | 41 + 4 | 0 | FULL |
| `py4gw/perf_counter.py` | `PerfCounter` + `_MetricData` | 8 + 3 | 0 | FULL |
| `py4gw/chat.py`, `py4gw/ui/*`, `py4gw/internals/*`, the contexts | — | functions and records, not classes | — | see `CONTEXT_INVENTORY.md` (data layer) and each port doc |

**The three classes that are done and done**: `Agent` (every member that can exist outside the injected
runtime), `AgentArray`, `Player` — each with its exception named above and a line saying why it cannot be
otherwise. Everything else above is a work queue, and no entry in it says a source feature is missing:
the sources are complete, and what is left is porting work with a name.

## Where a fresh session starts (handoff, 2026-09-26)

Everything below is offline work unless it says otherwise. The `Utils` item is **done** (this
change); what follows it is the queue as it now stands.

1. ~~**`Utils`**~~ — **landed 2026-09-26**: `py4gw/py4gwcorelib_src/utils.py` with `Color`, 37 of its
   40 members working, and the four members it was blocking elsewhere ported. Per-member record:
   [`UTILS_PORT.md`](UTILS_PORT.md).
   **`Skill` landed with it**, which completed `Utils.BalthazarSkillIdToDialogId` and therefore
   `Player.UnlockBalthazarSkill` — see [`SKILL_PORT.md`](SKILL_PORT.md) — and **`Skillbar` landed
   with it too**, which completed `Utils.GenerateSkillbarTemplate` — see
   [`SKILLBAR_PORT.md`](SKILLBAR_PORT.md). What is left in `Utils` is target-side work
   (item 7 below) and nothing else.
2. ~~**`Effects`/`Effect`**~~ — **landed 2026-09-26**: `py4gw/effect.py`, 12 of its 15 members
   working (the array walk, the two computed times and the two calls), which closed
   `Agent.IsMartial`/`Agent.IsMelee` and `Skillbar`'s slot `get_recharge`. It also brought
   `py4gw/memory/memory_manager.py` — the skill timer the effect snapshot and `get_recharge` both
   needed. What is left is `GetAlcoholLevel` (the entry hook native installs, in
   [`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md)) and `GetAlcoholTimeRemaining` (a binding member
   that does not exist). Per-member record: [`EFFECT_PORT.md`](EFFECT_PORT.md).
3. ~~**`Skillbar`**~~ — **landed 2026-09-26**: `py4gw/skillbar.py`, every read working (plus
   `ChangeHeroSecondary`), which completed `Utils.GenerateSkillbarTemplate` — the last
   offline-portable dependency `Utils` had. Per-member record: [`SKILLBAR_PORT.md`](SKILLBAR_PORT.md).
   Its `get_recharge` **landed with the skill timer in item 2**; what is left in its own queue is the
   keypress mechanism and the two template loaders, which need native's `DecodeSkillTemplate`.
4. ~~**The invented `AgentAllegiance`**~~ — **removed 2026-09-26.** `py4gw/context/agent_array.py`
   declared it in neither source, and it was read by `py4gw/__init__.py`, `player.py`, five probes
   and four test files. The module now imports the source's own
   `enums_src.game_data_enums.Allegiance` (7 members, `Unknown` included) and every call site reads
   the source's member names — `Allegiance.Enemy`, not `AgentAllegiance.ENEMY`. **The rest of the
   invented layer went with it** (2026-09-26): `AgentReference`, `AgentArraySnapshot`,
   `LivingAgentSnapshot`, `StaleAgentReferenceError`, the four `Reforged*Struct` duplicates,
   `AgentKind`, `_agent_record_type`, and the facade members built for them. See
   [`AGENT_PORT.md`](AGENT_PORT.md) for the module as it now stands and for the two findings the
   pass produced (the Reforged-Python-vs-native layout disagreement, and the module-level `get()`
   helpers that 24 other context modules still carry).
5. **`Agent`'s remaining 3, and none of them is porting work** — ~~the `PyAgent.get_agent_enc_name`
   binding~~ (**landed 2026-09-26**: `py4gw.agent.get_agent_enc_name`, ported over native's own walk,
   closing 8 of the 13) and ~~`Effects.HasEffect`~~ (**landed 2026-09-26** with `py4gw/effect.py`,
   closing `IsMartial` and `IsMelee`). What is left is `GetProfessionsTexturePaths`, which needs the
   **injected runtime's own module directory** (`Console.get_projects_path`,
   `system_bindings.cpp:72-74` → `process_manager.cpp:38-40`) — a path into an installation this
   project does not have, and the third member of the artifact kind — and the two frame-loop members,
   which the port's execution model has no dispatcher for. Both are recorded divergences, not items
   in a queue.
6. **The chat-history trio** — `Player.RequestChatHistory`/`IsChatHistoryReady`/`GetChatHistory`.
   The decode half is ported and live (`py4gw/ui/async_decode.py`, the emitted decoder stub), and
   `GW::chat::GetChatLog()` is `*chat_buffer_addr` (`chat_methods.cpp:70-73`) — a global the ported
   `ChatBuffer` context already walks — so what is left is the port of native's own walk
   (`player_bindings.cpp:276-325`) and the module state it fills.
7. ~~**The render viewport, for `Map.MissionMap.GetScale`**~~ — **done, and it landed with the frame geometry (rounds 36-53); round 78 made its consumer work.** The capture is live-verified (viewport 1678×1368, hook removed cleanly), `FramePositionStruct` carries native's `viewport_scale`/`top_left_on_screen`/`bottom_right_on_screen`/`size_on_screen`, and `Frame.rect`/`size`/`coords`/`viewport_scale`/`content_coords` answer over the root frame plus that viewport. `Map.MissionMap.GetScale` is `frame_info.viewport_scale()` and answers, which **also closed `Utils.GwinchToPixels` and `Utils.PixelsToGwinch`** — two members that were already written source-identical and only ever raised from that one read. The original entry, kept for the record: the chain is Reforged's `frame_info.viewport_scale()` (`FrameTree/frame.py:1381-1398`) → native's `FramePosition::GetViewportScale` (`include/GW/ui/ui.h:553-561`), which divides `GW::render::GetViewportWidth/Height()` by the frame's own viewport size — and the render viewport comes from the DX context (`Context::GetRenderContext()`), which native only learns from its `EndScene`/`Reset` detours (`render.cpp:75-111`).
8. **`Dialog`'s one item** — this build's `DialogLoader_GetText`. The two routes are named in
   [`RESEARCH.md`](RESEARCH.md): read the client's announce path out of `DialogShow`'s callers, or
   hook the confirmed text encoder and let one interaction name it. Offline tools for both are in
   `tools/` (`dialog_loader_hunt.py`, `resolve_offline.py`, `ghidra_scripts/`).
9. **Live passes owed** (these need the client, elevation and a UAC approval — do them deliberately,
   one at a time): the three chat *senders*' send half (`SendChatCommand`/`SendChat`/`SendWhisper`);
   and re-running `tests/probe_chat_log_write.py` after any change to the log write, since it is the
   only witness that path has. `tests/test_live_agent_chat.py` is ready for that now: its three call
   sites read ``PlayerAgentIdStruct.player_agent_id``, a field that does not exist — the struct
   declares ``agent_id`` (``py4gw/context/player_agent_id_context.py:34``) — so the suite failed for a
   reason that had nothing to do with the client; the field reads are corrected, and a live run of it
   is part of this pass.
10. **`UIManager`'s game-changing members** (owner-sanctioned later pass, 2026-09-27) — **`SendUIMessage`
    and `SendUIMessageRaw` are now live-verified (2026-09-29, round 81)**: `Map.TravelGH`/`Map.Travel`
    drove `SendUIMessageRaw` with `kGuildHall`/`kTravel` and `Map.LeaveGH` drove `SendUIMessage` with
    `kLeaveGuildHall`, and the client acted on all three (the map changed each time — see
    [`MAP_PORT.md`](MAP_PORT.md)). What is left of this item is
    `Keydown`/`Keyup`/`Keypress`, `SetWindowPosition` and the two dialog clicks, which are
    the only members of that class with no live execution behind them; they change the game, so they are
    one deliberate, owner-present run, one at a time. Four of them ride primitives that are **already**
    live-verified (`Frame.click` advanced a real dialog in round 59; the frame sender, rounds 58-59) and
    `SetWindowPosition` is the same four-word call round 77 verified live — so the genuinely unexercised
    surface is the two **message senders**. Named in full in
    [`UIMANAGER_PORT.md`](UIMANAGER_PORT.md) § Owed live pass.

**Method that paid off this session, worth keeping:** read the *file* before the client. `Gw.exe` on
disk plus a headless Ghidra project (`.ghidra/gw38888`, scripts in `tools/ghidra_scripts/`) settled
the dialog table's columns, the chat send's identity, the loader's absence from the table readers,
and the chat-log crash — none of which needed a running client, an elevation prompt, or a risk. The
one live crash of the session came from a call form this port *chose* rather than read
([`CHAT_PORT.md`](CHAT_PORT.md)). **And for a class that is pure Python, load the source file in the
test**: `tests/test_utils_offline.py` runs Reforged's own `Utils.py` beside the port over a table of
inputs, which is a real cross-check of 68-case tables and encoders that no hand-written expectation
would catch.

| Layer | In Reforged | In Stealth | State |
| --- | ---: | ---: | --- |
| Context modules (`native_src/context/*.py`) | 18 | 32 | **the data layer, largely ported** — more files here than there, because several contexts are several files (`skill_context.py` landed with `Skill`) |
| Top-level classes (`Py4GWCoreLib/*.py`) | 48 | 8 (`Map`, `Player`, `Party`, `Scanner`, `Dialog`, `Agent`, `Skill`, `SkillBar`) | **the class layer is the work queue** — 1 of the 8 is FULL, and every remaining member is named in its port doc |
| `py4gwcorelib_src` modules | 18 | 2 (`Utils`, `Color`) | the library's own helpers: `Utils` landed with `Color` (its only import); `Console`, `ActionQueue`, `FrameCache`, `Settings`, `Timer` and the rest are still unwritten |
| Native binding modules (`PYBIND11_EMBEDDED_MODULE(...)`) | 44 | 0 | the DLL modules themselves are not ported, because this project loads no DLL; what they *wrap* is ported member by member through the game's own functions (§3) |

**A member is portable when its own body's dependencies exist.** Module-level imports
are *not* the dependency: Reforged's Python is mutually recursive — from `Player.py`
the import closure reaches **112 modules and 54,623 lines**, which is essentially the
whole library. So the useful edge is "this member's body calls `PyX.something`" or
"this member's body reads context Y", and the question for each is which resolver,
call form or piece of state that body needs — and then that piece gets built.

## 2. The dependency surface is the native binding module

A class body talks to the client through `PyX`. How much of each `PyX` we can already
reach is the real map:

| Native module | Bound names | Our catalog area (resolvers) | Verdict |
| --- | ---: | --- | --- |
| `PyImGui` | 363 | `native_ui` (15) | the client's own ImGui; the names to call are the source inventory for that work |
| `PyUIManager` | 122 | `ui` (71), `native_ui` (15) | **in progress: this is the class being ported, and it is ported *as a class* — the primitives in scope (UI messages, the settings, the frame handles, the frame-tree handlers) are the work; the creation/widget surface is excluded by scope, not pending.** What is readable today is §4's frame surface; the row on the injected UI surface below carries the keep/drop table |
| `PyParty` | 114 | `party` (12) | class ported: the 30 action members are the work |
| `PyItem` | 98 | `item` (28) | context ported, `Item`/`Inventory` classes still to port |
| `PyPlayer` | 67 | `player` (5) | class ported: 18 members call through the game thread, 5 still to port |
| `PyOverlay` | 67 | `overlay` (2) | DX overlay; needs a render hook |
| `PySystem` | 66 | `memory` (7) | console/window/system; mostly in-client |
| `PySkill` | 64 | `gw_dat_reader` (8) | **data lookups** (names, descriptions), not calls |
| `PyCamera` | 63 | `camera` (3) | context ported; the 4 setters are client-state writes, still to port |
| `PyAgentRecolor` | 58 | `agent_recolor` (7) | the client's own recolor surface; the names to call are the inventory for that work |
| `PyDXOverlay` | 49 | — | the client's own DirectX overlay surface; still to port |
| `PyParticles` | 44 | — | the client's own particle surface; still to port |
| `PyQuest` | 40 | `quest` (5) | **portable, class not ported** |
| `PySkillbar` | 40 | `skillbar` (6) | **portable, class not ported** |
| `PyAgent` | 39 | `agent` (8) | array ported; the `Agent` class is not |
| `PyInventory` | 32 | `item` (28) | **portable, class not ported** |
| `PyMap` | 30 | `map` (16) | ported |
| `PyDialog` | 32 + 6 records | `agent` (2: the two dialog senders), `ui` (2: the decode pair) | **ported**: state from the client's own messages, the tables from the sources' own constants in code; the loader call is the one member that reports itself. `PyDialog` is the *sources'* name for their module — this port's class is `Dialog` |
| `PyEffects` | 26 | `effects` (2) | **ported 2026-09-26**: `py4gw/effect.py` carries the binding class, the two value snapshots and Reforged's `Effects` over them — 12 of 15 members; the alcohol level needs the entry hook, and the alcohol time names a binding member that does not exist |
| `PyMerchant` | 17 | `merchant` (2) | **portable, class not ported** |
| `PyChat` | 13 | `chat` (12) | **portable, class not ported** |
| `PyKeystroke` / `PyMouse` | 12 / 12 | — | the client's own input synthesis; still to port |
| `PyFriendList`, `PyTrade`, `PyGuild` | 8, 8, 5 | `friend_list` (5), `guild` (0) | contexts ported |
| `PyPathing` | 7 | `pathing` (1) | pathing is ported inside `MapContext` |
| `PyDatReader` | 2 | `gw_dat_reader` (8) | the DAT/text-table route |
| `PyPacketSniffer`, `PyCtoS`, `PyStoc` | 18, 1, 1 | `packet_sniffer`, `ctos`, `stoc` | needs the packet hooks |
| `PyGameThread` | 3 | `game_thread` (1) | **ours** (`py4gw/game_thread`) |
| `PyCallback` | 0 | — | the runtime's own callback system; **ours is `game_thread/callbacks`** |
| `PyScanner`, `PyProfiler` | 0, 6 | — | internal to the DLL |

Two things that table makes plain:

- **Most of the "big" native modules are data, not calls.** `PySkill` (64), `PyItem`
  (98) and `PyQuest` (40) are largely name/description lookups served from the client's
  DAT and text tables. Their classes need *reading text*, not calling
  functions — and that is now ported end to end: `py4gw/dat_reader.py` reads the table out
  of `gw.dat` through the client, and `py4gw/internals/string_table.py` renders its entries
  on the host. What these classes still need is their own porting.
- **For a whole tier of classes nothing is missing.** `Quest`, `Skillbar`, `Inventory`,
  `Merchant`, `Effect`, `ChatCommands`, `Agent`, `Camera` already have resolvers in this
  project's catalog and readable contexts underneath. They are unwritten work, not
  capability — 47 actions and 106 plain porting gaps in the last census.

## 3. Classes whose own surface is in the client

`PyImGui` (363 names), `PyOverlay`, `PyDXOverlay`, `PyParticles`, `PyAgentRecolor`,
`PyKeystroke`, `PyMouse` are surfaces of a process that draws and takes input. The
sources that wrap them — `UIManager`, `GWUI`, `Overlay`, `DXOverlay`, `HotkeyManager`,
`EnemyBlacklist`, `AgentRecolor`, `Keystroke` — have their game-side data ported, and the
parts that touch the in-client surface are the last of the work here rather than a
boundary: the capability layer already runs code on the client's own thread, which is
where the client's own ImGui, overlay and input functions are called from. Each of those
members carries what it needs.

## 4. The classes, grouped by what unblocks them

**A. Readable now; the class is simply not written yet.** Every one of these has a
ported context and resolvers already in the catalog:

| Class | Lines | Reads |
| --- | ---: | --- |
| `Agent` | 1657 | `AgentArray`, `AccAgentContext` |
| `Inventory` | 1477 | `ItemContext` |
| `Pathing` | 862 | `MapContext` pathing |
| `Item` | 827 | `ItemContext` |
| `AgentArray` | 482 | its own context is ported — **and the class is now ported too**: `py4gw/agent_array.py`, every member (13 getters + `Manipulation`/`Sort`/`Filter`/`Routines`), with one recorded divergence on the twelve array getters |
| `Camera` | 367 | `Camera` context |
| `Quest` | 245 | `quest` resolvers + world context |
| `ChatCommands` | 216 | `chat` resolvers + `ChatBuffer` |
| `Skillbar` | 209 | `skillbar` resolvers + world context |
| `Merchant` | 197 | `merchant` resolvers + `ItemContext` |
| `Effect` | ~~176~~ **ported 2026-09-26** | `effects` resolvers + the ported `WorldContext.party_effects` array + the skill timer (`py4gw/effect.py`, [`EFFECT_PORT.md`](EFFECT_PORT.md)) |
| `Item` | 827 (125 declarations) | **FULL (2026-09-27)** — `py4gw/item.py`, with `enums_src/item_enums.py`, `enums_src/model_enums.py`, `mods_types.py`, `mods_upgrades.py`, `mods_core.py` and `py_inventory.py` ported for it ([`ITEM_PORT.md`](ITEM_PORT.md)). Every declaration of the source's tree is present (AST-compared: nothing missing, and the port's only additions are the binding it carries) and **every member answers** — the last two, `GetItemIdFromModelID` and `GetItemByAgentID`, landed with the bag surface `py_inventory.py` supplies |
| `PyInventory` binding | 216 (native `inventory_bindings.cpp`) | **ported 2026-09-27, INCOMPLETE (15 of 17 members + 3 of 4 module functions)** — `py4gw/py_inventory.py`: `Bag` complete; of `PyInventory`'s members 11 answer (the reads, `PickUpItem`, `DropItem`, `DestroyItem`, `MoveItem` — which needed the four-word call form and has it since round 22 — and the gold four), while **the two that raise are the two paths nothing else supplies**: `OpenXunlaiWindow` (a StoC emulation) and `AcceptSalvageWindow` (a frame click). **The interact guard landed in round 57**, so `UseItem`, `EquipItem`, `IdentifyItem` and `Salvage` act: `CanInteractWithItem` → `IsStorageItem` → `IsStorageBag` → `CanAccessXunlaiChest` (`item_methods.cpp:52-74`) is ported into `py4gw/py_inventory.py` in native's own order, each member calls its own catalog resolver (`item.use_item_func`, `item.equip_item_func`, `item.identify_item_func`, `item.salvage_start_func`), and `Salvage` also sends the `kPreStartSalvage` packet and reads the salvage session (`:292-301`). **`BagType` is settled, and settling it exposed a defect in this port rather than a gap (round 56).** `Constants::BagType` is native's own enum (`include/GW/common/constants/item.h:7-14`: `None, Inventory, Equipped, NotCollected, Storage, MaterialStorage`, so `Inventory` is `1`, `Equipped` `2`, `Storage` `4`, `MaterialStorage` `5`) and it appears in neither this port nor Reforged's `enums_src/`, so it is ported here now — `BagType` in `py4gw/context/item_context.py`, re-exported by `py4gw/context/__init__.py` and `py4gw/__init__.py`, its zero member spelled `None_` (the sources' own Python spelling for such a member, `enums_src/Item_enums.py:25,34,155`). The port's bag record does carry a `bag_type` field (`py4gw/context/item_context.py:908`), and it **is** this enum — native's `Bag` declares it so (`item.h:54`) — but every comparison written against it was a `Bags` **id**: `8` is `Bags.Storage1`, `6` is `Bags.MaterialStorage`, `22` is `Bags.EquippedItems`, where native compares `BagType.Storage` `4`, `MaterialStorage` `5` and `Equipped` `2` (`1` was right only because `Bags.Backpack` and `BagType.Inventory` are both `1`). The effect was a **wrong value returned to callers, not a missing capability**: `is_storage_bag` and `is_material_storage` answered `False` for every real storage and material-storage bag, and `is_inventory_item` missed equipped items. Fixed in round 56 — `BagStruct`'s three predicates are native's own comparisons (`item.h:62-64`), `ItemStruct`'s two are native's own rules (`item.h:139-140`: inventory-or-equipped, and storage-or-material-storage, which is **not** the free `GW::item::IsStorageItem` of `item_methods.cpp:68-70` that the guard below asks), and the snake_case duplicates that carried the wrong constants are gone from both context structs, because those names are the *binding's* fields and this port already carries them where the binding declares them (`item.py`, from `item_bindings.cpp:302-303`). **What round 57 established, and the one divergence it recorded**: native takes the current map record from `map::GetCurrentMapInfo()` = `Context::GetAreaInfoArray()[GetMapID()]`, while `_can_access_xunlai_chest` takes it from the instance-info record's own pointer (`GWContext.InstanceInfo().GetMapInfo()`) — the same `AreaInfo` for the current map, through the read this port already has. The global `AreaInfo` array is still unported (it is what `Map.GetUnloadedMapInfo` raises for), so the array route is that member's work item, not this module's. The round also ported native's `Context::Region` (`context/map.h:56-85`, 28 members, `Region_Presearing` = 7) into `py4gw/context/instance_info_context.py` and its stub, and the module function `salvage` came with `PyInventory.Salvage` (`inventory_bindings.cpp:204-209`) |
| `ItemArray` | 212 (14 declarations) | **FULL (2026-09-27)** — `py4gw/item_array.py`: `CreateBagList`, `GetItemArray`, `GetAllBags`, `GetBag` over the ported bag surface, and the three nested namespaces `Filter` (2), `Manipulation` (3), `Sort` (2), AST-compared name for name and nesting for nesting. Two adaptations recorded: the three members' `@frame_cache` is dropped (no frame loop to key it to) and the two `PySystem.Console.Log` error lines have nowhere to go, so the control flow is kept and the log is not replaced by anything invented. Two source quirks pinned by the tests: `GetBag` cannot answer a bag through either an `int` or a `Bag` member, and the dotted attribute names the source's own docstrings use (`'Properties.GetValue'`) are not attributes of `Item`, because `getattr` does not walk the dot |
| The injected **UI surface** (native's `UIManagerShim` bound as `UIManager`, `ui_bindings.cpp:660`; Reforged imports it as `PyUIManager`) | 303 bound members | **Ported as a class, and the cut is by class — the owner's criterion, verbatim (2026-09-27):** *"the class is mostly ok up until line 611 where `InventoryBagWindow` starts, those classes we don't need."* Measured on the source: Reforged's `Py4GWCoreLib/UIManager.py` (1302 lines) is **`class UIManager`, lines 29-618, 53 methods** — the class this port ports — followed by **14 window classes, lines 619-1302, 56 methods**, which are **not ported**: `InventoryBagWindow` (619), `InventoryBagsWindow`, `XunlaiStorageWindow`, `SkillTrainerWindow`, `TraderWindow`, `MerchantWindow`, `CollectorWindow`, `CrafterWindow`, `UpgradeWindow`, `SalvageOptionsWindow`, `SalvageConfirmationPopup`, `LesserSalvageWindow`, `ExpertSalvageUnidentifiedWindow`, `AnySalvageWindow` — the per-window handlers for the injected runtime. Native's side shows the same boundary from below: the primitives stay (section table below), the per-widget families go. The owner's rule, verbatim: *"nothing from creating in-game windows, no dropdown, no create window, not even the class that handles them, no singletons, no handlers — only primitives."* **Kept**, from the source's own sections: `UI messages / input` (11), `Global state / language` (6), `Enc-string helpers` (3), `Preferences` (9 — the settings), `Built-in window (WindowID) position/visibility` (6), the bound record classes (`UIInteractionCallback` consumers, `FramePosition`, `FrameRelation`, `UIFrame` frame handles), `Frame tree traversal / discovery` (24), `Frame metadata / geometry` (14), and the primitive frame-state setters and label reads inside `Frame state setters` / `Text labels`. **Dropped**: `Widget creation` (14 factories), every per-widget family (`Dropdown` 11, `Button` 3, `Checkbox` 4, `Slider` 2, `Editable text` 7, `Progress bar` 5, `Tabs` 13, `Scrollable` 13), the item-frame tint/pop/shader family (native's own hooks), and anything above the primitive level in the sections not yet printed (overlay and draw among them). **The UI class itself is in scope and is to be ported**, carrying the owner's four, verbatim: *"what we need to have from the UI class, is the handling of UI messages, the settings, the frame handles, the frame tree handlers"* — with **no singleton instance and no handler class** beside it, and no per-widget class at all (*"not even the class that handles them"*). Today those members are resolved one by one on `Frame`/`_FrameTree`; that is where the class's port begins, not a substitute for it. **This is a permanent scope decision and not pending work**: the surface is deliberately *not* completed, so no round should list its dropped sections as outstanding, and none should reopen them without the owner. Section-by-section table: [`FRAME_TREE_PORT.md`](FRAME_TREE_PORT.md) |
| `FrameTree` package | 5,444 (7 modules) | **all seven modules ported (2026-09-27)** — `py4gw/frame_tree/`: the five tables verbatim (`frame_window_keys`, `frame_names`, `frame_aliases`, `frame_registry`, `frame_ids`), `frame.py` with both classes declared in full and in the source's own member order, and the source's own `__init__` re-export list, compared name for name against the source's `__all__` ([`FRAME_TREE_PORT.md`](FRAME_TREE_PORT.md)). **The package's modules are in; its two classes are not FULL** — the next two rows |
| `_FrameTree` | `frame.py:273-675` (41 members) | **ported 2026-09-27, INCOMPLETE (33 of 41 answering, measured from the module's AST)** — the lifecycle, the per-frame live copies, the structure queries, the four anchor lookups, the Frame-backed queries and `root`/`viewport_height`. The eight that raise name their requirement: `enable`/`disable` (`PyCallback` — Reforged's frame loop), `by_label`/`hash_for_label` (the client's `CreateHashWithWChar` over a wide string, i.e. a call form this port lacks), `child_by_parent_hash` (the client's `g_get_child_frame_id_func`), `color_frames`/`overlay` (the injected `PyOverlay` manager), and `anchor_ids`, which names only its *label fallback* and answers on its snapshot and hash paths. **`root` answers since round 36**: it is the catalog's `ui.get_root_frame_func` called on the client's own thread — native's `GetRootFrame` — with the id read at `+0xBC`. `viewport_height` reads through it, and `sort_by_vertical` delegates to `rect` |
| `Frame` | `frame.py:679-1620` (115 members) | **ported 2026-09-27, INCOMPLETE (95 of 115 answering, measured from the module's AST)** — every member is declared, in the source's own order, and 94 answer. **The geometry answers since round 37**: `rect`, `size`, `coords`, `viewport_scale` and `content_coords` are native's own arithmetic — `FramePosition`'s on-screen methods (`ui.h:504-561`) over the **root frame** and the **captured render viewport**, the two inputs whose absence made them raise before. **`send_message` answers since round 58** — the first of the frame-action group: the client's own callbacks-based sender is resolved (`ui.send_frame_ui_message_func`, native's `g_send_frame_ui_message_original`) and called with native's own **five** words — `&frame->frame_callbacks` (the record's address plus the field's `0xA8`), a null second word, the message id and the caller's two words — behind native's own guard (`frame && frame->frame_callbacks.size()`, `ui_methods.cpp:1332-1345`), with the binding's `true` as the answer. **`send_message` and `click` answer, and both were verified against the live client (round 59) — which is what corrected the call's shape**: that target is the client's `__thiscall` method, which Native declares `void(__fastcall*)(callbacks, void* edx, message_id, wparam, lparam)` for its detour ABI (`ui_patterns.cpp:32`), so `CallForm.FASTCALL_U32_U32_U32` puts `&frame->frame_callbacks` in **ECX**, the dummy in EDX, and only three words on the stack — the callee pops them (`ret 0xc`, read live). `click` is native's `ui::ButtonClick`: it reaches the parent by relation pointer, makes both `IsCreated` checks, and sends `MouseAction{child_offset_id, child_offset_id, MouseUp, &ButtonParam{0, field105_0x1c4, 0}}` as `kMouseClick2` to the **parent's** callbacks — clicking a real dialog button in the live client advanced the dialog. The 20 that still raise are three features: **the game-thread frame actions** (10 — `set_visible`, `set_disabled`, `show`, `set_layer`, `set_opacity`, `double_click`, `mouse_action`, `mouse_click_action`, `send_message_text`, `set_text`; native runs every one through `GW::game_thread::Enqueue`), **the client's own text, input and the overlay** (5 — `label` and `title`, which are one title-table call; `is_mouse_over`, the client's ImGui; `draw`, `draw_outline`, the injected overlay) and **the client-call lookups** (5 — `child_native`, `child_path_native`, `item`, `tab`, `io_events`). `hover` delegates to `mouse_action` |
| `Inventory` | 1477 (66 declarations) | **ported 2026-09-27, COMPLETE for this port's purposes (53 of 57 methods built; the 4 that raise are documented divergences, not pending work)** — `py4gw/inventory.py` in the source's own order: the three `TypedDict`s, the 9 class attributes, and **53 methods answering** — `inventory_instance`, the nine space/count members, the four "first" finders, identify/salvage, the storage window, the six item actions, the five gold members, `MoveItem`, `FindItemBagAndSlot`, both storage walkers (with the source's own capacity-derived bag list and its `getattr(Bags, f"Storage{i}")` reach) and `_collect_frame_text` (which the source itself answers `""`, `:503-513`). **The 4 that raise are documented divergences rather than work:** **3 are generators over Reforged's coroutine driver** (`HandleSalvageChoiceDialog`, `HandleSalvageChoiceMaterialConfirmDialog`, `_wait_for_salvage_choice_dialog_close`), which is that library's per-frame task framework (`Routines.py` → `routines_src/*` + `GLOBAL_CACHE`) — the same class of thing as `@frame_cache`, so a documented divergence rather than pending work; and **1 needs the injected console** (`_salvage_choice_debug_log`), which is `PySystem.Console` — Reforged's `py4gwcorelib_src/Console.py` is 38 lines that *are* the in-client ImGui console, so the log has nowhere to go; its **disabled** case returns before that, exactly as the source's own guard does, so only an enabled log raises. **The 3 that left this list in round 38 are the option assembly, the click strategy and the formatter** (`_get_salvage_choice_dialog_options`, `_choose_salvage_choice_dialog_option`, `_format_salvage_choice_option`), which waited on `Frame.rect` through `_build_visible_frame_entry_map`. **The 14 that left this list when the `FrameTree` package landed are the frame half of the dialog**: `AcceptSalvageMaterialsWindow`, `_frame_by_alias`, `_get_all_child_frame_ids_from_frame_id`, `_salvage_material_confirm_yes`, `IsSalvageChoiceMaterialConfirmVisible`, `_salvage_dialog`, `_salvage_option_container`, `_salvage_confirm`, `IsSalvageChoiceDialogVisible`, `_build_frame_children_map`, `_build_visible_frame_entry_map`, `_collect_salvage_choice_option_text`, `_collect_visible_frame_subtree_entries`, `_pick_salvage_choice_click_entry` — twelve of them answering outright, and two naming the feature they call (`AcceptSalvageMaterialsWindow` reaches `Frame.click`, `_build_visible_frame_entry_map` reaches `Frame.rect`). Two members (`EquipItem`, `UseItem`) are the source's own delegations whose raise comes from the binding member they call. Findings recorded: the source's `.enums` import is a 289-line re-export shim that also re-exports the two unported enum files, so `Bags` is taken from the module that declares it; `SalvageFirst` answers `False` on the path where it acted (`Inventory.py:386-388`) |

**B. Needs the string table (now ported).** The archive read and the decoder are ported and
live; what these classes need is their own members, plus a place to put a string for the
sending side:

| Class | Lines | Needs |
| --- | ---: | --- |
| `Dialog` | 173 | **ported** (§5) — the class and its state landed without a decoder; its text fields now wait on the catalog's decode queue, not on the decode |
| `Skill` | 511 | DAT/text-table reads (`PySkill` is mostly names and descriptions) — the table is available |
| `Item` (names/descriptions) | — | the same |
| `Chat`, chat history members | — | the table, and the sending side for chat |

**C. Needs work on the capability layer.** Small in count and named precisely in
[`NATIVE_EXECUTION_PLAN.md`](NATIVE_EXECUTION_PLAN.md): a string argument form, a string
region for text the client reads, the decode callback, the GW.dat chain's live call path, and
the 31 capture-wired `enable()` members. The value-returning call is in the block already
(the command record's `value`), so what that item is waiting for is its live verification.

**D. Their surface is in the client.** §3.

## 5. The worked example: the Dialog chain

`Dialog` is the class that was asked for first, and its chain is short enough to state
exactly.

```text
Dialog.py                        173 lines, uses TWO PyDialog calls
  |-- sanitize_dialog_text()      pure string work, ported as written
  |-- ActiveDialogInfo           built from the native object's fields
  |-- DialogButtonInfo           the same
  `-- get_active_dialog()
      get_active_dialog_buttons()
            |
            `-- PyDialog           32 static methods + 6 record classes bound
                 (dialog_bindings.cpp:94-138)
                   |
                   `-- dialog.cpp  1,847 lines
                        |-- 4 UI-message captures, registered at priority 0x1:
                        |     kDialogBody, kDialogButton,
                        |     kSendAgentDialog, kSendGadgetDialog  (dialog.cpp:1273-1288)
                        |-- AsyncDecodeStr for the body text and the button labels
                        |-- GetAgentByID, to name the agent a dialog belongs to
                        `-- caches, event logs and callback journals: the runtime's own
                            diagnostics, with no external equivalent
```

Two facts make this cheaper than it looks:

1. **Reforged's Python uses two of the thirty-two bound methods.** The other thirty
   (`read_dialog_*`, the event logs, the journals, `initialize`/`terminate`) are native
   surface Reforged's `Dialog` class never wraps. They are leads, like
   `unlocked_maps` was, not required work.
2. **The capture half is done, both messages.** `kDialogBody` and `kDialogButton` are
   captured by the connection, and both were verified live — the client reported agent
   `17`, the capture read `17`, and the buttons arrived with their ids. The two senders
   a dialog id is passed to were already resolvable (`agent.send_agent_dialog_func`,
   `agent.send_gadget_dialog_func`), which is why `Player.SendDialog` worked before the
   class existed. Only the decode was ever a real blocker, and it turned out to be
   needed for text alone.

**Both are now done, and the member that needed them is ported.** `Dialog` landed as
`py4gw/dialog.py`, and `Player.SendAutomaticDialog` with it. The class is taken **whole**
— the facade, the surface behind it and every record — and the per-member table, the work
each remaining member needs, and the state machine are in
[`DIALOG_PORT.md`](DIALOG_PORT.md):

| layer | members | state |
| --- | --- | --- |
| `Dialog.py` (Reforged's facade) | 10 module members: two getters, two record classes, the sanitiser, the inline-choice parser, three helpers | 9 work; 1 reports a divergence (`_call_native_dialog_method`, which reaches a binding object by dynamic name and has no object to reach here) |
| `PyDialog` (native surface) | 32 static methods + 6 record classes | **31 answer; 1 reports the work it needs** (`get_dialog_text_decoded`, and the catalog `content` behind `get_dialog_info`/`enumerate_available_dialogs`, which wait on this build's `DialogLoader_GetText`). The tables themselves answer: the sources' five constants, rebased in code |

What is left is one work item, and it is porting work:

- **This build's `DialogLoader_GetText`** — a catalog dialog's `content` is empty for
  `get_dialog_info`, `get_dialog_text_decoded` and `enumerate_available_dialogs`, because the client
  function the source calls through has not been identified on this build. **The sources are
  complete and working — `Reforged` and `Reforged Native` both resolve and call a loader — so the
  function is there to find**: what the 2026-09-26 pass over the file establishes is *where to look*
  and *what it is not*. The five hardcoded `DialogMemory` data addresses are stale for this build
  (the table resolves by the source's own `.rdata` scan instead), and the hardcoded code address
  `0x0079EEF0` lands inside a packet deserializer. The client's own dialog window inlines the path a
  loader would wrap — it reads the row's text id (`+0x14`) and calls the text module itself — so the
  loader is not a table reader on this build. The method, the tools and the decompiled row semantics
  are in [`RESEARCH.md`](RESEARCH.md); the per-member table is in [`DIALOG_PORT.md`](DIALOG_PORT.md).

**A button's caption is now produced**, and it is the port's own client-side work that did it: the
observer is placed where the source's callback runs — after the client's own send returns — and its
emitted code copies the string the packet names **inside that call**, into the event the host
reads. Live, 2026-09-25: the dialog's two buttons answered
`'Would you tell me more about the Northern Support bonus?'` and
`'Would you tell me more about the Guild versus Guild bonus?'`, each the client's own decoder's
text for the label the client announced, with both `recv_choice` rows carrying it. The earlier
reading — that a button's announced pointer carries no table reference — was a measurement of the
port's own mistake: read from outside the client's call, that pointer is a buffer the client
reuses, and the labels are real references (indices 99994 and 99946) that decode to those captions.

The journals (13 members) and `terminate` are **ported**: the appenders, both caps, the
direction lists, the sorting, and the filtered clear are `dialog.cpp:457-544` and `1693-1817`
as written, driven from the same dispatch the client's messages go through.

`is_dialog_active`, the one member that needed a resolver this project did not have on top of
the call form, is **served**: it finds the client's `"NPC Dialog"` root frame **by hash**
(`GetFrameIDByHash`, `dialog.cpp:1670-1683`), and the frame array's `frame_id_by_hash` is that
lookup.

**The metadata tables are the source's own resolution, held where the source holds it** — 8
members. Native keeps the five bases as constants in `DialogMemory` (`dialog.h:94-99`) and rebases
them in `dialog_patterns.cpp`, the file it keeps them in *because* its pattern system has no
module-base-relative op (`dialog.h:80-85`). This port does the same and nothing else: the six
constants are `py4gw/dialog.py`'s own, rebased through `RemoteScanner.to_module_address()`, and
the two-stage resolution with its validation pass and `.rdata` fallback is `DialogTables`, the port
of `dialog_patterns.cpp`. **No catalog file carries them, and no resolver op was added for them**:
an earlier pass had both (`offsets/dialog.json`, `module_relative`) and both were removed on the
project owner's direction, 2026-09-26 — a file that exists in neither source is not this project's
to add, and neither is a mechanism op its sources never had. Live, the fallback is what resolves
the five bases on this build; see [`DIALOG_PORT.md`](DIALOG_PORT.md).

**The loader is the one step that is not ported, and it reports itself.** The source rebases
`DialogMemory::DIALOG_LOADER_GETTEXT` and calls it; on this build that address is not the loader,
and calling it faulted the client (`RESEARCH.md`, 2026-09-25). `get_dialog_text_decoded` — and the
catalog `content` behind `get_dialog_info` and `enumerate_available_dialogs` — says what it needs
instead of calling it or answering an empty string in its place. Identifying this build's loader is
the item the project owner parked.

The five the state answers are `get_active_dialog`, `get_active_dialog_buttons`,
`get_last_selected_dialog_id`, `is_dialog_displayed` and `clear_cache`; the six the tables
answer are `is_dialog_available` and the five `read_dialog_*` columns.

What made it cheap is one measured fact about the packet:

```c
struct DialogButtonInfo {   // the client's kDialogButton packet, context/ui.h
    uint32_t button_icon;   // word 0
    wchar_t* message;       // word 1  — the only field that needs decoding
    uint32_t dialog_id;     // word 2
    uint32_t skill_id;      // word 3
};
```

Sixteen bytes, so the **whole packet fits in the four words the observer records**. The
id a caller sends is a word in the event, not something to be decoded — which is why a
member that only clicks a button needed no decoder at all, and why the decode is
correctly filed as the *next* blocker rather than this one's.

Verified live, twice over: the older run read the target out of the client's notice, and
the dialog run reported agent `17` with **2 buttons, ids 4484 and 6020**, read from the
button messages as they arrived.

`DialogCatalog.py` (45 lines) is **not** on the list: it imports `PyDialogCatalog`, which
native retired — *"legacy PyDialogCatalog module was retired; its remaining functions all
had PyDialog equivalents"* (`dialog_bindings.cpp:85-87`) — so against the current native
revision Reforged's own module falls back to `None` and returns nothing. Porting it
would port dead code.

## 6. Order the dependencies allow

1. **The GW.dat chain** — the six client functions that hand over a file's bytes, called on
   the client's own thread through the capability layer. **Done and live**: `py4gw/dat_reader.py`
   reads the archive, and `py4gw/internals/string_table.py` (Reforged's own decoder, Route A)
   renders what it holds. Unblocks `Dialog` text, the chat-history members, `get_player_name`,
   the party names for arbitrary agents, and every table lookup behind `Skill`/`Item` names —
   none of which needs a callback stub.
2. **The decode callback** — an emitted stub in the client that the client calls with the
   decoded text, a text area in the block, a counter to wait on. This is the *other* route
   (Native's `AsyncDecodeStr`), and it is wanted where a member needs the client's own
   parameter substitution rather than the table entry — and for button labels, whose announced
   pointer does not carry a table reference.
3. **A string region for the other direction** — writing a string the client reads.
   Unblocks the five `Player` chat members and any dialog response carrying text.
4. **`kDialogButton` capture + `Dialog`** — **done, and it did not need item 2.**
   The class is taken whole (§5) on a captured state that made the decoder
   unnecessary for everything Reforged's Python asks of it. What is left of it is
   the text, which is item 1's work, not a step of its own.
5. **The context-backed classes, one at a time** — `Agent`, `Inventory`, `Skillbar`,
   `Quest`, `Merchant`, `Effect`, `ChatCommands`, `Camera`, `Pathing`. No mechanism work
   at all; each is a file ported member by member, with what each member still needs
   recorded in its own port doc. `Agent` is the one to take first **among these**: `PyAgent`'s 39
   names are the most used by other classes, and the `Agent` class is 1,657 lines of members
   over a context that is already ported. It is *not* the next thing to do: this item comes after
   item 3, and `Agent` is in fact reached as a dependency of `Player.GetInstanceUptime`
   (`Player`'s remaining list in §1), so it is taken there — its queue, prepared ahead of that
   point, is [`AGENT_PORT.md`](AGENT_PORT.md).
6. **The value-returning call form** — **done and live**: the command record's `value` carries
   the callee's return register, and every `Get*` member whose source reads a return value is
   now unblocked.
7. **Wiring the 31 `enable()` captures** — one per context, now that the layer exists
   and has **two** working consumers to copy. The second one matters more than the
   first: `Player.GetTargetID` is a captured value feeding a **read**, which is exactly
   what an `enable()` member is, so the shape is no longer only proven for actions.

## 7. The added classes, ranked by friction

§6 is the *dependency* order. This is the *cost* order over the classes §4A lists as
readable-but-unwritten (`Effect`, `Quest`, `Camera`, `Merchant`, `AgentArray`, `Pathing`,
`Item`, `Inventory`, `ChatCommands`), measured from the two working trees on 2026-09-26.

Friction here is not size. It is **how much of the source's own surface is already answered
by something this port has** — a context read, a resolver, the decode path, the game-thread
dispatcher — and what is left that is genuinely new.

| # | Class | Source | Already answered | What is actually new |
| --- | --- | --- | --- | --- |
| 1 | ~~`Effects` (`Effect.py`)~~ **ported 2026-09-26** | 177 lines, 15 members | **12 of 15 work.** Native's `GetAgentEffects`/`GetAgentBuffs` are a walk of `Context::GetPartyEffectsArray()` (`effects_methods.cpp:29-63`), which is `WorldContext.party_effects_array` at `0x508` — already read (`world_context.py:1469,1795`, `AgentEffectsStruct.effects/buffs`), and `BuffExists`/`EffectExists`/`HasEffect`/`GetBuffID`/`EffectAttributeLevel` are that same walk; the two computed fields (`GetTimeElapsed`/`GetTimeRemaining`, `skill.cpp:39-45`) needed only the skill timer, which landed with this port (`py4gw/memory/memory_manager.py` — `timeGetTime()` plus the client global the catalog names `memory.skill_timer_ptr`) | **What is left is three members, and two are findings.** `DropBuff` and `ApplyDrunkEffect` work — the two resolvers (`effects.drop_buff_func`, `effects.post_process_effect_func`) called through the existing forms; `get_instance` works and is *not* an artifact: native's binding is a wrapper holding one `uint32_t` (`effects_bindings.cpp:130`), so the port's `PyEffects(agent_id)` is that object. `GetAlcoholLevel` **raises naming the entry hook it needs** (native captures the post-process call's first argument, `effects.cpp:24-41`; recorded in [`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md)), and `GetAlcoholTimeRemaining` **raises naming a source-vs-source disagreement**: its body calls a binding member the binding does not implement (`effects_bindings.cpp:181-183`), which the stub declares and native does not track. Per-member detail in [`EFFECT_PORT.md`](EFFECT_PORT.md). **It closed `Agent.IsMartial`/`IsMelee` and `Skillbar`'s slot `get_recharge`.** |
| 2 | `Quest` | 246 lines, 26 members | Reads are `GW::quest::GetQuest`, `Context::GetQuestLog` and `GetActiveQuestId` → the ported world context. Actions are 3 of the 5 resolvers the catalog already has (`set_active_quest_func`, `abandon_quest_func`, `request_quest_info_func`). Text is the client's own `AsyncGetQuestName`/`Description`/`NPC`/`Location`/`Objectives` plus `AsyncDecodeAnyEncStr` → the **ported async-decode path**, the one a dialog caption already uses | the per-field request bookkeeping (`quest_bindings.cpp:121-183` keeps a map per text field, keyed by quest id) |
| 3 | `Camera` | 368 lines, 46 members | The reads are free: 31 of the 46 members are single field reads off `camera_ptr` (30 `Get*` plus `IsPointInFOV`), and the ported `CameraStruct` (`camera_context.py:31-64`) already declares **every field they touch** (`yaw_to_go`, `pitch_to_go`, `dist_to_go`, `look_at_to_go`, `cam_pos_inverted_to_go`, `time_in_the_map`, `time_in_the_district`, `field_of_view`, `max_distance2`, …); `IsPointInFOV` is arithmetic over them, and `GetCurrentYaw` over two of them | the fourteen members that **act** on the camera: the eight `Set*` (`SetCameraPosition`, `SetLookAtTarget`, `SetYaw`, `SetPitch`, `SetCameraUnlock`, `SetMaxDistance`, `SetFieldOfView`, `SetFog`), the four movement helpers (`Forward`/`Vertical`/`Side`/`RotateMovement`), and `ComputeCameraPos`/`UpdateCameraPos` — every one of them a method call on the native camera object. Native runs them on the game thread (`camera_bindings.cpp:100-103`, `GW::game_thread::Enqueue`) and either writes the camera struct or calls `GW::camera::SetMaxDist`/`SetFieldOfView`/`SetFog` (`camera_methods.cpp:78,87,145`; `fog_patch_addr` is already in the catalog). Our dispatcher runs work on that same thread — but a **field write into the client** is an operation this port has not performed, and that is the decision this class carries |
| 4 | `Merchant` (`Trading`) | 198 lines, 17 members | Quotes and transactions are the existing `request_quote_func`/`transact_item_func`; the items are `ItemContext`, ported | the three list reads come from `PY4GW::listeners::Merchant()` (`merchant_bindings.cpp:199-201`) — the injected runtime's own UI-message listener, so a merchant-window capture has to be identified and copied: the shape of the chat-log watch, with a message still to find. The source's `@frame_cache` decorators drop, as they do everywhere |
| 5 | ~~`AgentArray`~~ **ported 2026-09-26** | 482 lines, 28 members | **every member is in** (`py4gw/agent_array.py`): the thirteen getters, `Manipulation` (3), `Sort` (4), `Filter` (3) and `Routines.DetectLargestAgentCluster`, over the ported `Agent`, `Utils` and the context view. The helpers are pure Python and are pinned by `tests/test_agent_array_class_offline.py`, which reads the source's own surface with `ast` and compares it member for member | **one recorded divergence, on the twelve array getters.** The source's live path is `SystemShaMemMgr.get_agent_array_wrapper()` — the injected runtime's shared-memory channel — and its second route, `GWContext.AgentArray.GetContext()`, is unreachable code after the `return` (`AgentArray.py:23-29`). This project has no such channel, so the members answer from that second route over this project's own context view, which reads the same client array. Closing it means the shared-memory channel, and that is the work item. **Also fixed with this port:** the package root now exposes the *class* as `AgentArray`, the way Reforged's `__init__.py:101` does, with the context view at `py4gw.context.AgentArray` (Reforged's `GWContext.AgentArray`, `Context.py:54`), and the three helper classes the context view had copied from this file are gone |
| 6 | `Pathing` | 863 lines, 45 members | the bulk is pure A*/navmesh arithmetic over the ported `MapContext` trapezoids, and `find_path_func` is in the catalog | `PyPathing.PathPlanner` (native's planner object, with its `PathStatus`) and `enums.name_to_map_id`, from an enum module that is not ported |
| 7 | `Item` | 828 lines, 92 members | `ItemContext` and the 28 item resolvers | `mods_core` (25 KB), `mods_types` (48 KB) and `mods_upgrades` (36 KB), none of them ported; `enums_src/Item_enums.py`; and the name/description text |
| 8 | `Inventory` | 1478 lines, 59 members | `ItemContext`, ported | `Item` first, then the `PyInventory` actions, and `PySystem` (`Console`), which is unwritten |
| 9 | `ChatCommands` | 217 lines, 22 members | the `chat` senders are ported and live | native's registry is *invoked by the client*: `chat_commands.cpp:56-79` hooks `kSendChatMessage`, checks `CHANNEL_COMMAND` and sets `blocked` to swallow the command before the game's own callback runs. A **blocking** UI-message hook is a capability this port does not have — its observer runs after the call and cannot swallow — and `PySystem.Console` is unwritten. The smallest member count in the list and the most new capability |

**The order this gives: `Effects`, then `Quest`, then `Camera`, then `Merchant`.** `Effects`
is first because it is the only class whose work is entirely inside things that already
exist, and because it closes two `Agent` members on the way. `ChatCommands` is last despite
being second-smallest: its size is the part that is already cheap.

## 8. Reproducing these numbers

Resolver counts per catalog area, from the project root. `crash.json` and `guild.json`
carry only `patterns` and no `resolvers`, so the lookup is a `.get`:

```text
python -c "import json, pathlib; [print(p.stem, len(json.loads(p.read_text(encoding='utf-8')).get('resolvers', {}))) for p in sorted(pathlib.Path('offsets').glob('*.json'))]"
```

Native binding sizes, and which module binds what (from the native checkout). Written
with `[.]`, `[(]` and `\x22` so that it contains no double quote and PowerShell passes
it through untouched:

```text
python -c "import re, pathlib; root = pathlib.Path(r'C:\Users\Apo\Py4GW_Reforged_Native\src'); [print(name, len(set(re.findall(r'[.]def(?:_readonly|_readwrite|_property_readonly|_property)?[(]\s*\x22([A-Za-z_]\w*)', text)))) for path in sorted(root.rglob('*bindings*.cpp')) for text in [path.read_text(encoding='utf-8', errors='replace')] for name in [m.group(1) for m in re.finditer(r'PYBIND11_EMBEDDED_MODULE[(]\s*(\w+)', text)]]"
```

Members still to port, per module:

```text
python -c "import pathlib; [print(p, p.read_text(encoding='utf-8').count('raise _unported(') + p.read_text(encoding='utf-8').count('raise NotImplementedError(')) for p in sorted(pathlib.Path('py4gw').rglob('*.py'))]"
```

The **classification** of those members into the buckets in §4 is the one number that is
not a one-liner: it needs an AST walk to pair each `raise` with its reason string. The
per-class sets are pinned by the offline suites instead —
`tests/test_player_offline.py` holds `DISABLED_MEMBERS` and `ACTION_MEMBERS` by name, and
`tests/test_party_offline.py` and `tests/test_map_offline.py` do the same for their
classes, so no class can lose a member or gain one silently.

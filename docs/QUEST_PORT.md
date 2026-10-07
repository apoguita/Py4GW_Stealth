# Quest port — the class and the binding behind it

**The class:** Reforged's `Py4GWCoreLib/Quest.py` (245 lines, one class, **26 members**).
**Behind it:** Native's `PyQuest` binding (`src/GW/quest/quest_bindings.cpp`, 506 lines), its
semantics (`src/GW/quest/quest_methods.cpp`, 139), the hooks it relies on (`src/GW/quest/quest.cpp`,
143), the record (`include/GW/context/quest.h`, `0x34`), and `QuestData`.

**Verdict: FULL.** Every one of the source's 26 members answers, with the source's own body — each is
a one-line call into the binding, which is ported whole in the same change, and **no member raises**.

## 1. The split is the source's

`Quest.py` is a delegation surface: every member returns or calls exactly one `PyQuest` method, and
`Quest.quest_instance()` is `PyQuest.PyQuest()`. So the port splits the same way:

| file | what it is |
| --- | --- |
| `py4gw/quest.py` | the class, member for member, in the source's order, with the source's bodies and argument defaults |
| `py4gw/native_src/quest/py_quest.py` | the `PyQuest` module: `PyQuest`, `QuestData`, and the free functions the binding also exposes |
| `py4gw/context/world_context.py` | the record reads — **already ported**: `QuestStruct` (`0x34`), `active_quest_id` (`0x28` in `WorldContext` terms, `+0x528`), `quest_log_array`, `mission_objectives_array` |

## 2. Where every member's behaviour comes from

| member(s) | source line |
| --- | --- |
| `quest_instance` | `Quest.py:4-6` → `quest_bindings.cpp:392` |
| `GetActiveQuest` | `quest_bindings.cpp:300-303` — `WorldContext::active_quest_id` |
| `SetActiveQuest` / `AbandonQuest` | `quest_bindings.cpp:293-310` → `quest_methods.cpp:20-46` → **the hook's body**, `quest.cpp:34-44` |
| `IsQuestCompleted` / `IsQuestPrimary` | `quest_bindings.cpp:311-320` — the record's `log_state & 0x2` / `& 0x20` |
| `IsMissionMapQuestAvailable` | `quest_bindings.cpp:81-84` — the mission-objective array is not empty |
| `GetQuestData` | `quest_bindings.cpp:321-335` — **seven fields copied** (`log_state`, `map_from`, `map_to`, `marker_x`, `marker_y`, `is_completed`, `is_primary`); the strings stay empty and `h0024`, `is_current_mission_quest` and `is_area_primary` stay at their defaults, even when the record carries those bits |
| `GetQuestLog` | `quest_bindings.cpp:342-356` — the lighter per-entry copy |
| `GetQuestLogIds` | `quest_bindings.cpp:336-341` |
| `RequestQuestInfo` | `quest_bindings.cpp:357-365` → `quest_methods.cpp:106-117` — **both** functions, info then data |
| the five `(Request / IsReady / Get)` trios | `quest_bindings.cpp:58-239` — one store per field, the client's decoder, and the mission constants below |
| `QuestData` | `quest_bindings.cpp:272-289` (16 fields) |
| `get_quest_entry_group_name` | `quest_methods.cpp:72-93` — the `log_state` switch and its three literal formats |

The log walk itself is `quest_methods.cpp:56-70`: id `0` is nothing, otherwise the first log entry
whose `quest_id` matches — which is what `_get_quest` is here.

## 3. The three divergences, all of them the execution model

1. **No worker thread — but the source's own bound is kept.** The binding pre-creates a store entry,
   decodes on a detached `std::thread`, and waits up to **1000 ms** for the game thread to run the
   decode, writing `"Timeout"` when it does not (`quest_bindings.cpp:90-113`, and per objective at
   `:216-225`). This port's call path *is* the game thread, so the decode is started inline: the
   detached thread is the part that cannot exist here, because there is nothing to wait for. The
   bound and its literal are **kept** — `DECODE_TIMEOUT_SECONDS = 1.0` and `TIMEOUT = "Timeout"` —
   measured from the request, with the decode slot returned to the pool when the answer never comes
   (a slot left in flight is one the next request cannot have). Pinned by
   `tests/test_quest_offline.py::test_a_decode_the_client_never_answers_times_out_the_sources_way`.
2. **Set-active and abandon call the client's own functions — proven live, and the message was not it.**
   The source calls `g_set_active_quest_func` / `g_abandon_quest_func` and hooks them; the hook body
   is `ui::SendUIMessage(kSendSetActiveQuest / kSendAbandonQuest, quest_id)` (`quest.cpp:34-44`).
   This port places no hook on those two functions, and an earlier version therefore sent the hook's
   own message instead of calling — the mechanism the ported `Map.Travel*` and the party actions use.
   **A live run on 2026-10-06 refuted it**: on pid 16972 (map 642, quest log of 23, active quest
   1098), `SetActiveQuest(167)` sent the message and the active quest was still 1098 after a full
   12 s settle, while calling `set_active_quest_func(167)` moved it to 167 instantly (settled 0.0 s).
   The port now **calls**, behind the source's guards: `< 0` refuses outright, then the function has
   to resolve, then the quest has to be in the log. That is also the closer port, not a new mechanism:
   the source's inner layer calls these functions and, with Native's runtime present, its hook
   intercepts the call exactly as it does for Native's own callers; with no runtime present, the
   client's own implementation runs. Pinned by
   `tests/test_quest_offline.py::test_setting_and_abandoning_call_the_clients_own_functions`, which
   asserts both the call and that no UI message is sent.
   **The return value is the enqueue's, not the callee's** (`quest_bindings.cpp:295-298`, `:305-308`,
   `:361-364`): the binding answers `true` for every id that is not negative, because the guards live
   *inside* the enqueued lambda. So a quest outside the log answers `true` while the client is never
   told — and an earlier version of this port answered the guards' outcome instead, which is pinned
   now by two tests whose names say which half they check.
3. **The five stores hold the client's decoded answer**, keyed by quest id, filled by an explicit
   `Request*` — which is the binding's own design (`AsyncStrEntry` + `g_quest_*_map`), not a cache of
   a client record: nothing is stored that a read could have produced again, and the store is what
   `Get*` answers from in the source too.

## 3b. Two traps the audit found, both now pinned by tests

Both were in this port, both produced a *plausible* value, and neither was reachable by the tests as
they stood — they came from re-reading the native lines against the port, not from a failure.

- **The marker is copied raw.** `quest_bindings.cpp:329-330` copies `q->marker.x` / `.y` as they
  stand. This port's record type also has a `marker` property that answers `None` when a component is
  not finite, and going through *that* wrote `0.0` — a guard the source does not make. The port now
  reads the two floats directly, so a non-finite marker arrives as one.
- **The objective text handed to the decoder is the record's raw string.**
  `MissionObjectiveStruct.enc_str` in this port is the *printable rendering* (`\xNNNN` escapes) and
  `enc_str_encoded_str` is the string as the client holds it. `AsyncDecodeAnyEncStr(obj.enc_str, …)`
  (`quest_bindings.cpp:210-212`) hands the client the string itself, so passing the rendering gave the
  client's decoder an escaped copy of its own output. Only reachable inside a mission with objectives,
  which is exactly what the owed live pass would have hit.

## 4. What a negative quest id means

The binding answers mission-map values for `quest_id < 0`, and those constants are its own
(`quest_bindings.cpp:115-151, 181-239`): `"Mission Objectives"` / `"No Active Mission"` for the name,
`"Mission Ongoing"` / `"No Active Mission"` for the description and NPC, the current map's own name
for the location (via `UInt32ToEncStr(name_id or 3, buffer, 8)`), and the mission objectives composed
into lines with `{s}`/`{sc}` bullets and a trailing newline. All of them are ported as written.

## 5. Gates

| check | command | result |
| --- | --- | --- |
| class parity | AST against `Py4GWCoreLib/Quest.py` | **26/26 members, same order, 0 argument-list differences** |
| binding parity | every `.def_static`/`m.def` name read out of `quest_bindings.cpp`, compared **both ways** | **25 statics and 24 module functions — none missing, none added**, and the binding's two classes present under their own names. Mutation-proven: adding one invented member fails the test |
| offline tests | `python -m unittest tests.test_quest_offline` | **20 tests OK** |
| offline suite | `python -m unittest discover -s tests -t .` | **1951 tests OK** (19 skipped: the elevated and connection-dependent ones). The one failure the pass surfaced was not a quest test — `tests/test_context.py` still pinned `CharContextStruct` at `0x448` where the structure is `0x450`, the number the offline test already carries; corrected in the same change |
| types | `pyright pyrightconfig.json py4gw/quest.py py4gw/native_src/quest/py_quest.py tests/test_quest_offline.py tests/probe_quest_live.py` | **0 errors, 0 warnings** |

## 6. The live pass

**The reads ran, 2026-10-05** — `tests/probe_quest_live.py reads`, against `Gw.exe` pid 8456 while the
client sat at the character-selection screen (`map=0`, no character in the world):
`quest_log_ids=[]`, `active_quest_id=0`, `mission_map_quest_available=False`, and every member
answered rather than raising. That is the empty case and it is worth having on the record: with no
world context to read, the ported members return the sources' "nothing there" values. Report:
`tests/live_reports/quest_reads_live.json`.

**The pass with a character in a map is the one below (§6b).** Three things at once were needed: a
logged-in character with quests in its log, an elevated shell, and the owner present for the two
members that change the game. The order is the sources' own: `GetQuestLogIds` → `GetActiveQuest` →
`RequestQuestInfo` → the five `Request`/`IsReady`/`Get` trios → `SetActiveQuest` → `AbandonQuest`,
re-reading the log afterwards to show the client acted. The probe names the two acting members only
when the owner passes them, so the read half can run on its own:

```text
python tests/probe_quest_live.py reads tests/live_reports/quest_reads_live.json
python tests/probe_quest_live.py act   tests/live_reports/quest_act_live.json              # elevated
python tests/probe_quest_live.py act   ... --set-active <id> --abandon <id>                # elevated
```

## 6b. The live pass, 2026-10-06 — the whole class, on a character with a real log

`Gw.exe` pid 16972, map 642 (`IsMapReady` true), a level-20 character with **23 quests** in the log and
quest **1098** active. Reports: `tests/live_reports/quest_member_live.json` (the flip and the whole
name table), `quest_abandon_live.json` (the one abandon), `quest_reads_after_abandon.json` (the
read-only confirmation) and `quest_mechanism_live.json` (the mechanism diagnostic below).

- **The reads answered, all of them.** `GetQuestLogIds` gave the 23 ids in order, `GetQuestLog` the
  per-entry `log_state`/`map_from`/`map_to`/marker, `IsQuestCompleted` false for all 23 and
  `IsQuestPrimary` true **only for 169** ("The Krytan Ambassador" — the log's one primary quest, which
  is exactly the shape a log should have). `IsMissionMapQuestAvailable` false. `GetQuestData(167)`
  answered with the source's seven copied fields and `name == ""`, which is the binding's own
  behaviour (`quest_bindings.cpp:321-335`) rather than a gap.
- **The five decode trios answered on the first poll, every field, 0.0–0.051 s** — for 1098:
  name `Fort Aspenwood`, description `Balthazar is watching over the Luxon and Kurzick forces in Fort
  Aspenwood. Join with one faction and win at least three battles before you return to Zehnchu. …`,
  objectives `{s}Win 3 PvP battles in Fort Aspenwood.{s}*BONUS* …`, location `Zaishen Combat`, npc
  `Zaishen Combat`; for 167 `Deliver a Message to My Wife` / `Ascalon` / `Gurn Blanston`. The marker is
  `[inf, inf]` on every entry — the client's own "no marker", copied raw as §3b requires.
- **`SetActiveQuest(1098)` moved the client: active 167 → 1098, settled in 0.0 s.** This is the run that
  proves the mechanism §3 records: the same member sent as a UI message did nothing for 12 s
  (`quest_flip2_live.json`), and calling the client's own function — which is what the member now does —
  moves it immediately.
- **`AbandonQuest(1432)` ("Wayfarer's Reverie: The Far North") took the quest out of the log, and
  nothing else moved.** Before: 23 ids including 1432. The call answered, and the id was gone from the
  next read in **0.1 s**. The read-only pass afterwards, run separately and unelevated, read
  `[167, 169, 194, 354, 400, 720, 722, 754, 782, 805, 818, 830, 842, 851, 860, 873, 890, 918, 957,
  1048, 1098, 1329]` — **22 ids, 1432 absent, every other id present in its original order, and the
  active quest still 1098**. The owner allowed exactly one abandon, which is why this is asserted from
  three independent reads rather than repeated.
- **Teardown clean**: `hooks_original_after_disconnect: true` after both acting runs — the four entry
  points' bytes are byte-identical to their pre-connect snapshot.

**Two harness defects this pass found, both in the probe and both fixed there:**

1. **`_settle` answers the predicate, not the log.** The abandon step kept the poll's boolean as
   "the remaining log", so a quest that had genuinely left in 0.1 s was reported as
   `gone: false, others_untouched: false`. The step now re-reads `GetQuestLogIds` after the poll and
   judges `gone` from that list — on a step that can be run once, a verdict that cannot be trusted is
   worse than no verdict.
2. **`--names`, added for this pass.** `GetQuestLogIds` says nothing but numbers, and the member that
   removes a quest cannot be taken back, so a run that has to name one reads the name of every id
   first, through the class's own `RequestQuestName`/`IsQuestNameReady`/`GetQuestName`. It changes
   nothing and it is what let the owner pick the target by name (`1432`) instead of by guess.

The probe can now be run without the owner by hand for the read half, and with two named flags for the
acting half; the sources' order, the 30 s window the abandon gets, and the byte check on teardown are
all in the file.


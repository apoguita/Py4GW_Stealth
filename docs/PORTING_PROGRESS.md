# Porting progress (live)

**This file is rewritten as work happens, so it can be read at any moment without asking.** If a
line in "Now" is older than the rounds below it, or the timestamp is stale, that is the signal that
something stopped — not something to wait on.

| | |
| --- | --- |
| **Goal** | `goal-f79c6454-c4a7-4aac-9e29-0e9d416aac38` — finish `Agent` + `AgentArray` faithfully |
| **Round** | 13 (`Camera` ported whole: 46 members, none raising, and the payload gained the write operation it needed) |
| **Round (prev)** | 12 (a name is decoded by the client: 15x faster than the dat route, and no dat record at all) |
| **Round (prev)** | 11 (the dat handling moved off the call path: pre-cached at connect, on a worker) |
| **Round (prev)** | 10 (the owner's second catch: the agent viewer's own scheme, and one name end to end) |
| **Phase** | **a name is decoded by the client** (`Agent.GetNameByID` = Native's `AsyncGetAgentName` route): ~115 ms the first time, 0.09 ms cached, **no dat read at all**; the connect-time dat warm-up is off, `dialog._on_string_decoded` no longer steals other modules' decodes, and a disconnect gives unclaimed name slots back (1074 tests OK) |
| **Phase (prev)** | **the GW.dat work is off the call path**: the connection starts the source's own load on one worker, the table is readable file by file, a decode asks for the one slot it needs instead of reading it, and `disconnect` joins the worker (1073 tests OK) |
| **Phase (prev)** | live: the viewer's scheme read member by member; **one name tested alone** (agent 15, gadget, `\x0C6E` -> "Random Arenas"), six agents put through the port's decoder and the client's; the slot mapping verified live for the first time; the ring cost measured (~1.0 s per string file) |
| **Phase (prev 2)** | live: names walked on all four branches with 0 byte mismatches; two client crashes traced to a killed run's orphaned patch |
| **Phase** | **`Camera` is FULL**: 46/46 members answer, live-verified (reads median 5 us, a write read back from the client's own struct, the camera-unlock patch proven byte-for-byte); the payload gained `WRITE_MEMORY` so a member can change client state on the game's own thread, and the class now caches a patch's address *and* bytes the way `MemoryPatcher` does |
| **Verdicts** | **`Agent`: COMPLETE for this port's purposes** (148 declared, 145 answer; the 3 that raise are two frame-loop halves and the injected-runtime artifact), **`AgentArray`: FULL**, **`Camera`: FULL (2026-09-27)** -- all from the modules' own AST |
| **Verdicts (prev)** | **`Agent`: COMPLETE for this port's purposes** (148 declared, 145 answer; the 3 that raise are two frame-loop halves and the injected-runtime artifact) and **`AgentArray`: FULL** (no raising member) -- both from the modules' own AST, 2026-09-27 |
| **Updated** | 2026-09-27 ~07:00 (round 13) |

## Now (round 12 - the client decodes the name, and it is 15x cheaper)

- **The owner's instruction:** *"i thought you were already using the AsyncGetAgentName path, okay we need
  to do that"* -- and it is done, for the reason the measurements had been pointing at: Reforged's table
  is free only because Reforged runs *inside* the client.
- **The change, and the divergence it carries.** ``Agent.GetNameByID`` keeps Reforged's name and
  two-call shape, but the *decode* is Native's: the encoded string is handed to the client's own decoder
  (``py4gw/ui/async_decode.py``, the port of ``ui::AsyncDecodeStr``) and the text comes back from its
  completion. ``agent_methods.cpp:318-325`` is the source line; Reforged's ``string_table.decode``
  remains in the tree and is still what a caller uses when a table entry has to be rendered on the host
  (``load_string_table``), but **no member reads that table any more**.
- **Measured, same client, side by side** (``live_reports/name_scheme8.txt``, ``find_npc*.txt``):
  a name is **~115 ms** the first time and **0.09-0.5 ms** afterwards, against **~2.1 s** for the first
  name in a slot on the dat route (one record opened ~1.1 s, 91 KB read and decompressed ~0.9 s). The
  texts agree on every agent sampled -- and the client even resolves ``Pet - My Pet`` where the table
  decode stops at ``Pet - %str1%``.
- **The whole run the owner timed** (find the closest "Master of Winds", target it, interact), process
  start to interact: **8974 ms -> 7955 ms -> 4018 ms**. The last step came from two fixes rather than
  from the name route itself: the connect-time dat warm-up is gone (it was competing with the decodes
  for the game thread, which is why target/interact fell from ~70 ms to ~32 ms), and the probe stopped
  burning a 3 s deadline polling for a target announcement that is a separate client notice.
- **What is left, stated plainly:** a *cold* map-wide sweep is still **~2.9 s**, because it is ~41
  first-time decodes at ~115 ms each (17 ms ring pickup + the client's own decode), serialised -- the
  client answers during the call. Two levers, both the owner's to pick: filter the candidates with the
  source's own arrays (``AgentArray.GetAllyArray``/``GetNPCMinipetArray``, a distance cut) so fewer names
  are asked for, or persist the string table so a sweep is the table's 0.1 ms per name.
- **Three real defects found on the way, all fixed and live-relevant:**
  1. **``dialog._on_string_decoded`` consumed decodes it did not own.** It called ``decoded_text(slot)``
     before checking its own three request queues, so any other module's decode (an agent's name!) was
     taken and its text discarded -- measured live, a name reached ``DONE`` and was then read as
     ``FREE`` with nothing cached. It now returns without taking, the rule ``chat._on_string_decoded``
     already followed.
  2. **A disconnect could fail and orphan the block** when names were left in flight: the bridge refuses
     to free a block with decodes outstanding. The name module now gives those slots back in
     ``ConnectedClient.close``, which is what lets the removal complete (``exit=0`` since).
  3. **The client answers only a few decodes at once.** A sweep that placed one per slot (32) answered
     **none** -- ``_name_requests`` now holds at most ``MAX_NAME_DECODES_IN_FLIGHT`` (8) and the rest
     answer ``""`` for the caller to ask again, which is the source's own two-call contract.
- **Also established this round, and it changes the dat picture:** the ring is *not* the cost. One
  command (PING) is **3.3 ms min / 16.6 ms median**, 60 hits/s; a dat record is ~1115 ms to open and
  close, and a whole ``read_file_by_hash`` ~2066 ms -- the client's own work. Batching commands (my
  earlier idea) would have saved ~50 ms per file, which is why it was dropped.
- **Evidence:** **1074 tests OK** (1.4 s), `pyright` on the touched files `0 errors`; the client was read
  back after each run and its two hook targets carry their own bytes; reports under ``live_reports/``
  (``find_npc11.txt``, ``name_member3.txt``, ``name_scheme8.txt``, ``perf_live.txt``).

## Now (round 11 - the dat handling pre-cached at connect, and nobody waits for it)

- **What was asked, in the owner's words:** *"the issue is not the reads, its the handling of the dats,
  what can we do, can we pre cache that on connect or map change so when the user gets a name doesnt
  have to pass trough the long warmup? could we fire a thread that does that on connect? would that
  make the connect take longer?"* — and then the requirement itself: *"if the dats were already
  previously dealt we shouldnt have those multiple secods but a 150 ms operation"*.
- **Both answers, and both are now in the tree.**
  1. **A thread does not make the connect longer.** The trigger in the `TextParser` refresh (which is
     what connect runs) now calls the source's own enqueue, `load_string_table(language_id)`
     (`text_parser_context.py:274-282`), and that returns immediately: the load runs on one daemon
     worker (`_start_warmup` -> `_warmup_worker`). The only connect-side work added is nothing at all —
     the language is already in hand at that point.
  2. **No caller ever reads a file again.** The table is parsed into `_string_table` **file by file as
     the worker reads them** (`_read_slot`), so a name whose entry has been read answers while the rest
     of the language is still loading; and a decode whose entry is *not* in it yet asks the worker for
     the one slot that entry lives in (`_request_slot`) and answers `""` — the source's own pending
     value — instead of reading it itself. A slot somebody is waiting for is read **next**
     (`_slot_order` checks for a request before every yield).
- **A map change needs nothing.** The table is the client's *language* table: same files, same entries,
  for the session. What a map change changes is which slots the names in play need, and those are read
  on demand (asked for, and served next). The per-language table is already kept across reconnects
  inside one controller process (`_string_tables_by_language`).
- **Two members the earlier rounds had invented for the on-demand path are gone** with it:
  `use_string_table_language` (the trigger's stand-in) and `_ensure_entry_loaded` (the inline read).
  What replaced them is the source's own call and one worker.
- **`disconnect` stops the worker before the block goes away** (`ConnectedClient.close`, right after the
  listener stops): the warm-up reads GW.dat through that connection, and a worker left running would
  also leave the record it was reading open in the client — the client's own `Gw.dat still open`
  assertion of round 10.
- **Evidence:** **1073 tests OK** (1.0 s; +2, the new `WarmupTests`), `pyright` on the five touched files
  `0 errors`. The two new tests pin exactly what was asked: `load_string_table` returns **while the
  worker is still inside its first read** (the connect does not wait), and a slot a decode asks for is
  read before the ones nobody wants (`calls[:3] == ["a", "c", "b"]`).
- **Still to measure live** (the client was closed): the first-name latency with the warm-up running,
  and how long the 99-file load takes in practice. One run of
  `python tests\perf_access_cost.py --live` prints the PING pickup, the hook-hit rate, the dat chain
  phase by phase and the first-vs-cached decode; `tests/probe_name_scheme.py` prints the whole table of
  names beside the viewer's own rows. Both are launched with one UAC prompt and need the game running.

## Now (round 10 - the owner pointed at the agent viewer, and was right to)

- **What the owner said, and where it sent me.** *"you will need to see the agent viewer in the reforged
  branch, it has a table where the agent names are displayed, you need to follow the exact scheme or
  else it wont work"*, and before that *"they keep a table of loaded names, the process is fairly fast,
  i think you might be doing something completely different"*. Both point at the sources' own name path.
  Here it is, read line by line, and here is one name taken through it live.
- **The agent viewer is `Widgets/Coding/Debug/Guild Wars/Agent Info.py`** (`MODULE_NAME = "Agent Info
  Viewer"`, 625 lines). Its scheme, which is the scheme to follow:
  - rows come from `AgentArray.GetAgentArray()` + `Agent.GetAgentByID(agent_id)` (`:519-524`), with the
    nearest enemy/ally/item/gadget/NPC/target rows above them (`:465-486`);
  - the **name column is `Agent.GetNameByID(agent.agent_id)`** (`:53`, `:77`);
  - the encoded column is `Agent.GetEncNameByID` / `Agent.GetEncNameStrByID` (`:49`, `:90`);
  - and its diagnostic variant prints exactly the state the port's table carries --
    `string_table._string_table_loaded`, `_load_enqueued`, `_last_load_status`, and
    `raw in string_table._pending` (`:61-68`).
  **That is the port's member set and the port's body**: `GetNameByID` = `PyAgent.get_agent_enc_name`
  + `string_table.decode` (`Agent.py:142-179`), implemented as written (`py4gw/agent.py:109-160`,
  `508-566`; `py4gw/internals/string_table.py:1143-1205`). Nothing in the scheme needed changing --
  which is why this round was spent **proving it**, not rewriting it.
- **Reforged and Native gather a name in the same two steps and differ only in the decoder:**
  | | fetch | decode |
  | --- | --- | --- |
  | Reforged (Python) | `PyAgent.get_agent_enc_name` (`agent_bindings.cpp:216-224`) | `string_table.decode` -- a table read out of GW.dat **in process**, so it is free |
  | Native | the same C++ `GW::agent::GetAgentEncName` (`agent_methods.cpp:249-316`) | `ui::AsyncDecodeStr` -- **the client decodes** (`agent_methods.cpp:318-325`, `ui_methods.cpp:2582-2607`) |
  The port has both mechanisms: the table (`py4gw/internals/string_table.py`) and the client's decoder
  (`py4gw/ui/async_decode.py`, the dialog and chat port). This round put a single name through both.
- **One name, alone, live** (`tests/probe_name_scheme.py`, new): the owner's instruction was *"grab a
  single npc name and test if it works"*, so the probe prints every intermediate value. Agent **15**,
  client `Gw.exe` pid 20496:

  ```text
  {"stage": "agent", "agent_id": 15, "type": 512, "is_gadget": true,
   "name_bytes": [110, 12, 0, 0], "pointer": 672027352}
  {"stage": "compare", "agent_id": 15, "client_name": "",
   "port_name": "Random Arenas", "port_ms": 2067.753, "agree": false}
  {"stage": "gadget_walk_record", "agent_id": 15, "record": true, "extra_info_sub_ptr": 663221008}
  {"stage": "gadget_walk_sub", "agent_id": 15, "sub": true, "gadget_name_enc": 0, "gadget_id": 75}
  {"stage": "gadget_walk_info", "agent_id": 15, "gadget_info_valid": true, "gadget_info_size": 9524,
   "gadget_id": 75}
  {"stage": "gadget_walk_info_record", "agent_id": 15, "record": true, "name_enc": 672027352}
  ```

  Read the way native reads it (`agent_methods.cpp:290-307`): `type = 0x200` is a **gadget**
  (`agent.h:136`), `gadget_name_enc` is **null**, so the name comes from `gadget_info[gadget_id].name_enc`
  with `gadget_id = 75` out of a 9524-entry table -- and the pointer the port read from that record **is
  the pointer the walk names**. The row is the source's, branch for branch.
- **Six agents, and four of them prove the decode.** Same run, same client:

  | id | type | encoded | the port's text | what it is |
  | ---: | --- | --- | --- | --- |
  | 15 | `0x200` gadget | `\x0C6E` | `Random Arenas` | a portal prototype |
  | 16 | `0x200` gadget | `\x0C9E` | `Great Temple of Balthazar` | a portal prototype |
  | 26 | `0xDB` living | `\x8102\x064F` | `Vekk` | a hero, by name |
  | 27 | `0xDB` living | `\x8101\x38AA` | `Dunkoro` | a hero, by name |
  | 28 | `0xDB` living | `\x0BAA\x0107...` | `Pet - %str1%` | a pet-name pattern |
  | 29 | `0x200` gadget | `\x8102\x35B5\xE9AA...` | `Zaishen Chest` | the chest |

  `Vekk`, `Dunkoro` and `Zaishen Chest` are the client's own names for those records, and two of them
  come through the table's RC4 path -- a wrong index or a wrong key cannot produce them. So the decoder
  is not "gathering whatever": it renders four independent records correctly, one of them a hero and one
  of them a chest.
- **`Random Arenas` is a map name, out of the sources' own table** --
  `Py4GW_Reforged_Native/include/GW/common/constants/maps.h:954` (`"Random Arenas"`, in the outpost
  list, with `Great Temple of Balthazar` beside it). The objects that carry such a name are the client's
  **gadget prototypes named after their destination** -- the portals. The string is therefore the
  client's own name for the prototype that record points at: a portal gadget in a Battle Isles map, in
  the same map as the Zaishen Chest. The probe prints the map id (next run), which will name the map.
- **The slot mapping was verified live for the first time, and it is the source's.** The probe prints
  what `_load_table_for_language` rests on (`string_table.py:766-805`): `language_id = 0`,
  `entries_per_file = 1024`, `slot_count = 99`, and slots 0-7 each carry
  `start_index == slot_index * 1024`, `end_index == start_index + 1024`, `lang_id = 0`. Entry 2926 is
  therefore in slot 2 at `2 * 1024` -- exactly the file the port read, and exactly what Reforged reads
  for that entry.
- **The client's own decoder, called for the first time, and it answered empty.**
  `py4gw/ui/async_decode.py` is Native's route; every precondition was there
  (`ui.validate_async_decode_str_func` resolves, the decoder stub is placed at `0x035F0000`, the
  `TextParser` address is live) and each call round-tripped in **~130 ms**, but the answer was `""` for
  all six strings. Empty is also what the wrapper's own three refusals write, so the next run prints
  `decode_state(slot)` plus the preconditions before the call, which tells those two apart. **Open, and
  this is the work item.**
- **Why a name costs what it costs here, measured.** The dispatcher takes **one command per hit**
  (`py4gw/game_thread/payload.py:978-996`) and one command round trip measures **~130 ms**; the GW.dat
  chain is four of them. Live, per string file: **1055 / 1060 / 1066 ms** for three *new* slots,
  **20.7 ms** for a slot already in the table, **0.104 ms** for a cached decode. Reforged pays none of
  this -- its dat read is in-process -- and the source's eager load of all 99 files would cost **~100 s**
  through this ring, which is why the port reads the one file an entry names and keeps it. That is a
  **mechanism divergence and it is recorded as one**.
- **The map was the Isle of the Nameless, and that is what makes the two names readable.** The run
  printed `map_id = 280`; the sources' own table says `NAME_FROM_ID[280] = "Isle of the Nameless"`
  (`Py4GW_Reforged_Native/include/GW/common/constants/maps.h`, the array at line 765; the `MapID` enum
  agrees: 279 `Leviathan Pits`, 280 `Isle_of_the_Nameless`, 281 `Zaishen_Challenge_outpost`). That map
  is where the **Zaishen Chest** stands (`settings ... items.json`: *"The Battle Isles / Isle of the
  Nameless / Zaishen Chest"*) and where the **portals to the Battle Isles outposts** are -- so the two
  gadget names are the destinations those portals lead to, which is what the client's gadget-prototype
  table calls them. The owner's objection -- *"there no random arenas anywhere in this map"* -- is
  answered by the map itself: the *portal* to Random Arenas is in the Isle of the Nameless, and the
  Zaishen Chest standing beside it is the proof that the decoded names are the client's own.
- **The fetch is cross-validated by a second client field.** `Agent.GetGadgetID` (Reforged
  `Agent.py:1600-1606`, the agent record's own `gadget_id` at `+0x0D0`, `agent.h:177`) answers
  **75** for agent 15 and **3651** for agent 16 -- exactly the `gadget_id` the summary sub-record
  carries, which is the field native's walk indexes `gadget_info` with. Two independent client fields
  agree, so the record the port indexed is the record native indexes.
- **The client's own decoder is not a proven route on this build, and that reframes the empty answer.**
  `tests/test_live_dialog_text.py` records that the dialog step that fills `AsyncDecodeStr` is *blocked*
  on this client (`DialogLoader_GetText` is not the loader here, and calling it faulted the client on
  2026-09-25), so **the client-decode route has never been live-exercised with an expected text** --
  before this round it had never been called at all. The six empty answers are therefore at least as
  likely to be this side of the boundary (the emitted stub, or the slot the host reads) as the client
  refusing a valid string, and the probe now carries a **control**: the local player's own encoded name,
  which the client renders on the nameplate. If that one also comes back empty, the stub/slot path is
  the defect; if it comes back as the character's name, the client is refusing these particular strings.
  The probe also reports the call's three timings apart (placement, call, wait for the callback), which
  is what tells a host-side refusal (completed during the call) from the client answering later.
- **The run that carried this vanished mid-way, and the owner's crash log names the damage.** `Gw.exe`
  pid 20496 stayed alive and responsive and the probe's console stops after agent 27 with no traceback
  and no `done` marker, i.e. the Python process was terminated externally. Sixteen minutes later, when
  the client was closed, it asserted: **`Error: file 'F:\GW\GW1\Gw.dat' still open`
  (`NtFile.cpp(321)`, 19:39:35)**. That is this project's footprint and nothing else: the only thing
  here that opens a dat record is the string-table chain (`py4gw/dat_reader.py`), and a controller that
  dies between `ReadFileBuffer` and `CloseRecObj` leaves the record open in the client until it exits.
  Confirmed read-only before the client closed: the entry hook was still installed
  (`leave_game_thread_func` at `0x00845880` = `BaseAddr + 0x235880` read `e9 7b a7 74 03 90 90 90`).
  **Full analysis, including what a crash log does and does not reveal about this project's traces, is
  in [`RESEARCH.md`](RESEARCH.md) § *The 2026-09-26 19:39 client exit assertion*.** The operational rule
  is unchanged and now has a second reason behind it: **a live run must be allowed to finish**, and a
  run that dies leaves a client to be restarted.
- **Next:** start the client again (a restart clears the hook and the record), then one elevated run of
  `tests/probe_name_scheme.py` (`live_reports/name_scheme7*`), which prints the map id, the decode
  preconditions, the three decode timings per string, the **control string**, the gadget walk, and the
  viewer's own rows — so the port's table can be put beside the viewer's and read off. The open item
  behind it: if the control answers text, the client-decode route is the one-command name path
  (~130 ms, no GW.dat) and the stub's empty answers for agent names become a specific finding; if it
  answers empty, the stub/slot path is the work item.

## Now (round 9 — live)

- **The owner's catch, and it was two real defects — both about how the sources gather a name:**
  1. **Reforged loads the string table once, on the first frame** (`TextContext.py:152-155`, inside the
     `TextParser` refresh) and then every name is a dictionary hit. This port had the same trigger but
     nothing fired it until a *decode* did, so the whole GW.dat chain ran **inside the first
     `Agent.GetNameByID`** — and again on every later read while a load had not succeeded
     (`load_string_table` resets its flag on failure). Fixed: `ConnectedClient.__init__` refreshes the
     `TextParser` context once, right after the capability layer is installed — this port's startup,
     where Reforged's first frame would be. Pinned by
     `test_the_string_table_is_loaded_by_the_connection`.
  2. **The record behind a name is a table index, not a rebuilt cache.** Native's
     `GetAgentEncName(id)` reaches the record through `GW::agent::GetAgentByID` — *one index* into the
     client's agent table plus the movement check (`agent_methods.cpp:73-88`). This port called
     Reforged's **Python** `Agent.GetAgentByID`, whose view answers from `_build_allegiance_cache`: a
     traversal of every slot (975) to answer one id. Now ported as native writes it —
     `_get_agent_by_id` in `py4gw/agent.py`, with **both** halves indexed (the movement array too;
     the first attempt still materialized it). Live A/B on the same client, 25 agents:
     **0.09 ms** per name against **2.10 ms** for the view-cache path cold — 22× for the case that
     matters, a caller asking for one name — with **0 byte mismatches** and all four branches intact.
- **The client crashed twice, and neither crash was a read path.** Both came from a run being
  **killed without `disconnect()`**, which leaves this project's entry patch live in the client; the
  next connect then refuses to patch the stale target (fail-closed — *"expected 55 8b ec 8b 45 08 83
  f8 56, observed 55 8b ec 83 ec 2c 53 8b 5d. Nothing was written."* at `0x008440C0`) while the
  client's game thread is still running the orphaned stub, and the client dies at `eip=01b00000`.
  Restarting the client clears it. Full timeline, trace and evidence: [`RESEARCH.md`](RESEARCH.md).
  **Consequence for how live runs are done: a run must be allowed to finish.**
- **What the live runs proved before that:**
  - `tests.test_agent_array` — **6 tests OK (2 skipped)** on a real connection (client pid 47456):
    resolver `0x00E0C714`, header `size=188, capacity=251`, categories **all=43, ally=3, enemy=10,
    gadgets=3**, `Agent.GetAgentByID(15)` → gadget at `(-1943, -1725, 0)`. That is the live proof of
    the point-of-use `AccAgentContext` refresh.
  - `tests.test_live_agent_effects` — `test_encoded_names_are_the_clients_own_bytes` **ok** on the
    same connection (the binding's bytes, terminator included).
  - **The names, unelevated and complete** (`tests/probe_agent_effects_live.py`, every present
    agent): branches **player array 1 / world `agent_infos` 35 / NPC record 4 / gadget context 3**,
    43 named records, **0 byte mismatches** between the ported `get_agent_enc_name` and an
    independent read, and `IsMartial`/`IsMelee` over **23 armed agents with 0 mismatches** against
    the source's own body.
- **Two live-test defects found and fixed** (both mine, neither the port's): the martial test compared
  the `ILLUSIONARY_WEAPONRY_ID` memo before anything had written it (it is `0` until
  `IsMartial`/`IsMelee` runs, `Agent.py:1340-1342`); and the name tests retried per agent, which
  multiplied the table-load wait by the sample size and made a slow run look hung.
- **Next:** restart the client, then the suite in one uninterrupted elevated run:
  `pwsh -NoProfile -File tools\run_live_suites.ps1 tests.test_live_agent_effects tests.test_agent_array`

- **The live run happened, without elevation.** `py4gw.connect()` is a write and asserts elevation,
  so the probe reads **directly** instead: `tests/probe_agent_effects_live.py` opens the read-only
  reader, builds the same facades `ConnectedClient` builds, registers that stand-in as the current
  client, and lets the ported members run unmodified. Client: `Gw.exe` pid 46544
  (`F:\GW\GW1\Gw.exe`). Full output: `live_reports/probe_agent_effects_live.txt`.
- **The agent name — all four branches of the source's walk answered:**
  | branch (`agent_methods.cpp:263-316`) | agents |
  | --- | ---: |
  | player array (`players[login_number].name_enc`) | 55 |
  | world `agent_infos[agent_id].name_enc` | 26 |
  | NPC record (`GetNPCByID(player_number).name_enc`) | 7 |
  | gadget context (`gadget_info[id].name_enc`) | 2 |
  90 of the 93 non-null records carried a name, and **the ported `get_agent_enc_name` returned
  exactly the bytes an independent read of the same pointer returned for every one of them**
  (`port_bytes_mismatches: []`).
- **55 player names decoded through `Agent.GetNameByID`**, with no string table at all — the inline
  `0x0BA9` form: `Blacki D Dragon`, `Twiddly Knobs`, `Zero Refrain`, `Soul Hanako`,
  `Ragnarok Windwalker`, `Smeagol The Sinless`, `Hammers Are Amazing`, … The live byte shape is
  `0x0BA9` + `0x0107` + UTF-16LE text + `0x0001` + terminator (38 bytes for 15 characters), and the
  offline fixture in `tests/test_agent_offline.py` now reproduces it exactly — including why that
  word must be nonzero: the binding's copy stops at the first zero **code unit**.
- **The names that are not player names are string-table indices** (`\x8102\x3B6F…`), so their text
  needs the table GW.dat fills — a call into the client. That half is
  `tests/test_live_agent_effects.py` (the elevated suite, written this round).
- **The skill timer is the client's clock:** `2202888165 → 2202888416`, **+251 ms** across a 250 ms
  sleep; `GetGWWindowHandle()` = `592774`.
- **The array view reads as the source describes:** `agent.agent_array_addr` = `0xE0C714`, header
  `buffer=0x31411068, size=975, capacity=1024`, 975 slots → 93 non-null (91 living, 2 gadgets),
  categories **all 93, ally 56, enemy 0, items 0, gadgets 2**, and `view.GetAgentByID(10)` =
  `Agent.GetAgentByID(10)` = record 10.
- **One live defect, found and fixed:** the view's cache gate read `AccAgentContext.get_context()`,
  a class cache nothing refreshed outside Reforged's frame loop — live, every category list answered
  **empty** (including `GetAgentArray()`). Fixed by the port's own point-of-use rule
  (`AccAgentContext._update_ptr()` before `get_context()`, exactly as `string_table` refreshes
  `TextParser`), and the literals above are the post-fix readings. Recorded in `docs/RESEARCH.md`.
- **The effects array was null at run time** (`buffer=0x0, size=0, capacity=0`): the character had no
  effects or buffs running, so the walk correctly answered empty/`0`/`False`. The elevated suite
  compares block for block when blocks exist and skips with that reason when they do not.
- **What only the elevated suite can do:** the GW.dat string-table decode (non-player names), and
  everything through the real `ConnectedClient`. Run:
  `pwsh -NoProfile -File tools\run_live_suites.ps1 tests.test_live_agent_effects tests.test_agent_array`
  — the runner's default list now includes both (and the probe). **Two runner defects were fixed so
  the probes actually run:** its `*.py` branch built the path with a dot-to-backslash replacement
  that mangled the extension (`…_live\py`), and its per-suite log name embedded the entry's slashes,
  so a probe's report could not be written. A probe entry is now a path (`tests/probe_x.py`) and the
  log is named for the suite's leaf (`live_reports\probe_x.py.log`) — verified by running the probe
  through the runner: `exit=0, 2s`.
- **Evidence:** the probe's report file (above); `1070 tests OK` after the fixture was corrected to
  the live byte shape; scoped `pyright` on the live files, the probe and the touched library files
  `0 errors`. The probe was run twice, in two different districts (93 then 43 non-null records,
  55 then 1 other player), and **both runs reported zero byte mismatches** — the walk is not
  state-specific.

## Now (round 8)

- **`py4gw/effect.py` landed**: Reforged's `Effects` (15 members) over Native's `PyEffects` binding
  over the `GW::effects` walk — **12 of the 15 work**. The walk is `Context::GetPartyEffectsArray()`
  scanned for the matching `agent_id` (`effects_methods.cpp:29-55`), which this port already reads
  (`WorldContextStruct.party_effects` → `AgentEffectsStruct.effects`/`.buffs`; native's layouts
  0x24/0x18/0x10 all match), so every effect and buff answer is a read: the counts, both `*Exists`
  walks, `HasEffect`, `EffectAttributeLevel`, `GetEffectTimeRemaining`, `GetBuffID`, `get_instance`
  and the two list builders.
- **The skill timer landed with it** — `py4gw/memory/memory_manager.py`, the port of
  `PY4GW::MemoryManager` (7 members): `GetSkillTimer` = `timeGetTime() + *g_skill_timer_ptr`
  (`memory_manager.cpp:69-71`, the global the catalog names `memory.skill_timer_ptr`),
  `GetGWWindowHandle` (`*window_handle_ptr`), `GetGWVersion`/`MemAlloc`/`MemRealloc`/`MemFree` as
  typed calls on the client's own thread, and `Scan` as the source's resolve-once step. Reached as
  `client.memory_manager`.
- **What that closed:** `Agent.IsMartial`, `Agent.IsMelee` (**`Agent` 145 of 148**, three left:
  the console path and the two frame-loop members), the effect snapshot's two computed fields, and
  **`Skillbar.SkillbarSkill.get_recharge`** — which had been raising with exactly this requirement
  in its message since the `Skillbar` port. `DropBuff` and `ApplyDrunkEffect` are the two client
  calls (`effects.drop_buff_func` / `effects.post_process_effect_func`, forms `U32` and `U32_U32`).
- **Two findings, both on their member:** `GetAlcoholLevel` is *not* a read — native captures the
  client's post-process argument with an entry hook (`effects.cpp:24-41`), so the member raises and
  the entry is now in `docs/TARGET_SIDE_WORK.md` with its next step; and `GetAlcoholTimeRemaining`
  calls `PyEffects.PyEffects.GetAlcoholTimeRemaining()`, **which the binding does not implement**
  (`effects_bindings.cpp:181-183`) — the stub declares it and native tracks no alcohol time, so the
  member reports that disagreement rather than inventing a clock.
- **Evidence:** `1070 tests OK` (1.0 s; +19 this round, `tests/test_effects_offline.py` is 16 of
  them); scoped `pyright` on the nine touched files `0 errors`; `Agent`'s raising set pinned at
  **3** from the module's own `ast`; the skillbar slot's recharge pinned against a fixture timer
  (both branches: a zero recharge answers `0` without asking, a real one is the masked `DWORD`
  subtraction).
- **The last port-side helper in the context module is gone.** `_timed` — a `contextmanager` the
  deleted layer had introduced to time the resolver — is removed, with the `perf_counter` parameters
  it fed on `AgentArray.resolve_address`/`initialize`/`read_context`; `client.py` calls
  `initialize()` like every other facade. The definition inventory of
  `py4gw/context/agent_array.py` against the pre-deletion backup now reads: **nothing added, and
  every missing name is an invented one**. `_memory_reader` stays, and deliberately: it is the
  annotation-only `Protocol` the same module uses for its reader parameters, declared identically in
  20 other ported context modules — no behaviour, nothing calls it, and the module has carried it as
  its annotation shape throughout.
- **Agent's remaining three are now classified, and none of them is porting work.**
  `enable`/`_invalidate_property_cache` are the two halves of Reforged's per-frame cache
  registration — no frame loop here, and `PORTING_RULES.md` forbids standing in a throttle of our
  own. `GetProfessionsTexturePaths` prefixes its paths with
  `PySystem.Console.get_projects_path()`, which native defines as
  **the injected runtime's own module directory** (`system_bindings.cpp:72-74` →
  `process_manager.cpp:38-40`, where its `Assets/Textures/Profession_Icons` live): this project is a
  controller package with no such module and no such assets, so there is no path to build. The
  member is the **third of the artifact kind** — `AGENTS.md` § *the unit of work is the class* now
  names all three, with `Player.player_instance` and `Dialog._call_native_dialog_method` — and it
  reports that rather than returning a string the source never produces. `AGENT_PORT.md` carries the
  table.
- **Next:** (1) **the module-level `get()` sweep** — still the open cornerstone violation, 24
  context modules and ~60 call sites, and it needs the owner's call; (2) **`Quest`**, the next class
  in the friction order (the async-decode path a dialog caption already uses); (3) the alcohol hook
  (`TARGET_SIDE_WORK.md`) and the frame loop (structural); (4) back to `Player`.

## Now (round 7)

- **`PyAgent.get_agent_enc_name` is ported, and it was never target-side work** — the note that
  called it that was wrong. The binding (`agent_bindings.cpp:216-224`) calls **native's own**
  `GW::agent::GetAgentEncName` (`agent_methods.cpp:249-316`), which is Py4GW's C++ over client state
  this port already reads, so the port is read-only: no `game_thread` call, no patch. What it needed
  was the cascade, and every step of it is now in place —
  `py4gw/agent.py` carries `get_agent_enc_name` plus native's two functions as
  `_get_agent_enc_name_by_id` / `_get_agent_enc_name_by_agent` (the agent record, the world's
  agent-name array, the player array by login number, the NPC fallback, the agent-summary gadget
  entry, the gadget context, the item array), and `item::GetItemById`
  (`item_methods.cpp:109-112`) was added to `py4gw/context/item_context.py` because the item branch
  needs it.
- **What it closed:** `Agent.GetNameByID`, `GetEncNameByID`, `GetEncNameStrByID` and, through them,
  `IsNameReady`, `GetAgentIDByName`, `GetAgentIDByEncString`, `GetModelIDByEncString` and the
  `RequestName` alias — **8 of the 13 raisers**, so `Agent` is **143 of 148**, and the five that
  remain are the two `Effects.HasEffect` members, the console-path one and the two frame-loop ones.
  **`Player.GetName` is the source's body again** (`Agent.GetNameByID(Player.GetAgentID())`); it had
  been adapted to read the character context's name field only because this binding was missing.
- **The one divergence, and it is the external read's:** the binding walks the client's `wchar_t*`
  to its terminator (that pointer is in its own process); this port reads it through a bounded
  `ReadProcessMemory`, so the copy stops at the terminator or at `MAX_ENC_NAME_CODE_UNITS` (256 code
  units). Documented on `get_agent_enc_name` and in `AGENT_PORT.md`.
- **Evidence:** `1051 tests OK` (1.0 s) — 10 more than last round, all of them new; scoped `pyright`
  on `py4gw/agent.py`, `py4gw/context/item_context.py`, `py4gw/player.py` and the test file
  `0 errors`. New offline coverage: `AgentEncNameTests` (11 tests) drives **every branch** of the
  walk against records a fixture builds and a reader that serves them — the agent record, the world
  agent-name array, the player array by login number (and the null answer past its size), the NPC
  fallback, the agent-summary gadget entry, `gadget_info`, the item array by item id, the bound, and
  the four members that call it. The raising-set test now pins **5**, from the module's own `ast`.
- **Next, in the order I would take it:** (1) **`Effect`/`Effects`** — the class map's next class,
  closing `IsMartial`/`IsMelee` (2 of the 5) and the last offline dependency `Agent` has;
  (2) the **module-level `get()` sweep** (24 context modules, ~60 call sites — the owner's call is
  still open on it); (3) the console path and the frame loop, both of which are structural rather
  than porting work; (4) back to `Player`.

## Now

- **Step 3 done: `py4gw/context/agent_array.py` holds only the sources' own surface.** The module
  went 2639 → 1569 lines (28 definitions deleted): `AgentReference`, `AgentArraySnapshot`,
  `LivingAgentSnapshot`, `StaleAgentReferenceError`, `AgentKind`, the four `Reforged*Struct`
  duplicates, `_agent_record_type`, and the facade members that existed for them (`read`,
  `read_agent`, `read_agent_by_id`, `snapshot`, `living_snapshot`,
  `refresh_living_agents`, `get_living_agent`, `_read_snapshot`, `_validate_reference_current`,
  `_read_record`, `_read_pointer_values`, `_read_pointer_at`, `_kind_from_type_flags`,
  `max_pointer_slots`, `max_references`, the dead offset constants and their `__init__` arguments).
- **A name-based deletion removed 8 members it should not have, and they are back**: the AST pass
  matched any definition called `snapshot`, so `AgentStruct.snapshot`, `DyeInfoStruct.snapshot`,
  `ItemDataStruct.snapshot`, `EquipmentItemsUnionStruct.snapshot`, `EquipmentItemIDsUnionStruct.snapshot`,
  `EquipmentStruct.snapshot`, `TagInfoStruct.snapshot` and `VisibleEffectStruct.snapshot` went with
  the facade's `snapshot` property. All eight are restored verbatim, and the check is now an **AST
  inventory diff** against the pre-deletion backup: every name that is missing is an invented one,
  and every name that is present is the source's. That is the gate for the next deletion too.
- **Consumers re-pointed** (nothing in the tree references a deleted name):
  `examples/all_contexts.py` → `client.agent_array.get_context`; `tests/test_agent_array.py` — the
  live suite's subject *was* the invented API, so it is rewritten on the source surface
  (`read_context()` header + `Get*Array()` + `Agent.GetAgentByID`); `tests/perf_agent_array.py` —
  same, it now measures the view read and nested record access; `tests/test_agent_array_offline.py`
  — the three tests that pinned the snapshot's truncation/staleness guards are replaced by
  `GWArrayView` boundary tests (the place the port actually keeps the bounded-read decision);
  `AGENTS.md` step 1 of the live-dialog procedure named `client.read_agent_array()` and now names
  the source idiom. Both `__init__.py` export lists lost the deleted names.
- **Evidence:** `1039 tests OK` (1.0 s); scoped `pyright` on the 8 touched files `0 errors`.
- **Findings recorded this round, both new:**
  - Reforged's *Python* declarations of `ItemData`/`Equipment`/`AgentLiving` (0x13 / 0xF3 / 0x1C2)
    disagree with native's own `static_assert`s (0x10 / 0xD8 / 0x1C4), which is what the deleted
    `Reforged*` duplicates existed to keep visible. The port reads with native's sizes; the
    disagreement is written down in `AGENT_PORT.md` and in the struct test instead of kept as a
    second set of structs.
  - **The module-level `get()` helpers are a port-side invention.** 24 of the 25 ported
    `py4gw/context/*.py` modules end with `def get()` ("the context of the current selected
    client"); Reforged's `native_src/context/*.py` declare **no** module-level functions at all
    (only `MapContext.py`'s private `_file_hash_to_file_id` / `_get_prop_model_file_id`, which the
    port has). This is the same shape as the cornerstones' worked failures and it is the next
    question to settle — see the open items.
- **Step 4 done: docs rewritten, and `Agent`'s 13 raisers re-walked member by member.** Every
  recorded requirement was checked against the line it cites — `Agent.py:40-50` (the four caches
  `_invalidate_property_cache` clears), `Agent.py:52-60` (`enable`'s `PyCallback.Register`),
  `agent_bindings.cpp:216` + `stubs/PyAgent.pyi:98` (`get_agent_enc_name`, which wraps the client's
  own `GW::agent::GetAgentEncName`), `Effect.py:102` (`Effects.HasEffect`), `stubs/PySystem.pyi:105`
  (`get_projects_path`) — and all of them are accurate. The split is **8 direct + 4 transitive + the
  `RequestName` alias = 13 of 148**, computed from the port's own `ast`, not counted by hand.
  **Two checks came out of the walk and are now tests** (`tests/test_agent_offline.py`,
  `AgentSourceReferenceTests`): every member's docstring reference must be its own block in the
  source (that caught a real off-by-one — `GetRotationSin` named `750` for a member starting at
  `751`), and the raising set must be exactly those 13 names.
- **Evidence:** `1041 tests OK` (1.0 s); scoped `pyright` on the touched files `0 errors`;
  reference audit: 146 members point at their `@staticmethod` line and 2 (`GetModelID`, `GetXY`) at
  their two-decorator block start, because they are the two `@frame_cache` members.
- **Step 5 needs the owner's call — the four candidates, in the order I would take them:**
  1. **`Effect`/`Effects`** (item 2 of the class map's handoff queue) — closes `Agent.IsMartial` and
     `Agent.IsMelee`, i.e. 2 of the 13, and it is the last *offline* dependency `Agent` has. Its
     mechanism is native's `PyEffects`/`effects_bindings.cpp` over the effect array the ported
     `AgentLivingStruct` already reads.
  2. **The module-level `get()` sweep** — the cornerstone violation found this round: 24 context
     modules carry a `def get()` with no counterpart in either source (Reforged's context modules
     declare none), and ~60 call sites read them. Delete-and-route-through-`client.*`, or record
     them as the port's documented accessor divergence. Cheap to start, wide in reach.
  3. **`PyAgent.get_agent_enc_name`** — closes 3 direct + 4 transitive raisers (7 of the 13), but it
     is **target-side** work: it needs the client's own `GetAgentEncName` driven through
     `py4gw/game_thread` (`docs/TARGET_SIDE_WORK.md`), which is the largest item here.
  4. **Back to `Player`** — the original scope: `Player` is INCOMPLETE and its remaining members are
     named in `PLAYER_PORT.md`.

## Rules this file follows

- **A line is written before anything slow starts**, and rewritten when it finishes — no silent
  minutes.
- **Every claim carries its evidence** (the command, its result and how long it took), so nothing
  here has to be taken on faith.
- **Type-checking is scoped** to the files a change touches (`pyright <files>`, ~1 s). A whole-repo
  `pyright` (4–5 min) is run **only when the user asks**, and never twice at once.
- The test suite is the other gate: `python -m unittest discover -s tests -p 'test_*offline*.py'`
  (~1 s).

## Round log

| round | when | what changed | evidence | verdict |
| --- | --- | --- | --- | --- |
| 12 | 2026-09-27 04:30 | **a name is decoded by the client.** `Agent.GetNameByID` now hands the encoded string to the client's decoder (Native's `AsyncGetAgentName` route, `agent_methods.cpp:318-325`) and takes the text from its completion: **~115 ms** first time, **0.09-0.5 ms** cached, against ~2.1 s for the dat route's first name in a slot — and with no dat record at all. The table route stays in the tree for a caller that wants a table entry rendered on the host, and **no member reads it any more**, so the connect-time warm-up is off (it was competing with the decodes for the game thread: target/interact 70 ms -> 32 ms). Three defects fixed: `dialog._on_string_decoded` was taking decodes it did not own (consuming agent names and discarding their text), a disconnect could fail with names in flight (block orphaned), and the client answers only a few decodes at once (32 at once answered none; capped at 8). The owner's timed run: 8974 -> 7955 -> **4018 ms** process-start-to-interact | `1074 tests OK`; `pyright` `0 errors`; `live_reports/find_npc11.txt`, `name_member3.txt`, `name_scheme8.txt`, `perf_live.txt`; hook targets read back clean after every run | landed; cold map-wide sweep still ~2.9 s (levers named) |
| 11 | 2026-09-27 02:30 | **the GW.dat handling left the call path.** The `TextParser` trigger (connect) now calls the source's own enqueue `load_string_table(language_id)`; the load runs on one daemon worker (`_start_warmup`/`_warmup_worker`), the table is parsed in file by file (`_read_slot`, so a name answers as soon as its file has been read), a decode whose entry is missing *asks* for the slot it needs (`_request_slot`) and is served next (`_slot_order`), and `ConnectedClient.close` joins the worker before the block it reads through is released. The two members invented for the on-demand path (`use_string_table_language`, `_ensure_entry_loaded`) are deleted. Nothing is re-read on a map change (the table is the client's language table) | `1073 tests OK` (1.0 s; `WarmupTests` pins the non-blocking enqueue and the requested-slot-first order); scoped `pyright` on 5 files `0 errors`; `docs/STRING_DECODE_PLAN.md` § 10.1 | landed, live timing to measure |
| 10 | 2026-09-27 01:00 | **the owner's catch followed to the line**: the Reforged agent viewer (`Widgets/Coding/Debug/Guild Wars/Agent Info.py`) read member by member -- its rows, its name column (`Agent.GetNameByID`), its encoded column and its string-table state, which is the port's own scheme; `tests/probe_name_scheme.py` added and run live -- **one name alone** (agent 15: type `0x200` gadget, `\x0C6E`, entry 2926, slot 2, "Random Arenas") with native's gadget walk printed beside it (`gadget_name_enc = 0`, `gadget_id = 75`, `gadget_info` size 9524, the record's `name_enc` = the pointer read), six agents put through the port's decoder (Vekk, Dunkoro, Pet - %str1%, Zaishen Chest -- four correct records, two of them through RC4) and through the client's own decoder (native's route, first call: preconditions live, ~130 ms per call, answer empty -- open); **the slot mapping verified live for the first time** (`entries_per_file 1024`, `slot_count 99`, slots 0-7 `start_index == slot*1024`); the ring cost measured (one command per dispatcher hit, ~130 ms per command, ~1.0 s per string file, 0.104 ms cached) | `live_reports/name_scheme.txt`, `live_reports/name_scheme2*` (probe output); `pyright tests/probe_name_scheme.py` 0 errors; the sources' own tables quoted (`maps.h:954`, `agent.h:136`, `payload.py:978-996`, `Agent Info.py:42-90`, `:465-524`) | live: single name walked end to end; client-decode comparison open |
| 9 | 2026-09-26 22:40 | **live verification** (no elevation): `tests/probe_agent_effects_live.py` added — it builds the client's facades over the read-only reader, registers the stand-in as the current client, and runs the ported members unmodified against `Gw.exe` pid 46544; the agent-name walk answered on **all four branches** (player 55 / world agent_infos 26 / NPC 7 / gadget 2), 90 of 93 named records matched an independent read byte for byte, **55 player names decoded** through `Agent.GetNameByID`, the skill timer advanced **+251 ms** over 250 ms; `tests/test_live_agent_effects.py` added for the elevated half (GW.dat decode, the real connection); the runner's default list now includes both plus `tests.test_agent_array`; **one live defect found and fixed** (the view's category lists were empty because `AccAgentContext`'s class cache was never refreshed outside a frame loop); the offline name fixture corrected to the live byte shape | `live_reports/probe_agent_effects_live.txt`; `1070 tests OK`; scoped `pyright` `0 errors`; `docs/RESEARCH.md` carries the observations | live, elevated suite still to run |
| 8 | 2026-09-26 21:40 | `py4gw/effect.py` — Reforged's `Effects` (15 members, 12 working) over Native's `PyEffects` binding over the `GW::effects` walk of the ported `WorldContext.party_effects` array; `py4gw/memory/memory_manager.py` — the whole `PY4GW::MemoryManager` (the skill timer `timeGetTime() + *g_skill_timer_ptr`, the window handle, the version call and the three allocators), reached as `client.memory_manager`; `Agent.IsMartial`/`IsMelee` answer (**`Agent` 143 → 145 of 148**); `Skillbar`'s `get_recharge` closed with the timer; the last port-side helper in `context/agent_array.py` (`_timed`, with the `perf_counter` parameters it fed) removed, so the module's definition inventory now adds nothing over the sources; `Agent.GetProfessionsTexturePaths` classified as the third injected-runtime artifact member; two findings recorded on their members (the alcohol level needs the entry hook → `TARGET_SIDE_WORK.md`; the alcohol time calls a binding member that does not exist) | `1070 tests OK` (1.0 s; +19, incl. `tests/test_effects_offline.py`'s 16); scoped `pyright` on 15 files `0 errors`; the raising set pinned at 3 from `ast`; the definition inventory diff vs the pre-deletion backup adds nothing | landed |
| 7 | 2026-09-26 19:25 | `PyAgent.get_agent_enc_name` ported in `py4gw/agent.py` over native's own `GW::agent::GetAgentEncName` walk (agent record → world agent-name array → player array → NPC → agent-summary gadget entry → gadget context → item array), with `item::GetItemById` added to `py4gw/context/item_context.py`; the three name readers and the five members that called them answer (**8 of the 13 raisers closed**, `Agent` 135 → **143 of 148**); `Player.GetName` restored to the source's body; `AgentEncNameTests` (11 tests) drives every branch of the walk offline, and the raising-set test now pins 5 | `1051 tests OK` (1.0 s); scoped `pyright` on 4 files `0 errors`; the walk's own branches each have a test | landed |
| 6 | 2026-09-26 18:25 | steps 3–4: the invented layer is deleted (2639 → 1569 lines) and the 8 source `snapshot` methods the name-based deletion took with it are restored (AST inventory diff against the backup is clean); both export lists, `examples/all_contexts.py`, the two array test files and `AGENTS.md` step 1 re-pointed; `AGENT_PORT.md`/`CLASS_PORT_MAP.md` rewritten; `Agent`'s 13 raisers re-walked — every cited line verified, 8 direct + 4 transitive + the `RequestName` alias, now pinned by `AgentSourceReferenceTests` (reference audit + raising set from `ast`) | `1041 tests OK` (1.0 s); scoped `pyright` `0 errors`; 148/148 member references verified against the source's own lines; one real off-by-one found and fixed | steps 1–4 done |
| 5 | 2026-09-26 17:05 | steps 1–2: the record chain is the source's own (`Agent.GetAgentByID` → `AgentArray.GetAgentByID` → `client.agent_array.get_context()` → the view); all 13 class getters route through `get_context()`, item/owned-item/gadget names bridged as `AgentArray.py:145` does; the facade's twelve port-side `Get*Array` members, `client.read_agent_array`/`read_agent`/`read_agent_by_id`/`living_snapshot`/`refresh_living_agents`/`get_living_agent` and the context's module-level `get()` all **deleted**; every probe and live suite converted to the source's idiom (`AgentArray.Get*Array` + `Agent.*` fields + `view.GetAgentByID`) | `1042 tests OK` (1.1 s); scoped `pyright` on 11 files `0 errors` (2.5 s), and each converted live file checks clean on its own | steps 1–2 done, step 3 open |
| 4 | 2026-09-26 15:35 | context rebuilt on the source's own logic: `raw_agents` walks the array through the ported `GWArrayView`; `_build_allegiance_cache` is `AgentContext.py:1160-1256` (valid-agents gate, `is_*_type` flags, owned items, the allegiance switch with dead lists); `GetAgentByID` answers from that cache with a recorded divergence where the source reads shared memory; `AgentArrayStruct` no longer touches the snapshot at all; `tests/test_agent_array_offline.py` rewritten to pin the array-driven buckets and the context gate | `1042 tests OK` (0.9 s); scoped `pyright` on 4 files `0 errors` (1.2 s) | done |
| 3 | 2026-09-26 15:00 | `py4gw/agent_array.py` added — every member of Reforged's `AgentArray.py`; package root now exports the class (Reforged `__init__.py:101`), context view at `py4gw.context.AgentArray`; the context's three copied helper groups (`Manipulation`/`Sort`/`Filter`) deleted; `tests/test_agent_array_class_offline.py` added | `1041 tests OK` (0.9 s); scoped `pyright` on 7 touched files `0 errors` (1.2 s) | done |
| 2 | 2026-09-26 14:45 | agent records read through the ported `internals/types.py` (`Vec2f`/`Vec3f`/`GamePos`); `Vec2fStruct`/`GamePositionStruct` gone; every field offset verified against the sources' own comments and native's `static_assert`s | `1032 tests OK`; layout check: `AgentStruct` `0xC4`, `AgentLivingStruct` `0x1C4`, `allegiance` `0x1B5` | done |
| 1 | 2026-09-26 14:20 | invented `AgentAllegiance` deleted (26 call sites in 15 files now read the sources' `Allegiance` with its own member names); `py4gw/internals/types.py` ported (Reforged's `native_src/internals/types.py`) | `1032 tests OK`; scoped `pyright` `0 errors` | done |

## Open items, with their size

| item | where | size |
| --- | --- | --- |
| **module-level `get()` helpers** — no counterpart in Reforged's context modules | 24 `py4gw/context/*.py` modules + their exports | 24 members, ~60 call sites (tests, probes, examples); **needs the owner's decision**: delete and route through `client.*`, or record as the port's accessor divergence |
| `Agent`'s remaining raisers | `py4gw/agent.py` | **3 of 148, and none is portable work**: the frame loop 2 (the port's execution model; `PORTING_RULES.md` forbids a stand-in) and `GetProfessionsTexturePaths` 1 (the injected runtime's own module directory — the third artifact member) |
| `Effects`' remaining members | `py4gw/effect.py` | 3 of 15: `GetAlcoholLevel` (the entry hook, in `TARGET_SIDE_WORK.md`), `GetAlcoholTimeRemaining` (a binding member that does not exist), and the alcohol time it would need |
| frame-loop members | `Agent.enable`, `Agent._invalidate_property_cache`, `AgentArray.enable` | 3 — all three are Reforged's per-frame registration/clearing (`Agent.py:40-60`, `AgentContext.py:1443-1452`), which the port's execution model has no dispatcher for; each names its source lines and the reason |
| package-root exports are uneven | `py4gw/__init__.py` | `AgentArray` is exported (Reforged `__init__.py:101`) but `Agent`, `Dialog`, `Skill`, `Skillbar` and `Effects` are not, though Reforged's own `__init__.py` star-imports each module (`:106-108`). Not this round's business, but it is drift worth settling in one pass |
| whole-repo `pyright` on the current tree | — | never completed (the run was killed); unknown, will be run on request |
| **the client's own decoder (Native's route) answered empty** | `py4gw/ui/async_decode.py` via `tests/probe_name_scheme.py` | 6 strings, all empty, with every precondition live (`validate_async_decode_str_func` resolves, stub placed, TextParser live) and ~130 ms per call. Empty is also the wrapper's own refusal answer, so the next run prints `decode_state(slot)` to tell them apart. If the client really refuses these strings, that is a finding about the strings, not about the port's table decode (four of six names are provably right) |
| live verification of the two new read paths | `tests/test_live_player.py`, a probe | `Agent.GetNameByID`/`Player.GetName` and `Effects` are offline-verified against records; a live client would confirm the client's own buffers decode to real names and that the skill timer matches the client's clock (needs the user and an elevated shell) |

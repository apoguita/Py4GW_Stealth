# What is cached in this library

The owner's rule, and the reason this document exists — stated by the owner on 2026-10-05, verbatim in
substance:

> **We can only cache things that are never supposed to change — the pathing maps, for example, are
> 100% static. Everything read from the client can go stale frame to frame, and we are not in a
> frame-based environment, so we cannot know when a cache went stale.**

So the test is not "is this expensive to read again" but **"can this value ever differ from what was
stored?"** A `gw.dat` pathing map cannot; a record in the running client can, between any two frames,
and nothing here would notice. Before anything else is removed, this is the inventory of what is
actually stored, where it came from, and which kind of thing it is. Nothing here is a proposal to keep
something; it is the list you asked to see so deletions are made with your consent rather than around
you.

## 1. What counts as a cache

> **A cache is state that outlives the call that produced it, so a later call answers from the stored
> result instead of reading again.**

That definition is the test used below. It deliberately excludes three things that look similar:

| Not a cache | Why |
| --- | --- |
| **A resolved address** (a pattern scan's answer) | The client's module never changes inside a session, so nothing is "answered from the past" — the same read would produce the same value. `README.md` allows exactly this: *"cache what the pattern scan produced, because that is stable"*. |
| **A constant table** (an enum, a name table, `_MAP_ID_TO_DAT_FILE_ID`) | Not read from the client at all; it is the sources' own data, built at import. |
| **In-flight bookkeeping** (a pending decode slot) | It holds work that has not finished; it is not an answer served in place of a read. It becomes a cache only if a finished answer is left in it. |

And the four kinds that **are** caches, worst first:

| Kind | What it stores | Status under the rule |
| --- | --- | --- |
| **K2 — live dereferenced state** | Records, array headers, context views, pathing snapshots read out of the running client | **Forbidden twice over**: by your directive, and by `README.md` / `AGENTS.md` / `PORTING_RULES.md` — *"never cache a dereferenced pointer, because that is map-scoped"* |
| **K2b — decoded text** | Strings the client produced (decoded names, decoded dialog text), keyed by the encoded bytes | Same rule; content-addressed keys make it *safe* but it is still a stored answer |
| **K3 — file data keyed by map id** | `gw.dat` contents parsed once per map | Stable per file, but still a stored answer — your call |
| **K4 — the sources' own cache API** | `FfnaMapMethods.ClearCache` / `CacheResult` / `HasDatEntry` exist as *members* in Reforged | Removing the state turns those ported members into no-ops |

## 2. The agent-array cache — what it was, and why it hid a walking character

**What it stored.** `AgentArrayStruct` held two dictionaries: `_agent_by_id` (agent id → a
*materialized* `AgentStruct`) and `_allegiance_cache` (category name → list of ids), both filled by
`_build_allegiance_cache()`. Alongside them, `AgentArray` held `_context_view`: a copy of the client's
`GWArray<Agent*>` **header** (buffer, capacity, size).

**Where it came from.** Reforged's `native_src/context/AgentContext.py` (`_build_allegiance_cache`, the
per-id cache) and `Agent.py`'s four per-frame record caches. In Reforged those are correct because its
injected runtime refreshes them **every frame**: `Agent.enable()` registers
`PyCallback.Register(..., Phase.PreUpdate, self._invalidate_property_cache)`. This port has no frame
loop, and both `enable` and `_invalidate_property_cache` raise for exactly that reason.

**What it did here.** `GetAgentByID` answered `self._agent_by_id.get(agent_id)` whenever the id was
present, with **no freshness test of any kind**. The only thing that rebuilt it was an id that was
*missing*. So the first read of an agent froze that agent's record for the life of the connection.

**Why that mattered.** The stored record is a snapshot — `GWArrayView` materializes it with
`from_buffer_copy` — so every field read straight off it was frozen. Measured live 2026-10-05: a
character walked 500 units in 1.6 s while `Agent.GetXY` answered the same coordinates to the
millimetre, and `Agent.IsMoving` was the only signal that moved — because it converts to a *living*
record, and `GetAsAgentLiving()` re-reads memory at the record's own address
(`context/agent_array.py:470-478`). Three separate conclusions were drawn from that stale read before
it was caught, including "the move did not work" (the move worked; the character arrived within
**0.0013 units** of the goal).

**What replaces it (done, 2026-10-05).**

| member | before | now |
| --- | --- | --- |
| `AgentArrayStruct.GetAgentByID` | serve `_agent_by_id` if present, else build | re-run the traversal from the client's array, answer from that, keep nothing |
| `AgentArrayStruct._ids` | serve `_allegiance_cache` | re-run the traversal, then answer |
| `AgentArray.get_context` / `read_context` | build `_context_view` once, return it | read the header on every call; `_context_view` deleted |
| `AgentArray.reset_cache` | dropped `_context_view` and the view's caches | the source's member, name kept; there is no stored state left to drop, and its docstring says so |

## 3. The inventory

`file:line` as it stands today. "Origin" is **source** when the state comes from Reforged/Reforged
Native (ported deliberately), **this port** when it was introduced here, and **(?) ** where I have not
yet verified whose it is — I would rather mark that than guess.

### K1 — resolved addresses and scan results (allowed by `README.md`)

| where | what |
| --- | --- |
| `memory/memory_manager.py` | the `Scan()` result (the maintained globals) |
| every `context/*_context.py`: `_context_address`, `_base_pointer_address`, `_message_address`, `_buffer_pointer_address`, `_typing_pointer_address`, `_array_address` | the resolver's answer per context |
| `client.py:480` `_ui_message_address`, `dialog.py:543` `_loader_address` | declared function addresses |
| `client.py:364` `_agent_array_cache_contexts_are_valid` | *not* a cache: the validator that decided the K2 cache above was still good — worth naming because it is why a stale answer was served |

### K2 — live dereferenced state (the rule's target)

| where | what it stores | origin | state |
| --- | --- | --- | --- |
| ~~`context/agent_array.py` `_agent_by_id`, `_allegiance_cache`~~ | agent records, category ids | source | **removed** — traversal re-run per call |
| ~~`context/agent_array.py` `_context_view`~~ | the agent-array header | source | **removed** — header read per call |
| ~~`context/map_context.py` `_pathing_maps_cache`, `_pathing_maps_cache_raw`~~ | pathing-map snapshots keyed `(pid, map_id)` | source | **removed** — read per call; `ClearPathingCache` keeps its name with nothing to drop |
| ~~`pathing.py` `AutoPathing.pathing_map_cache`~~ | built navmesh keyed by map group | source | **removed** — `get_navmesh` builds per call (0.027 s for a 3,361-trapezoid map, measured) |
| `dialog.py:1608` `_dialog_buttons` (and the journals at `1738-1743`) | the buttons the client announced for the current dialog; the event journals | source | **present** — this is the client's own announcement (protocol state, not re-readable) |
| `chat.py:389` `_live_history` | announced chat log lines | source | **present** — same: an event store; deleting it deletes the feature |
| `agent.py:108` `_name_cache` | decoded agent names, keyed by the encoded bytes | source's `Agent.py` decode path | **present** — decode result; the client's decoder is language-dependent |
| `item.py:62` `_item_name_map` | decoded item names | source | **present** — as above |
| `internals/string_table.py:128`, `239`, `261`, `262` | decoded text tables and decoded strings | source's `TextParser` cache | **present** — as above |

In-flight bookkeeping (not caches, listed so they are not mistaken for them): `agent.py:112`
`_name_requests`, `item.py:82` `_item_name_requests`, `dialog.py:1675/1680/1719` `_body_decodes` /
`_catalog_decodes` / `_button_decodes` and the two `_pending` maps.

### K3 — file data keyed by map id

| where | what it stores | origin | state |
| --- | --- | --- | --- |
| `ffna_map_methods.py:92-94` `_pathing_cache`, `_spawn_cache`, `_portal_cache` | pathing maps, spawns and portals parsed out of `gw.dat` per map id | source | **present** |

### K4 — the sources' own cache API around K3

`FfnaMapMethods.ClearCache` / `ClearCache(map_id)` / `CacheResult` / `HasDatEntry`
(`ffna_map_methods.py:158-175`) are Reforged's own members whose whole meaning is the K3 dictionaries.
Deleting the dictionaries makes those members no-ops, which the porting rules allow only with a written
justification — so this one is a decision, not a sweep.

### Not caches

`enums_src/*` tables, `skill_names.py`, `frame_names.py`/`frame_aliases.py`/`frame_registry.py`,
`mods_core.py`/`mods_upgrades.py`'s `_EFFECT`/`_TEXT`/`UPGRADE_*`, `listeners.py:57` `PACKET_WORDS`,
`ffna_map_methods.py:644` `_MAP_ID_TO_DAT_FILE_ID` — module-level constants, not read from the client.

## 4. What is left to decide or do

**Done so far (2026-10-05):** every cache of *live client state* that the sweep found — the agent
records, the agent-array header, the pathing-map snapshots and the navmesh — is gone, replaced by a read
taken when the member is asked. Suite **1818 tests OK**, scoped `pyright` **0 errors**.

Still open, in the order the rule takes them:

1. **The decoded-text stores** — `agent.py:108` `_name_cache`, `item.py:62` `_item_name_map`,
   `internals/string_table.py`'s four dictionaries. These hold strings the **client's decoder**
   produced. That decoder follows the client's text language, which a preference can change at
   runtime, so a stored decode is exactly the thing this rule forbids; removing them makes every name
   and dialog string decode again on the call that needs it. The request bookkeeping beside them
   (`_name_requests`, `_item_name_requests`, the `_pending` maps) is in-flight state, not a cache, and
   stays.
2. **The dialog and chat stores** — `dialog._dialog_buttons` plus the journals, `chat._live_history`.
   These are **not caches under the definition above**: the client *announces* them once (a dialog
   opening, a log line) and there is no read that could produce them again. Removing them removes the
   feature. Listed here so the distinction is on the record rather than assumed.
3. **K3/K4 stay** — `FfnaMapMethods`' three dictionaries cache `gw.dat`, which is the owner's own
   example of what may be cached, and the four source members built on them (`ClearCache`,
   `CacheResult`, `HasDatEntry`) keep their meaning. No change proposed.

**The gate for every removal** is the live read-follows-the-client probe
(`tests/probe_agent_reads_live.py`): a read that does not move while the character moves is the failure
it exists to catch.

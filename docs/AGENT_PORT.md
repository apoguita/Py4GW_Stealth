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
| `AgentContext` (`AgentStruct`, `AgentLivingStruct`, `AgentItemStruct`, `AgentGadgetStruct`) | the class's whole read surface | **ported** — `py4gw/context/agent_array.py` (the map's `AgentArray`, 482 lines) with `read_agent` / `read_agent_by_id` |
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
   `GetAgentIDByName`, `GetAgentIDByEncString`, `GetModelIDByEncString`: the three
   `PyAgent.get_agent_enc_name` calls, plus the ported string table and helpers.
4. **The derived members** — profession names and texture paths, conditions and stances, casting and
   target state, item/gadget extras: each one is a member of its own with its own source lines, and
   several read `Skill`/`Utils` (the two `Player` members that do are named in
   [`PLAYER_PORT.md`](PLAYER_PORT.md)); a member that needs one of those records that need in its
   body rather than approximating it.
5. **The verdict**, in the same change that moves the class: it goes into
   [`CLASS_PORT_MAP.md`](CLASS_PORT_MAP.md) §1 as INCOMPLETE until the last member works, with each
   remaining member named here.

## Where the class stands (2026-09-26)

**148 members declared, 134 answer, 14 raise** — 9 directly and 5 through the member they call.
Two dependencies landed after the class did, and each one moved a member: `Utils` gave
`GetEnergyPips`/`GetHealthPips` (`Utils.calculate_energy_pips`/`calculate_health_pips`,
[`UTILS_PORT.md`](UTILS_PORT.md)), and `Skill` (`py4gw/skill.py`, [`SKILL_PORT.md`](SKILL_PORT.md))
removed the other half of `IsMartial`/`IsMelee`'s block — `Skill.GetID("Illusionary_Weaponry")`
answers `33` now, so those two members wait on `Effects.HasEffect` alone. The remaining list is the
one in [`CLASS_PORT_MAP.md`](CLASS_PORT_MAP.md) §1: the `PyAgent.get_agent_enc_name` binding (3
direct, 5 transitive), `Effects.HasEffect` (2 — `IsMartial`, `IsMelee`),
`PySystem.Console.get_projects_path` (1 — `GetProfessionsTexturePaths`), `UIManager.GetFPSLimit`
(1 — `GetInstanceUptime`, which `Player.GetInstanceUptime` delegates to), plus the two frame-loop
members.

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

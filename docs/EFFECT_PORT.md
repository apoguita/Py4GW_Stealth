# Effect port (`Effect.py` / the `PyEffects` binding)

**Sources.** Reforged's `Py4GWCoreLib/Effect.py` — 176 lines, `class Effects` at line 5, **15**
`@staticmethod`s — and the binding every member of it calls: Native's
`src/GW/effects/effects_bindings.cpp` (`PYBIND11_EMBEDDED_MODULE(PyEffects, m)`, lines 34-184), over
`src/GW/effects/effects_methods.cpp` (the `GW::effects` walk, lines 29-72) and the records
`Context::Effect` / `Context::Buff` / `Context::AgentEffects` (`include/GW/context/skill.h:124-152`).
`stubs/PyEffects.pyi` is the same surface in stub form.

**Where it lives here.** `py4gw/effect.py` carries all three layers in the source's own order — the
two value snapshots (`EffectType`, `BuffType`), the binding class (`PyEffects`) with its module-level
twins, and Reforged's `Effects` class over them — because that is where Reforged puts them: its
`Effect.py` is 176 lines of `PyEffects.PyEffects(agent_id).Something()`, and native's `PyEffects` is
one embedded module. `py4gw/memory/memory_manager.py` carries the timer the snapshots need.

**Verdict: INCOMPLETE.** **12 of the 15 members work.** The three that do not are named below, and
two of them are findings rather than outstanding porting.

| Member | State |
| --- | --- |
| `get_instance` | works — returns the port's `PyEffects(agent_id)`, which is native's own wrapper (`PyEffectsWrapper { uint32_t agent_id; }`, `effects_bindings.cpp:130`) |
| `GetBuffs`, `GetEffects`, `GetBuffCount`, `GetEffectCount`, `BuffExists`, `EffectExists`, `HasEffect`, `EffectAttributeLevel`, `GetEffectTimeRemaining`, `GetBuffID` | work — the array walk and the two computed times |
| `DropBuff` | works — a one-word call to `effects.drop_buff_func`, gated on the resolver the way native gates on `g_drop_buff_func` |
| `ApplyDrunkEffect` | works — a two-word call to `effects.post_process_effect_func` |
| `GetAlcoholLevel` | **raises, naming target-side work**: native's number is the `intensity` argument of the client's post-process call, captured by the entry hook it installs (`effects.cpp:24-41`, `g_alcohol_level`). Entry on [`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md) |
| `GetAlcoholTimeRemaining` | **raises, naming a source-vs-source disagreement**: the body calls `PyEffects.PyEffects.GetAlcoholTimeRemaining()`, and **the binding implements no such member** (`effects_bindings.cpp:181-183` has `GetAlcoholLevel` and `ApplyDrunkEffect` only). The stub declares it (`PyEffects.pyi:41`), and native tracks no alcohol *time* anywhere — `g_alcohol_level` is a bare word with no companion timestamp |

## The walk, and why the port is a read

```text
Effects.GetEffects(agent_id)
  → PyEffects(agent_id).GetEffects()
    → GW::effects::GetAgentEffects(agent_id)                       effects_methods.cpp:47-50
      → GetAgentEffectsArray(agent_id)                             effects_methods.cpp:29-41
        → Context::GetPartyEffectsArray()   = world->party_effects  world.h:290
          scan for agent_effect.agent_id == agent_id
      → effects->effects.valid() ? &effects->effects : nullptr
    → per record: the six fields, plus                                    effects_bindings.cpp:100-109
        time_elapsed   = GetSkillTimer() - timestamp                      skill.cpp:39-41
        time_remaining = (DWORD)(duration * 1000.0f) - time_elapsed       skill.cpp:43-45
```

Every step is something this port already had except the timer: `world->party_effects` is
`WorldContextStruct.party_effects` (`py4gw/context/world_context.py`), whose `AgentEffectsStruct`
carries the `buff_array`/`effect_array` sub-arrays with native's own layout (`AgentEffects` 0x24,
`Effect` 0x18, `Buff` 0x10 — all three `static_assert`s matched). No call, no hook, no write.

## The three things that are not the array walk

1. **The skill timer — ported, and it had two other claimants.**
   `PY4GW::MemoryManager::GetSkillTimer()` is `timeGetTime() + *g_skill_timer_ptr`
   (`memory_manager.cpp:69-71`): a host `winmm` call plus a client global the catalog already names
   (`memory.skill_timer_ptr`, `offsets/memory.json:48-57`). It is ported as
   `py4gw/memory/memory_manager.py` — the whole `PY4GW::MemoryManager` surface, since that is the
   class the member belongs to — and reached as `client.memory_manager`. Closing it also closed
   **`Skillbar.SkillbarSkill.get_recharge`**, which had been raising with that exact requirement in
   its message, and the `EffectType.time_elapsed`/`time_remaining` fields here.
2. **`DropBuff` and `ApplyDrunkEffect` are calls**, the two the sources make into the client:
   `g_drop_buff_func(buff_id)` (`effects_methods.cpp:65-72`) and
   `g_post_process_effect_original(intensity, tint)` (`:23-27`). Both resolvers are in the catalog
   (`offsets/effects.json`), and both are issued through the existing call machinery with the forms
   the sources declare — `U32` and `U32_U32`. Where native calls the *original* pointer its own hook
   saved, this port calls the client's code at the resolved address: there is no hook here to save a
   pointer from, and it is the same target.
3. **`GetAlcoholLevel` is a hook capture, not a read.** `OnPostProcessEffect` stores its first
   argument into `g_alcohol_level` (`effects.cpp:32-41`), which means the number exists only while
   the client is calling that function and only for a controller watching it. `ApplyDrunkEffect`'s
   sibling call needs no hook; the level does. That is the entry on
   [`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md).

## What it closed

| Member elsewhere | How |
| --- | --- |
| `Agent.IsMartial` | `Effects.HasEffect(agent_id, Skill.GetID("Illusionary_Weaponry"))` (`Agent.py:1344-1347`) — **ported 2026-09-26**, so `Agent` is 145 of 148 |
| `Agent.IsMelee` | the same check with the melee weapon list (`Agent.py:1384-1387`) |
| `Skillbar.SkillbarSkill.get_recharge` | `recharge - PY4GW::MemoryManager::GetSkillTimer()` (`skill.cpp:20-25`) |

## Divergences and findings, all recorded on the member

- **The alcohol time that does not exist.** `Effects.GetAlcoholTimeRemaining` calls a binding member
  the binding does not implement. The member raises and names both files rather than inventing a
  clock.
- **`GetBuffID`'s docstring disagrees with its body**: the docstring says `-1` for "not found", the
  body returns `0` (`Effect.py:139-149`). The body is ported.
- **The value snapshots are `dataclass`es, not pybind objects.** Native's `EffectType`/`BuffType` are
  read-only pybind classes (`def_readonly`); the port's are frozen-shape dataclasses with the same
  field names and order, so attribute reads — and the `isinstance` checks Reforged's `BuffStruct.py`
  makes against those names — behave the same. Nothing in either source mutates one.

## Evidence

`tests/test_effects_offline.py` — **16 tests**, all offline: the counts and both `*Exists` walks, the
two computed times (including the `DWORD` wrap), `HasEffect`'s short-circuit, the two scanning
members, `GetBuffID`, `get_instance`, a missing world context, the two calls with their
resolver-gating and their exact argument words, and the two alcohol members' messages. The fixture's
records are real `EffectStruct`/`BuffStruct` instances, so the offsets are exercised too.
`Agent`'s side is in `tests/test_agent_offline.py` (`AgentMartialTests`, 3 tests), and the skillbar's
in `tests/test_skillbar_offline.py` (`test_the_slot_recharge_is_the_source_s_subtraction`).

**Live (2026-09-26).** `tests/probe_agent_effects_live.py` read the walk's source array against a
running client without elevation: `party_effects_array` was **null** at the time
(`buffer=0x0, size=0, capacity=0`), so the character had no effect or buff running and every member
correctly answered empty/`0`/`False` — a real answer, not a failure, and the suite
(`tests/test_live_agent_effects.py`) compares block for block when blocks exist and skips with that
reason when they do not. Both of the class's calls resolve on this build
(`effects.drop_buff_func`, `effects.post_process_effect_func`), and neither is issued by the suite:
dropping a buff and driving the drunk post-process are game actions. The skill timer the snapshot
depends on was live and advancing (`+251 ms` over a 250 ms sleep) — see
[`RESEARCH.md`](RESEARCH.md).

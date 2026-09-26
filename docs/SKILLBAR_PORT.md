# Skillbar port

**Source:** `Py4GWCoreLib/Skillbar.py` — 209 lines, `class SkillBar` at line 5 with **18**
`@staticmethod`s. Ported as `py4gw/skillbar.py`, over native's binding object
(`skillbar_bindings.cpp:25-142`, bound as `PySkillbar.Skillbar`, with `PySkillbar.SkillbarSkill`
beside it) and the client state those members read.

**Verdict: INCOMPLETE.** **12 of the 18 members work** — every read — plus
`ChangeHeroSecondary`, the one action whose mechanism this port already has. **6 members raise**, and
each names what it needs:

| Member | What it needs |
| --- | --- |
| `UseSkill`, `UseSkillTargetless`, `HeroUseSkill` | the client's **control actions**: native's `ui::Keypress` (`ui_methods.cpp:1408-1426`) is a `kKeyDown` frame message carrying a `KeyAction` payload, then a game-thread `kKeyUp` — and `UseSkill` targets first (`skillbar_methods.cpp:439-443`). The catalog has the frame-message function and the port has the UI-message form; what is missing is the control-action values, the button-action frame and the key pairing. Registered on [`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md). |
| `LoadSkillTemplate`, `LoadHeroSkillTemplate` | native's `DecodeSkillTemplate` and the profession/attribute gating (`skillbar_methods.cpp:230-411`), which stand in front of the three functions this project already resolves (`skillbar.load_skills_func`, `load_attributes_func`, `change_secondary_func`). Pure porting work, no target-side piece. |
| `SkillbarSkill.get_recharge` | `MemoryManager::GetSkillTimer` (`memory_manager.cpp:69-71`) = `timeGetTime() + *g_skill_timer_ptr` — the client global the catalog names `memory.skill_timer_ptr`, plus a host `timeGetTime()`. The same timer is what `Effect.GetTimeElapsed`/`GetTimeRemaining` need, so it lands with that class. |

## What each read is, in the source's own terms

| Read | Native | Port |
| --- | --- | --- |
| the snapshot | `GetContext()`: the map gate, then `GetPlayerSkillbar()` (`skillbar_bindings.cpp:30-42`, `skillbar_methods.cpp:467-476`) | the ported `Map.IsMapReady()` gate, then the ported `WorldContext.party_skillbar_array` walked for the controlled character's agent id |
| `GetSkillbar`, `GetZeroFilledSkillbar`, `GetSkillIDBySlot`, `GetSlotBySkillID`, `GetSkillData` | eight slots, ``skill.id.id`` (`Skillbar.py:28-146`) | the same loops over the ported `SkillbarStruct`, with `SkillID` from the `Skill` port so `.id.id` and `.id.GetName()` work |
| `GetAgentID`, `GetDisabled`, `GetCasting` | `data.agent_id`, `data.disabled`, `data.casting` (`skillbar_bindings.cpp:170-172`) | the record's own words; `casting` is native's `0xB0` word, which the ported record carries as the queued-cast array's size |
| `GetHeroSkillbar` | `GetHeroSkillbar(hero_index)` (`skillbar_methods.cpp:478-488`) | the same walk for `agent::GetHeroAgentID`, which is the ported `Party.Heroes.GetHeroAgentIDByPartyPosition`, and the same `> 7` refusal |
| `GetHoveredSkillID` | `GetHoveredSkill()` (`skillbar_bindings.cpp:130-133`, `skillbar_methods.cpp:490-496`) | the ported tooltip read (`py4gw/ui/tooltip.py`), the same `payload_len == 0x14` guard, and the skill record's own `skill_id` |
| `IsSkillUnlocked` | the account context's `unlocked_account_skills` bitset (`skillbar_methods.cpp:546-558`) | the ported account context's `is_account_skill_unlocked` |
| `IsSkillLearnt` | the world context's `unlocked_character_skills` bitset (`skillbar_methods.cpp:560-570`) | the same word/bit test over the ported world context's array |
| `ChangeHeroSecondary` | `ChangeSecondProfession(profession, hero_index)` → `g_change_secondary_func(agent_id, profession)` (`skillbar_methods.cpp:85-93`) | the same call through the catalog's `skillbar.change_secondary_func` resolver, after the same «no agent id, no call» guard |

## The one divergence, and it is a tooltip

Native's `GetCurrentTooltip` dereferences twice through a global it declares `TooltipInfo***`
(`ui_methods.cpp:2658-2661`, `ui_patterns.cpp:17`). **On this build that global holds the tooltip
pointer directly**, so the port reads it once — and this is measured, not inferred:

1. the client's own code compares the global's value against a tooltip record pointer
   (`cmp edi, [0x00C15050]` at `0x00653A23`, where the same function indexes `edi` at `+0x54`);
2. the client stores a record pointer into it and clears it the same way
   (`mov [0x00C15050], edi` at `0x00653A93`; `mov dword ptr [0x00C15050], 0` at `0x006537D3`, the
   clear `ui.cpp:973` performs);
3. read **live**, through this project's own resolver on the running client, the global's value was a
   plausible heap pointer whose record carried `payload_len` at the struct's own offset `+0xC` (the
   value was `0xC` — not the `0x14` a skill tooltip carries, so the record and the offset both check
   out).

Under native's typing the extra dereference would read the record's `bit_field` word as a pointer —
`0` on this client — so the source's expression would answer "no tooltip" for a tooltip that exists.
The port reproduces the reading the client performs; the difference is recorded here and in
`py4gw/ui/tooltip.py`'s own docstring. This is the kind of claim the project's authority order puts
the client's behaviour first for, and the evidence is above rather than asserted.

## What it unblocked

`Utils.GenerateSkillbarTemplate` — the last offline-portable dependency `Utils` had. The member is now
the source's own body (`Utils.py:622-665`), with one recorded route difference: the source reads the
skill ids through `GLOBAL_CACHE.SkillBar.GetSkillIDBySlot`, a mirror layer this project does not port
(`docs/WRAPPER_MIGRATION_ASSESSMENT.md`), and the port calls the class the mirror mirrors — the two
bodies are the same line, `PySkillbar.Skillbar().GetSkill(slot).id.id`
(`GlobalCache/SkillbarCache.py:21-22` and `Skillbar.py:110-119`). The value is the source's; what
changes is which of the two identical call sites is reached, and it is written on the member.

## Verification

- `tests/test_skillbar_offline.py` — **20 offline tests**: the 18 source member names in the source's
  order, read out of `Skillbar.py` at test time; native's bound surface on both binding types; the
  slot arithmetic and the eight-slot walks; native's own edges (a slot outside `1..8` refused, a hero
  index above `7` answering an empty list, a non-skill tooltip not reading its payload); both skill
  bitsets including the past-the-end case; `ChangeHeroSecondary`'s arguments and its
  no-agent-id guard; and the six raising members naming their work.
- `tests/test_utils_offline.py` — `GenerateSkillbarTemplate` is driven through its four reads and the
  template is compared against `encode_skill_template` for the same inputs, including the source's own
  two details (an attribute at level `0` is left out; a `None` profession becomes `0`), plus the
  source's `except` branch answering `""`.
- No live run is needed for this change: every implemented member is a context read, and the tooltip
  chain it depends on was checked against the running client with a read-only scanner.
